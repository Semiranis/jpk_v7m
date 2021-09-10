# -*- coding: utf-8 -*-
# Copyright (c) 2021, Marcin Lewicz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import calendar
from frappe.model.document import Document
from frappe.utils import flt

from jpk_v7m.external_tools.JPK_V7M_creator.jpk_v7m_creator import *
from jpk_v7m.helpers.eu import get_eu_countries, eu_codes

# Set global variables for better performance.
# Calling get_eu_countries() would be inefficient.
all_eu_countries = get_eu_countries()
# Get list of EU countries without Poland
other_eu_countries = get_eu_countries(omit_pl = True)


class JPK_V7M(Document):

	def autoname(self):
		"""
		Set custom document name, including:
		- company abbreviation,
		- year,
		- month
		- 1 (if first upload) or consecutive number (if it's amendment)
		"""

		partial_name = self.abbr + "-" + self.year + "-" + "{:02d}".format(int(self.month)) + "-"

		other_docs = frappe.get_all("JPK_V7M",
			fields=['name'],
			filters={'name': ['like', partial_name + "%"]}
		)

		num_of_docs = len(other_docs)

		if self.is_amendment == "No":
			self.consecutive_number = 1
		elif num_of_docs > 1:
			self.consecutive_number = num_of_docs + 1
		else:
			# Omit "1" if it is amendment
			# because "1" will mean "original" JPK_V7M
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
		amendment_reasons,
		input_tax_accounts,
		output_tax_accounts
	):
		"""
		Main method, calling functions for gathering processed documents
		data and creating JPK_V7M xml file.
		"""

		input_tax_documents = get_input_tax_documents(year, month, input_tax_accounts)
		output_tax_documents = get_output_tax_documents(year, month, output_tax_accounts)

		file_name = "JPK_V7M-" + self.name + ".xml"
		file_path_short = "/private/files/" + file_name
		file_path = frappe.local.site + file_path_short
		app_name = "ERPNext " + frappe.get_module("erpnext").__version__

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
			app_name,
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


def get_input_tax_documents(year, month, tax_accounts):
	"""
	Return processed:
	- Purchase Invoices from Poland
	- Purchase Invoices from other EU countries
	- Customs clearance data for import in standard procedure

	WARNING! Not implemented:
	- Internal documents
	"""

	documents = []

	# for calculation of month length
	year_int = int(year)
	month_int = int(month)
	
	month_days = calendar.monthrange(year_int, month_int)[1]

	# year and month in format YYYY-DD-
	year_and_month = year + "-" + "{:02d}".format(month_int) + "-"

	start_date = year_and_month + "01"
	end_date = year_and_month + str(month_days)

	# find and process all purchase invoices
	invoice_names = frappe.db.get_all(
		"Purchase Invoice",
		filters = [
				['posting_date', '>=', start_date],
				['posting_date', '<=', end_date]
			],
		order_by = 'creation'
		)

	for invoice_name in invoice_names:
		doc = frappe.get_doc("Purchase Invoice", invoice_name)
		document = process_input_tax_document(doc, tax_accounts)
		# document will be None if supplier not from EU
		if document:
			documents.append(document)

	# find and process all customs clearance journal entries
	journal_entries = frappe.db.get_all(
		"Journal Entry",
		filters = [
				['posting_date', '>=', start_date],
				['posting_date', '<=', end_date]
			],
		order_by = 'creation'
		)

	for entry_name in journal_entries:
		entry = frappe.get_doc("Journal Entry", entry_name)
		if entry.jpk_is_imp:
			document = process_import_input_tax_document(entry, tax_accounts)
			if document:
				documents.append(document)

	return documents


