# Healthcare Pro - Complete System Documentation

## Overview

Healthcare Pro is a comprehensive healthcare appointment scheduling and management system built on Frappe Framework. It provides patient registration, appointment booking with conflict detection and waitlisting, medical records management, practitioner scheduling, and dual portal interfaces for patients and practitioners.

**Site Name:** better.care
**App Name:** Healthcare Pro  
**Publisher:** Nelson Atuya  
**Framework:** Frappe  

---

## Table of Contents

1. [DocTypes & Data Models](#1-doctypes--data-models)
2. [API Endpoints](#2-api-endpoints)
3. [User Flows & Workflows](#3-user-flows--workflows)
4. [Portal Interfaces](#4-portal-interfaces)
5. [Booking System & Conflict Handling](#5-booking-system--conflict-handling)
6. [Waitlist Management](#6-waitlist-management)
7. [Email Notifications](#7-email-notifications)
8. [Google Calendar Integration](#8-google-calendar-integration)
9. [Permissions & Security](#9-permissions--security)
10. [Data Model Relationships](#10-data-model-relationships)

---

## 1. DocTypes & Data Models

### 1.1 Healthcare Patient
**Naming:** `PAT-.YYYY-.#####`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| full_name | Data | Yes | Patient's full name |
| date_of_birth | Date | Yes | Used for age calculation |
| gender | Select | Yes | Male / Female / Other |
| email | Data | Yes | Used for login & notifications |
| mobile | Phone | Yes | Contact number |
| insurance_id | Data | Yes | Health insurance ID |
| insurance_card | Attach Image | No | Insurance card upload |
| id_attachment | Attach | No | ID document upload |
| age | Data | No | Auto-calculated from DOB |
| give_consent | Check | No | Data processing consent |

**Validations:**
- Duplicate detection on: full_name + DOB + gender + mobile + email
- Age auto-calculated on validate

---

### 1.2 Healthcare Practitioner
**Naming:** `DOC-.#####`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| practitioner_name | Data | Yes | Display name |
| specialization | Link | Yes | Links to Medical Specialty |
| department | Link | No | Links to Department |
| user_id | Link | No | Links to User account |
| email | Data | No | Contact email |
| mobile | Phone | No | Contact phone |
| table_locw | Table | No | Schedule Slot child table |

**Schedule Slot (Child Table):**

| Field | Type | Notes |
|-------|------|-------|
| day | Select | Monday through Sunday |
| from_time | Time | Working hours start |
| to_time | Time | Working hours end |

---

### 1.3 Patient Appointment
**Naming:** `APP-.YYYY.###` | **Submittable**

| Field | Type | Notes |
|-------|------|-------|
| patient | Link | Links to Healthcare Patient |
| practitioner | Link | Links to Healthcare Practitioner |
| date | Date | Appointment date |
| time | Time | Appointment time |
| status | Select | Open / Scheduled / Completed / Cancelled |
| google_event_id | Data | Google Calendar event reference |

**Validation Pipeline (on validate):**
1. `validate_datetime()` — Prevents past dates/times
2. `validate_double_booking()` — 1-hour overlap detection for practitioner
3. `check_global_holiday()` — Blocks appointments on holiday dates
4. `check_practitioner_leave()` — Prevents bookings during leave periods
5. `check_practitioner_schedule()` — Validates time falls within working hours
6. `update_status_to_scheduled()` — Changes status from Open to Scheduled

**On Submit:**
- Creates Google Calendar event
- Sends confirmation email to patient
- Sends notification email to practitioner

**On Cancellation:**
- Deletes Google Calendar event
- Promotes first waitlisted patient to a new appointment
- Sends cancellation email to patient

---

### 1.4 Appointment Waitlist
**Naming:** `AW.-YYYY-.####`

| Field | Type | Notes |
|-------|------|-------|
| patient | Link | Links to Healthcare Patient |
| practitioner | Link | Links to Healthcare Practitioner |
| date | Date | Requested appointment date |
| time | Time | Requested appointment time |
| priority | Int | Queue priority |
| status | Select | Waiting / Notified / Converted |

---

### 1.5 Medical Record
**Naming:** `REC-.YYYY-.#####` | **Submittable**

| Field | Type | Notes |
|-------|------|-------|
| patient | Link | Links to Healthcare Patient |
| practitioner | Link | Links to Healthcare Practitioner |
| appointment | Link | Links to Patient Appointment |
| date | Date | Record date |
| symptoms | Small Text | Patient symptoms |
| diagnosis | Text Editor | Medical diagnosis |
| prescription | Table | Medical Entry child table |
| lab_results | Attach | Lab test file upload |

**Medical Entry (Prescription Child Table):**

| Field | Type | Notes |
|-------|------|-------|
| drug_name | Data | Medication name |
| dosage | Data | Dosage specification |
| period | Select | Morning / Twice a Day / Weekly |

**On Submit:** Sets linked appointment status to Completed.

---

### 1.6 Practitioner Leave
**Naming:** `LV.####` | **Submittable**

| Field | Type | Notes |
|-------|------|-------|
| practitioner | Link | Links to Healthcare Practitioner |
| from_date | Date | Leave start |
| to_date | Date | Leave end |
| reason | Small Text | Leave reason |
| status | Select | Pending / Approved |

**Validation:** Blocks approval if practitioner has scheduled appointments during leave period.

---

### 1.7 Healthcare Holiday
**Naming:** `HDY-.###`

| Field | Type | Notes |
|-------|------|-------|
| holiday_name | Data | Name of holiday |
| holiday_date | Date | Date of holiday |
| description | Small Text | Holiday description |

Appointments cannot be scheduled on dates matching a Healthcare Holiday record.

---

### 1.8 Other DocTypes

- **Medical Specialty** — Master list of practitioner specializations (e.g., Cardiology, Dentistry)
- **Department** — Organizational departments
- **Patient Feedback** — Star rating and comment per practitioner (submittable)
- **Medicine** — Placeholder for future drug master implementation

---

## 2. API Endpoints

### Patient Registration & Authentication

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `register_patient.register_new_patient` | POST | Guest | Register new patient, creates User account, sends password reset email |
| `register_patient.get_patients` | GET | Login | Returns current logged-in patient's details |

### Appointment Management

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `create_appointment.book_appointment` | POST | Login | Book appointment with auto-waitlist on conflict |
| `get_appointments.get_appointments` | GET | Login | List appointments (filterable by patient, practitioner, date, status) |
| `enhanced_booking.check_booking_conflicts` | POST | Login | Pre-check for patient and practitioner conflicts before booking |
| `enhanced_booking.confirm_booking` | POST | Login | Confirm booking after conflict check, supports force_waitlist |
| `patient_appointment.cancel_appointment` | POST | Login | Cancel appointment, triggers waitlist promotion |

### Practitioner Management

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `get_practitioners.get_practitioners_with_specializations` | GET | Guest | List practitioners with ratings, availability, working hours |
| `get_practitioners.get_practitioner_specializations` | GET | Guest | List unique specializations for filtering |
| `get_practitioners.search_practitioners` | GET | Guest | Search practitioners by name or specialty |
| `get_current_practitioner.get_current_practitioner` | GET | Login | Get logged-in practitioner's record |

### Scheduling

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `get_schedule.get_practitioner_schedule` | GET | Guest | Get working hours for all or specific practitioner |

### Medical Records

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `create_medical_record.create_medical_record` | POST | Login | Create medical record linked to appointment |
| `create_medical_record.get_medical_records` | GET | Login | Get medical records for current patient |

---

## 3. User Flows & Workflows

### 3.1 Patient Registration

1. Patient fills registration form (full name, DOB, gender, email, mobile, insurance ID)
2. System validates no duplicate patient exists
3. Creates Healthcare Patient record (`PAT-YYYY-#####`)
4. Creates Frappe User account with Website User role
5. Sends password reset email
6. Patient sets password and can log into the portal

### 3.2 Appointment Booking

1. Patient selects a practitioner (can search by name or specialty)
2. System shows practitioner's available days (Mon, Wed, Fri, etc.)
3. Patient picks a date and time slot
4. **Pre-check phase:** System calls `check_booking_conflicts` to detect:
   - Patient already has an appointment at that time (blocked)
   - Practitioner slot already booked (offered waitlist)
5. **Confirmation phase:** Patient confirms or joins waitlist
6. **Validation pipeline** runs (past date, overlap, holiday, leave, schedule)
7. Appointment created and submitted
8. Google Calendar event created
9. Confirmation emails sent to patient and practitioner

### 3.3 Appointment Cancellation

1. Patient clicks Cancel on an appointment
2. Confirmation modal shows appointment details and consequences
3. On confirm: appointment status set to Cancelled
4. Google Calendar event deleted
5. Cancellation email sent to patient
6. **Waitlist promotion:** First waiting patient auto-promoted to a new appointment and notified

### 3.4 Appointment Rescheduling

1. Patient clicks Reschedule on an appointment
2. Selects new date and time slot
3. Original appointment is cancelled
4. New appointment is booked with the same practitioner
5. Waitlist promotion runs on the cancelled slot

### 3.5 Medical Record Creation

1. After appointment, practitioner opens appointment in desk
2. Clicks "Create Medical Record" (pre-fills patient, practitioner, appointment)
3. Fills in symptoms, diagnosis, prescriptions, lab results
4. On submit: linked appointment status changes to Completed
5. Patient can view record in the patient portal

---

## 4. Portal Interfaces

### 4.1 Patient Portal (`/healthcare_portal`)

**Design:**  modern healthcare theme with ocean blue palette, DM Sans typography, scroll animations, and responsive mobile menu.

**Pages:**
- **Dashboard (Home)** — Hero banner with greeting, stats bar (upcoming appointments, medical records, waitlisted), services section, practitioner directory, upcoming appointments, personal details
- **Book Appointment** — Practitioner selector with availability days, date picker with hints, time slot grid, conflict detection modal
- **My Appointments** — Table of all appointments with status badges, cancel/reschedule/view record actions
- **Medical Records** — Table of records with view detail modal (diagnosis, symptoms, prescriptions)
- **My Profile** — Gradient header with avatar, personal information card, contact & insurance card

**Features:**
- Preloader animation on page load
- Transparent topbar overlaying hero, solid on other pages
- Scroll-triggered fade-in animations (bidirectional)
- Scrolling marquee text strip
- Mobile hamburger dropdown menu (< 900px)
- Toast notifications
- Real-time data from Frappe API

### 4.2 Practitioner Portal (`/practitioner_portal`)

**Design:** Professional dark-mode interface with navy and teal palette.

**Pages:**
- **Dashboard** — Stats (today's appointments, this week, completed, waitlisted), today's appointment list
- **My Calendar** — Month view (calendar grid with appointment chips) and Week view (7am-8pm time grid with positioned appointment blocks)
- **All Appointments** — Paginated table view sorted newest first
- **My Profile** — Practitioner details and working schedule display

---

## 5. Booking System & Conflict Handling

### Conflict Types

| Conflict | Detection | Outcome |
|----------|-----------|---------|
| Patient double-booking | Patient has appointment at same time with any practitioner | Booking blocked |
| Practitioner slot taken | Another patient booked at same time with same practitioner | Offered waitlist |
| 1-hour overlap | Practitioner has appointment within 1 hour of requested time | Auto-waitlisted |
| Global holiday | Appointment date matches Healthcare Holiday | Booking blocked |
| Practitioner leave | Appointment date falls within approved leave period | Booking blocked |
| Outside schedule | Appointment time outside practitioner's working hours | Booking blocked |

### Booking Confirmation Modal

- **No conflicts:** Shows appointment details with Confirm Booking button
- **Patient conflict:** Shows warning, Confirm button hidden (blocked)
- **Practitioner conflict:** Shows warning with Join Waitlist button

---

## 6. Waitlist Management

### How It Works

1. When a slot is unavailable, patient is added to Appointment Waitlist with status "Waiting"
2. Duplicate waitlist entries for same patient/practitioner/date/time are prevented
3. When an appointment is cancelled, `promote_waitlist()` runs:
   - Finds first "Waiting" entry for same practitioner/date/time
   - Creates new Patient Appointment from waitlist entry
   - Changes waitlist status to "Converted"
   - Sends notification email to promoted patient
4. Promotion is automatic and immediate on cancellation

---

## 7. Email Notifications

| Event | Recipient | Content |
|-------|-----------|---------|
| Appointment booked | Patient | Confirmation with date, time, practitioner details |
| Appointment booked | Practitioner | New appointment notification with patient details |
| Appointment cancelled | Patient | Cancellation confirmation with "What happens next" section |
| Waitlist promoted | Patient | Slot available notification with new appointment details |
| Registration | Patient | Password reset link email |

All emails use rich HTML formatting with professional styling.

---

## 8. Google Calendar Integration

- **On appointment submit:** Creates a 1-hour Google Calendar event with appointment details
- **On appointment cancel:** Deletes the Google Calendar event
- **Configuration:** Uses Frappe's Google Settings (refresh_token, client_id, client_secret)
- **Error handling:** If sync fails, appointment still saved locally with logged error
- **Event ID** stored in `google_event_id` field on Patient Appointment

---

## 9. Permissions & Security

| DocType | System Manager | Healthcare Receptionist | Healthcare Doctor | Practitioner |
|---------|---------------|------------------------|-------------------|--------------|
| Healthcare Patient | Full CRUD | Full CRUD | Read only | — |
| Patient Appointment | Full CRUD | — | — | — |
| Medical Record | Full CRUD + Submit | — | — | Full CRUD + Submit |
| Practitioner Leave | Full CRUD + Submit | — | — | — |
| Healthcare Holiday | Full CRUD | — | — | — |

**API Access Levels:**
- **Guest access:** Patient registration, practitioner listings, schedule viewing
- **Authenticated:** Appointment booking/management, medical records, profile access
- **Row-level security:** Patients see only their own data; practitioners see only their appointments

---

## 10. Data Model Relationships

```
Healthcare Patient (PAT-YYYY-#####)
  |
  |-- Patient Appointment (many)
  |-- Medical Record (many)
  |-- Appointment Waitlist (many)
  |-- Patient Feedback (many)

Healthcare Practitioner (DOC-#####)
  |
  |-- Schedule Slot [child table] (many)
  |-- Patient Appointment (many)
  |-- Medical Record (many)
  |-- Practitioner Leave (many)
  |-- Appointment Waitlist (many)
  |-- Patient Feedback (many)
  |-- Medical Specialty [link]
  |-- Department [link]

Patient Appointment (APP-.YYYY.###)
  |
  |-- Medical Record (one)
  |-- Google Calendar Event (one, external)
  |-- Triggers: Appointment Waitlist promotion on cancel

Appointment Waitlist (AW.-YYYY-.####)
  |
  |-- Promoted to: Patient Appointment (on slot availability)
```

---

## Tech Stack

- **Backend:** Python 3 / Frappe Framework
- **Frontend (Portals):** Vanilla HTML, CSS, JavaScript
- **Database:** MariaDB (via Frappe ORM)
- **Email:** Frappe email queue (enqueue)
- **Calendar:** Google Calendar API
- **Design:** DM Sans font, ocean blue palette, CiyaCare-inspired UI
