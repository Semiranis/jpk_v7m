# coding=UTF-8
"""
MF XSD Extractor

Extracts documented restrictions from XSD files created by Polish Ministry
of Finance.

Currently (Jul 2021) valid link to the mentioned XSD files:
https://www.podatki.gov.pl/e-deklaracje/dokumentacja-it/struktury-dokumentow-xml/

Use case:
If you need e.g. list of tax offices with corresponding codes, or countries with
codes, you can use this to extract them from proper XSD.

Example of XSD case with technical details:
File: KodyKrajow_v7-0E.xsd
Result: list of country codes and corresponding country names
Technical details: This XSD contains "simpleType" element with attribute
name="TKodKraju". This element has restrictions in form of "enumaration"
elements with attributes value="XX", where XX are country codes. These
enumerations have "documentation" element (as subelement of "annotation")
containing country name. So you can get list of country codes and corresponding
country names checking restrictions of TKodKraju.

--- HOW TO USE ---

This script can be used by user to simply display extracted data, or by software
developers.

INSTRUCTIONS FOR USERS (Linux)

Open folder containing this script in Terminal (or use cd command) and type:
python3 xsd_extractor.py

If you want to save the results in some file (e.g. results.txt), type:
python3 xsd_extractor.py > results.txt
You can use any other name for output file

INSTRUCTIONS FOR SOFTWARE DEVELOPERS

Instructions for developers are included in comments.
Check def print_formatted() to find a way how to read the returned dict.


Author: Marcin Lewicz
Licence: MIT
"""

import xml.etree.ElementTree as ET
import os
import os.path


def xsd_extract_documented_restrictions(file_name, polish_title_case = False):
        """
        Returns nested dict containing value restrictions and corresponding
        descriptions extracted from XSD provided by Polish Mininstry of Finance.

        Arguments:
        - file_name (string): name (and path if needed) of XSD file
        - polish_title_case (bool): changes letter cases if True

        Return: nested dict:
        - outer dict:
         - key: type name defined in XSD
         - value: dict of restrictions
        - dict of restrictions:
         - key: restriction value from XSD (e.g. country code)
         - value: restriction documentation (e.g. country name)
        """

        # Parse XSD file
        tree = ET.parse(file_name)

        # Get dict of namespace prefixes and corresponding namespaces
        ns_dict = get_xmlns_dict(file_name)

        # Dict to collect all restrictions for all types defined in XSD
        restrictions = {}

        # Find parent elements (/..) of restriction elements in all namespaces
        restricted_nodes = find_ns_subelements(tree, "restriction/..", ns_dict)

        for restricted_node in restricted_nodes:

                # Get only named types. The name will be used as a key in a dict.
                if "name" not in restricted_node.attrib:
                        continue
                
                type_name = restricted_node.attrib["name"]

                # Dict to collect restrictions only for current node
                type_restrictions = {}

                # type node (restricted) can include some other nodes
                # not only restriction, so let's filter restrictions only
                restriction_nodes = find_ns_subelements(restricted_node, "restriction", ns_dict)

                for restriction_node in restriction_nodes:

                        # restriction node includes enumerations
                        for r in restriction_node:

                                #some xsd files include documentation in pl & en
                                #TODO: option to choose langauge or sth
                                #below code uses first version only

                                doc_nodes = find_ns_subelements(r, "documentation", ns_dict)
                                if doc_nodes:
                                        doc = doc_nodes[0].text
                                        if polish_title_case:
                                                doc = change_case(doc)
                                        value = r.attrib['value']

                                        type_restrictions[value] = doc
                                        
                if len(type_restrictions):
                        restrictions[type_name] = type_restrictions

        return restrictions


def get_xmlns_dict(xml):
        """
        returns dict containing XML namespaces from given file (prefix and full
        namespace)

        attributes:
        - xml (string): name of file including any xml (xsd is xml, too)
        """

        return dict([node for event, node in ET.iterparse(xml, events=['start-ns'])])


def find_ns_subelements(element, subelement_name, ns_dict):
        """
        retuns list of subelements with given name in any given namespace

        Arguments:
        - element (ElementTee.Element): main element to search in
        - subelement_name (string): searched name of element
        - ns_dict: dict of prefixes and corresponding full namespaces

        Hint:
        To search for parent element, add "/.." in the end.
        Example:
        fund_ns_subelements(root, "my_element/../..", ns_dict)
        will return list of grandparents of elements "my_element"
        """

        subelements = []

        # Search term explanation:
        # .//* read from right to left means:
        # all elements (*) in any level (//) in top-level element (.)
        # If you want to search nodes with some attribute:
        # .//*[@attr='something'] means:
        # nodes with attribute attr='something' located anywhere (.//*)
        # Our case: elements with namespace (in {}) and name, anywhere:
        # .//{namespace}name

        # We are looking for given element in any namespace.
        # In newer Python versions you can use *
        # and the solution would be one-liner:
        # return element.findall(f".//{{*}}{subelement_name}")
        # Below code should be compatible with older versions

        for prefix in ns_dict:
                ns = ns_dict[prefix]
                match = f".//{{{ns}}}{subelement_name}"
                found = element.findall(match)
                for subelement in found:
                        subelements.append(subelement)
        return subelements


def change_case(text):
        """
        Converts text to "Polish" title case.

        Use case: countries and other names

        Example:
        change_case("BOŚNIA I HERCEGOWINA")
        will return "Bośnia i Hercegowina" (lower i), not "Bośnia I Hercegowina"
        """

        # convert to "standard" title case first
        text = text.title()

        # TODO: add all required options, or find more elegant solution
        polish_cases = {
                " I ": " i ",
                " W ": " w ",
                " WE ": " we ",
                " Z ": " z ",
                " ZE ": " ze "
                }

        for c in polish_cases:
                text = text.replace(c, polish_cases[c])

        return text


def print_formatted(dicts, separator = " - ", swap = False):
        """
        Displays results in more "human friendly" way.

        How it works:
        gets outer dict, displays it's key (variable name defined in XSD)
        then displays content of inner dict and goes to next dict(s) (if any)
        """
        
        for dict_name in dicts:
                print("")
                print(dict_name)
                subdict = dicts[dict_name]

                for key in subdict:
                        if swap:
                                print(subdict[key] + separator + key)
                        else:
                                print(key + separator + subdict[key])


if __name__ == '__main__':

        # TODO: add command line options for:
        # - user-defined xsd folder
        # - changing separator
        # - swapping displayed values
        # - converting XSD restriction documentations to "Polish" title case

        xsd_folder = "./xsd"
        separator = " - "
        swap = False
        polish_title_case = False

        # TODO: keep messages in line with xsd_folder variable
        if not os.path.isdir(xsd_folder):
                print("Error: xsd directory missing!")
                print("")
                print("Please create a folder named xsd and copy the XSD files into it.")
        else:
                files = os.listdir(xsd_folder)
                if len(files) < 1:
                        print("Error: xsd directory contains no files!")
                        print("")
                        print("Please copy the selected XSD files to the xsd directory.")
                        
                for f in files:
                        print("")
                        print(f)
                        file_path = xsd_folder + "/" + f
                        if os.path.isfile(file_path):
                                restrictions = xsd_extract_documented_restrictions(file_path, polish_title_case)
                                print_formatted(restrictions, separator, swap)
                        #input("Press Enter for next file")
