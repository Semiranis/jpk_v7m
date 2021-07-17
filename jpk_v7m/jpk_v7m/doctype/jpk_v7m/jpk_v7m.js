// Copyright (c) 2021, Marcin Lewicz and contributors
// For license information, please see license.txt

frappe.ui.form.on('JPK_V7M', {
	onload(frm) {
		if(frm.doc.year == undefined) {
			var today = new Date();
			var year = today.getFullYear();
			var month = today.getMonth();

			if (month == 0) {
				month = 12;
				year -= 1;
			}
			frm.set_value("year", year.toString());
			frm.set_value("month", month.toString());
		}

		frm.page.add_action_item("Generuj XML", function() {
			if(cur_frm.is_dirty()) frappe.msgprint("Dokument nie jest zapisany");
			else call_jpk_creator(cur_frm);
		})
	},

	onload_post_render(frm) {
		if(frm.fields_dict["guidance_accepted"].value == "")
			frm.fields_dict["guidance_section"].collapse(false);
		else
			frm.fields_dict["guidance_section"].collapse(true);
	},

	"guidance_accepted": function(frm) {
		frm.fields_dict["guidance_section"].collapse(true);
	},

	after_save(frm) {
		frm.page.add_action_item("Generuj XML", function() {
			if(cur_frm.is_dirty()) frappe.msgprint("Dokument nie jest zapisany");
			else call_jpk_creator(cur_frm);
		})
	}
});

function call_jpk_creator(frm)
{
	var is_guidance_accepted = "0";

	if(frm.fields_dict["guidance_accepted"].value == "Yes")
		is_guidance_accepted = "1";

	var purpose = "1";

	if(frm.fields_dict["is_amendment"].value == "Yes")
		purpose = "2";

	var tax_office_code = frm.fields_dict["tax_office_code"].value;
	var year = frm.fields_dict["year"].value;
	var month = frm.fields_dict["month"].value;
	
	var is_natural_person = "0";

	if(frm.fields_dict["is_natural_person"].value == "Yes")
		is_natural_person = "1";

	var first_name = frm.fields_dict["first_name"].value;
	var last_name = frm.fields_dict["last_name"].value;
	var date_of_birth = frm.fields_dict["date_of_birth"].value;

	var full_name = frm.fields_dict["company"].value;

	var tax_number = frm.fields_dict["tax_id"].value;
	var email = frm.fields_dict["email"].value;
	var phone = frm.fields_dict["phone_number"].value;
	var forwarded_excess_of_input_tax = frm.fields_dict["forwarded_excess_of_input_tax"].value;
	var amendment_reasons = "";
	var reasons_value = frm.fields_dict["amendment_reasons"].value;
	if (reasons_value) amendment_reasons = reasons_value;

	frm.call('get_jpk', {
	        is_guidance_accepted: is_guidance_accepted,
	        purpose: purpose,
	        tax_office_code: tax_office_code,
	        year: year,
	        month: month,
	        is_natural_person: is_natural_person,
	        first_name: first_name,
	        last_name: last_name,
	        date_of_birth: date_of_birth,
	        full_name: full_name,
	        tax_number: tax_number,
	        email: email,
	        phone: phone,
	        forwarded_excess_of_input_tax: forwarded_excess_of_input_tax,
	        amendment_reasons: amendment_reasons
	})
	.then(r => {
		if (r.message) {
		var file_name = r.message;

		// refresh attachments list
		frm.attachments.attachment_uploaded(file_name);
        	}
        })	
}