def get_output_tax_documents(year, month, tax_accounts):
	"""
	Returns processed:
	- Sales Invoices for customers in Poland
	- Purchase Invoices from suppliers from other EU contries

	WARNING! Not implemented:
	- import of goods in simplified procedure
	- internal documents
	"""

	# TODO:
	# - import of goods in simplified procedure
	# - internal documents

	documents = []

	# for calculation of month length
	year_int = int(year)
	month_int = int(month)
	
	# month length
	month_days = calendar.monthrange(year_int, month_int)[1]

	# year and month in format YYYY-DD-
	year_and_month = year + "-" + "{:02d}".format(month_int) + "-"

	start_date = year_and_month + "01"
	end_date = year_and_month + str(month_days)

	# find and process all sales invoices
	invoice_names = frappe.db.get_all(
		"Sales Invoice",
		filters = [
				['posting_date', '>=', start_date],
				['posting_date', '<=', end_date]
			],
		order_by = 'creation'
		)

	for invoice_name in invoice_names:
		doc = frappe.get_doc("Sales Invoice", invoice_name)
		document = process_output_tax_document(doc, tax_accounts)
		if document:
			documents.append(document)

	# find and process purchase invoices from EU suppliers
	purchase_invoice_names = frappe.db.get_all(
		"Purchase Invoice",
		filters = [
				['posting_date', '>=', start_date],
				['posting_date', '<=', end_date]
			],
		order_by = 'creation'
		)

	for invoice_name in purchase_invoice_names:

		doc = frappe.get_doc("Purchase Invoice", invoice_name)

		country = get_supplier_country(doc)

		if country.name in other_eu_countries:
			document = process_eu_purchase_output_tax_document(doc, tax_accounts)
			if document:
				documents.append(document)

	return documents


def get_output_tax_details(invoice, tax_accounts):
	"""
	Should return net and tax values for applicable tax rates, but is only
	partially implemented. Will work for rates: 5%, 7%, 8%, 22% and 23%,
	but WARNING: net for 0% can be wrong, and special cases are
	not implemented.
	"""

	vat0 = 0.0
	vat5 = {"net": 0.0, "amount": 0.0}
	vat7 = {"net": 0.0, "amount": 0.0}
	vat22 = {"net": 0.0, "amount": 0.0}
	item_net = {}

	for item in invoice.items:
		item_name = item.item_code or item.item_name
		item_net[item_name] = item.net_amount

	for tax in invoice.taxes:
		if tax.account_head in tax_accounts:
			item_wise_tax = json.loads(tax.item_wise_tax_detail)

			for i in item_wise_tax:
				i_tax = item_wise_tax[i]
				# important: if tax is 0: omit
				# because item can have other tax rate
				if i_tax and i_tax[0]:
					net = item_net.pop(i, None)
					if net:
						rate = i_tax[0]
						amount = i_tax[1]
						# base rate
						if rate == 22.0 or rate == 23.0:
							vat22["net"] += net
							vat22["amount"] += amount
						elif rate == 7.0 or rate == 8.0:
							vat7["net"] += net
							vat7["amount"] += amount
						elif rate == 5.0:
							vat7["net"] += net
							vat7["amount"] += amount
						elif rate:
							frappe.throw(("Wrong tax rate: " + str(rate) + " in: " + i))
				
	# TODO: check if it's correct!
	# Probably only items with rate 0 are left,
	# because items with other rates are already "popped",
	# but it can be wrong
	for name in item_net:
		vat0 += item_net[name]

	return {"vat0": vat0, "vat5": vat5, "vat7": vat7, "vat22": vat22}


