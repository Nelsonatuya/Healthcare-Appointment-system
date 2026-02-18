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
    # Show a button on the success message to redirect users to the booking page
    # This will be rendered after the web form submission completes
    context.success_message = (
        "<div class=\"alert alert-success\">Your details have been submitted successfully.</div>"
        "<a class=\"btn btn-primary\" href=\"/book-an-appointment\">Book an Appointment</a>"
    )

    return context
