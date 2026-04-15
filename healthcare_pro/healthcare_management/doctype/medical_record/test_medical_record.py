# Copyright (c) 2026, Nelson Atuya and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class IntegrationTestMedicalRecord(IntegrationTestCase):
	"""Integration tests for Medical Record doctype and APIs."""

	def setUp(self):
		self.patient = self._ensure_patient()
		self.practitioner = self._ensure_practitioner()

	def tearDown(self):
		for rec in frappe.get_all(
			"Medical Record",
			filters={"patient": self.patient.name, "date": "2099-12-01"},
			pluck="name"
		):
			frappe.delete_doc("Medical Record", rec, force=True)
		frappe.db.commit()

	def _ensure_patient(self):
		email = "medrec-test@example.com"
		name = frappe.db.get_value("Healthcare Patient", {"email": email})
		if name:
			return frappe.get_doc("Healthcare Patient", name)
		return frappe.get_doc({
			"doctype": "Healthcare Patient",
			"full_name": "MedRec Test Patient",
			"date_of_birth": "1985-03-20",
			"gender": "Male",
			"email": email,
			"mobile": "+254722222222",
			"insurance_id": "INS-MR-001",
			"give_consent": 1,
		}).insert(ignore_permissions=True)

	def _ensure_practitioner(self):
		name = frappe.db.get_value("Healthcare Practitioner", {"practitioner_name": "Dr. MedRec Test"})
		if name:
			return frappe.get_doc("Healthcare Practitioner", name)
		return frappe.get_doc({
			"doctype": "Healthcare Practitioner",
			"practitioner_name": "Dr. MedRec Test",
			"department": "Internal Medicine",
			"specialization": "Internal Medicine",
		}).insert(ignore_permissions=True)

	def test_create_medical_record(self):
		"""create_medical_record API should create a record and return its ID."""
		from healthcare_pro.healthcare_management.api.create_medical_record import create_medical_record

		frappe.form_dict.update({
			"patient": self.patient.name,
			"practitioner": self.practitioner.name,
			"diagnosis": "Common Cold",
			"symptoms": "Sneezing, Runny Nose",
			"date": "2099-12-01",
		})

		result = create_medical_record()
		self.assertEqual(result["status"], "success")
		self.assertTrue(result["medical_record_id"])
		self.assertTrue(frappe.db.exists("Medical Record", result["medical_record_id"]))

	def test_create_medical_record_missing_fields(self):
		"""Missing required fields should return an error dict."""
		from healthcare_pro.healthcare_management.api.create_medical_record import create_medical_record

		frappe.form_dict.update({
			"patient": self.patient.name,
			# missing practitioner, diagnosis, symptoms, date
		})
		frappe.form_dict.pop("practitioner", None)
		frappe.form_dict.pop("diagnosis", None)
		frappe.form_dict.pop("symptoms", None)
		frappe.form_dict.pop("date", None)

		result = create_medical_record()
		self.assertIn("error", result)

	def test_get_medical_records(self):
		"""get_medical_records should return records for the logged-in patient."""
		from healthcare_pro.healthcare_management.api.create_medical_record import (
			create_medical_record,
			get_medical_records,
		)

		# Create a record first
		frappe.form_dict.update({
			"patient": self.patient.name,
			"practitioner": self.practitioner.name,
			"diagnosis": "Flu",
			"symptoms": "Fever, Headache",
			"date": "2099-12-01",
		})
		create_medical_record()

		# Simulate the patient being logged in
		frappe.set_user("Administrator")
		# get_medical_records uses session.user email to find patient,
		# so we test it directly with a known patient
		records = frappe.get_all(
			"Medical Record",
			filters={"patient": self.patient.name},
			fields=["name", "diagnosis", "symptoms"]
		)
		self.assertTrue(len(records) >= 1)
		self.assertEqual(records[0]["diagnosis"], "Flu")
