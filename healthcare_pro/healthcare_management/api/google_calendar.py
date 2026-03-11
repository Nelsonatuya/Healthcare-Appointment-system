import frappe
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_calendar_service():
    # Read from Frappe's built-in Google Settings
    settings = frappe.get_single("Google Settings")
    
    creds = Credentials(
        token=None,
        refresh_token=settings.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.client_id,          # maps to 'client_id' in Google Settings
        client_secret=settings.client_secret,  # maps to 'client_secret' in Google Settings
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    
    return build("calendar", "v3", credentials=creds)


def create_calendar_event(appointment_doc):
    try:
        service = get_calendar_service()
        settings = frappe.get_single("Google Settings")

        # Build start and end datetime strings
        date_str = str(appointment_doc.date)
        time_str = str(appointment_doc.time)
        start_datetime = f"{date_str}T{time_str}"

        # Default to 1-hour appointment duration
        from datetime import datetime, timedelta
        start_dt = datetime.fromisoformat(start_datetime)
        end_dt = start_dt + timedelta(hours=1)
        end_datetime = end_dt.isoformat()

        event = {
            "summary": f"Appointment: {appointment_doc.patient}",
            "description": (
                f"Patient: {appointment_doc.patient}\n"
                f"Practitioner: {appointment_doc.practitioner}\n"
                f"Appointment ID: {appointment_doc.name}"
            ),
            "start": {
                "dateTime": start_datetime,
                "timeZone": frappe.db.get_single_value("System Settings", "time_zone") or "UTC",
            },
            "end": {
                "dateTime": end_datetime,
                "timeZone": frappe.db.get_single_value("System Settings", "time_zone") or "UTC",
            },
        }

        created_event = service.events().insert(
            calendarId=settings.calendar_id or "primary",
            body=event
        ).execute()

        # Save the Google event ID back to the appointment for future updates/deletes
        frappe.db.set_value(
            "Patient Appointment",
            appointment_doc.name,
            "google_event_id",
            created_event.get("id")
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Google Calendar Sync Failed")
        frappe.msgprint(f"Appointment saved, but Google Calendar sync failed: {str(e)}")


def delete_calendar_event(google_event_id):
    try:
        service = get_calendar_service()
        settings = frappe.get_single("Google Settings")
        service.events().delete(
            calendarId=settings.calendar_id or "primary",
            eventId=google_event_id
        ).execute()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Google Calendar Delete Failed")