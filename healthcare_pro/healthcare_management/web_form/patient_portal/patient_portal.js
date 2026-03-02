frappe.ready(function() {
    if (frappe.web_form) {
        frappe.web_form.after_save = function(data) {
            if (data && data.patient) {
                // Try to find an <a> tag first
                var btn = document.querySelector('.alert-success + a.btn-primary');
                if (btn) {
                    btn.href = '/book-an-appointment?patient=' + encodeURIComponent(data.patient);
                } else {
                    // Try to find a <button> element
                    var button = document.querySelector('.success-state .btn-primary');
                    if (button) {
                        button.onclick = function() {
                            window.location.href = '/book-an-appointment?patient=' + encodeURIComponent(data.patient);
                        };
                    }
                }
            }
        };
    }
});