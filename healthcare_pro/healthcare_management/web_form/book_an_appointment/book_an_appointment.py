import frappe
from frappe import _
from frappe.utils import get_url_to_form

# This function will be called when the form is loaded
# It checks for a 'patient' parameter in the request and returns it to the frontend

def get_context(context):
    patient = frappe.form_dict.get('patient')
    if patient:
        context.patient = patient
    # Add any other context variables as needed
    return context

# Example function to handle appointment booking (to be called via API or form submission)
@frappe.whitelist(allow_guest=True)
def book_appointment(patient, appointment_date, appointment_time, practitioner):
    # Implement your appointment creation logic here
    # For demonstration, we'll just create a Patient Appointment doctype
    doc = frappe.get_doc({
        'doctype': 'Patient Appointment',
        'patient': patient,
        'appointment_date': appointment_date,
        'appointment_time': appointment_time,
        'practitioner': practitioner
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    # Return the name/id for redirecting to details
    return {
        'appointment_id': doc.name,
        'details_url': get_url_to_form('Patient Appointment', doc.name)
    }
