# Copyright (c) 2026, Nelson Atuya and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class IntegrationTestPatientAppointment(IntegrationTestCase):
	"""Integration tests for Patient Appointment doctype and booking APIs."""

	def setUp(self):
		self.patient = self._ensure_patient()
		self.practitioner = self._ensure_practitioner()

	def tearDown(self):
		# Cancel and delete test appointments
		for appt_name in frappe.get_all(
			"Patient Appointment",
			filters={"patient": self.patient.name, "date": "2099-12-01"},
			pluck="name"
		):
			doc = frappe.get_doc("Patient Appointment", appt_name)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc("Patient Appointment", appt_name, force=True)

		# Delete test waitlist entries
		for wl in frappe.get_all(
			"Appointment Waitlist",
			filters={"patient": self.patient.name, "date": "2099-12-01"},
			pluck="name"
		):
			frappe.delete_doc("Appointment Waitlist", wl, force=True)

		frappe.db.commit()

	def _ensure_patient(self):
		email = "appt-test-patient@example.com"
		name = frappe.db.get_value("Healthcare Patient", {"email": email})
		if name:
			return frappe.get_doc("Healthcare Patient", name)
		return frappe.get_doc({
			"doctype": "Healthcare Patient",
			"full_name": "Appointment Test Patient",
			"date_of_birth": "1990-06-15",
			"gender": "Female",
			"email": email,
			"mobile": "+254711111166",
			"insurance_id": "INS-APPT-001",
			"give_consent": 1,
		}).insert(ignore_permissions=True)

	def _ensure_practitioner(self):
		name = frappe.db.get_value("Healthcare Practitioner", {"practitioner_name": "Dr. Test Practitioner"})
		if name:
			return frappe.get_doc("Healthcare Practitioner", name)
		return frappe.get_doc({
			"doctype": "Healthcare Practitioner",
			"practitioner_name": "Dr. Test Practitioner",
			"department": "cardiothorastic",
			"specialization": "cardiology",
		}).insert(ignore_permissions=True)

	def _book(self, date="2099-12-01", time="10:00:00"):
		"""Helper to book an appointment via the API function."""
		from healthcare_pro.healthcare_management.api.create_appointment import book_appointment

		frappe.form_dict.update({
			"patient_name": self.patient.name,
			"practitioner_name": self.practitioner.name,
			"date": date,
			"time": time,
		})
		return book_appointment()

	def test_book_appointment_success(self):
		result = self._book()
		self.assertEqual(result["status"], "scheduled")
		self.assertTrue(result["appointment_id"])

		# Verify it exists in the database
		self.assertTrue(frappe.db.exists("Patient Appointment", result["appointment_id"]))

	def test_book_appointment_missing_fields(self):
		"""Booking without required fields should raise."""
		from healthcare_pro.healthcare_management.api.create_appointment import book_appointment

		frappe.form_dict.update({
			"patient_name": self.patient.name,
			# missing practitioner, date, time
		})
		frappe.form_dict.pop("practitioner_name", None)
		frappe.form_dict.pop("date", None)
		frappe.form_dict.pop("time", None)
		with self.assertRaises(frappe.exceptions.ValidationError):
			book_appointment()

	def test_double_booking_creates_waitlist(self):
		"""Booking the same slot twice should waitlist the second request."""
		result1 = self._book()
		self.assertEqual(result1["status"], "scheduled")

		result2 = self._book()
		self.assertEqual(result2["status"], "waitlisted")
		self.assertTrue(result2.get("waitlist_id"))

	def test_get_appointments_by_patient(self):
		"""Appointments should be retrievable via the get_appointments API."""
		from healthcare_pro.healthcare_management.api.get_appointments import get_appointments

		self._book()
		appointments = get_appointments(patient=self.patient.name)
		self.assertTrue(len(appointments) >= 1)
		self.assertEqual(appointments[0]["patient"], self.patient.name)

	def test_get_appointments_by_practitioner(self):
		"""Appointments should be filterable by practitioner."""
		from healthcare_pro.healthcare_management.api.get_appointments import get_appointments

		self._book()
		appointments = get_appointments(practitioner=self.practitioner.name)
		self.assertTrue(len(appointments) >= 1)
		self.assertEqual(appointments[0]["practitioner"], self.practitioner.name)
