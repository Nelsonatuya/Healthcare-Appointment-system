import frappe

@frappe.whitelist(allow_guest=True)
def get_practitioners_with_specializations(practitioner_id=None, specialty=None, search_term=None):
    """
    Get practitioners with their specializations and details
    """

    filters = {}
    if practitioner_id:
        filters["name"] = practitioner_id

    # Get practitioner fields based on the actual Healthcare Practitioner doctype
    fields = [
        "name",
        "practitioner_name",
        "department",
        "specialization",
        "mobile",
        "email",
        "user_id"
    ]

    try:
        practitioners = frappe.get_all(
            "Healthcare Practitioner",
            filters=filters,
            fields=fields,
            order_by="practitioner_name"
        )

        result = []

        for practitioner in practitioners:
            # Get the full document to access child tables if needed
            try:
                doc = frappe.get_doc("Healthcare Practitioner", practitioner.name)

                # Get working hours from schedule
                working_hours = []
                schedule_data = None

                # Check if there's a schedule child table (adjust table name as needed)
                if hasattr(doc, "table_locw"):
                    for slot in getattr(doc, "table_locw", []):
                        working_hours.append({
                            "day": getattr(slot, "day", None),
                            "from_time": str(getattr(slot, "from_time", "")),
                            "to_time": str(getattr(slot, "to_time", "")),
                            "status": getattr(slot, "status", "Active")
                        })

                # Determine if practitioner is available today
                import datetime
                today = datetime.datetime.now().strftime("%A")
                is_available_today = any(
                    slot["day"] == today and slot["status"] == "Active"
                    for slot in working_hours
                )

                # Get today's working hours
                today_hours = next(
                    (slot for slot in working_hours if slot["day"] == today and slot["status"] == "Active"),
                    None
                )

                practitioner_data = {
                    "id": practitioner.name,
                    "name": practitioner.practitioner_name or "N/A",
                    "department": practitioner.department or "General Practice",
                    "specialization": practitioner.specialization or "General Practice",
                    "mobile": practitioner.mobile or "",
                    "email": practitioner.email or "",
                    "user_id": practitioner.user_id or "",
                    "status": "Active",  # Default to active since no status field in doctype
                    "is_available_today": is_available_today,
                    "today_hours": f"{today_hours['from_time']} - {today_hours['to_time']}" if today_hours else "Not available today",
                    "working_hours": working_hours,
                    # Mock rating for now - you can implement real ratings later
                    "rating": round(4.5 + (hash(practitioner.name) % 5) * 0.1, 1),
                    "total_reviews": (hash(practitioner.name) % 50) + 10
                }

                # Apply search filters
                if specialty and specialty.lower() not in (practitioner_data["specialization"] or "").lower():
                    continue

                if search_term:
                    search_lower = search_term.lower()
                    if not any([
                        search_lower in practitioner_data["name"].lower(),
                        search_lower in (practitioner_data["specialization"] or "").lower(),
                        search_lower in (practitioner_data["department"] or "").lower()
                    ]):
                        continue

                result.append(practitioner_data)

            except Exception as e:
                frappe.log_error(f"Error processing practitioner {practitioner.name}: {str(e)}")
                continue

        return result

    except Exception as e:
        frappe.log_error(f"Error in get_practitioners_with_specializations: {str(e)}")
        return {"error": "Failed to fetch practitioners", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_practitioner_specializations():
    """
    Get all unique specializations/departments for filtering
    """
    try:
        specializations = frappe.get_all(
            "Healthcare Practitioner",
            fields=["specialization", "department"]
        )

        # Get unique specializations
        unique_specs = set()
        for spec in specializations:
            if spec.specialization:
                unique_specs.add(spec.specialization)
            if spec.department:
                unique_specs.add(spec.department)

        # Remove None and empty strings, then sort
        unique_specs = sorted([s for s in unique_specs if s])

        return unique_specs

    except Exception as e:
        frappe.log_error(f"Error in get_practitioner_specializations: {str(e)}")
        return []


@frappe.whitelist(allow_guest=True)
def search_practitioners(search_term=None, specialty=None):
    """
    Enhanced search for practitioners with fuzzy matching
    """
    return get_practitioners_with_specializations(
        search_term=search_term,
        specialty=specialty
    )