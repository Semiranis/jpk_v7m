# -*- coding: utf-8 -*-
# Copyright (c) 2021, Marcin Lewicz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class JPKCompanySettings(Document):

	@frappe.whitelist()
	def fill_tax_accounts_lists(self):
		"""
		Calls methods that fill the tables with lists of tax accounts
		"""
	
		self.fill_tax_accounts_list(self.input_tax_accounts, "input_tax_accounts_list")
		self.fill_tax_accounts_list(self.output_tax_accounts, "output_tax_accounts_list")
		return
	
	def fill_tax_accounts_list(self, source_table, list_table_name):
		"""
		Fills table with list of leaf accounts, according to data from other table.
		If source table contains accounts that are groups, the second table will
		contain all the leaf accounts included in the groups (instead of groups).

		Arguments:
		- source_table: child table with names of accounts, both leaf and group
		- list_table_name: name of the table to be filled with leaf account names
		"""
	
		for account in source_table:
			account_names = get_leaf_accounts(account.account_name)
			for account_name in account_names:
				if not self.table_contains_account_name(list_table_name, account_name):
					row = self.append(list_table_name, {})
					row.account_name = account_name
		return
	
	def table_contains_account_name(self, list_table_name, account_name):
		"""
		Returns True if the table already contains given account name.
		
		Used to avoid duplicate rows.
		
		Arguments:
		- list_table_name (string): the name of the table with account names
		- account_name (string): the name to be checked if alredy exists in the table
		"""
	
		for item in self.get(list_table_name):
			if item.account_name == account_name:
				return True
		return False
	

def get_leaf_accounts(account_name):
	"""
	Returns list of all leaf accounts (not groups) of the account with given name.

	Uses recursive function to walk through the chart of accounts tree.

	Arguments:
	- account_name (string): the name of account. Can be group, or leaf.
	"""

	account = frappe.get_doc("Account", account_name)

	if account.is_group:
		leafs = []
		return get_leaf_accounts_recursive(account.name, leafs)
	else:
		# string would be iterated as single letters
		return [account_name]


def get_leaf_accounts_recursive(account_name, leafs):
	"""
	Returns list of all leaf accounts (not groups) of the group account with given name.

	Arguments:
	- account_name (string): the name of group account
	- leafs (list of strings): list of leaf accounts collected in previous recursion
	"""

	subaccount_names = frappe.get_all("Account", filters = {'parent_account': account_name}, pluck = 'name')

	for subaccount_name in subaccount_names:
		subaccount = frappe.get_doc("Account", subaccount_name)
		if subaccount.is_group:
			get_leaf_accounts_recursive(subaccount.name, leafs)
		else:
			leafs.append(subaccount.name)
	return leafs
