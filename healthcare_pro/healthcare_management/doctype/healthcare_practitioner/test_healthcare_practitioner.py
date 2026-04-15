# Copyright (c) 2026, Nelson Atuya and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class IntegrationTestHealthcarePractitioner(IntegrationTestCase):
	"""Integration tests for Healthcare Practitioner and related APIs."""

	def setUp(self):
		self.practitioner = self._ensure_practitioner()

	def _ensure_practitioner(self):
		name = frappe.db.get_value("Healthcare Practitioner", {"practitioner_name": "Dr. API Test"})
		if name:
			return frappe.get_doc("Healthcare Practitioner", name)
		return frappe.get_doc({
			"doctype": "Healthcare Practitioner",
			"practitioner_name": "Dr. API Test",
			"department": "Cardiology",
			"specialization": "Cardiology",
			"email": "dr-api-test@example.com",
		}).insert(ignore_permissions=True)

	def test_create_practitioner(self):
		self.assertTrue(self.practitioner.name)
		self.assertEqual(self.practitioner.practitioner_name, "Dr. API Test")
		self.assertEqual(self.practitioner.specialization, "Cardiology")

	def test_get_practitioners_api(self):
		"""get_practitioners_with_specializations should return practitioner list."""
		from healthcare_pro.healthcare_management.api.get_practitioners import (
			get_practitioners_with_specializations,
		)

		result = get_practitioners_with_specializations()
		self.assertIsInstance(result, list)
		# Our test practitioner should be in the results
		ids = [p["id"] for p in result]
		self.assertIn(self.practitioner.name, ids)

	def test_get_practitioners_filter_by_specialty(self):
		"""Filtering by specialty should narrow results."""
		from healthcare_pro.healthcare_management.api.get_practitioners import (
			get_practitioners_with_specializations,
		)

		result = get_practitioners_with_specializations(specialty="Cardiology")
		self.assertTrue(len(result) >= 1)
		for p in result:
			self.assertIn("cardiology", p["specialization"].lower())

	def test_get_practitioners_search_term(self):
		"""Search term should match practitioner name."""
		from healthcare_pro.healthcare_management.api.get_practitioners import (
			get_practitioners_with_specializations,
		)

		result = get_practitioners_with_specializations(search_term="API Test")
		ids = [p["id"] for p in result]
		self.assertIn(self.practitioner.name, ids)

	def test_get_specializations(self):
		"""get_practitioner_specializations should return a list of strings."""
		from healthcare_pro.healthcare_management.api.get_practitioners import (
			get_practitioner_specializations,
		)

		specs = get_practitioner_specializations()
		self.assertIsInstance(specs, list)
		self.assertIn("Cardiology", specs)

	def test_get_schedule_api(self):
		"""get_practitioner_schedule should return schedule or 'no schedule' message."""
		from healthcare_pro.healthcare_management.api.get_schedule import get_practitioner_schedule

		result = get_practitioner_schedule(practitioner_id=self.practitioner.name)
		# Practitioner has no schedule rows, so expect the no-data message
		if isinstance(result, dict):
			self.assertIn("message", result)
		else:
			self.assertIsInstance(result, list)

