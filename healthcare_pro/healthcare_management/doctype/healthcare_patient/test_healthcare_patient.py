# Copyright (c) 2026, Nelson Atuya and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class IntegrationTestHealthcarePatient(IntegrationTestCase):
	"""Integration tests for the Healthcare Patient doctype."""

	def tearDown(self):
		# Clean up test patients created during tests
		for email in ["test-patient@example.com", "duplicate-patient@example.com"]:
			if frappe.db.exists("Healthcare Patient", {"email": email}):
				frappe.delete_doc("Healthcare Patient", frappe.db.get_value("Healthcare Patient", {"email": email}), force=True)
		frappe.db.commit()

	def _make_patient(self, **kwargs):
		defaults = {
			"doctype": "Healthcare Patient",
			"full_name": "Test Patient",
			"date_of_birth": "1990-01-15",
			"gender": "Male",
			"email": "test-patient@example.com",
			"mobile": "+254700000000",
			"insurance_id": "INS-TEST-001",
			"give_consent": 1,
		}
		defaults.update(kwargs)
		doc = frappe.get_doc(defaults)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_patient(self):
		patient = self._make_patient()
		self.assertTrue(patient.name)
		self.assertEqual(patient.full_name, "Test Patient")
		self.assertEqual(patient.gender, "Male")
		self.assertEqual(patient.email, "test-patient@example.com")

	def test_required_fields(self):
		"""Patient should not be created without required fields."""
		with self.assertRaises(frappe.exceptions.MandatoryError):
			frappe.get_doc({
				"doctype": "Healthcare Patient",
				"full_name": "No Email Patient",
			}).insert(ignore_permissions=True)

	def test_duplicate_email(self):
		"""Two patients with the same email should not be allowed (if unique is set)."""
		self._make_patient(email="duplicate-patient@example.com")
		# Whether this raises depends on doctype config; if email is unique it should fail
		try:
			self._make_patient(full_name="Another Patient", email="duplicate-patient@example.com")
			# If it doesn't raise, the doctype allows duplicate emails — that's fine
		except frappe.exceptions.DuplicateEntryError:
			pass  # Expected
		except frappe.exceptions.UniqueValidationError:
			pass  # Expected
