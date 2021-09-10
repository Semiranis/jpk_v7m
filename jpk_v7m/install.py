# -*- coding: utf-8 -*-

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def after_install():

	create_custom_field("Journal Entry", {
		"label": _("JPK: IMP"),
		"fieldname": "jpk_is_imp",
		"fieldtype": "Check",
		"default": 0,
		"insert_after": "reference"
		})

	create_custom_field("Journal Entry", {
		"label": _("Purchase Invoice"),
		"fieldname": "jpk_purchase_invoice",
		"fieldtype": "Link",
		"options": "Purchase Invoice",
		"insert_after": "jpk_is_imp",
		"mandatory_depends_on": "jpk_is_imp"
		})

	create_custom_field("Journal Entry", {
		"label": _("Customs Reference Net Value"),
		"fieldname": "jpk_imp_net",
		"fieldtype": "Data",
		"insert_after": "jpk_purchase_invoice",
		"mandatory_depends_on": "jpk_is_imp"
		})

	create_custom_field("Purchase Invoice", {
		"label": _("Is Split Payment"),
		"fieldname": "is_split_payment",
		"fieldtype": "Check",
		"default": 0,
		"insert_after": "set_posting_time"
		})

	create_custom_field("Sales Invoice", {
		"label": _("Is Split Payment"),
		"fieldname": "is_split_payment",
		"fieldtype": "Check",
		"default": 0,
		"insert_after": "set_posting_time"
		})

	
