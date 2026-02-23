# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PractitionerSchedule(Document):
	def validate(self):
		
		#set the schedule name to be the practitioner's name and the day of the week for easy identification
		self.schedule_name = "{0} - {1}-{2}".format(self.practitioner, self.from_time, self.to_time)
		#the fields from_time and to_time belong to a field called time_slot which is a child table called schedule slot
		
		