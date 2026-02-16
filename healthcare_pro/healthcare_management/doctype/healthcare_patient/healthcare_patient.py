# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HealthcarePatient(Document):
    def validate(self):
        """Check for duplicate patient records before save."""
        self.check_duplicate_patient()

    def check_duplicate_patient(self):
        """Prevent registration of duplicate patients based on identifying fields."""
        patient_conflict = frappe.db.exists("Healthcare Patient", {
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth,
            "gender": self.gender,
            "mobile": self.mobile,
            "email": self.email,
            "name": ["!=", self.name],
        })
        if patient_conflict:
            frappe.throw("Patient already exists", title=("Duplicate patient"))