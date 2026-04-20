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

    appointments = frappe.get_all(
        "Patient Appointment",
        fields=["name", "patient", "practitioner", "date", "time", "status"],
        filters=filters,
        order_by="date desc",
        ignore_permissions=True
    )

    # Resolve patient names
    patient_ids = list({a.patient for a in appointments if a.patient})
    patient_names = {}
    if patient_ids:
        for pid in patient_ids:
            full_name = frappe.db.get_value("Healthcare Patient", pid, "full_name")
            if full_name:
                patient_names[pid] = full_name

    # Resolve practitioner names
    practitioner_ids = list({a.practitioner for a in appointments if a.practitioner})
    practitioner_names = {}
    if practitioner_ids:
        for prid in practitioner_ids:
            pname = frappe.db.get_value("Healthcare Practitioner", prid, "practitioner_name")
            if pname:
                practitioner_names[prid] = pname

    for a in appointments:
        a["patient_name"] = patient_names.get(a.patient, "")
        a["practitioner_name"] = practitioner_names.get(a.practitioner, "")

    return appointments