import frappe


def get_context(context):

    def on_submit(doc):
        patient_conflict = frappe.db.exists("Healthcare Patient", {
            "full_name": doc.full_name,
            "date_of_birth": doc.date_of_birth,
            "gender": doc.gender,
            "mobile": doc.mobile,
            "email": doc.email,
            "name": ["!", doc.name],
        })
        if patient_conflict:
            frappe.throw("Patient already exists")


    context.on_submit = on_submit
    return context
