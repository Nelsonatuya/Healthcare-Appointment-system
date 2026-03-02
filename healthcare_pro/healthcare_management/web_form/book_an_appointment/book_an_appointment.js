frappe.ready(function() {
    // Pre-fill patient field if context.patient is available
    if (window.frappe && frappe.web_form && frappe.web_form.context && frappe.web_form.context.patient) {
        frappe.web_form.set_value('patient', frappe.web_form.context.patient);
        // Optionally make the patient field read-only
        frappe.web_form.fields_dict['patient'].df.read_only = 1;
        frappe.web_form.fields_dict['patient'].refresh();
    }

    // After successful submission, show a button to view appointment details page
    frappe.web_form.after_save = function(data) {
        if (data && data.appointment_id) {
            let btn = document.createElement('a');
            btn.href = '/appointment-details?appointment=' + encodeURIComponent(data.appointment_id);
            btn.className = 'btn btn-primary';
            btn.innerText = 'Go to Appointment Details';
            btn.style.marginTop = '20px';
            // Insert the button after the form
            let form_wrapper = document.querySelector('.web-form-wrapper');
            if (form_wrapper) {
                form_wrapper.appendChild(btn);
            } else {
                document.body.appendChild(btn);
            }
        }
    };
});
