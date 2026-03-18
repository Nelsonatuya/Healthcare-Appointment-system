import frappe
from frappe.utils import get_url
from frappe.utils.background_jobs import enqueue

@frappe.whitelist(allow_guest=True)
def register_new_patient():
    frappe.set_user("Administrator")

    # Read from JSON body (frontend sends Content-Type: application/json)
    data = frappe.request.get_json(silent=True) or frappe.form_dict

    full_name = data.get('full_name')
    date_of_birth = data.get('date_of_birth')
    gender = data.get('gender')
    email = data.get('email')
    mobile = data.get('mobile')
    insurance_id = data.get('insurance_id')
    insurance_card = data.get('insurance_card')
    id_attachment = data.get('id_attachment')

    required_fields = ['full_name', 'date_of_birth', 'gender', 'email', 'mobile', 'insurance_id']
    for field in required_fields:
        if not data.get(field):
            frappe.throw(f"Missing required field: {field}")

    if frappe.db.exists("User", email):
        frappe.throw("An account with this email already exists.")

    new_patient = frappe.get_doc({
        "doctype": "Healthcare Patient",
        "full_name": full_name,
        "date_of_birth": date_of_birth,
        "gender": gender,
        "email": email,
        "mobile": mobile,
        "insurance_id": insurance_id,
        "insurance_card": insurance_card,
        "id_attachment": id_attachment,
        "give_consent": 1,
        "published": 0
    })
    new_patient.insert(ignore_permissions=True)

    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": full_name,
        "send_welcome_email": 0,
        "user_type": "Website User",
        "roles": []
    })
    user.insert(ignore_permissions=True)
    frappe.db.commit()

    reset_key = frappe.generate_hash(length=32)
    frappe.db.set_value("User", email, "reset_password_key", reset_key)
    frappe.db.commit()

    reset_link = get_url(f"/update-password?key={reset_key}")
    enqueue(
        send_set_password_email,
        queue="short",
        now=False,
        email=email,
        full_name=full_name,
        reset_link=reset_link
    )

    return {"patient_name": new_patient.name}


def send_set_password_email(email, full_name, reset_link):
    frappe.sendmail(
        recipients=[email],
        subject="Set your better.care portal password",
        message=f"""
            <p>Hello {full_name},</p>
            <p>Your patient account has been created. Click below to set your password:</p>
            <p>
              <a href="{reset_link}"
                 style="background:#0d9488;color:white;padding:10px 20px;
                        border-radius:8px;text-decoration:none;display:inline-block;">
                Set My Password
              </a>
            </p>
            <p>If you did not register, please ignore this email.</p>
            <p>— The better.care team</p>
        """
    )


@frappe.whitelist()
def get_patients():
    patient = frappe.db.get_value(
        "Healthcare Patient",
        {"email": frappe.session.user},
        ["name", "full_name", "date_of_birth", "gender", "email", "mobile", "insurance_id", "age"],
        as_dict=True
    )
    if not patient:
        return []
    return [patient]