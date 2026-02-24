// Copyright (c) 2026, Nelson Atuya and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient Appointment', {
    refresh: function(frm) {
        if (frm.doc.status !== 'Cancelled' && !frm.doc.__islocal) {
            // Create Medical Record button
            frm.add_custom_button(__('Create Medical Record'), function() {
                frappe.route_options = {
                    "appointment": frm.doc.name,
                    "patient": frm.doc.patient,
                    "practitioner": frm.doc.practitioner
                };
                frappe.set_route("Form", "Medical Record", "new-medical-record-1");
            }, __('Actions'));
            // Cancel Appointment button
            frm.add_custom_button(__('Cancel Appointment'), function() {
                frappe.call({
                    method: "healthcare_pro.healthcare_management.doctype.patient_appointment.patient_appointment.cancel_appointment",
                    args: {
                        appointment: frm.doc.name
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frm.reload_doc();
                            frappe.msgprint(__('Appointment has been cancelled.'));
                        }
                    }
                });
            }, __('Actions'));
        }
        // Set status to read-only if cancelled
        if (frm.doc.status === 'Cancelled') {
            frm.set_df_property('status', 'read_only', 1);
        }
    
    }
});