def process_output_tax_document(document, tax_accounts):
	"""
	Should return processed Sales Invoice, but is only partially implemented.

	WARNING! Not implemented:
	- processing of sales invoices to countries other than Poland.
	Due to above, output tax can be lower (underestimated), causing
	troubles for the taxpayer!
	"""

	party = get_party_data(document)

	if party["country_code"] != "PL":
		# TODO: process sales invoices for other countries
		return None

	document_number = document.name
	document_date = document.posting_date

	# TODO: sales date if different than posting date
	sales_date = None
	
	# TODO: RO - cash register sales report, WEW - internal, FP - receipt based invoice
	document_type = None

	is_split_payment = document.is_split_payment

	# TODO: GTU codes
	gtu_01 = None
	gtu_02 = None
	gtu_03 = None
	gtu_04 = None
	gtu_05 = None
	gtu_06 = None
	gtu_07 = None
	gtu_08 = None
	gtu_09 = None
	gtu_10 = None
	gtu_11 = None
	gtu_12 = None
	gtu_13 = None

	# TODO: sales to EU, other than intra-community supply of goods
	# e.g. to private persons, companies without EU-VAT number
	# Note: may be not applicable anymore due to VAT OSS
	sw = None

	# TODO: electronic services, telecommunication, etc.
	ee = None

	# TODO: and affiliated entity
	tp  = None
		
	# TODO: three-way transactions
	tt_wnt = None
	tt_d = None
	i_42 = None
	i_63 = None

	# TODO: "VAT margin" invoices
	mr_t = None
	mr_uz = None

	# TODO: single- and multi-purpose vouchers
	b_spv = None
	b_spv_dostawa = None
	b_mpv_prowizja = None

	tax_details = get_output_tax_details(document, tax_accounts)
	
	# TODO: Bad debt relief
	tax_base_amendment = None

	# TODO: Net amount for tax exempt
	k_10 = None
	# TODO: Sales abroad
	k_11 = None
	# TODO: ... of which sales of services to the EU
	k_12 = None

	# Net amount for tax 0%
	k_13 = tax_details["vat0"]

	# TODO: ... of which tax returned to tourist
	k_14 = None

	# Net amount for tax 5%
	k_15 = tax_details["vat5"]["net"]
	# Tax amount (5%)
	k_16 = tax_details["vat5"]["amount"]
	# Net amount for tax 7% or 8%
	k_17 = tax_details["vat7"]["net"]
	# Tax amount (7% or 8%)
	k_18 = tax_details["vat7"]["amount"]
	# Net amount for tax 22% or 23%
	k_19 = tax_details["vat22"]["net"]
	# Tax amount (22% or 23%)
	k_20 = tax_details["vat22"]["amount"]
	
	# TODO: Net amount sales of goods to the EU
	k_21 = None
	# TODO: Net amount sales of goods exported
	k_22 = None

	# Net amount purchase of goods from EU - processed in other place
	k_23 = None
	# Tax amount (purchase of goods from EU) - processed in other place
	k_24 = None

	# TODO: Net amount import in simplified procedure
	k_25 = None
	# TODO: Tax amount (import in simplified procedure)
	k_26 = None
	# TODO: Net amount import of services except acc. to  art. 28b (supplier paid tax in other country)
	k_27 = None
	# TODO: Tax amount (import of services except acc. to art. 28b)
	k_28 = None
	# TODO: Net amount import of services acc. to art. 28b (tax to be paid by buyer in Poland, most common case)
	k_29 = None
	# TODO: Tax amount (import of services acc. to art. 28b)
	k_30 = None
	# TODO: Net amount sales where tax will be paid by buyer
	k_31 = None
	# TODO: Tax amount that will be paid by buyer
	k_32 = None
	# TODO: Tax amount acc. to art.15 sec.5 (physical inventory e.g. on closure of business, etc.)
	k_33 = None
	# TODO: Repayment of tax refunded or deducted on purchase of cash registers (e.g. closure of business, lack of service inspection)
	k_34 = None
	# TODO: Tax amount purchase of means of transport from EU
	k_35 = None
	# TODO: Tax amount acc. to art. 103 sec. 5aa (purchase of fuels from EU)
	k_36 = None
	# TODO: Gross amount of sales with VAT margin invoice
	vat_margin = None
	
	doc = {}

	doc["party_country_code"] = party["country_code"]
	doc["party_tax_id"] = party["tax_id"]
	doc["party_name"] = party["name"]
	doc["document_number"] = document_number
	doc["document_date"] = document_date
	doc["sales_date"] = sales_date
	
	doc["document_type"] = document_type

	if is_split_payment:
		doc["split_payment"] = "1"

	doc["gtu_01"] = gtu_01
	doc["gtu_02"] = gtu_02
	doc["gtu_03"] = gtu_03
	doc["gtu_04"] = gtu_04
	doc["gtu_05"] = gtu_05
	doc["gtu_06"] = gtu_06
	doc["gtu_07"] = gtu_07
	doc["gtu_08"] = gtu_08
	doc["gtu_09"] = gtu_09
	doc["gtu_10"] = gtu_10
	doc["gtu_11"] = gtu_11
	doc["gtu_12"] = gtu_12
	doc["gtu_13"] = gtu_13

	doc["sw"] = sw
	doc["ee"] = ee
	doc["tp"] = tp
	doc["tt_wnt"] = tt_wnt
	doc["tt_d"] = tt_d
	doc["mr_t"] = mr_t
	doc["mr_uz"] = mr_uz
	doc["i_42"] = i_42
	doc["i_63"] = i_63
	doc["b_spv"] = b_spv
	doc["b_spv_dostawa"] = b_spv_dostawa
	doc["b_mpv_prowizja"] = b_mpv_prowizja
	doc["tax_base_amendment"] = tax_base_amendment

	doc["k_10"] = k_10
	doc["k_11"] = k_11
	doc["k_12"] = k_12
	doc["k_13"] = k_13
	doc["k_14"] = k_14
	doc["k_15"] = k_15
	doc["k_16"] = k_16
	doc["k_17"] = k_17
	doc["k_18"] = k_18
	doc["k_19"] = k_19
	doc["k_20"] = k_20
	doc["k_21"] = k_21
	doc["k_22"] = k_22
	doc["k_23"] = k_23
	doc["k_24"] = k_24
	doc["k_25"] = k_25
	doc["k_26"] = k_26
	doc["k_27"] = k_27
	doc["k_28"] = k_28
	doc["k_29"] = k_29
	doc["k_30"] = k_30
	doc["k_31"] = k_31
	doc["k_32"] = k_32
	doc["k_33"] = k_33
	doc["k_34"] = k_24
	doc["k_35"] = k_35
	doc["k_36"] = k_36

	if(vat_margin):
		doc["vat_margin"] = round(vat_margin, 2)

	for i in range(10,37):
		k_i = "k_" + str(i)
		if doc[k_i]:
			doc[k_i] = round(doc[k_i], 2)                        

	return doc

