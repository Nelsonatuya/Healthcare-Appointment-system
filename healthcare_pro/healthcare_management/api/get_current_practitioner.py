import frappe

@frappe.whitelist()
def get_current_practitioner():
    """
    Get the current logged-in practitioner's record
    Uses elevated permissions to bypass doctype read restrictions
    """
    try:
        current_user_email = frappe.session.user

        # Use frappe.db.get_value with ignore_permissions to get practitioner record
        practitioner = frappe.db.get_value(
            "Healthcare Practitioner",
            {"email": current_user_email},
            ["name", "practitioner_name", "email"],
            as_dict=True
        )

        if not practitioner:
            frappe.throw("No practitioner record found for the current user. Please contact your administrator.")

        return practitioner

    except Exception as e:
        frappe.log_error(f"Error getting current practitioner: {str(e)}")
        frappe.throw(f"Unable to load practitioner profile: {str(e)}")