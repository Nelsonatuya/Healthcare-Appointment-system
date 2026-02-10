# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_time, nowdate, nowtime

class PatientAppointment(Document):
    def validate(self):
        self.validate_double_booking()
        self.validate_datetime()

    def validate_datetime(self):
        # 1. Prevent Past Dates
        if getdate(self.date) < getdate(nowdate()):
            frappe.throw(_("You cannot schedule an appointment for a past date."), Title=_("Invalid Date"))

        # 2. Prevent Past Times (if the date is today)
        if getdate(self.date) == getdate(nowdate()):
            if get_time(self.time) < get_time(nowtime()):
                frappe.throw(_("The appointment time has already passed for today."))

    # 1. Check if the Doctor is busy
    def validate_double_booking(self): 
        conflict = frappe.db.exists("Patient Appointment", {
            "practitioner": self.practitioner,
            "date": self.date,
            "time": self.time,
            "name": ["!=", self.name], # Don't conflict with itself when editing
            "status": ["not in", ["Cancelled"]]
        })

        if conflict:
            frappe.throw(_("Conflict: Practitioner {0} is already booked at {1} on {2}")
                .format(self.practitioner, self.time, self.date))

        # 2. Check if the Patient already has an appointment then too
        patient_conflict = frappe.db.exists("Patient Appointment", {
            "patient": self.patient,
            "date": self.date,
            "time": self.time,
            "name": ["!=", self.name],
            "status": ["not in", ["Cancelled"]]
        })

        if patient_conflict:
            frappe.throw(_("Patient {0} already has another appointment at this time.")
                .format(self.patient))