def process_eu_purchase_output_tax_document(document, tax_accounts):
	"""
	Returns processed Purchase Invoice from EU countries for output tax
	"""

	party = get_party_data(document)

	document_number = document.bill_no
	document_date = document.bill_date

	if not document_number:
		frappe.throw(_("Supplier invoice number missing: ") + document.name)
			
	if not document_date:
		frappe.throw(_("Supplier invoice date missing: ") + document.name)
			

	# NOTE: only necessary fields are given below.
	# For all fields check def process_output_tax_document(...)

	# TODO: an affiliated entity
	tp  = None
		
	# TODO: three-way transactions
	tt_wnt = None
	tt_d = None
	i_42 = None
	i_63 = None

	sum_of_net = 0.0
	sum_of_tax = 0.0
	
	# get sum of net values
	for item in document.items:
			sum_of_net += item.net_amount

	# get sum of taxes
	for tax in document.taxes:
		if tax.account_head in tax_accounts:
			item_wise_tax = json.loads(tax.item_wise_tax_detail)

			for item_name in item_wise_tax:
				sum_of_tax += item_wise_tax[item_name][1]

	# Net amount purchase of goods from EU
	k_23 = sum_of_net
	# Tax amount (purchase of goods from EU, "theoretical" tax, same amount declared in input tax, so it makes no impact)
	k_24 = sum_of_tax
	# TODO: Tax amount purchase of means of transport from EU
	k_35 = None
	# TODO: Tax amount acc. to art. 103 sec. 5aa (purchase of fuels from EU)
	k_36 = None
	
	doc = {}

	doc["party_country_code"] = party["country_code"]
	doc["party_tax_id"] = party["tax_id"]
	doc["party_name"] = party["name"]
	doc["document_number"] = document_number
	doc["document_date"] = document_date
	
	doc["tp"] = tp
	doc["tt_wnt"] = tt_wnt

	doc["k_23"] = k_23
	doc["k_24"] = k_24
	doc["k_35"] = k_35
	doc["k_36"] = k_36

	for k_i in ["k_23", "k_24", "k_35", "k_36"]:
		if doc[k_i]:
			doc[k_i] = round(doc[k_i], 2)

	return doc


