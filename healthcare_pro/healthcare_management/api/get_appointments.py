import frappe
@frappe.whitelist()
def get_appointments(patient=None, practitioner=None, date=None, time=None, status=None):
    if not patient:
        patient = frappe.db.get_value(
            "Healthcare Patient",
            {"email": frappe.session.user},
            "name"
        )

    filters = {}
    if patient:
        filters["patient"] = patient
    if practitioner:
        filters["practitioner"] = practitioner
    if date:
        filters["date"] = date
    if status:
        filters["status"] = status

    return frappe.get_all(
        "Patient Appointment",
        fields=["name", "patient", "practitioner", "date", "time", "status"],
        filters=filters,
        order_by="date desc"
    )