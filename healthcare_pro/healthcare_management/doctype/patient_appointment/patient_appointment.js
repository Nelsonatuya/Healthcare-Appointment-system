// Copyright (c) 2026, Nelson Atuya and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient Appointment', {
    refresh: function(frm) {
        if (frm.doc.status !== 'Cancelled' && !frm.doc.__islocal) {
            frm.add_custom_button(__('Create Medical Record'), function() {
                frappe.route_options = {
                    "appointment": frm.doc.name,
                    "patient": frm.doc.patient,
                    "practitioner": frm.doc.practitioner
                };
                frappe.set_route("Form", "Medical Record", "new-medical-record-1");
            }, __("Create Medical Record"));
        }
    }
});