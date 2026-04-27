import frappe
from frappe import _
from frappe.utils import getdate, nowdate


@frappe.whitelist()
def get_blocked_days(practitioner, from_date=None, to_date=None):
    """Return all approved Practitioner Leave records for a practitioner within a date range."""
    if not practitioner:
        frappe.throw(_("Practitioner is required."))

    filters = {
        "practitioner": practitioner,
        "status": "Approved",
        "docstatus": 1,
    }

    if from_date:
        filters["to_date"] = [">=", from_date]
    if to_date:
        filters["from_date"] = ["<=", to_date]

    leaves = frappe.get_all(
        "Practitioner Leave",
        filters=filters,
        fields=["name", "practitioner", "from_date", "to_date", "reason"],
        order_by="from_date asc",
    )

    return leaves


@frappe.whitelist()
def get_day_appointments(practitioner, date):
    """Return all non-cancelled appointments for a practitioner on a given date."""
    if not practitioner or not date:
        frappe.throw(_("Practitioner and date are required."))

    appointments = frappe.get_all(
        "Patient Appointment",
        filters={
            "practitioner": practitioner,
            "date": date,
            "status": ["not in", ["Cancelled"]],
        },
        fields=["name", "patient", "date", "time", "status"],
        order_by="time asc",
    )

    for a in appointments:
        a["patient_name"] = frappe.db.get_value(
            "Healthcare Patient", a.patient, "full_name"
        ) or a.patient
        a["patient_email"] = frappe.db.get_value(
            "Healthcare Patient", a.patient, "email"
        ) or ""

    return appointments


@frappe.whitelist()
def reschedule_and_notify(appointment_name, reason=None):
    """Cancel an appointment due to practitioner day-off and email the patient."""
    doc = frappe.get_doc("Patient Appointment", appointment_name)

    if doc.status == "Cancelled":
        frappe.throw(_("This appointment is already cancelled."))

    practitioner_name = frappe.db.get_value(
        "Healthcare Practitioner", doc.practitioner, "practitioner_name"
    ) or doc.practitioner

    doc.status = "Cancelled"
    doc.save(ignore_permissions=True)

    from healthcare_pro.healthcare_management.api.google_calendar import (
        delete_calendar_event,
    )
    if doc.google_event_id:
        delete_calendar_event(doc.google_event_id)

    _send_reschedule_email(doc, practitioner_name, reason)

    frappe.db.commit()
    return {"status": "ok", "appointment": appointment_name}


@frappe.whitelist()
def block_day(practitioner, date, reason=None):
    """Block a day by creating a Practitioner Leave record.

    Only succeeds if there are no remaining non-cancelled appointments
    on that date for this practitioner.
    """
    if getdate(date) < getdate(nowdate()):
        frappe.throw(_("Cannot block a day in the past."))

    remaining = frappe.db.count("Patient Appointment", {
        "practitioner": practitioner,
        "date": date,
        "status": ["not in", ["Cancelled"]],
    })

    if remaining:
        frappe.throw(
            _("There are still {0} appointment(s) on {1}. "
              "Please reschedule them before blocking this day.").format(remaining, date)
        )

    existing_leave = frappe.db.exists("Practitioner Leave", {
        "practitioner": practitioner,
        "from_date": ["<=", date],
        "to_date": [">=", date],
        "docstatus": 1,
    })

    if existing_leave:
        frappe.throw(_("This day is already blocked."))

    leave_doc = frappe.get_doc({
        "doctype": "Practitioner Leave",
        "practitioner": practitioner,
        "from_date": date,
        "to_date": date,
        "reason": reason or "Day blocked via Practitioner Portal",
        "status": "Approved",
    })
    leave_doc.insert(ignore_permissions=True)
    leave_doc.submit()
    frappe.db.commit()

    return {"status": "ok", "leave": leave_doc.name}


def _send_reschedule_email(appointment_doc, practitioner_name, reason=None):
    """Send reschedule notification to the patient."""
    try:
        patient_doc = frappe.get_doc("Healthcare Patient", appointment_doc.patient)
        if not patient_doc.email:
            return

        import datetime as dt

        formatted_time = "Time TBD"
        if appointment_doc.time:
            time_obj = dt.datetime.strptime(str(appointment_doc.time), "%H:%M:%S").time()
            formatted_time = time_obj.strftime("%I:%M %p")

        formatted_date = str(appointment_doc.date)
        if appointment_doc.date:
            date_obj = dt.datetime.strptime(str(appointment_doc.date), "%Y-%m-%d").date()
            formatted_date = date_obj.strftime("%B %d, %Y")

        reason_html = ""
        if reason:
            reason_html = f"""
                <tr>
                    <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Reason:</td>
                    <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{reason}</td>
                </tr>
            """

        frappe.sendmail(
            recipients=[patient_doc.email],
            subject="Appointment Rescheduling Required - Better Care",
            message=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8fafc;">
                <div style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">

                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #d97706; margin: 0; font-size: 24px;">Appointment Rescheduling Required</h1>
                        <p style="color: #64748b; margin: 5px 0 0 0;">Your practitioner is unavailable on your appointment date</p>
                    </div>

                    <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                        <h3 style="color: #92400e; margin: 0 0 15px 0; font-size: 16px;">Affected Appointment</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; color: #64748b; font-weight: 500; width: 30%;">Appointment ID:</td>
                                <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{appointment_doc.name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Date:</td>
                                <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{formatted_date}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Time:</td>
                                <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{formatted_time}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Practitioner:</td>
                                <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{practitioner_name}</td>
                            </tr>
                            {reason_html}
                        </table>
                    </div>

                    <div style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                        <h4 style="color: #0369a1; margin: 0 0 10px 0; font-size: 14px;">What happens next:</h4>
                        <ul style="color: #475569; font-size: 14px; margin: 0; padding-left: 20px;">
                            <li>Your original appointment has been cancelled</li>
                            <li>Please book a new appointment at your convenience</li>
                            <li>We apologise for any inconvenience</li>
                        </ul>
                    </div>

                    <div style="text-align: center; margin-bottom: 20px;">
                        <p style="color: #64748b; font-size: 14px; margin-bottom: 15px;">
                            Ready to reschedule?
                        </p>
                        <a href="{frappe.utils.get_url()}/book-an-appointment"
                           style="background: #0f172a; color: white; padding: 12px 24px; text-decoration: none;
                                  border-radius: 8px; font-weight: 600; display: inline-block;">
                            Book New Appointment
                        </a>
                    </div>

                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 25px 0;">

                    <div style="text-align: center;">
                        <p style="color: #64748b; font-size: 12px; margin: 0;">
                            This is an automated message from Better Care Healthcare Portal.<br>
                            If you have questions, please contact our office directly.
                        </p>
                    </div>
                </div>
            </div>
            """,
        )

        frappe.logger().info(
            f"Reschedule notification sent to {patient_doc.email} "
            f"for appointment {appointment_doc.name}"
        )

    except Exception as e:
        frappe.logger().error(
            f"Failed to send reschedule notification for "
            f"{appointment_doc.name}: {str(e)}"
        )
