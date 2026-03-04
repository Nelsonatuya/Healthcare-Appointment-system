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
    # Button href is upgraded with ?patient=<name> by client script after save.
    context.success_message = (
        "<div class=\"alert alert-success\">You have been successfully registered. Do you wish to book an appointment?</div>"
        "<a class=\"btn btn-primary book-appointment-btn\" href=\"/book-an-appointment\">Book an Appointment</a>"
    )

    return context
