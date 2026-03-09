import frappe


@frappe.whitelist(allow_guest=True)
def get_practitioner_schedule(practitioner_id=None):

    filters = {}
    if practitioner_id:
        filters["name"] = practitioner_id

    practitioners = frappe.get_all(
        "Healthcare Practitioner",
        filters=filters,
        fields=["name", "practitioner_name"]
    )

    result = []

    for practitioner in practitioners:
        doc = frappe.get_doc("Healthcare Practitioner", practitioner.name)

        for slot in getattr(doc, "table_locw", []):
            result.append({
                "practitioner_id": practitioner.name,
                "practitioner_name": practitioner.practitioner_name,
                "day": getattr(slot, "day", None),
                "from_time": getattr(slot, "from_time", None),
                "to_time": getattr(slot, "to_time", None),
                "working_time": f"{getattr(slot, 'from_time', '')} - {getattr(slot, 'to_time', '')}",
                "status": getattr(slot, "status", "Active")
            })

    if not result:
        return {"message": "No practitioner schedule found"}

    return result