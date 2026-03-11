import frappe

#########################
# get practitioner leave
#########################
@frappe.whitelist()
def get_practitioner_leave():
	getleave = frappe.get_all(
			"Practitioner Leave",
			fields=["name", "practitioner", "from_date", "to_date"],
			filters={"status": "Approved"}
		)
	return getleave







