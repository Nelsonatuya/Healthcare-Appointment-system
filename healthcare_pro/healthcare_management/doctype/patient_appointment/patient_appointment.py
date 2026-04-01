# Copyright (c) 2026, Nelson Atuya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_time, nowdate, nowtime
from datetime import datetime, timedelta
from healthcare_pro.healthcare_management.api.google_calendar import (
    create_calendar_event, delete_calendar_event
)


class PatientAppointment(Document):

    # ==========================
    # MAIN VALIDATION PIPELINE
    # ==========================

    def validate(self):
        self.validate_datetime()
        self.validate_double_booking()
        self.check_global_holiday()  
        self.check_practitioner_leave()
        self.check_practitioner_schedule()
        self.update_status_to_scheduled()

    def on_submit(self):
        self.check_practitioner_leave()
        create_calendar_event(self)
        self.send_appointment_confirmation()
        self.notify_practitioner()

    def on_update(self):
        if self.has_value_changed("status") and self.status == "Cancelled":
            # Delete from Google Calendar when cancelled
            google_event_id = frappe.db.get_value(
                "Patient Appointment", self.name, "google_event_id"
            )
            if google_event_id:
                delete_calendar_event(google_event_id)
            
            self.promote_waitlist()

    # ==========================
    # DATE & TIME VALIDATION
    # ==========================

    def validate_datetime(self):
        if getdate(self.date) < getdate(nowdate()):
            frappe.throw(
                _("You cannot schedule an appointment for a past date."),
                title=_("Invalid Date Error"),
            )

        if getdate(self.date) == getdate(nowdate()):
            if get_time(self.time) < get_time(nowtime()):
                frappe.throw(_("The appointment time has already passed for today."))

    # ==========================
    # 1-HOUR OVERLAP VALIDATION
    # ==========================

    def validate_double_booking(self):

        appointment_datetime = datetime.combine(
            getdate(self.date),
            get_time(self.time)
        )

        one_hour_before = appointment_datetime - timedelta(hours=1)
        one_hour_after = appointment_datetime + timedelta(hours=1)

        existing_appointments = frappe.get_all(
            "Patient Appointment",
            filters={
                "practitioner": self.practitioner,
                "date": self.date,
                "name": ["!=", self.name],
                "status": ["not in", ["Cancelled"]],
            },
            fields=["name", "time"],
        )

        for appt in existing_appointments:
            existing_datetime = datetime.combine(
                getdate(self.date),
                get_time(appt.time)
            )

            if one_hour_before < existing_datetime < one_hour_after:

                # Add to waitlist if not already added
                existing_wait = frappe.db.exists(
                    "Appointment Waitlist",
                    {
                        "patient": self.patient,
                        "practitioner": self.practitioner,
                        "date": self.date,
                        "time": self.time,
                        "status": "Waiting",
                    },
                )

                if not existing_wait:
                    wait_doc = frappe.get_doc({
                        "doctype": "Appointment Waitlist",
                        "patient": self.patient,
                        "practitioner": self.practitioner,
                        "date": self.date,
                        "time": self.time,
                        "status": "Waiting",
                    })
                    wait_doc.insert(ignore_permissions=True)
                    frappe.db.commit()

                frappe.throw(
                    _("This practitioner already has an appointment within  this time. You have been added to the waitlist."),
                    title=_("Time Slot Conflict"),
                )

        # ==========================
        # Patient self-conflict check
        # ==========================

        patient_conflict = frappe.db.exists(
            "Patient Appointment",
            {
                "patient": self.patient,
                "date": self.date,
                "time": self.time,
                "name": ["!=", self.name],
                "status": ["not in", ["Cancelled"]],
            },
        )

        if patient_conflict:
            frappe.throw(
                _("Patient already has another appointment at this exact time.")
            )

    # ==========================
    # PRACTITIONER LEAVE CHECK
    # ==========================

    def check_practitioner_leave(self):

        leave_name = frappe.db.exists(
            "Practitioner Leave",
            {
                "practitioner": self.practitioner,
                "from_date": ["<=", self.date],
                "to_date": [">=", self.date],
                "docstatus": 1,
            },
        )

        if leave_name:
            reason = frappe.db.get_value("Practitioner Leave", leave_name, "reason")

            msg = _("Practitioner {0} is on leave on {1}.").format(
                self.practitioner, self.date
            )

            if reason:
                msg += _(" Reason: {0}").format(reason)

            frappe.throw(msg, title=_("Practitioner Unavailable"))


    # ==========================
    # HOLIDAY CHECK
    # ==========================        
    def check_global_holiday(self):

        holiday = frappe.db.exists(
            "Healthcare Holiday",
            {
                "holiday_date": self.date
            }
        )

        if holiday:
            holiday_name = frappe.db.get_value(
                "Healthcare Holiday",
                holiday,
                "holiday_name"
            )

            frappe.throw(
                _("Appointments cannot be scheduled on {0} ({1}).")
                .format(self.date, holiday_name),
                title=_("Public Holiday")
            )

    # ==========================
    # PRACTITIONER WORKING HOURS
    # ==========================

    def check_practitioner_schedule(self):

        appointment_day = getdate(self.date).strftime("%A")

        schedule_slots = frappe.get_all(
            "Schedule Slot",
            filters={
                "parent": self.practitioner,
                "parenttype": "Healthcare Practitioner",
                "parentfield": "table_locw",
                "day": appointment_day,
            },
            fields=["from_time", "to_time"],
        )

        if not schedule_slots:
            frappe.throw(
                _("Practitioner {0} does not have a scheduled working day on {1}. Working days are: {2}")
                .format(self.practitioner, appointment_day, self.get_working_days())
            )

        appointment_time = get_time(self.time)
        is_within_schedule = False

        for slot in schedule_slots:
            from_time = get_time(slot.from_time)
            to_time = get_time(slot.to_time)

            if from_time <= appointment_time <= to_time:
                is_within_schedule = True
                break

        if not is_within_schedule:
            frappe.throw(
                _("Appointment time {0} is outside practitioner's scheduled working hours.")
                .format(self.time)
            )

    def get_working_days(self):
        working_days = frappe.get_all(
            "Schedule Slot",
            filters={
                "parent": self.practitioner,
                "parenttype": "Healthcare Practitioner",
                "parentfield": "table_locw",
            },
            fields=["day"],
            distinct=True
        )
        return ", ".join([day.day for day in working_days])

    # ==========================
    # STATUS MANAGEMENT
    # ==========================

    def update_status_to_scheduled(self):
        if self.status == "Open":
            self.status = "Scheduled"

    # ==========================
    # WAITLIST PROMOTION
    # ==========================

    def promote_waitlist(self):

        if frappe.flags.in_waitlist_promotion:
            return

        frappe.flags.in_waitlist_promotion = True

        try:
            waitlisted = frappe.get_all(
                "Appointment Waitlist",
                filters={
                    "practitioner": self.practitioner,
                    "date": self.date,
                    "status": "Waiting",
                },
                order_by="creation asc",
                limit=1,
            )

            if not waitlisted:
                return

            wait_doc = frappe.get_doc("Appointment Waitlist", waitlisted[0].name)

            # Check 1-hour conflict before promoting
            temp_doc = frappe.get_doc({
                "doctype": "Patient Appointment",
                "patient": wait_doc.patient,
                "practitioner": self.practitioner,
                "date": self.date,
                "time": wait_doc.time,
                "status": "Scheduled",
            })

            temp_doc.validate_double_booking()

            temp_doc.insert(ignore_permissions=True)
            temp_doc.submit()  # This triggers on_submit() which sends notifications

            wait_doc.status = "Converted"
            wait_doc.save(ignore_permissions=True)

            self.notify_waitlisted_patient(wait_doc.patient, temp_doc.name)

            frappe.db.commit()

        finally:
            frappe.flags.in_waitlist_promotion = False

    # ==========================
    # NOTIFICATION
    # ==========================

    def notify_waitlisted_patient(self, patient, appointment_name):

        patient_doc = frappe.get_doc("Healthcare Patient", patient)

        if patient_doc.email:
            frappe.sendmail(
                recipients=[patient_doc.email],
                subject="Appointment Scheduled from Waitlist",
                message=f"""
                Good news!

                A slot became available and your appointment has been scheduled.

                Appointment ID: {appointment_name}
                Date: {self.date}
                Time: {self.time}

                Please contact the clinic if you need to reschedule.
                """,
            )

    # ==========================
    # APPOINTMENT CONFIRMATION
    # ==========================

    def send_appointment_confirmation(self):
        """Send email confirmation when appointment is booked"""

        try:
            # Get patient details
            patient_doc = frappe.get_doc("Healthcare Patient", self.patient)

            # Get practitioner name
            practitioner_name = frappe.db.get_value(
                "Healthcare Practitioner",
                self.practitioner,
                "practitioner_name"
            ) or self.practitioner

            if patient_doc.email:
                # Format time for display
                import datetime
                if self.time:
                    time_obj = datetime.datetime.strptime(str(self.time), "%H:%M:%S").time()
                    formatted_time = time_obj.strftime("%I:%M %p")
                else:
                    formatted_time = "Time TBD"

                # Format date for display
                if self.date:
                    date_obj = datetime.datetime.strptime(str(self.date), "%Y-%m-%d").date()
                    formatted_date = date_obj.strftime("%B %d, %Y")
                else:
                    formatted_date = str(self.date)

                frappe.sendmail(
                    recipients=[patient_doc.email],
                    subject="Appointment Confirmed - Better Care",
                    message=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8fafc;">
                        <div style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">

                            <div style="text-align: center; margin-bottom: 30px;">
                                <h1 style="color: #0f172a; margin: 0; font-size: 24px;">✅ Appointment Confirmed</h1>
                                <p style="color: #64748b; margin: 5px 0 0 0;">Your healthcare appointment has been scheduled</p>
                            </div>

                            <div style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                                <h3 style="color: #0369a1; margin: 0 0 15px 0; font-size: 16px;">Appointment Details</h3>
                                <table style="width: 100%; border-collapse: collapse;">
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; width: 30%;">Appointment ID:</td>
                                        <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{self.name}</td>
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
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Status:</td>
                                        <td style="padding: 8px 0;"><span style="background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;">Scheduled</span></td>
                                    </tr>
                                </table>
                            </div>

                            <div style="background: #f8fafc; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                                <h4 style="color: #0f172a; margin: 0 0 10px 0; font-size: 14px;">📋 What to bring:</h4>
                                <ul style="color: #64748b; font-size: 14px; margin: 0; padding-left: 20px;">
                                    <li>Government-issued ID</li>
                                    <li>Insurance card</li>
                                    <li>Any relevant medical records</li>
                                    <li>List of current medications if currently on any</li>
                                </ul>
                            </div>

                            <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px; margin-bottom: 25px;">
                                <p style="color: #92400e; margin: 0; font-size: 14px; font-weight: 500;">
                                    ⏰ Please arrive 15 minutes early for check-in and paperwork.
                                </p>
                            </div>

                            <div style="text-align: center; margin-bottom: 20px;">
                                <p style="color: #64748b; font-size: 14px; margin-bottom: 15px;">
                                    Need to make changes to your appointment?
                                </p>
                                <a href="{frappe.utils.get_url()}/healthcare_portal?appointment={self.name}"
                                   style="background: #0f172a; color: white; padding: 12px 24px; text-decoration: none;
                                          border-radius: 8px; font-weight: 600; display: inline-block;">
                                    Manage Appointment
                                </a>
                            </div>

                            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 25px 0;">

                            <div style="text-align: center;">
                                <p style="color: #64748b; font-size: 12px; margin: 0;">
                                    This is an automated message from Better Care Healthcare Portal.<br>
                                    Please do not reply to this email.
                                </p>
                            </div>
                        </div>
                    </div>
                    """,
                )

                frappe.logger().info(f"Appointment confirmation sent to {patient_doc.email} for appointment {self.name}")

        except Exception as e:
            # Don't fail the appointment creation if email fails
            frappe.logger().error(f"Failed to send appointment confirmation for {self.name}: {str(e)}")
            pass

    # ==========================
    # PRACTITIONER NOTIFICATION
    # ==========================

    def notify_practitioner(self):
        """Notify practitioner of new appointment booking"""

        try:
            # Get practitioner details
            practitioner_doc = frappe.get_doc("Healthcare Practitioner", self.practitioner)

            # Get patient name
            patient_name = frappe.db.get_value(
                "Healthcare Patient",
                self.patient,
                "full_name"
            ) or self.patient

            if practitioner_doc.email:
                # Format time and date for display
                import datetime
                if self.time:
                    time_obj = datetime.datetime.strptime(str(self.time), "%H:%M:%S").time()
                    formatted_time = time_obj.strftime("%I:%M %p")
                else:
                    formatted_time = "Time TBD"

                if self.date:
                    date_obj = datetime.datetime.strptime(str(self.date), "%Y-%m-%d").date()
                    formatted_date = date_obj.strftime("%B %d, %Y")
                else:
                    formatted_date = str(self.date)

                frappe.sendmail(
                    recipients=[practitioner_doc.email],
                    subject="New Appointment Booked - Better Care",
                    message=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8fafc;">
                        <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">

                            <div style="text-align: center; margin-bottom: 25px;">
                                <h1 style="color: #0f172a; margin: 0; font-size: 22px;">📅 New Appointment Booked</h1>
                                <p style="color: #64748b; margin: 5px 0 0 0;">A patient has scheduled an appointment with you</p>
                            </div>

                            <div style="background: #f0fdf4; border: 1px solid #22c55e; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                                <h3 style="color: #166534; margin: 0 0 15px 0; font-size: 16px;">Appointment Details</h3>
                                <table style="width: 100%; border-collapse: collapse;">
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b; font-weight: 500; width: 30%;">Patient:</td>
                                        <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{patient_name}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b; font-weight: 500;">Date:</td>
                                        <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{formatted_date}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b; font-weight: 500;">Time:</td>
                                        <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{formatted_time}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b; font-weight: 500;">Appointment ID:</td>
                                        <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{self.name}</td>
                                    </tr>
                                </table>
                            </div>

                            <div style="text-align: center; margin-bottom: 20px;">
                                <a href="{frappe.utils.get_url()}/practitioner-portal"
                                   style="background: #0f172a; color: white; padding: 10px 20px; text-decoration: none;
                                          border-radius: 8px; font-weight: 600; display: inline-block; margin-right: 10px;">
                                    View in Portal
                                </a>
                                <a href="{frappe.utils.get_url()}/app/patient-appointment/{self.name}"
                                   style="background: #06b6d4; color: white; padding: 10px 20px; text-decoration: none;
                                          border-radius: 8px; font-weight: 600; display: inline-block;">
                                    Manage Appointment
                                </a>
                            </div>

                            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">

                            <div style="text-align: center;">
                                <p style="color: #64748b; font-size: 12px; margin: 0;">
                                    Better Care Healthcare Management System<br>
                                    This is an automated notification.
                                </p>
                            </div>
                        </div>
                    </div>
                    """,
                )

                frappe.logger().info(f"Practitioner notification sent to {practitioner_doc.email} for appointment {self.name}")

        except Exception as e:
            # Don't fail the appointment creation if email fails
            frappe.logger().error(f"Failed to send practitioner notification for {self.name}: {str(e)}")
            pass


    # ==========================
    # CANCELLATION NOTIFICATION
    # ==========================

    def send_cancellation_notification(self):
        """Send email notification when appointment is cancelled"""

        try:
            # Get patient details
            patient_doc = frappe.get_doc("Healthcare Patient", self.patient)

            # Get practitioner name
            practitioner_name = frappe.db.get_value(
                "Healthcare Practitioner",
                self.practitioner,
                "practitioner_name"
            ) or self.practitioner

            if patient_doc.email:
                # Format time and date for display
                import datetime
                if self.time:
                    time_obj = datetime.datetime.strptime(str(self.time), "%H:%M:%S").time()
                    formatted_time = time_obj.strftime("%I:%M %p")
                else:
                    formatted_time = "Time TBD"

                if self.date:
                    date_obj = datetime.datetime.strptime(str(self.date), "%Y-%m-%d").date()
                    formatted_date = date_obj.strftime("%B %d, %Y")
                else:
                    formatted_date = str(self.date)

                frappe.sendmail(
                    recipients=[patient_doc.email],
                    subject="Appointment Cancelled - Better Care",
                    message=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8fafc;">
                        <div style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">

                            <div style="text-align: center; margin-bottom: 25px;">
                                <h1 style="color: #dc2626; margin: 0; font-size: 24px;">❌ Appointment Cancelled</h1>
                                <p style="color: #64748b; margin: 5px 0 0 0;">Your appointment has been successfully cancelled</p>
                            </div>

                            <div style="background: #fee2e2; border: 1px solid #fca5a5; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                                <h3 style="color: #991b1b; margin: 0 0 15px 0; font-size: 16px;">Cancelled Appointment</h3>
                                <table style="width: 100%; border-collapse: collapse;">
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; width: 30%;">Appointment ID:</td>
                                        <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{self.name}</td>
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
                                </table>
                            </div>

                            <div style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                                <h4 style="color: #0369a1; margin: 0 0 10px 0; font-size: 14px;">📋 What happens next:</h4>
                                <ul style="color: #475569; font-size: 14px; margin: 0; padding-left: 20px;">
                                    <li>Your appointment slot is now available for other patients</li>
                                    <li>If there was a waitlist, the next patient has been notified</li>
                                    <li>No charges apply for this cancellation</li>
                                    <li>You can book a new appointment anytime through the portal</li>
                                </ul>
                            </div>

                            <div style="text-align: center; margin-bottom: 20px;">
                                <p style="color: #64748b; font-size: 14px; margin-bottom: 15px;">
                                    Need to book a new appointment?
                                </p>
                                <a href="{frappe.utils.get_url()}/healthcare_portal"
                                   style="background: #0f172a; color: white; padding: 12px 24px; text-decoration: none;
                                          border-radius: 8px; font-weight: 600; display: inline-block;">
                                    Book New Appointment
                                </a>
                            </div>

                            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 25px 0;">

                            <div style="text-align: center;">
                                <p style="color: #64748b; font-size: 12px; margin: 0;">
                                    This is an automated message from Better Care Healthcare Portal.<br>
                                    If you have questions, please contact our office directly.<br>
                                    © 2026 Better.Care. All rights reserved. 
                                </p>
                            </div>
                        </div>
                    </div>
                    """,
                )

                frappe.logger().info(f"Cancellation notification sent to {patient_doc.email} for appointment {self.name}")

        except Exception as e:
            # Don't fail the cancellation if email fails
            frappe.logger().error(f"Failed to send cancellation notification for {self.name}: {str(e)}")
            pass


@frappe.whitelist()
def cancel_appointment(appointment):
    doc = frappe.get_doc("Patient Appointment", appointment)

    # Update status (now allowed after submission due to allow_on_submit)
    doc.status = "Cancelled"
    doc.save(ignore_permissions=True)

    # Send cancellation notification
    doc.send_cancellation_notification()

    frappe.db.commit()
    return True