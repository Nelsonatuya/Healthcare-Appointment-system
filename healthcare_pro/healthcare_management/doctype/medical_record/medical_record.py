# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MedicalRecord(Document):
    @frappe.whitelist()
    def set_appointment_details(self):
        if self.appointment:
            appointment_doc = frappe.get_doc("Patient Appointment", self.appointment)
            self.patient = appointment_doc.patient
            self.practitioner = appointment_doc.practitioner
            self.date = appointment_doc.date
            
    def validate(self):
        # Ensure we always have the details if appointment is linked
        if self.appointment and not self.patient:
            self.set_appointment_details()

