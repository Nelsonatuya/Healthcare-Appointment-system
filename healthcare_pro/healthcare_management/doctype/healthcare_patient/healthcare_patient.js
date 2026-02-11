// Copyright (c) 2026, Nelson Atuya and contributors
// For license information, please see license.txt

 frappe.ui.form.on("Healthcare Patient", {
 	refresh(frm) {
        frm.add_custom_button(__('Book Appointment'), function() {
            frappe.model.with_doctype('Patient Appointment', function() {
                let appointment = frappe.model.get_new_doc('Patient Appointment');
                appointment.patient = frm.doc.name;
                frappe.set_route('Form', 'Patient Appointment', appointment.name);
            });
        }, __("Book Appointment"));
    
 	},
 });
