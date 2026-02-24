# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PractitionerLeave(Document):
	#check if practitioner has a scheduled appointment before approving leave
	def validate(self):
		if self.docstatus == 1:  # Only check when the document is being submitted
			conflict = frappe.db.exists("Patient Appointment", {
				"practitioner": self.practitioner,
				"date": ["between", [self.from_date, self.to_date]],
				"status": ["not in", ["Cancelled"]]
			})
			if conflict:
				frappe.throw(("Cannot approve leave: Practitioner {0} has scheduled appointments during this period.")
					.format(self.practitioner), title=("Leave Time conflict Error"))
			else:
				if self.status=="pending":
					self.status = "Approved"

	