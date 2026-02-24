import frappe
#get practitioner leave
@frappe.whitelist()
def get_practitioner_leave():
	gettask = frappe.get_all(
			"Practitioner Leave",
			fields=["name", "practitioner", "from_date", "to_date"],
			filters={"status": "Approved"}
		)
	return gettask

#get practitioner schedule
@frappe.whitelist()
def get_patients():
	all_patients = frappe.get_all("Healthcare Patient", fields=["name", "full_name", "date_of_birth", "gender", "email", "mobile"])
	return all_patients





