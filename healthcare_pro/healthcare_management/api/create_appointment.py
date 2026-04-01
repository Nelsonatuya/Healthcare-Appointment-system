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
    appointment.submit()  # This triggers on_submit() which sends notifications

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

# Debug function to check practitioner filtering
@frappe.whitelist()
def debug_practitioner_appointments():
    """Debug function to check practitioner and appointment data"""

    # Get current logged-in user
    current_user = frappe.session.user

    # Get practitioner record for current user
    practitioner = frappe.db.get_value(
        "Healthcare Practitioner",
        {"email": current_user},
        ["name", "practitioner_name", "email"],
        as_dict=True
    )

    # Get all appointments
    all_appointments = frappe.get_all(
        "Patient Appointment",
        fields=["name", "patient", "practitioner", "date", "time", "status"],
        order_by="date desc"
    )

    # Get appointments for this practitioner
    filtered_appointments = []
    if practitioner:
        filtered_appointments = frappe.get_all(
            "Patient Appointment",
            fields=["name", "patient", "practitioner", "date", "time", "status"],
            filters={"practitioner": practitioner.name},
            order_by="date desc"
        )

    return {
        "current_user": current_user,
        "practitioner_record": practitioner,
        "total_appointments": len(all_appointments),
        "filtered_appointments": len(filtered_appointments),
        "all_appointments_sample": all_appointments[:5],  # First 5 for debugging
        "filtered_appointments_sample": filtered_appointments[:5]
    }
