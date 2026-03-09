import frappe

@frappe.whitelist(allow_guest=True)
def get_appointment_details(name=None, patient=None, practitioner=None, date=None, time=None, status=None):
    
    filters = {}

    if name:
        filters["name"] = name

    if patient:
        filters["patient"] = patient

    if practitioner:
        filters["practitioner"] = practitioner

    if date:
        filters["date"] = date

    if time:
        filters["time"] = time

    if status:
        filters["status"] = status

    appointments = frappe.get_all(
        "Patient Appointment",
        fields=[
            "name",
            "patient",
            "practitioner",
            "date",
            "time",
            "status"
        ],
        filters=filters
    )

    return appointments
