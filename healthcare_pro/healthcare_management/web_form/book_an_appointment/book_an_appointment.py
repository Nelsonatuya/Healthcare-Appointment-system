import frappe


def get_context(context):

    def on_submit(doc):
        patient_conflict = frappe.db.exists("Patient Appointment", {
            "patient": doc.patient,
            "practitioner": doc.practitioner,
            "date": doc.date,
            "time": doc.time,
            "name": ["!", doc.name],
        })
        if patient_conflict:
            frappe.throw("Patient appointment  already exists")


    context.on_submit = on_submit
    # Button href is upgraded with ?patient=<name> by client script after save.
    context.success_message = (
        "<div class=\"alert alert-success\">You have successfully booked an appointment. Do you wish to book another?</div>"
    )

    return context