def process_input_tax_document(document, tax_accounts):
	"""
	Returns processed document for purchase invoices from EU and Poland,
	or None if supplier is not from EU
	"""

	# ----- get required data ------

	party = get_party_data(document)

	if party["country_code"] not in eu_codes:
		# import tax documents are processed in other place
		# TODO: import in simplified procedure?
		return None

	document_number = document.bill_no
	document_date = document.bill_date

	if not document_number:
		frappe.throw(_("Supplier invoice number missing: ") + document.name)
			
	if not document_date:
		frappe.throw(_("Supplier invoice date missing: ") + document.name)
			
	# NOT IMPLEMENTED: document receipt date (optional)
	document_receipt_date = None
	
	# TODO: MK, VAT_RR, WEW
	document_type = None
	
	is_split_payment = document.is_split_payment

	# not applicable for purchase invoices from EU and Poland
	is_import = None

	fixed_assets = []

	net_fixed_assets = 0.0
	tax_fixed_assets = 0.0

	net_other = 0.0
	tax_other = 0.0

	# get sums of net values
	for item in document.items:
		if item.is_fixed_asset:
			net_fixed_assets += item.net_amount
			item_name = item.item_code or item.item_name
			fixed_assets.append(item_name)
		else:
			net_other += item.net_amount

	# get sums of input taxes
	for tax in document.taxes:
		if tax.account_head in tax_accounts:
			item_wise_tax = json.loads(tax.item_wise_tax_detail)

			for item_name in item_wise_tax:
				if item_name in fixed_assets:
					tax_fixed_assets += item_wise_tax[item_name][1]
				else:
					tax_other += item_wise_tax[item_name][1]
					
	# TODO: purchase with "VAT margin" invoice
	vat_margin = None

	# TODO: Fixed assets input tax amendment
	tax_amendment_fixed_assets = None
	# TODO: Other goods or services input tax amendment
	tax_amendment_other = None
	# TODO: Input tax amendment due to unpaid invoice
	tax_amendment_bad_debt = None
	# TODO: Input tax amendment due to payment of unpaid invoice (with previously amendet input tax)
	tax_amendment_bad_debt_paid = None
	

	# ----- fill required structure --------

	doc = {}
	doc["party_country_code"] = party["country_code"]
	doc["party_tax_id"] = party["tax_id"]
	doc["party_name"] = party["name"]
	doc["document_number"] = document_number
	doc["document_date"] = document_date
	doc["document_receipt_date"] = document_receipt_date
	doc["document_type"] = document_type
	if is_split_payment:
		doc["split_payment"] = "1"
	doc["import"] = is_import
	doc["k_40"] = net_fixed_assets
	doc["k_41"] = tax_fixed_assets
	doc["k_42"] = net_other
	doc["k_43"] = tax_other
	doc["k_44"] = tax_amendment_fixed_assets
	doc["k_45"] = tax_amendment_other
	doc["k_46"] = tax_amendment_bad_debt
	doc["k_47"] = tax_amendment_bad_debt_paid

	if vat_margin:
		doc["vat_margin"] = round(vat_margin, 2)

	for i in range(40, 48):
		k_i = "k_" + str(i)
		if doc[k_i]:
			doc[k_i] = round(doc[k_i], 2)                        
	return doc


def process_import_input_tax_document(document, tax_accounts):
	"""
	Process Journal Entry for SAD/PZC (customs declaration)
	"""

	# ----- get required data ------

	invoice = frappe.get_doc("Purchase Invoice", document.jpk_purchase_invoice)

	party = get_party_data(invoice)

	document_number = document.bill_no
	document_date = document.bill_date
	# TODO: document receipt date (optional)
	document_receipt_date = None
	
	# it is import document, so "IMP" field has to be set
	is_import = "1"

	# TODO: split into fixed assets and other goods or services (use invoice)
	net_fixed_assets = 0.0
	tax_fixed_assets = 0.0
	net_other = flt(document.jpk_imp_net, 2)
	tax_other = 0.0

	# get sums of input taxes
	for account in document.accounts:
		if account.account in tax_accounts:
			tax_other += account.credit
			tax_other -= account.debit

	# Below lines are not related to import of goods
	# MK, VAT_RR, WEW
	document_type = None
	# split payment
	is_split_payment = None
	# purchase with "VAT margin" invoice
	vat_margin = None
	# Fixed assets input tax amendment
	tax_amendment_fixed_assets = None
	# Other goods or services input tax amendment
	tax_amendment_other = None
	# Input tax amendment due to unpaid invoice
	tax_amendment_bad_debt = None
	# Input tax amendment due to payment of unpaid invoice (with previously amendet input tax)
	tax_amendment_bad_debt_paid = None
	

	# ----- fill required structure --------

	doc = {}
	doc["party_country_code"] = party["country_code"]
	doc["party_tax_id"] = party["tax_id"]
	doc["party_name"] = party["name"]
	doc["document_number"] = document_number
	doc["document_date"] = document_date
	doc["document_receipt_date"] = document_receipt_date
	doc["document_type"] = document_type
	if is_split_payment:
		doc["split_payment"] = "1"
	doc["import"] = is_import
	doc["k_40"] = net_fixed_assets
	doc["k_41"] = tax_fixed_assets
	doc["k_42"] = net_other
	doc["k_43"] = tax_other
	doc["k_44"] = tax_amendment_fixed_assets
	doc["k_45"] = tax_amendment_other
	doc["k_46"] = tax_amendment_bad_debt
	doc["k_47"] = tax_amendment_bad_debt_paid

	if vat_margin:
		doc["vat_margin"] = round(vat_margin, 2)

	for i in range(40, 48):
		k_i = "k_" + str(i)
		if doc[k_i]:
			doc[k_i] = round(doc[k_i], 2)                        

	return doc


