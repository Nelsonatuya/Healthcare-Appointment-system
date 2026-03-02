import frappe

@frappe.whitelist(allow_guest=True)
def get_appointment_details(appointment_id=None):
    if not appointment_id:
        appointment_id = frappe.form_dict.get("appointment_id")
    if not appointment_id:
        frappe.throw("Missing appointment_id")

    if not frappe.db.exists("Patient Appointment", appointment_id):
        frappe.throw("Appointment not found")

    appointment = frappe.get_doc("Patient Appointment", appointment_id)

    return {
        "name": appointment.name,
        "patient": appointment.patient,
        "practitioner": appointment.practitioner,
        "date": appointment.date,
        "time": appointment.time,
        "status": appointment.status
    }



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
