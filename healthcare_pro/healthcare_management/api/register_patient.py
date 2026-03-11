import frappe

@frappe.whitelist()
def register_new_patient():
	full_name = frappe.form_dict.get('full_name')
	date_of_birth = frappe.form_dict.get('date_of_birth')
	gender = frappe.form_dict.get('gender')
	email = frappe.form_dict.get('email')
	mobile = frappe.form_dict.get('mobile')
	insurance_id = frappe.form_dict.get('insurance_id')
	insurance_card = frappe.form_dict.get('insurance_card')
	id_attachment = frappe.form_dict.get('id_attachment')

	required_fields = ['full_name', 'date_of_birth', 'gender', 'email', 'mobile', 'insurance_id']
	for field in required_fields:
		if not locals().get(field):
			frappe.throw(f"Missing required field: {field}")
	
	new_patient = frappe.get_doc({
		"doctype": "Healthcare Patient",
		"full_name": full_name,
		"date_of_birth": date_of_birth,
		"gender": gender,
		"email": email,
		"mobile": mobile,
		"insurance_id": insurance_id,
		"insurance_card": insurance_card,
		"id_attachment": id_attachment,
		"give_consent": 1,  
		"published": 0  
	})
	
	new_patient.insert()
	return {"patient_name": new_patient.name}


@frappe.whitelist()
def get_patients():
    patient = frappe.db.get_value(
        "Healthcare Patient",
        {"email": frappe.session.user},
        ["name", "full_name", "date_of_birth", "gender", "email", "mobile", "insurance_id", "age"],
        as_dict=True
    )
    if not patient:
        return []
    return [patient]