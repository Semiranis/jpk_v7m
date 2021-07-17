// Copyright (c) 2021, Levitating Frog and contributors
// For license information, please see license.txt

frappe.ui.form.on('JPK Tax Office Importer', {
	process: function(frm) {
		import_tax_office_codes(frm);
	}
});

function import_tax_office_codes(frm) {
	var file_path = frm.fields_dict["xsd_file"].value;
	var update = frm.fields_dict["update_existing"].value;

	frappe.show_alert("Import started. Please wait...", 5);

	frm.call('import_from_xsd', {xsd: file_path, update_existing: update})
	.then( r => {msgprint(r.message);});
}
