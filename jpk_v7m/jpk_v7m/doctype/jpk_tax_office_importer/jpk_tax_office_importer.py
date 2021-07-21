# Copyright (c) 2021, Levitating Frog and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

from jpk_v7m.external_tools.mf_xsd_extractor.xsd_extractor import *


class JPKTaxOfficeImporter(Document):

	@frappe.whitelist()
	def import_from_xsd(self,
			    xsd,
			    type_name = "TKodUS",
			    update_existing = True,
			    change_case = True
			    ):
		
		restrictions = xsd_extract_documented_restrictions(
			frappe.get_site_path() + xsd,
			polish_title_case = change_case
			)

		if type_name not in restrictions:
			return "This file doesn't contain any restrictions for " + type_name

		codes = restrictions[type_name]

		new_codes = 0
		updated_codes = 0
		updated_names = 0

		for code in codes:
			# can be only one (or zero), because code is unique
			existing_tax_office = frappe.db.get_list("JPK Tax Office", filters = {'code': code})

			if len(existing_tax_office):
				current_name = existing_tax_office[0].name
				new_name = codes[code]
				
				if update_existing and current_name != new_name:
					updated_names += 1
					frappe.rename_doc("JPK Tax Office", current_name, new_name)
			else:
				if not frappe.db.exists("JPK Tax Office", codes[code]):
					new_codes += 1
					# create new "JPK Tax Office" type document
					tax_office = frappe.get_doc({'doctype': 'JPK Tax Office', "code": code, "tax_office": codes[code]})
					# save the document
					tax_office.insert()
				elif update_existing:
					updated_codes += 1
					tax_office = frappe.get_doc("JPK Tax Office", codes[code])
					tax_office.code = code
					tax_office.save()

		return "<p>Number of tax offices added: " + str(new_codes) + "<br>Updated codes: " + str(updated_codes) + "<br>Updated names: " + str(updated_names) + "</p><p>Number of tax offices found in XSD: " + str(len(codes)) + "</p>"
