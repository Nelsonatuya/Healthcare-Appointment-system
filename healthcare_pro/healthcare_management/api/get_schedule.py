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
            fields=["name", "patient", "practitioner", "date", "time", "status"],
            filters=filters
        )
        return appointments



@frappe.whitelist(allow_guest=True)
def get_practitioner_schedule(practitioner_id=None):
    practitioners = []
    if practitioner_id:
        practitioners = frappe.get_all("Healthcare Practitioner", filters={"name": practitioner_id}, fields=["name"])
    else:
        practitioners = frappe.get_all("Healthcare Practitioner", fields=["name"])

    result = []
    for practitioner in practitioners:
        doc = frappe.get_doc("Healthcare Practitioner", practitioner.name)
        for slot in getattr(doc, "time_slots", []):
            result.append({
                "practitioner": practitioner.name,
                "day": getattr(slot, "day", None),
                "working_time": f"{getattr(slot, 'from_time', '')} - {getattr(slot, 'to_time', '')}",
                "from_time": getattr(slot, "from_time", None),
                "to_time": getattr(slot, "to_time", None),
                "status": getattr(slot, "status", None)
            })
    if not result:
        return {"message": "No schedule slots found."}
    return result
