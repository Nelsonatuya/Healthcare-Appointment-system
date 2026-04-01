import frappe
@frappe.whitelist()
def get_appointments(patient=None, practitioner=None, date=None, time=None, status=None):
    filters = {}

    # If practitioner is specified, filter by practitioner only
    if practitioner:
        filters["practitioner"] = practitioner
    # If no practitioner specified, try to get patient from current user
    elif not patient:
        patient = frappe.db.get_value(
            "Healthcare Patient",
            {"email": frappe.session.user},
            "name"
        )

    # Add other filters
    if patient:
        filters["patient"] = patient
    if date:
        filters["date"] = date
    if status:
        filters["status"] = status

    return frappe.get_all(
        "Patient Appointment",
        fields=["name", "patient", "practitioner", "date", "time", "status"],
        filters=filters,
        order_by="date desc",
        ignore_permissions=True
    )