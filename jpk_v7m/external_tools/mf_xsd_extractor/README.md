# MF XSD extractor (xsd_extractor.py)

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

