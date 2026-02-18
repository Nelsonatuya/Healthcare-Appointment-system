# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_time, nowdate, nowtime

class PatientAppointment(Document):
    def validate(self):
        self.validate_double_booking()
        self.validate_datetime()
        self.check_practitioner_leave()
        self.check_practitioner_schedule()
        self.update_status_to_scheduled()

    def on_submit(self):
        self.check_practitioner_leave()

    def validate_datetime(self):
        if getdate(self.date) < getdate(nowdate()):
            frappe.throw(_("You cannot schedule an appointment for a past date."), title=_("Invalid Date"))
        # 2. Prevent Past Times (if the date is today)
        if getdate(self.date) == getdate(nowdate()):
            if get_time(self.time) < get_time(nowtime()):
                frappe.throw(_("The appointment time has already passed for today."))

    #check if doctor has a scheduled appointment at the same time
    def validate_double_booking(self): 
        conflict = frappe.db.exists("Patient Appointment", {
            "practitioner": self.practitioner,
            "date": self.date,
            "time": self.time,
            "name": ["!=", self.name], 
            "status": ["not in", ["Cancelled"]]
        })
        if conflict:
            frappe.throw(_("Conflict: Practitioner {0} is already booked at {1} on {2}")
                .format(self.practitioner, self.time, self.date))

        #check for preexiting patient-appointment
        patient_conflict = frappe.db.exists("Patient Appointment", {
            "patient": self.patient,
            "date": self.date,
            "time": self.time,
            "name": ["!=", self.name],
            "status": ["not in", ["Cancelled"]]
        })
        if patient_conflict:
            frappe.throw(_("Patient {0} already has another appointment at this time.")
                .format(self.patient))
            
        #check if practitioner is on leave
    def check_practitioner_leave(self):
        # Fetch the leave record name if it exists
        leave_name = frappe.db.exists("Practitioner Leave", {
            "practitioner": self.practitioner,
            "from_date": ["<=", self.date],
            "to_date": [">=", self.date],
            "docstatus": 1 #if submitted
        })
        if leave_name:
            reason = frappe.db.get_value("Practitioner Leave", leave_name, "reason")
            msg = _("Practitioner {0} is on leave on {1}.").format(self.practitioner, self.date)
            if reason:
                msg += _(" Reason: {0}").format(reason)
                
            frappe.throw(msg, title=_("Practitioner Unavailable"))
    
    def check_practitioner_schedule(self):
        # Get the day of the week from the appointment date
        appointment_day = getdate(self.date).strftime("%A")
        # Get practitioner's schedule slots for this day
        schedule_slots = frappe.get_all("Schedule Slot", 
            filters={
                "parent": self.practitioner,
                "parenttype": "Healthcare Practitioner",
                "parentfield": "table_locw",
                "day": appointment_day
            },
            fields=["from_time", "to_time"]
        )
        
        if not schedule_slots:
            frappe.throw(_("Practitioner {0} does not have scheduled working hours on {1}.")
                .format(self.practitioner, appointment_day))
        
        # Check if appointment time falls within any scheduled slot
        appointment_time = get_time(self.time)
        is_within_schedule = False
        
        for slot in schedule_slots:
            from_time = get_time(slot.from_time)
            to_time = get_time(slot.to_time)
            
            if from_time <= appointment_time <= to_time:
                is_within_schedule = True
                break
        
        if not is_within_schedule:
            frappe.throw(_("Appointment time {0} is outside practitioner's scheduled working hours on {1}.")
                .format(self.time, appointment_day))


    def update_status_to_scheduled(self):
        """Set status to scheduled after save"""
        if self.status == "Open":
            self.status = "Scheduled"