def get_party_data(document):
	"""
	Return data of a party (customer or supplier) from given doc.
	"""

	party_name = ""
	party_type = ""
	tax_id = document.tax_id
	tax_id_short = "BRAK"
	country = ""
	country_code = ""

	if hasattr(document, "customer_name"):
		party_name = document.customer_name
		country = get_customer_country(document)
		if (not tax_id) and is_tax_id_obligatory(country):
			tax_id = get_obligatory_tax_id(document.customer_name, "Customer")
	elif hasattr(document, "supplier_name"):
		party_name = document.supplier_name
		country = get_supplier_country(document)
		if (not tax_id) and is_tax_id_obligatory(country):
			tax_id = get_obligatory_tax_id(document.supplier_name, "Supplier")

	# country codes in ERPNext are lowercase, so we have to use "upper()"
	country_code = country.code.upper()

	if tax_id:
		tax_id = tax_id.upper()
		if tax_id[0:2] == country_code:
			tax_id_short = tax_id[2:]
		else:
			tax_id_short = tax_id

	return {"name": party_name, "country_code": country_code, "tax_id": tax_id_short}


def get_customer_country(document):
	"""
	Returns Country of customer from given Purchase Invoice, or Poland if
	address not set.

	Looks for address in:
	- customer_address
	- customer.customer_primary_address
	"""

	address_name = document.shipping_address_name

	# if shipping adress is not set on document
	if not address_name:
		address_name = document.customer_address

	# if customer address is not set on document, too
	if not address_name:
		customer = frappe.get_doc("Customer", document.customer)
		address_name = customer.customer_primary_address

	return get_country_from_address(address_name, return_default = True)
	

def get_supplier_country(document):
	"""
	Returns Country of supplier from given document. 
	"""

	# checking document.supplier_address could be omitted, but
	# someone could forget to change default country in supplier.country
	# and still set correct country in supplier_address

	address_name = document.supplier_address

	if address_name:
		return get_country_from_address(address_name)

	supplier = frappe.get_doc("Supplier", document.supplier)
	return frappe.get_doc("Country", supplier.country)


def get_country_from_address(address_name, return_default = False):
	"""
	Returns Country (doctype) according to country set in address.

	Arguments:
	- address_name: name of Address doctype
	- return_default: if True, will return default company's country name if
	country not found in address or if address_name is None
	"""

	country_name = None
	
	if address_name:
		address = frappe.get_doc("Address", address_name)
		country_name = address.country

	if (not country_name) and return_default:
		default_company_name = frappe.defaults.get_user_default("Company")
		default_company = frappe.get_doc("Company", default_company_name)
		country_name = default_company.country
	
	if country_name:
		return frappe.get_doc("Country", country_name)
	else:
		frappe.throw(_("Country name missing."))


def get_obligatory_tax_id(party_name, party_doctype_name):
	"""
	Returns Tax ID of given party, or None if the party is not a company

	If the party is a company, but the Tax ID is not set, it throws an error.
	"""

	party = frappe.get_doc(party_doctype_name, party_name)

	is_company = False

	if hasattr(party, "customer_type"):
		if party.customer_type == "Company":
			is_company = True
	elif hasattr(party, "supplier_type"):
		if party.supplier_type == "Company":
			is_company = True

	if is_company:
		if party.tax_id:
			return party.tax_id
		else:
			frappe.throw(_("Tax ID missing: ") + party_name)
	else:
		return None


def is_tax_id_obligatory(country):
	"""
	Returns True if country is in EU or is Poland. Returns False for others.
	"""

	if country.name in all_eu_countries:
		return True

	return False
