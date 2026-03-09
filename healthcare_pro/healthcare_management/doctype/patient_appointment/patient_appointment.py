# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_time, nowdate, nowtime
from datetime import datetime, timedelta

# Google Calendar Integration
import requests


class PatientAppointment(Document):

    # ==========================
    # MAIN VALIDATION PIPELINE
    # ==========================

    def validate(self):
        self.set_datetime_fields()
        self.validate_datetime()
        self.validate_double_booking()
        self.check_global_holiday()
        self.check_practitioner_leave()
        self.check_practitioner_schedule()
        self.update_status_to_scheduled()

    def on_submit(self):
        self.check_practitioner_leave()
        self.create_google_event()

    def on_update(self):
        if self.has_value_changed("status") and self.status == "Cancelled":
            self.delete_google_event()
            self.promote_waitlist()
        else:
            self.update_google_event()

    # ==========================
    # DATETIME AUTO GENERATION
    # ==========================

    def set_datetime_fields(self):
        appointment_datetime = datetime.combine(
            getdate(self.date),
            get_time(self.time)
        )

        self.start_datetime = appointment_datetime
        self.end_datetime = appointment_datetime + timedelta(hours=1)

    # ==========================
    # DATE VALIDATION
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
    # DOUBLE BOOKING VALIDATION
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
                    _("This practitioner already has an appointment within this time. You have been added to the waitlist."),
                    title=_("Time Slot Conflict"),
                )

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
            frappe.throw(_("Patient already has another appointment at this exact time."))

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
    # PRACTITIONER SCHEDULE CHECK
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
            fields=["from_time", "to_time", "day"],
        )

        if not schedule_slots:
            frappe.throw(
                _("Practitioner {0} does not have a scheduled working day on {1}. Working days are: {2}.")
                .format(self.practitioner, appointment_day,)
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
                _("Appointment time {0} is outside practitioner's scheduled working hours. working hours are on {1} are from {2} to {3}.")
                .format(self.time, appointment_day, schedule_slots[0].from_time, schedule_slots[0].to_time)
            )

    # ==========================
    # STATUS MANAGEMENT
    # ==========================

    def update_status_to_scheduled(self):
        if self.status == "Open":
            self.status = "Scheduled"

    # ==========================
    # GOOGLE CALENDAR INTEGRATION
    # ==========================

    def create_google_event(self):
        try:
            if self.google_event_id:
                return

            access_token = frappe.db.get_single_value("Google Settings", "access_token")

            if not access_token:
                frappe.log_error("Google not authenticated", "Google Sync")
                return

            url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            event = {
                "summary": f"Appointment: {self.patient}",
                "description": f"Practitioner: {self.practitioner}",
                "start": {
                    "dateTime": self.start_datetime.isoformat(),
                    "timeZone": "Africa/Nairobi"
                },
                "end": {
                    "dateTime": self.end_datetime.isoformat(),
                    "timeZone": "Africa/Nairobi"
                }
            }

            response = requests.post(url, json=event, headers=headers)

            if response.status_code == 200:
                event_data = response.json()
                self.db_set("google_event_id", event_data.get("id"))
                self.db_set("synced_to_google", 1)
            else:
                frappe.log_error(response.text, "Google Event Creation Failed")

        except Exception:
            frappe.log_error(frappe.get_traceback(), "Google Sync Failed")

    def update_google_event(self):
        if not self.google_event_id:
            return

        try:
            access_token = frappe.db.get_single_value("Google Settings", "access_token")

            url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{self.google_event_id}"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            event = {
                "summary": f"Appointment: {self.patient}",
                "description": f"Practitioner: {self.practitioner}",
                "start": {
                    "dateTime": self.start_datetime.isoformat(),
                    "timeZone": "Africa/Nairobi"
                },
                "end": {
                    "dateTime": self.end_datetime.isoformat(),
                    "timeZone": "Africa/Nairobi"
                }
            }

            requests.put(url, json=event, headers=headers)

        except Exception:
            frappe.log_error(frappe.get_traceback(), "Google Update Failed")

    def delete_google_event(self):
        if not self.google_event_id:
            return

        try:
            access_token = frappe.db.get_single_value("Google Settings", "access_token")

            url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{self.google_event_id}"

            headers = {
                "Authorization": f"Bearer {access_token}",
            }

            requests.delete(url, headers=headers)
            self.db_set("synced_to_google", 0)

        except Exception:
            frappe.log_error(frappe.get_traceback(), "Google Delete Failed")

@frappe.whitelist()
def cancel_appointment(appointment):
    doc = frappe.get_doc("Patient Appointment", appointment)
    doc.status = "Cancelled"
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return True