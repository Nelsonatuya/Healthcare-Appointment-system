# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_time, nowdate, nowtime


class PatientAppointment(Document):

    # ==========================
    # MAIN VALIDATION PIPELINE
    # ==========================

    def validate(self):
        self.validate_datetime()
        self.validate_double_booking()
        self.check_practitioner_leave()
        self.check_practitioner_schedule()
        self.update_status_to_scheduled()

    def on_submit(self):
        self.check_practitioner_leave()

    def on_update(self):
        # Only trigger when status changes to Cancelled
        if self.has_value_changed("status") and self.status == "Cancelled":
            self.promote_waitlist()

    # ==========================
    # DATE & TIME VALIDATION
    # ==========================

    def validate_datetime(self):
        if getdate(self.date) < getdate(nowdate()):
            frappe.throw(
                _("You cannot schedule an appointment for a past date."),
                title=_("Invalid Date Error")
            )

        # Prevent past time if booking for today
        if getdate(self.date) == getdate(nowdate()):
            if get_time(self.time) < get_time(nowtime()):
                frappe.throw(_("The appointment time has already passed for today."))

    # ==========================
    # DOUBLE BOOKING VALIDATION
    # ==========================

    @frappe.whitelist()
    def validate_double_booking(self):
        # Check practitioner conflict
        practitioner_conflict = frappe.db.exists(
            "Patient Appointment",
            {
                "practitioner": self.practitioner,
                "date": self.date,
                "time": self.time,
                "name": ["!=", self.name],
                "status": ["not in", ["Cancelled"]],
            },
        )

        if practitioner_conflict:
            # Check if already waitlisted (avoid duplicates)
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
                wait_doc = frappe.get_doc(
                    {
                        "doctype": "Appointment Waitlist",
                        "patient": self.patient,
                        "practitioner": self.practitioner,
                        "date": self.date,
                        "time": self.time,
                        "status": "Waiting",
                    }
                )
                wait_doc.insert(ignore_permissions=True)
                frappe.db.commit()

            frappe.msgprint(
                _("Practitioner already booked. Patient has been added to waitlist."),
                alert=True,
            )

            # Stop saving this appointment
            frappe.throw(_("The doctor is already booked at this time. You have been added to the waitlist."), title=_(" Booking Error"))

        # Check patient conflict (still block this)
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
                _("Patient {0} already has another appointment at this time.")
                .format(self.patient)
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
                _("Practitioner {0} does not have a scheduled working day on {1}.Working days are: {2}")
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
                _("Appointment time {0} is outside practitioner's scheduled working hours on {1}. [Working hours: {2} - {3}].")
                .format(self.time, appointment_day, schedule_slots[0].from_time, schedule_slots[0].to_time)
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
    # WAITLIST PROMOTION LOGIC
    # ==========================

    def promote_waitlist(self):
        """Promote earliest waitlisted patient for this exact slot."""

        # Prevent recursive calls
        if frappe.flags.in_waitlist_promotion:
            return

        frappe.flags.in_waitlist_promotion = True

        try:
            # Get earliest waitlisted patient for SAME practitioner + date + time
            waitlisted = frappe.get_all(
                "Appointment Waitlist",
                filters={
                    "practitioner": self.practitioner,
                    "date": self.date,
                    "time": self.time,
                    "status": "Waiting",
                },
                order_by="creation asc",
                limit=1,
            )

            if not waitlisted:
                return

            wait_doc = frappe.get_doc("Appointment Waitlist", waitlisted[0].name)

            # Re-check slot availability (race-condition safety)
            slot_taken = frappe.db.exists(
                "Patient Appointment",
                {
                    "practitioner": self.practitioner,
                    "date": self.date,
                    "time": self.time,
                    "status": ["not in", ["Cancelled"]],
                },
            )

            if slot_taken:
                return

            # Create new scheduled appointment
            new_appointment = frappe.get_doc(
                {
                    "doctype": "Patient Appointment",
                    "patient": wait_doc.patient,
                    "practitioner": self.practitioner,
                    "date": self.date,
                    "time": self.time,
                    "status": "Scheduled",
                }
            )

            new_appointment.insert(ignore_permissions=True)

            # Update waitlist status
            wait_doc.status = "Converted"
            wait_doc.save(ignore_permissions=True)

            # Notify patient
            self.notify_waitlisted_patient(wait_doc.patient, new_appointment.name)

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