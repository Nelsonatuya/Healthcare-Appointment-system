import frappe


def get_context(context):
    appointment_id = frappe.form_dict.get("appointment")
    context.title = "Appointment Details"
    context.appointment = None
    context.error = None

    if not appointment_id:
        context.error = "Missing appointment ID."
        return context

    if not frappe.db.exists("Patient Appointment", appointment_id):
        context.error = "Appointment not found."
        return context

    context.appointment = frappe.get_value(
        "Patient Appointment",
        appointment_id,
        ["name", "patient", "practitioner", "date", "time", "status"],
        as_dict=True,
    )
    return context
