# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_time, nowdate, nowtime


class MedicalRecord(Document):
    @frappe.whitelist()
    def set_appointment_details(self):
        if self.appointment:
            appointment_doc = frappe.get_doc("Patient Appointment", self.appointment)
            self.patient = appointment_doc.patient
            self.practitioner = appointment_doc.practitioner
           
            
    def validate(self):
        if self.appointment and not self.patient:
            self.set_appointment_details()

        self.check_appointment_date()

    def check_appointment_date(self):
        if self.appointment and self.date:
            #Fetch the date from the linked Patient Appointment
            appointment_date = frappe.db.get_value("Patient Appointment", self.appointment, "date")
            
            # Compare dates using getdate to ensure they are the same format
            if getdate(self.date) < getdate(appointment_date):
                frappe.throw(("Medical Record date ({0}) cannot be earlier than the Appointment date ({1})")
                             .format(self.date, appointment_date), title=("Invalid Date" ))

    def on_submit(self):
        if self.appointment:
            frappe.db.set_value("Patient Appointment", self.appointment, "status", "Completed")
            frappe.msgprint(("Linked Appointment {0} has been marked as Completed.").format(self.appointment), title=("Appointment Updated"))

