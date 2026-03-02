import frappe

@frappe.whitelist()
def book_appointment():
    patient = frappe.form_dict.get("patient_name")
    practitioner = frappe.form_dict.get("practitioner_name")
    date = frappe.form_dict.get("date")
    time = frappe.form_dict.get("time")

    if not patient or not practitioner or not date or not time:
        frappe.throw("Missing required fields")

    # Check if slot is already taken
    conflict = frappe.db.exists(
        "Patient Appointment",
        {
            "practitioner": practitioner,
            "date": date,
            "time": time,
            "status": ["not in", ["Cancelled"]],
        },
    )

    if conflict:
        existing_wait = frappe.db.exists(
                "Appointment Waitlist",
                {
                    "patient": patient,
                    "practitioner": practitioner,
                    "date": date,
                    "time": time,
                    "status": "Waiting",
                },
            )

        if not existing_wait:
        # Add to waitlist
            wait_doc = frappe.get_doc({
                "doctype": "Appointment Waitlist",
                "patient": patient,
                "practitioner": practitioner,
                "date": date,
                "time": time,
                "status": "Waiting",
            })
            wait_doc.insert(ignore_permissions=True)

            return {
                "status": "waitlisted",
                "message": "Doctor fully booked. Added to waitlist.",
                "waitlist_id": wait_doc.name
            }

    # No conflict → create appointment
    appointment = frappe.get_doc({
        "doctype": "Patient Appointment",
        "patient": patient,
        "practitioner": practitioner,
        "date": date,
        "time": time,
        "status": "Open",
    })

    appointment.insert(ignore_permissions=True)

    return {
        "status": "scheduled",
        "appointment_id": appointment.name
    }

#Get appointment details
@frappe.whitelist()
def get_appointments(patient=None, practitioner=None, date=None, time=None, status=None):
	filters = {}
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
