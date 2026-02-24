# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

import frappe
from frappe.website.website_generator import WebsiteGenerator


class HealthcarePatient(WebsiteGenerator):
    def validate(self):
        self.check_duplicate_patient()
        self.calculate_age()

    def check_duplicate_patient(self):
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

        if self.route == " ":
            self.route = "patient-{0}".format(self.full_name)

    def calculate_age(self):
        """Calculate age from date of birth and set it on the age field"""
        if self.date_of_birth:
            today = frappe.utils.today()
            age = frappe.utils.getdate(today).year - frappe.utils.getdate(self.date_of_birth).year
            self.age = age
    
        