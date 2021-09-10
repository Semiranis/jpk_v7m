# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

eu_codes = [
	"AT",
	"BE",
	"BG",
	"CY",
	"CZ",
	"DE",
	"DK",
	"EE",
	"EL",
	"ES",
	"FI",
	"FR",
	"HR",
	"HU",
	"IE",
	"IT",
	"LT",
	"LU",
	"LV",
	"MT",
	"NL",
	"PL",
	"PT",
	"RO",
	"SE",
	"SI",
	"SK",
	"XI"
	]


def get_eu_countries(omit_pl = False):
	"""
	Returns list of names of Country doctypes for EU countries

	Arguments:
	- omit_pl: if set, returned list won't contain Poland.
	  Use case: purchase of goods from EU to PL
	"""

	codes = eu_codes.copy()

	if omit_pl:
		codes.remove("PL")

	all_countries = frappe.db.get_all("Country")
	eu_countries = []

	for country_name in all_countries:
		country = frappe.get_doc("Country", country_name)
		if country.code:
			# country codes in ERPNext are lowercase as standard
			if country.code.upper() in codes:
				eu_countries.append(country.name)

	return eu_countries
	
