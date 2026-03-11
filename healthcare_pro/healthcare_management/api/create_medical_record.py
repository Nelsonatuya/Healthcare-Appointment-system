import frappe

@frappe.whitelist()
def create_medical_record():
    patient = frappe.form_dict.get("patient")
    practitioner = frappe.form_dict.get("practitioner")
    diagnosis = frappe.form_dict.get("diagnosis")
    symptoms = frappe.form_dict.get("symptoms")
    date = frappe.form_dict.get("date")
    appointment = frappe.form_dict.get("appointment")

    if not patient or not practitioner or not diagnosis or not symptoms or not date:
        return {"error": "Missing required fields"}

    medical_record = frappe.get_doc({
        "doctype": "Medical Record",
        "patient": patient,
        "practitioner": practitioner,
        "diagnosis": diagnosis,
        "appointment": appointment,
        "symptoms": symptoms,
        "date": date
    })

    medical_record.insert(ignore_permissions=True)

    return {
        "status": "success",
        "medical_record_id": medical_record.name
    }
#example payload
# {     "patient": "PAT-00001",
#     "practitioner": "DOC-00005",
#     "diagnosis": "Common Cold",
#     "symptoms": "Sneezing, Runny Nose, Sore Throat",  
#     "date": "2024-06-01",
#     "appointment": "APP-00001"
# }

@frappe.whitelist()
def get_medical_records():
    patient = frappe.db.get_value(
        "Healthcare Patient",
        {"email": frappe.session.user},
        "name"
    )
    if not patient:
        return []
    return frappe.get_all(
        "Medical Record",
        filters={"patient": patient},
        fields=["name", "date", "practitioner", "diagnosis", "appointment", "symptoms"]
    )