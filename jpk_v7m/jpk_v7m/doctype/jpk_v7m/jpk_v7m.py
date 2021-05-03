# -*- coding: utf-8 -*-
# Copyright (c) 2021, Marcin Lewicz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

from jpk_v7m.external_tools.JPK_V7M_creator.jpk_v7m_creator import *

class JPK_V7M(Document):

	def autoname(self):

		partial_name = self.abbr + "-" + self.year + "-" + "{:02d}".format(int(self.month)) + "-"

		other_docs = frappe.get_all("JPK_V7M",
			fields=['name'],
			filters={'name': ['like', partial_name + "%"]}
		)

		num_of_docs = len(other_docs)

		if self.is_amendment == "No":
			self.consecutive_number = 1
		elif len(other_docs) > 1:
			self.consecutive_number = num_of_docs + 1
		else:
			# Avoid "1" if it is amendment
			# "1" will mean "original" JPK_V7M
			self.consecutive_number = 2

		self.name = partial_name + str(self.consecutive_number)


	@frappe.whitelist()
	def get_jpk(self,
	        is_guidance_accepted,
	        purpose,
	        tax_office_code,
	        year,
	        month,
	        is_natural_person,
	        first_name,
	        last_name,
	        date_of_birth,
	        full_name,
	        tax_number,
	        email,
	        phone,
	        forwarded_excess_of_input_tax,
	        amendment_reasons
        ):

		#TODO: get documents from ERPNext
		# at the moment it does nothing...
		input_tax_documents = []
		output_tax_documents = []

		# TODO: get company abbreviation and insert it somewhere
		file_name = "JPK_V7M-" + str(year) + "-" + "{:02d}-".format(int(month)) + purpose + ".xml"
		file_path_short = "/private/files/" + file_name
		file_path = frappe.local.site + file_path_short

		create_jpk(
		        is_guidance_accepted,
		        purpose,
		        tax_office_code,
		        year,
		        month,
		        is_natural_person,
		        first_name,
		        last_name,
		        date_of_birth,
		        full_name,
		        tax_number,
		        email,
		        phone,
		        forwarded_excess_of_input_tax,
		        input_tax_documents,
		        output_tax_documents,
		        amendment_reasons,
			"ERPNext",
                        file_path
	        )

		new_file = frappe.get_doc({
			'doctype': 'File',
			'attached_to_doctype': self.doctype,
			'attached_to_name': self.name,
			'file_url': file_path_short,
			'file_name': file_name,
			'is_private': 1
		})
    
		new_file.insert()

		return file_name


