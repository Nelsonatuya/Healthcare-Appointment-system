import frappe

@frappe.whitelist()
def check_booking_conflicts():
    """
    Check for booking conflicts before making an appointment
    Returns detailed conflict information for frontend to handle
    """
    patient = frappe.form_dict.get("patient_name")
    practitioner = frappe.form_dict.get("practitioner_name")
    date = frappe.form_dict.get("date")
    time = frappe.form_dict.get("time")

    if not patient or not practitioner or not date or not time:
        frappe.throw("Missing required fields")

    conflicts = {
        "has_conflicts": False,
        "patient_conflict": False,
        "practitioner_conflict": False,
        "existing_appointment": None,
        "messages": []
    }

    # Check if patient already has an appointment at this time (with ANY practitioner)
    patient_existing = frappe.db.get_value(
        "Patient Appointment",
        {
            "patient": patient,
            "date": date,
            "time": time,
            "status": ["not in", ["Cancelled"]],
        },
        ["name", "practitioner", "status"],
        as_dict=True
    )

    if patient_existing:
        conflicts["has_conflicts"] = True
        conflicts["patient_conflict"] = True
        conflicts["existing_appointment"] = patient_existing

        # Get practitioner name for the message
        practitioner_name = frappe.db.get_value("Healthcare Practitioner", patient_existing.practitioner, "practitioner_name")
        conflicts["messages"].append(f"You already have an appointment at {time} on {date} with {practitioner_name}")
        return conflicts

    # Check if practitioner slot is already taken
    practitioner_conflict = frappe.db.exists( 
        "Patient Appointment",
        {
            "practitioner": practitioner,
            "date": date,
            "time": time,
            "status": ["not in", ["Cancelled"]],
        },
    )

    if practitioner_conflict:
        conflicts["has_conflicts"] = True
        conflicts["practitioner_conflict"] = True

        # Check if patient is already on waitlist for this slot
        existing_waitlist = frappe.db.exists(
            "Appointment Waitlist",
            {
                "patient": patient,
                "practitioner": practitioner,
                "date": date,
                "time": time,
                "status": "Waiting",
            },
        )

        if existing_waitlist:
            conflicts["messages"].append("You are already on the waitlist for this time slot")
        else:
            conflicts["messages"].append("This time slot is fully booked. You can join the waitlist.")

    return conflicts


@frappe.whitelist()
def confirm_booking():
    """
    Confirm and create appointment after user confirmation
    This is called after the user confirms they want to proceed
    """
    patient = frappe.form_dict.get("patient_name")
    practitioner = frappe.form_dict.get("practitioner_name")
    date = frappe.form_dict.get("date")
    time = frappe.form_dict.get("time")
    force_waitlist = frappe.form_dict.get("force_waitlist", False)

    if not patient or not practitioner or not date or not time:
        frappe.throw("Missing required fields")

    # Get practitioner name for response messages
    practitioner_name = frappe.db.get_value("Healthcare Practitioner", practitioner, "practitioner_name")

    # Double-check for patient conflicts (safety check)
    patient_existing = frappe.db.exists(
        "Patient Appointment",
        {
            "patient": patient,
            "date": date,
            "time": time,
            "status": ["not in", ["Cancelled"]],
        },
    )

    if patient_existing:
        frappe.throw("You already have an appointment at this time. Cannot book overlapping appointments.")

    # Check practitioner availability
    practitioner_conflict = frappe.db.exists(
        "Patient Appointment",
        {
            "practitioner": practitioner,
            "date": date,
            "time": time,
            "status": ["not in", ["Cancelled"]],
        },
    )

    if practitioner_conflict or force_waitlist:
        # Check if already on waitlist
        existing_waitlist = frappe.db.exists(
            "Appointment Waitlist",
            {
                "patient": patient,
                "practitioner": practitioner,
                "date": date,
                "time": time,
                "status": "Waiting",
            },
        )

        if existing_waitlist:
            return {
                "status": "error",
                "message": "You are already on the waitlist for this appointment slot."
            }

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
            "message": f"Added to waitlist for {practitioner_name} on {date} at {time}",
            "waitlist_id": wait_doc.name
        }

    # Create appointment
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
        "message": f"Appointment confirmed with {practitioner_name} on {date} at {time}",
        "appointment_id": appointment.name
    }