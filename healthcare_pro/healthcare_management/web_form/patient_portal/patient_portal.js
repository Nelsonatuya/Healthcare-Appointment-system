frappe.ready(function() {
    if (frappe.web_form) {
        frappe.web_form.after_save = function(data) {
            var patient = (data && (data.patient || data.name))
                || (frappe.web_form.doc && frappe.web_form.doc.name);

            if (patient) {
                try {
                    localStorage.setItem('book_appointment_patient', patient);
                } catch (e) {
                    // Ignore storage errors and continue with URL-based flow.
                }

                var targetUrl = '/book-an-appointment/new?patient=' + encodeURIComponent(patient);
                var btn = document.querySelector('.book-appointment-btn')
                    || document.querySelector('.success-state a.btn-primary');

                if (btn) {
                    btn.href = targetUrl;
                }

                var button = document.querySelector('.success-state .btn-primary');
                if (button && button.tagName === 'BUTTON') {
                    button.onclick = function() {
                        window.location.href = targetUrl;
                    };
                }
            }
        };
    }
});
