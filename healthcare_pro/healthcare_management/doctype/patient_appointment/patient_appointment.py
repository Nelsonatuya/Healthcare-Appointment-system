# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_time, nowdate, nowtime
from datetime import datetime, timedelta


class PatientAppointment(Document):

    # ==========================
    # MAIN VALIDATION PIPELINE
    # ==========================

    def validate(self):
        self.validate_datetime()
        self.validate_double_booking()
        self.check_global_holiday()  
        self.check_practitioner_leave()
        self.check_practitioner_schedule()
        self.update_status_to_scheduled()

    def on_submit(self):
        self.check_practitioner_leave()

    def on_update(self):
        if self.has_value_changed("status") and self.status == "Cancelled":
            self.promote_waitlist()

    # ==========================
    # DATE & TIME VALIDATION
    # ==========================

    def validate_datetime(self):
        if getdate(self.date) < getdate(nowdate()):
            frappe.throw(
                _("You cannot schedule an appointment for a past date."),
                title=_("Invalid Date Error"),
            )

        if getdate(self.date) == getdate(nowdate()):
            if get_time(self.time) < get_time(nowtime()):
                frappe.throw(_("The appointment time has already passed for today."))

    # ==========================
    # 1-HOUR OVERLAP VALIDATION
    # ==========================

    def validate_double_booking(self):

        appointment_datetime = datetime.combine(
            getdate(self.date),
            get_time(self.time)
        )

        one_hour_before = appointment_datetime - timedelta(hours=1)
        one_hour_after = appointment_datetime + timedelta(hours=1)

        existing_appointments = frappe.get_all(
            "Patient Appointment",
            filters={
                "practitioner": self.practitioner,
                "date": self.date,
                "name": ["!=", self.name],
                "status": ["not in", ["Cancelled"]],
            },
            fields=["name", "time"],
        )

        for appt in existing_appointments:
            existing_datetime = datetime.combine(
                getdate(self.date),
                get_time(appt.time)
            )

            if one_hour_before < existing_datetime < one_hour_after:

                # Add to waitlist if not already added
                existing_wait = frappe.db.exists(
                    "Appointment Waitlist",
                    {
                        "patient": self.patient,
                        "practitioner": self.practitioner,
                        "date": self.date,
                        "time": self.time,
                        "status": "Waiting",
                    },
                )

                if not existing_wait:
                    wait_doc = frappe.get_doc({
                        "doctype": "Appointment Waitlist",
                        "patient": self.patient,
                        "practitioner": self.practitioner,
                        "date": self.date,
                        "time": self.time,
                        "status": "Waiting",
                    })
                    wait_doc.insert(ignore_permissions=True)
                    frappe.db.commit()

                frappe.throw(
                    _("This practitioner already has an appointment within  this time. You have been added to the waitlist."),
                    title=_("Time Slot Conflict"),
                )

        # ==========================
        # Patient self-conflict check
        # ==========================

        patient_conflict = frappe.db.exists(
            "Patient Appointment",
            {
                "patient": self.patient,
                "date": self.date,
                "time": self.time,
                "name": ["!=", self.name],
                "status": ["not in", ["Cancelled"]],
            },
        )

        if patient_conflict:
            frappe.throw(
                _("Patient already has another appointment at this exact time.")
            )

    # ==========================
    # PRACTITIONER LEAVE CHECK
    # ==========================

    def check_practitioner_leave(self):

        leave_name = frappe.db.exists(
            "Practitioner Leave",
            {
                "practitioner": self.practitioner,
                "from_date": ["<=", self.date],
                "to_date": [">=", self.date],
                "docstatus": 1,
            },
        )

        if leave_name:
            reason = frappe.db.get_value("Practitioner Leave", leave_name, "reason")

            msg = _("Practitioner {0} is on leave on {1}.").format(
                self.practitioner, self.date
            )

            if reason:
                msg += _(" Reason: {0}").format(reason)

            frappe.throw(msg, title=_("Practitioner Unavailable"))


    # ==========================
    # HOLIDAY CHECK
    # ==========================        
    def check_global_holiday(self):

        holiday = frappe.db.exists(
            "Healthcare Holiday",
            {
                "holiday_date": self.date
            }
        )

        if holiday:
            holiday_name = frappe.db.get_value(
                "Healthcare Holiday",
                holiday,
                "holiday_name"
            )

            frappe.throw(
                _("Appointments cannot be scheduled on {0} ({1}).")
                .format(self.date, holiday_name),
                title=_("Public Holiday")
            )

    # ==========================
    # PRACTITIONER WORKING HOURS
    # ==========================

    def check_practitioner_schedule(self):

        appointment_day = getdate(self.date).strftime("%A")

        schedule_slots = frappe.get_all(
            "Schedule Slot",
            filters={
                "parent": self.practitioner,
                "parenttype": "Healthcare Practitioner",
                "parentfield": "table_locw",
                "day": appointment_day,
            },
            fields=["from_time", "to_time"],
        )

        if not schedule_slots:
            frappe.throw(
                _("Practitioner {0} does not have a scheduled working day on {1}. Working days are: {2}")
                .format(self.practitioner, appointment_day, self.get_working_days())
            )

        appointment_time = get_time(self.time)
        is_within_schedule = False

        for slot in schedule_slots:
            from_time = get_time(slot.from_time)
            to_time = get_time(slot.to_time)

            if from_time <= appointment_time <= to_time:
                is_within_schedule = True
                break

        if not is_within_schedule:
            frappe.throw(
                _("Appointment time {0} is outside practitioner's scheduled working hours.")
                .format(self.time)
            )

    def get_working_days(self):
        working_days = frappe.get_all(
            "Schedule Slot",
            filters={
                "parent": self.practitioner,
                "parenttype": "Healthcare Practitioner",
                "parentfield": "table_locw",
            },
            fields=["day"],
            distinct=True
        )
        return ", ".join([day.day for day in working_days])

    # ==========================
    # STATUS MANAGEMENT
    # ==========================

    def update_status_to_scheduled(self):
        if self.status == "Open":
            self.status = "Scheduled"

    # ==========================
    # WAITLIST PROMOTION
    # ==========================

    def promote_waitlist(self):

        if frappe.flags.in_waitlist_promotion:
            return

        frappe.flags.in_waitlist_promotion = True

        try:
            waitlisted = frappe.get_all(
                "Appointment Waitlist",
                filters={
                    "practitioner": self.practitioner,
                    "date": self.date,
                    "status": "Waiting",
                },
                order_by="creation asc",
                limit=1,
            )

            if not waitlisted:
                return

            wait_doc = frappe.get_doc("Appointment Waitlist", waitlisted[0].name)

            # Check 1-hour conflict before promoting
            temp_doc = frappe.get_doc({
                "doctype": "Patient Appointment",
                "patient": wait_doc.patient,
                "practitioner": self.practitioner,
                "date": self.date,
                "time": wait_doc.time,
                "status": "Scheduled",
            })

            temp_doc.validate_double_booking()

            temp_doc.insert(ignore_permissions=True)

            wait_doc.status = "Converted"
            wait_doc.save(ignore_permissions=True)

            self.notify_waitlisted_patient(wait_doc.patient, temp_doc.name)

            frappe.db.commit()

        finally:
            frappe.flags.in_waitlist_promotion = False

    # ==========================
    # NOTIFICATION
    # ==========================

    def notify_waitlisted_patient(self, patient, appointment_name):

        patient_doc = frappe.get_doc("Healthcare Patient", patient)

        if patient_doc.email:
            frappe.sendmail(
                recipients=[patient_doc.email],
                subject="Appointment Scheduled from Waitlist",
                message=f"""
                Good news!

                A slot became available and your appointment has been scheduled.

                Appointment ID: {appointment_name}
                Date: {self.date}
                Time: {self.time}

                Please contact the clinic if you need to reschedule.
                """,
            )


@frappe.whitelist()
def cancel_appointment(appointment):
    doc = frappe.get_doc("Patient Appointment", appointment)
    doc.status = "Cancelled"
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return True