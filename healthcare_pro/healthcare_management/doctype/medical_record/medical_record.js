// Copyright (c) 2026, Nelson Atuya and contributors
// For license information, please see license.txt

 frappe.ui.form.on('Medical Record', {
    appointment: function(frm) {
        if (frm.doc.appointment) {
            
            frappe.db.get_value('Patient Appointment', frm.doc.appointment, 
                ['patient', 'practitioner'], (r) => {
                    if (r) {
                        frm.set_value('patient', r.patient);
                        frm.set_value('practitioner', r.practitioner);
                       
                    }
                }
            );
        }
    }
});