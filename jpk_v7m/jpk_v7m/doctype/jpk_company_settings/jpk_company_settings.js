// Copyright (c) 2021, Marcin Lewicz and contributors
// For license information, please see license.txt

frappe.ui.form.on('JPK Company Settings', {
	// Manual refreshing of lists of accounts
	refresh_lists: function(frm) {
		refresh_tax_accounts_lists(frm);
	},
	before_save(frm) {
		// Automatic refreshing of lists of accounts
		refresh_tax_accounts_lists_before_save(frm);
	}		
});


function refresh_tax_accounts_lists(frm) {

	// Clear tables to avoid duplicate rows
	clear_tables(frm);

	// Load tables again (call server script)
	frm.call('fill_tax_accounts_lists')
	.then( r => {
		frappe.show_alert(__('Accounts lists refreshed'));
		// Set status "not saved"
		frm.dirty();
		frm.refresh();
	});
}

// Almost same as refresh_tax_accounts_lists, but called before saving document
// so "frm.dirty()" shouldn't be called
function refresh_tax_accounts_lists_before_save(frm) {

	clear_tables(frm);

	frm.call('fill_tax_accounts_lists')
	.then( r => {
		frappe.show_alert(__('Accounts lists refreshed'));
		frm.refresh();
	});
}

function clear_tables(frm) {
	frm.clear_table('input_tax_accounts_list');
	frm.clear_table('output_tax_accounts_list');
}
