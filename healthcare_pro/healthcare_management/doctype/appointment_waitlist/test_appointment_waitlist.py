# Copyright (c) 2026, Nelson Atuya and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class IntegrationTestAppointmentWaitlist(IntegrationTestCase):
	"""Integration tests for enhanced booking conflict checks and waitlist."""

	def setUp(self):
		self.patient = self._ensure_patient()
		self.practitioner = self._ensure_practitioner()

	def tearDown(self):
		for appt_name in frappe.get_all(
			"Patient Appointment",
			filters={"date": "2099-11-01"},
			pluck="name"
		):
			doc = frappe.get_doc("Patient Appointment", appt_name)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc("Patient Appointment", appt_name, force=True)

		for wl in frappe.get_all(
			"Appointment Waitlist",
			filters={"date": "2099-11-01"},
			pluck="name"
		):
			frappe.delete_doc("Appointment Waitlist", wl, force=True)
		frappe.db.commit()

	def _ensure_patient(self):
		email = "waitlist-test@example.com"
		name = frappe.db.get_value("Healthcare Patient", {"email": email})
		if name:
			return frappe.get_doc("Healthcare Patient", name)
		return frappe.get_doc({
			"doctype": "Healthcare Patient",
			"full_name": "Waitlist Test Patient",
			"date_of_birth": "1992-08-10",
			"gender": "Female",
			"email": email,
			"mobile": "+254733333333",
			"insurance_id": "INS-WL-001",
			"give_consent": 1,
		}).insert(ignore_permissions=True)

	def _ensure_practitioner(self):
		name = frappe.db.get_value("Healthcare Practitioner", {"practitioner_name": "Dr. Waitlist Test"})
		if name:
			return frappe.get_doc("Healthcare Practitioner", name)
		return frappe.get_doc({
			"doctype": "Healthcare Practitioner",
			"practitioner_name": "Dr. Waitlist Test",
			"department": "General Practice",
			"specialization": "General Practice",
		}).insert(ignore_permissions=True)

	def _create_appointment(self, patient=None, practitioner=None, date="2099-11-01", time="09:00:00"):
		appt = frappe.get_doc({
			"doctype": "Patient Appointment",
			"patient": patient or self.patient.name,
			"practitioner": practitioner or self.practitioner.name,
			"date": date,
			"time": time,
			"status": "Open",
		})
		appt.insert(ignore_permissions=True)
		appt.submit()
		return appt

	def test_no_conflict_on_empty_slot(self):
		"""check_booking_conflicts should report no conflicts for an open slot."""
		from healthcare_pro.healthcare_management.api.enhanced_booking import check_booking_conflicts

		frappe.form_dict.update({
			"patient_name": self.patient.name,
			"practitioner_name": self.practitioner.name,
			"date": "2099-11-01",
			"time": "09:00:00",
		})
		result = check_booking_conflicts()
		self.assertFalse(result["has_conflicts"])

	def test_practitioner_conflict_detected(self):
		"""Should detect when a practitioner's slot is already booked."""
		from healthcare_pro.healthcare_management.api.enhanced_booking import check_booking_conflicts

		# Book the slot first
		self._create_appointment()

		# Now another patient tries to check the same slot
		other_patient = self._ensure_other_patient()
		frappe.form_dict.update({
			"patient_name": other_patient.name,
			"practitioner_name": self.practitioner.name,
			"date": "2099-11-01",
			"time": "09:00:00",
		})
		result = check_booking_conflicts()
		self.assertTrue(result["has_conflicts"])
		self.assertTrue(result["practitioner_conflict"])

	def test_patient_conflict_detected(self):
		"""Should detect when a patient already has an appointment at the same time."""
		from healthcare_pro.healthcare_management.api.enhanced_booking import check_booking_conflicts

		self._create_appointment()

		# Same patient tries to book with a different practitioner at the same time
		frappe.form_dict.update({
			"patient_name": self.patient.name,
			"practitioner_name": self.practitioner.name,
			"date": "2099-11-01",
			"time": "09:00:00",
		})
		result = check_booking_conflicts()
		self.assertTrue(result["has_conflicts"])
		self.assertTrue(result["patient_conflict"])

	def test_confirm_booking_success(self):
		"""confirm_booking should create appointment for an open slot."""
		from healthcare_pro.healthcare_management.api.enhanced_booking import confirm_booking

		frappe.form_dict.update({
			"patient_name": self.patient.name,
			"practitioner_name": self.practitioner.name,
			"date": "2099-11-01",
			"time": "09:00:00",
		})
		result = confirm_booking()
		self.assertEqual(result["status"], "scheduled")
		self.assertTrue(result["appointment_id"])

	def test_confirm_booking_waitlist_on_conflict(self):
		"""confirm_booking should add to waitlist when slot is taken."""
		from healthcare_pro.healthcare_management.api.enhanced_booking import confirm_booking

		# Fill the slot
		self._create_appointment()

		# Another patient tries to confirm
		other_patient = self._ensure_other_patient()
		frappe.form_dict.update({
			"patient_name": other_patient.name,
			"practitioner_name": self.practitioner.name,
			"date": "2099-11-01",
			"time": "09:00:00",
		})
		result = confirm_booking()
		self.assertEqual(result["status"], "waitlisted")

	def _ensure_other_patient(self):
		email = "waitlist-other@example.com"
		name = frappe.db.get_value("Healthcare Patient", {"email": email})
		if name:
			return frappe.get_doc("Healthcare Patient", name)
		return frappe.get_doc({
			"doctype": "Healthcare Patient",
			"full_name": "Other Waitlist Patient",
			"date_of_birth": "1988-04-22",
			"gender": "Male",
			"email": email,
			"mobile": "+254744444444",
			"insurance_id": "INS-WL-002",
			"give_consent": 1,
		}).insert(ignore_permissions=True)
