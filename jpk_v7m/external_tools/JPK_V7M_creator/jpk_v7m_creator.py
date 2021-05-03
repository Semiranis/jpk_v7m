# coding=UTF-8
"""
JPK_V7M XML creator

This script was created as base or starting point for implementation of JPK_V7M 
feature in other applications.

It can be used stand alone, due to use of input() in get_{some_data}() functions, 
but it has no "undo" feature. You can try it simply calling:
python3 jpk_v7m_creator.py

To reuse the code for your own app with minimal effort, you can make one of
these things:
- pass all required arguments calling create_jpk()
- reimplement all get_{some_data} functions to get data from your own app

Please note that some parts:
1. Are not implemented
2. Will not be implemented
3. Are not needed in my case and that's the biggest reason for previous point

Author: Marcin Lewicz

Licence: MIT
"""

# TODO:
# (or not to do, but not implemented):
# - code for fields P_49, P_50, P_52, P_54 up to P_61, P_63 up to P_67
# - code for data validation in get_input_tax_document()
# - code for data validation in get_output_tax_document()
# - feature to get data from some application or some file

# used for easy manipulation of XML elements
import xml.etree.ElementTree as ET

# required if we want to use string in ElementTree.iterparse
from io import StringIO

# used for creation date and time of JPK
from datetime import datetime

# for translations
import gettext
_ = gettext.gettext

# used to get system settings
import os

lang = os.environ['LANG']

if lang[:2] == "pl":
        # relative path doesn't work if you call script from e.g. parent directory
        pl = gettext.translation("messages", os.path.join(os.path.dirname(__file__), "locales"), ['pl'])
        pl.install()
        _ = pl.gettext


def create_jpk(
        is_guidance_accepted = None,
        purpose = None,
        tax_office_code = None,
        year = None,
        month = None,
        is_natural_person = None,
        first_name = None,
        last_name = None,
        date_of_birth = None,
        full_name = None,
        tax_number = None,
        email = None,
        phone = None,
        forwarded_excess_of_input_tax = None,
        input_tax_documents = None,
        output_tax_documents = None,
        amendment_reasons = None,
        system_name = "jpk_v7m_creator.py",
        file_name = None
        ):
        """
        Main function of JPK_V7M XML creator
        
        Usage:
        - If you want to ask the user for every single required data, just call
          create_jpk() without arguments
        - If you already have some or all required data, pass them as arguments

        Below is short information about arguments. For more details check
        get_{argument name} function defininition.

        Arguments:
        - is_guidance_accepted (string) - "1" if user accepted the guidance
          about legal consequences
        - purpose (string) - "1" if it will be first JPK for the period,
          "2" if it will be ammendment of already sent JPK
        - tax_office_code (string) - 4-digit code of Tax Office that will
          receive the JPK
        - year (string) - 4-digit year of JPK period
        - month (string) - number of month (1-12) of JPK period
        - is_natural_person (string) - "1" if the entity is natural person,
          "0" if the entity is legal person
        - first_name (string) - first name of natural person (omit for legal
          person)
        - last_name (string) - last name of natural person (omit for legal
          person)
        - date_of_birth (string in format YYYY-MM-DD) - date of birth of natural
          person (omit for legal person)
        - full_name (string) - full name of legal person (omit for natural
          person)
        - tax_number (string with 10 digits) - tax number of entity creating JPK
        - email (string) - e-mail to be used by Tax Office for contact
        - phone (string) - optional phone number to be used by Tax Office for
          contact
        - forwarded_excess_of_input_tax (string) - excess of input tax over
          output tax carried forward from previous JPK period (from field P_62)
        - input_tax_documents (list) - list of dicts containing data of every
          input tax document. For details see: def get_input_tax_documents
        - output_tax_documents (list) - list of dicts containing data of every
          output tax document. For details see: def get_output_tax_documents
        - amendment_reasons (string) - optional description for Tax Office
        """

        # ---- Check if guidance about legal consequences is accepted ---------
        if is_guidance_accepted is None:
                is_guidance_accepted = get_is_guidance_accepted()

        # -------- Initialize variables ----------
        
        # Create and initialize list for summation of values of JPK fields
        # named tns:K_{number}
        # The sums will be used in declaration part of JPK
        sum_of_field_k = []
        initialize_list(sum_of_field_k, 48, 0.0)

        # initialize variable for bad debt relief calculation
        sum_of_bad_debt_relief = { "net": 0, "tax": 0}

        # Initialize root element of JPK
        jpk_root = initialize_jpk()

        #  --------- Get required data. ---------

        # For detailed description see get_{...} functions description

        if purpose is None:
                purpose = get_purpose()

        if tax_office_code is None:
                tax_office_code = get_tax_office_code()

        if year is None:
                year = get_year()

        if month is None:
                month = get_month(year)

        if is_natural_person is None:
                is_natural_person = get_is_natural_person()

        if first_name is None:
                first_name = get_first_name(is_natural_person)
                
        if last_name is None:
                last_name = get_last_name(is_natural_person)

        if date_of_birth is None:
                date_of_birth = get_date_of_birth(is_natural_person)
                
        if full_name is None:
                full_name = get_full_name(is_natural_person)
                
        if tax_number is None:
                tax_number = get_tax_number()

        if email is None:
                email = get_email()

        if phone is None:
                phone = get_phone_number()

        if forwarded_excess_of_input_tax is None:
                forwarded_excess_of_input_tax = get_forwarded_excess_of_input_tax()

        if amendment_reasons is None:
                amendment_reasons = get_amendment_reasons()

        # ---- create required parts of JPK. ------

        jpk_entity = create_jpk_entity(
                is_natural_person,
                tax_number,
                email,
                first_name,
                last_name,
                full_name,
                phone,
                date_of_birth
                )

        # evidence must be processed before declaration
        # to get required tax values
        jpk_evidence = create_jpk_evidence(
                input_tax_documents,
                output_tax_documents,
                sum_of_field_k,
                sum_of_bad_debt_relief
                )

        jpk_declaration = create_jpk_declaration(
                is_guidance_accepted,
                sum_of_field_k,
                sum_of_bad_debt_relief,
                forwarded_excess_of_input_tax,
                amendment_reasons
                )

        # header contains date and time of creation, so processing it after
        # the time consuming parts is good IMHO
        jpk_header = create_jpk_header(
                purpose,
                tax_office_code,
                month,
                year,
                system_name
                )

        # -------- put the parts of JPK together -----------
        
        # append parts to JPK in order defined in government brochure
        # (I'm not sure if it's important)
        jpk_root.append(jpk_header)
        jpk_root.append(jpk_entity)
        jpk_root.append(jpk_declaration)
        jpk_root.append(jpk_evidence)

        # ------- create xml file ------------
        if file_name is not None:
                create_file(jpk_root, file_name)

        # just for preview - not required
        show_xml(ET.tostring(jpk_root))


def create_file(root, file_name):
        """
        Write xml of ElementTree.Element into file with given name
        """
        # Create ElementTree from root Element. Will be used for writing a file.
        tree = ET.ElementTree(root)

        # save XML as a file
        tree.write(file_name, encoding="UTF-8", xml_declaration=True)


def get_is_guidance_accepted():
        """
        Get information if the user accepted the guidance about legal
        consequences.

        Return string "1" if guidance accepted.
        Could return "0" in not accepted, but the guidance MUST be accepted.
        You should not omit asking the user in some way.
        """

        # TODO: get data from application

        print("________________________________________________________________________________\n")
        print("\t\t\t\t" + _("GUIDANCE") + "\n")
        print(_("This return serves as a basis to issue an enforcement title document according\nto statutory provisions governing administrative enforcement procedure in cases\nwhere the tax due is not paid when due or is underpaid.") + "\n")
        #print(_("W przypadku niewpłacenia w obowiązującym terminie podatku podlegającego wpłacie\ndo urzędu skarbowego lub wpłacenia go w niepełnej wysokości niniejsza deklaracja\nstanowi podstawę do wystawienia tytułu wykonawczego, zgodnie z przepisami o\npostępowaniu egzekucyjnym w administracji.") + "\n")
        print(_("For providing untrue information or concealing the truth resulting in the \npossible tax underpayment the taxable person shall bear liability according to \nthe Code of Fiscal Offences."))
        #print(_("Za podanie nieprawdy lub zatajenie prawdy i przez to narażenie podatku na\nuszczuplenie grozi odpowiedzialność przewidziana w przepisach Kodeksu karnego\nskarbowego."))
        print("________________________________________________________________________________\n")

        answer = input(_("Do you accept above guidance?") + _(" [y/N]: "))
        answer = answer.lower()

        if answer == "1" or answer == "t" or answer == "y":
                return "1"
        else:
                return get_is_guidance_accepted()


def get_purpose():
        """
        Get information if the JPK will be sent first time for the period, or
        it's amendment.

        Return string:
        - "1" if it's first version of JPK
        - "2" if it's amendment of already sent JPK
        """

        # TODO: get data from application

        answer = input(_("Is it JPK amendment?") + _(" [y/N]: "))
        answer = answer.lower()
        
        if answer == "t" or answer == "1" or answer == "y":
                return "2"
        elif answer == "n" or answer == "0" or answer == "":
                return "1"
        else:
                return get_purpose()


def get_tax_office_code():
        """
        Get 4-digit code of the tax office which will receive the JPK

        In GUI version there could be some search field or drop down list.
        Possible filtering by voivodeship, city, etc.

        Return string containing 4-digit code
        """

        # TODO: get data from application

        answer = input(_("Enter the 4-digit code of the Tax Office") + ": ")

        if answer.isdecimal() and len(answer) == 4:
                return answer
        else:
                return get_tax_office_code()


def get_year():
        """
        Get the year of period related to this JPK.

        Return string containing 4-digits year number
        """

        # TODO: get data from application

        today = datetime.today()
        year = today.year
        
        if today.month == 1:
                year -= 1
                
        year_string = str(year)

        answer = input(_("Enter JPK year if different than") + " " + year_string + ": ")

        if answer == "":
                return year_string
        elif answer.isdecimal() and len(answer) == 4:
                answer_year = int(answer)
                if answer_year >= 2020 and answer_year <= year:
                        return answer
                else:
                        return get_year()
        else:
                return get_year()


def get_month(year):
        """
        Get the month of period related to this JPK.

        Return string containing number of month (1-12).
        """

        # TODO: get data from application

        previous_month = datetime.today().month - 1
        current_year = str(datetime.today().year)
        
        if previous_month == 0:
                previous_month = 12

        previous_month_string = str(previous_month)

        answer = input(_("Enter JPK month if different than") + " " + previous_month_string + ": ")

        if answer == "":
                return previous_month_string
        elif answer.isdecimal():
                month = int(answer)

                if current_year == year and month >= previous_month:
                        print(_("JPK can be sent only for past months"))
                        return get_month(year)
                
                if month >= 1 and month <= 12:
                        return str(month)
                else:
                        print(_("Wrong month number"))
                        return get_month(year)
        else:
                return get_month(year)


def get_is_natural_person():
        """"
        Get information if the entity related to this JPK is natural or legal
        person.

        Return string:
        - "0" if the company creating JPK is legal person
        - "1" if natural person
        """

        # TODO: get data from application

        answer = input(_("Is the entity a natural person?") + _(" [y/N]: "))
        answer = answer.lower()
        
        if answer == "t" or answer == "1" or answer == "y":
                return "1"
        elif answer == "n" or answer == "0" or answer == "":
                return "0"
        else:
                return get_is_natural_person()


def get_first_name(is_natural_person):
        """
        Get first name of the owner if the entity is natural person.

        Return:
        - None if the company creating JPK is legal person
        - first name as string if natural person
        """

        if is_natural_person == "0":
                return None
        
        # TODO: get data from application

        answer = input(_("First name of natural person") + ": ")
        
        # answer not empty and without digits (names don't have digits)
        if len(answer) > 0 and not contains_digits(answer):
                return answer.capitalize()
        else:
                return get_first_name(is_natural_person)


def contains_digits(s):
        """
        Check if the string contains any digit.

        Arguments:
        - s: string to check

        Returns True if string contains any digit
        """

        return any(c.isdigit() for c in s)


def get_last_name(is_natural_person):
        """
        Get last name of the owner if the entity is natural person.

        Return:
        - None if the company creating JPK is legal person
        - last name as string if natural person
        """

        if is_natural_person == "0":
                return None

        # TODO: get data from application

        answer = input(_("Last name of natural person") + ": ")
        if len(answer) > 0 and not contains_digits(answer):
                return answer.capitalize()
        else:
                return get_last_name(is_natural_person)


def get_full_name(is_natural_person):
        """
        Get full name if the entity is legal person

        Return:
        - None if the company creating JPK is natural person
        - first name as string if legal person
        """

        if is_natural_person == "1":
                return None

        # TODO: get data from application
        answer = input(_("Full name of legal person") + ": ")
        if len(answer) > 0:
                return answer
        else:
                return get_full_name(is_natural_person)


def get_date_of_birth(is_natural_person):
        """
        Get date of birth of the owner if the entity is natural person

        Return:
        - None if the company creating JPK is legal person
        - string containing date of birth if natural person
        """

        if is_natural_person == "0":
                return None
        
        # TODO: get data from application

        answer = input(_("Birth date (YYYY-MM-DD)") + ": ")

        if is_date_format_correct(answer):
                return answer
        else:
                return get_date_of_birth(is_natural_person)


def is_date_format_correct(date_string):
        """
        Check if date is in format YYYY-MM-DD

        Return:
        - True if format correct
        - False if format wrong
        """

        if len(date_string) != 10:
                return False

        try:
                date = datetime.strptime(date_string, "%Y-%m-%d")
        
        except ValueError:
                return False

        if date > datetime.now():
                return False

        return True

def get_tax_number():
        """
        Get tax number of the entity creating JPK.

        Return string containing 10-digits tax number
        """
        
        # TODO: get data from application

        answer = input(_("Tax number (10 digits)") + ": ")

        # tax number should contain only 10 digits
        if answer.isdecimal() and len(answer) == 10:
                return answer
        else:
                return get_tax_number()


def get_email():
        """
        Get e-mail address of the entity. Tax office will use it for contact.

        Return string containing e-mail address.
        """
        
        # TODO: get data from application

        answer = input(_("E-mail address") + ": ")

        # e-mail address should contain:
        # - at least 1 letter before @
        # - 1 @
        # - at least 1 letter between @ and .
        # - at least one .
        # - at least one letter in the end
        # that makes at least 6 signs

        # note: use regular expressions, not as below

        # if string too short
        if len(answer) < 6:
                return get_email()

        # if string doesn't contain single @
        if answer.count("@") != 1:
                return get_email()

        position_of_at = answer.find("@")

        # if @ is first or missing
        if position_of_at < 1:
                return get_email()

        position_of_last_dot = answer.rfind(".")

        # if last dot is before @
        if position_of_last_dot < position_of_at:
                return get_email()

        # if dot is last
        if position_of_last_dot == (len(answer) - 1):
                return get_email()
        
        return answer


def get_phone_number():
        """
        Get phone number. Tax office will use it for contact. It's optional.

        Return string containing phone number.
        """
        
        # TODO: get data from application

        answer = input(_("Phone number (optional)") + ": ")

        # according to XSD of JPK_V7M, phone number has no restrictions.
        # In practice it MUST contain some digits and CAN contain:
        # - separators (like " " or "-")
        # - country numbers starting with "+"
        # - area codes between "(" and ")"
        # - extension numbers with markers like "wew", "wewn.", "ext", etc.
        # and so on, so check only if answer contains any digit or is ""
        
        if answer == "":
                return None
        elif contains_digits(answer):
                return answer
        else:
                return get_phone_number()


def get_forwarded_excess_of_input_tax():
        """
        Get forwarded excess of input tax over output tax from previous period
        (field P_62 in JPK for previous period)

        Return value or None
        """
        
        # TODO: get data from application

        answer = input(_("Carried forward excess of input tax") + ": ")

        # amount should contain only digits
        if answer.isdecimal():
                return answer
        elif answer == "":
                return "0"
        else:
                return get_forwarded_excess_of_input_tax()


def get_amendment_reasons():

        # TODO: get data from application

        return input(_("Reasons of amendments (if any)") + ": ")


def register_namespaces(xml):
        """
        Not used anymore. Left for possible future use.
        
        Registers namespaces occuring in xml string as global ElementTree names.

        Required if we want custom namespace names instead of standard ns0, ns1,
        ns2, ... - probably only when reading (parsing) existing XML.
        Seems useless when we create our own XML and use:
        Element.set("xmlns:prefix", "URI")

        Reads namespaces from given XML string and registers as ElementTree
        global namespaces

        Returns None
        """

        namespaces = dict([node for event, node in ET.iterparse(StringIO(xml), events=['start-ns'])])
        for ns in namespaces:
                ET.register_namespace(ns, namespaces[ns])


def create_jpk_header(purpose, tax_office_code, month, year, system_name, creation_date = None):
        """
        Create ElementTree.Element containing JPK header data.

        Arguments:
        - purpose (string): "1" if it's first JPK for given period,
          "2" if it's amendment of already sent JPK
        - tax_office_code (string): 4-digit code of Tax Office that will
          receive the JPK
        - month (string): number of month of JPK period
        - year (string): year of JPK period
        - creation_date (datetime object): date and time when JPK was generated

        Note: could be better to add the date after all time-consuming parts of
        JPK are ready, so prefer to create the header as last part. In other way
        the header will contain the time of starting the creation.

        Returns ElementTree.Element containing all required JPK header data
        """

        header_element = ET.Element("tns:Naglowek")

        # <tns:KodFormularza kodSystemowy="JPK_V7M (1)" wersjaSchemy="1-2E">
        #       JPK_VAT
        # </tns:KodFormularza>
        form_code_element = ET.SubElement(header_element, "tns:KodFormularza")
        form_code_element.set("kodSystemowy", "JPK_V7M (1)")
        form_code_element.set("wersjaSchemy", "1-2E")
        form_code_element.text = "JPK_VAT"

        # <tns:WariantFormularza>1</tns:WariantFormularza>
        form_variant_element = ET.SubElement(header_element, "tns:WariantFormularza")
        form_variant_element.text = "1"

        if creation_date is None:
                creation_date = datetime.now()
        # <tns:DataWytworzeniaJPK>2020-11-01T00:00:00</tns:DataWytworzeniaJPK>
        creation_date_element = ET.SubElement(header_element, "tns:DataWytworzeniaJPK")
        creation_date_element.text = creation_date.replace(microsecond=0).isoformat()

        # <tns:NazwaSystemu>System Name</tns:NazwaSystemu>
        system_name_element = ET.SubElement(header_element, "tns:NazwaSystemu")
        system_name_element.text = system_name

        # <tns:CelZlozenia poz="P_7">1</tns:CelZlozenia>
        purpose_element = ET.SubElement(header_element, "tns:CelZlozenia")
        purpose_element.text = purpose
        purpose_element.set("poz", "P_7")

        # <tns:KodUrzedu>0202</tns:KodUrzedu>
        tax_office_element = ET.SubElement(header_element, "tns:KodUrzedu")
        tax_office_element.text = tax_office_code

        # <tns:Rok>2020</tns:Rok>
        year_element = ET.SubElement(header_element, "tns:Rok")
        year_element.text = year

        # <tns:Miesiac>10</tns:Miesiac>
        month_element = ET.SubElement(header_element, "tns:Miesiac")
        month_element.text = month

        return header_element


def initialize_jpk():
        """
        Create root ElementTree.Element of JPK and set required things

        Returns root ElementTree.Element of JPK
        """

        # create ElementTree.Element
        jpk_root = ET.Element("tns:JPK")

        # set 3 namespace declarations
        jpk_root.set("xmlns:etd", "http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2020/03/11/eD/DefinicjeTypy/")
        jpk_root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        jpk_root.set("xmlns:tns", "http://crd.gov.pl/wzor/2020/05/08/9393/")

        return jpk_root


def create_jpk_person(is_natural_person, tax_number, email, first_name=None, last_name=None, full_name=None, phone=None, date_of_birth=None):
        """
        Create ElementTree.Element containing required data of natural or legal
        person

        Arguments:
        - is_natural_person (string): "0" if entity is legal person, "1" if
          natural person
        - tax_number (string): 10-digit tax tumber of the entity creating JPK
        - email (string): e-mail addres that will be used by tax office for
          contact
        - first_name (string): first name of owner if entity is natural person
        - last_name (string): last name of owner if entity is natural person
        - full_name (string): full name of the company if entity is legal person
        - phone (string): (optional) phone number to be used by tax office for
          contact
        - date_of_birth: date of birth of owner if entity is natural person

        Returns Element containing required natural or legal person data
        """

        if is_natural_person == "0":

		# <tns:OsobaNiefizyczna>
                person_element = ET.Element("tns:OsobaNiefizyczna")
                
		# <tns:NIP>9999999999</tns:NIP>
                tax_number_element = ET.SubElement(person_element, "tns:NIP")
                tax_number_element.text = tax_number
                
		# <tns:PelnaNazwa>AAAAAAAA</tns:PelnaNazwa>
                full_name_element = ET.SubElement(person_element, "tns:PelnaNazwa")
                full_name_element.text = full_name

		# <tns:Email>nazwa@nazwa.pl</tns:Email>
                email_element = ET.SubElement(person_element, "tns:Email")
                email_element.text = email
                
		# <tns:Telefon>111111111</tns:Telefon>
                phone_element = ET.SubElement(person_element, "tns:Telefon")
                phone_element.text = phone

                return person_element

        elif is_natural_person == "1":

                person_element = ET.Element("tns:OsobaFizyczna")

                tax_number_element = ET.SubElement(person_element, "etd:NIP")
                tax_number_element.text = tax_number

                first_name_element = ET.SubElement(person_element, "etd:ImiePierwsze")
                first_name_element.text = first_name
                
                last_name_element = ET.SubElement(person_element, "etd:Nazwisko")
                last_name_element.text = last_name
                
                date_of_birth_element = ET.SubElement(person_element, "etd:DataUrodzenia")
                date_of_birth_element.text = date_of_birth

                email_element = ET.SubElement(person_element, "tns:Email")
                email_element.text = email

                phone_element = ET.SubElement(person_element, "tns:Telefon")
                phone_element.text = phone

                return person_element
                

def create_jpk_entity(is_natural_person, tax_number, email, first_name=None, last_name=None, full_name=None, phone=None, date_of_birth=None):
        """
        Create ElementTree.Element containing all required data of entity
        creating JPK

        Arguments:
        - is_natural_person (string): "0" if entity is legal person, "1" if
          natural person
        - tax_number (string): 10-digit tax tumber of the entity creating JPK
        - email (string): e-mail addres that will be used by tax office for
          contact
        - first_name (string): first name of owner if entity is natural person
        - last_name (string): last name of owner if entity is natural person
        - full_name (string): full name of the company if entity is legal person
        - phone (string): (optional) phone number to be used by tax office for
          contact
        - date_of_birth: date of birth of owner if entity is natural person

        Returns Element containing all required data of entity creating JPK
        """

        # <tns:Podmiot1 rola="Podatnik">
        entity_element = ET.Element("tns:Podmiot1")
        entity_element.set("rola", "Podatnik")

        person_element = create_jpk_person(
                is_natural_person,
                tax_number,
                email,
                first_name,
                last_name,
                full_name,
                phone,
                date_of_birth
                )

        if person_element is not None:
                entity_element.append(person_element)

        return entity_element


def create_jpk_evidence(input_tax_documents, output_tax_documents, sum_of_field_k, sum_of_bad_debt_relief):
        """
        Create element containing tax evidence, including input tax, output tax
        and control fields.

        Arguments:
        - input_tax_documents - list of dicts or None
        - output_tax_documents - list of dicts or None
        For more information see def get_input_tax_documents and
        def get_output_tax_documents

        Returns Element containing output and input tax evidence and control
        fields
        """

        # <tns:Ewidencja>
        evidence_element = ET.Element("tns:Ewidencja")

        input_rows_count = 0

        input_tax_rows = create_jpk_input_tax_rows(input_tax_documents, sum_of_field_k)

        input_tax_total = sum_fields(sum_of_field_k, [41, 43, 44, 45, 46, 47])

        for row in input_tax_rows:
                evidence_element.append(row)
                input_rows_count += 1
        else:
                # <tns:ZakupCtrl>
                input_tax_control_element = ET.SubElement(evidence_element, "tns:ZakupCtrl")

                # <tns:LiczbaWierszyZakupow>1</tns:LiczbaWierszyZakupow>
                input_rows_count_element = ET.SubElement(input_tax_control_element, "tns:LiczbaWierszyZakupow")
                input_rows_count_element.text = str(input_rows_count)

                # <tns:PodatekNaliczony>0</tns:PodatekNaliczony>
                input_tax_total_element = ET.SubElement(input_tax_control_element, "tns:PodatekNaliczony")
                input_tax_total_element.text = str(input_tax_total)
                
        output_rows_count = 0

        output_tax_rows = create_jpk_output_tax_rows(output_tax_documents, sum_of_field_k, sum_of_bad_debt_relief)

        output_tax_total = sum_fields(sum_of_field_k, [16, 18, 20, 24, 26, 28, 30, 32, 33, 34]) - sum_fields(sum_of_field_k, [35, 36]) 

        for row in output_tax_rows:
                evidence_element.append(row)
                output_rows_count += 1
        else:
		# <tns:SprzedazCtrl>
                output_tax_control_element = ET.SubElement(evidence_element, "tns:SprzedazCtrl")

                # <tns:LiczbaWierszySprzedazy>1</tns:LiczbaWierszySprzedazy>
                output_rows_count_element = ET.SubElement(output_tax_control_element, "tns:LiczbaWierszySprzedazy")
                output_rows_count_element.text = str(output_rows_count)
                
		# <tns:PodatekNalezny>0</tns:PodatekNalezny>
                output_tax_total_element = ET.SubElement(output_tax_control_element, "tns:PodatekNalezny")
                output_tax_total_element.text = str(output_tax_total)
        
        return evidence_element


def create_jpk_input_tax_rows(documents, sum_of_field_k):
        """
        Create list of ElementTree.Element containing data of input tax
        documents evidence

        Returns list of elements containing input tax evidence
        """

        rows = []
        row_number = 0
        
        raw_rows = []

        if documents is not None:
                raw_rows = documents
        else:
                raw_rows = get_input_tax_documents()

        for raw_row in raw_rows:
                row_number += 1
                row = create_jpk_input_tax_row(row_number, raw_row, sum_of_field_k)
                rows.append(row)
                
        return rows


def get_input_tax_documents():
        """
        Get data of input tax documents.

        Single document must be converted into dict and added to list that will
        be returned.

        for list of keys see: create_jpk_input_tax_row()

        Returns list of dictionaries containing input tax documents data
        """

        # TODO: get data from application

        documents = []

        document = get_input_tax_document()

        while document is not None:
                documents.append(document)
                document = get_input_tax_document()


        return documents


def get_input_tax_document():
        """
        Get data of input tax document in form of a dict.

        Return:
        - data of tax document as dict with keys according to element_names dict
          declared in create_jpk_input_tax_row()
        - None if no more documents
        """

        # TODO: get data from application

        doc = {}

        print("\n\t_____________________________________\n")
        
        next_doc = input(_("Do you want to add input tax document?") + _(" [Y/n]: "))
        next_doc = next_doc.lower()

        if next_doc == "" or next_doc == "t" or next_doc == "1" or next_doc == "y":

                # TODO: verify data format
                print("\n" + _("Warning") + ":\n" + _("Data validation not implemented!") + "\n")

                doc["party_country_code"] = input(_("Party country code (2 letters)") + ": ")
                doc["party_tax_id"] = input(_("Party tax ID (10 digits)") + ": ")
                doc["party_name"] = input(_("Party full name") + ": ")
                doc["document_number"] = input(_("Document number") + ": ")
                doc["document_date"] = input(_("Dcoument date (YYYY-MM-DD)") + ": ")
                doc["document_receipt_date"] = input(_("Document receipt date (optional)") + ": ")
                doc["document_type"] = input(_("Document type (optional: MK - cash method, VAT_RR, WEW - internal)") + ": ")

                is_split_payment = input(_("Split payment?") + _(" [y/N]: "))

                if is_split_payment == "t" or is_split_payment == "y" or is_split_payment == "1":
                        doc["split_payment"] = "1"

                is_import = input(_("Import?") + _(" [y/N]: "))

                if is_import == "t" or is_import == "1" or is_import == "y":
                        doc["import"] = "1"

                # TODO: better validation

                net_fixed_assets = None

                while net_fixed_assets == None:
                        net_fixed_assets = validate_float(input(_("Fixed assets purchase amount (optional)") + ": "))
                else:
                        doc["k_40"] = net_fixed_assets

                if net_fixed_assets != "0.0":
                        doc["k_41"] = input(_("Tax amount for above") + ": ")

                net_other = None

                while net_other == None:
                        net_other = validate_float(input(_("Other goods or services purchase amount") + ": "))
                else:
                        doc["k_42"] = net_other

                if net_other != "0.0":
                        doc["k_43"] = input(_("Tax amount for above") + ": ")

                doc["vat_margin"] = input(_("Purchase amount with VAT margin invoice (optional)") + ": ")

                is_tax_amendment = input(_("Do you want to fill tax amendment fields?") + _(" [y/N]"))

                if is_tax_amendment == "t" or is_tax_amendment == "1" or is_tax_amendment == "y":
                        doc["k_44"] = input(_("Fixed assets input tax amendment (optional)") + ": ")
                        doc["k_45"] = input(_("Other goods or services input tax amendment (optional)") + ": ")
                        doc["k_46"] = input(_("Input tax amendment due to unpaid invoice (optional)") + ": ")
                        doc["k_47"] = input(_("Input tax amendment due to payment of unpaid invoice (with previously amendet input tax like above) (optional)") + ": ")

        else:
                return None

        return doc


def create_jpk_element_if_key_exist(data, key, name):
        """
        Create ElementTree.Element if the given key exists in the given dict and
        then set the Element text from value associated with the key.

        It's used for batch creating JPK elements in tax evidence where many
        fields are optional. 

        Arguments:
        - data: dict of key-value pairs
        - key: key that we are searching for
        - name: a name for new Element

        Return ElementTree.Element or None
        """

        if data.get(key, None):
                new_element = ET.Element(name)
                new_element.text = data[key]
                return new_element


def create_jpk_input_tax_row(row_number, raw_row, sum_of_field_k):
        """
        Creates ElementTree.Element containing data of single input tax document

        Converts data in form of dict in ElementTree.Element with subelements.

        Arguments:
        - row_number: consecutive number of row
        - raw_row: dict containing data of single input tax document

        Returns element containing input tax row data
        """
        
        input_tax_row_element = ET.Element("tns:ZakupWiersz")

        element_names = {
                "party_country_code": "tns:KodKrajuNadaniaTIN",
                "party_tax_id": "tns:NrDostawcy",
                "party_name": "tns:NazwaDostawcy",
                "document_number": "tns:DowodZakupu",
                "document_date": "tns:DataZakupu",
                "document_receipt_date": "tns:DataWplywu",
                "document_type": "tns:DokumentZakupu",
                "split_payment": "tns:MPP",
                "import": "tns:IMP",
                "k_40": "tns:K_40",
                "k_41": "tns:K_41",
                "k_42": "tns:K_42",
                "k_43": "tns:K_43",
                "k_44": "tns:K_44",
                "k_45": "tns:K_45",
                "k_46": "tns:K_46",
                "k_47": "tns:K_47",
                "vat_margin": "tns:ZakupVAT_Marza"
        }
                
        # <tns:LpZakupu>1</tns:LpZakupu>
        row_number_element = ET.SubElement(input_tax_row_element, "tns:LpZakupu")
        row_number_element.text = str(row_number)

        for key in element_names:
                el = create_jpk_element_if_key_exist(raw_row, key, element_names[key])
                if el is not None:
                        input_tax_row_element.append(el)

        for i in range(40, 48):
                tax = raw_row.get("k_" + str(i), "0.0")

                # tax can be empty string (ValueError)
                if isinstance(tax, str) and len(tax) > 0 and tax.lstrip('-').replace('.', '').isdigit():
                        sum_of_field_k[i] += float(tax)
                elif isinstance(tax, int) or isinstance(tax, float):
                        sum_of_field_k[i] += tax

        return input_tax_row_element


def create_jpk_output_tax_row(row_number, raw_row, sum_of_field_k, sum_of_bad_debt_relief):
        """
        Creates ElementTree.Element containing data of single output tax
        document.

        Converts data in form of dict into ElementTree.Element with subelements.

        Arguments:
        - row_number: consecutive number of row
        - raw_row: data of single output tax document as dict

        Returns element containing output tax row data
        """
        
        output_tax_row_element = ET.Element("tns:SprzedazWiersz")

        element_names = {
                "party_country_code": "tns:KodKrajuNadaniaTIN",
                "party_tax_id": "tns:NrKontrahenta",
                "party_name": "tns:NazwaKontrahenta",
                "document_number": "tns:DowodSprzedazy",
                "document_date": "tns:DataWystawienia",
                "sales_date": "tns:DataSprzedazy",
                "document_type": "tns:TypDokumentu",
                "gtu_01": "tns:GTU_01",
                "gtu_02": "tns:GTU_02",
                "gtu_03": "tns:GTU_03",
                "gtu_04": "tns:GTU_04",
                "gtu_05": "tns:GTU_05",
                "gtu_06": "tns:GTU_06",
                "gtu_07": "tns:GTU_07",
                "gtu_08": "tns:GTU_08",
                "gtu_09": "tns:GTU_09",
                "gtu_10": "tns:GTU_10",
                "gtu_11": "tns:GTU_11",
                "gtu_12": "tns:GTU_12",
                "gtu_13": "tns:GTU_13",
                "sw": "tns:SW",
                "ee": "tns:EE",
                "tp": "tns:TP",
                "tt_wnt": "tns:TT_WNT",
                "tt_d": "tns:TT_D",
                "mr_t": "tns:MR_T",
                "mr_uz": "tns:MR_UZ",
                "i_42": "tns:I_42",
                "i_63": "tns:I_63",
                "b_spv": "tns:B_SPV",
                "b_spv_dostawa": "tns:B_SPV_DOSTAWA",
                "b_mpv_prowizja": "tns:B_MPV_PROWIZJA",
                "split_payment": "tns:MPP",
                "tax_base_amendment": "tns:KorektaPodstawyOpodt",
                "k_10": "tns:K_10",
                "k_11": "tns:K_11",
                "k_12": "tns:K_12",
                "k_13": "tns:K_13",
                "k_14": "tns:K_14",
                "k_15": "tns:K_15",
                "k_16": "tns:K_16",
                "k_17": "tns:K_17",
                "k_18": "tns:K_18",
                "k_19": "tns:K_19",
                "k_20": "tns:K_20",
                "k_21": "tns:K_21",
                "k_22": "tns:K_22",
                "k_23": "tns:K_23",
                "k_24": "tns:K_24",
                "k_25": "tns:K_25",
                "k_26": "tns:K_26",
                "k_27": "tns:K_27",
                "k_28": "tns:K_28",
                "k_29": "tns:K_29",
                "k_30": "tns:K_30",
                "k_31": "tns:K_31",
                "k_32": "tns:K_32",
                "k_33": "tns:K_33",
                "k_34": "tns:K_34",
                "k_35": "tns:K_35",
                "k_36": "tns:K_36",
                "vat_margin": "tns:SprzedazVAT_Marza"
        }
                
        row_number_element = ET.SubElement(output_tax_row_element, "tns:LpSprzedazy")
        row_number_element.text = str(row_number)

        for key in element_names:
                el = create_jpk_element_if_key_exist(raw_row, key, element_names[key])
                if el is not None:
                        output_tax_row_element.append(el)

        bad_debt_relief = False
        if raw_row.get("tax_base_amendment") == "1":
                bad_debt_relief = True

        fp = False
        if raw_row.get("document_type") == "FP":
                fp = True

        for i in range(10, 37):
                # TODO: remane "tax"? It can be tax base or tax value
                tax = raw_row.get("k_" + str(i), 0.0)

                tax_as_float = validate_float(tax)

                if tax_as_float == None:
                        print(_("Warning! Wrong tax value: ") + str(tax))
                else:
                        # omit for documents "FP"
                        if not fp:
                                sum_of_field_k[i] += tax_as_float

                        if  bad_debt_relief and tax_as_float < 0:
                                # amendet net amounts
                                if i in [15, 17, 19]:
                                        sum_of_bad_debt_relief["net"] += tax_as_float
                                # amendet tax values
                                elif i in [16, 18, 20]:
                                        sum_of_bad_debt_relief["tax"] += tax_as_float

        return output_tax_row_element


def validate_float(data):
        """
        Checks if data contains something that can be used as float:
        - string containing float
        - int
        - float itself
        and converts it to string.

        Return:
        - string containing float if possible
        - "0.0" if empty string
        - None if float not possible
        """

        if isinstance(data, str):
                if len(data) > 0:
                        if data.lstrip('-').replace('.', '').isdigit():
                                return data
                else:
                        return "0.0"
        elif isinstance(data, float):
                return str(data)
        elif isinstance(data, int):
                return str(float(data))
        else:
                return None
        
                                      
def create_jpk_output_tax_rows(documents, sum_of_field_k, sum_of_bad_debt_relief):
        """
        Create list of ElementTree.Element containing output tax documents
        evidence

        Return list of elements containing output tax documents evidence
        """

        rows = []
        row_number = 0

        raw_rows = []

        if documents is not None:
                raw_rows = documents
        else:
                raw_rows = get_output_tax_documents()

        for raw_row in raw_rows:
                row_number += 1
                row = create_jpk_output_tax_row(row_number, raw_row, sum_of_field_k, sum_of_bad_debt_relief)
                rows.append(row)
                
        return rows


def get_output_tax_documents():
        """
        Get data of output tax documents

        Single document must be converted into dict and added to list that will
        be returned

        For list of dict keys see: def create_jpk_output_tax_row()

        Returns list of dictionaries containing output tax documents data
        """

        # TODO: get data from application

        documents = []

        document = get_output_tax_document()

        while document is not None:
                documents.append(document)
                document = get_output_tax_document()

        return documents


def get_output_tax_document():
        """
        Get data of output tax document in form of dict.

        Return:
        - data of tax document as dict with keys according to element_names dict
          declared in create_jpk_output_tax_row()
        - None if no more documents
        """

        # TODO: get data from application

        doc = {}

        print("\n\t_____________________________________\n")
        
        next_doc = input(_("Do you want to add output tax document?") + _(" [Y/n]: "))
        next_doc = next_doc.lower()

        if next_doc == "" or next_doc == "t" or next_doc == "1" or next_doc == "y":

                # TODO: verify data format
                print("\n" + _("Warning") + ":\n" + _("Data validation not implemented!") + "\n")

                print(_("For numbers:\n - don't use separators (type 1000 instead of 1 000 or 1,000)\n - use dot for fractional part (1000.00)\n"))

                doc["party_country_code"] = input(_("Party country code (2 letters)") + ": ")
                doc["party_tax_id"] = input(_("Party tax ID (10 digits)") + ": ")
                doc["party_name"] = input(_("Party full name") + ": ")
                doc["document_number"] = input(_("Document number") +": ")
                doc["document_date"] = input(_("Document date (YYYY-MM-DD)") + ": ")
                doc["sales_date"] = input(_("Sales date (if other than document date)") + ": ")
                doc["document_type"] = input(_("Document type (optional: RO - cash register sales report, WEW - internal, FP - receipt based invoice)") + ": ")

                is_split_payment = input(_("Split payment?") + _(" [y/N]: "))

                if is_split_payment == "t" or is_split_payment == "1" or is_split_payment == "y":
                        doc["split_payment"] = "1"

                print("\n")
                print(_("All descriptions are indicative only. Check full requirements in official JPK documentation!"))
                print("\n")

                print(_("Type 1 or leave blank"))
                print("\n")

                doc["gtu_01"] = input(_("GTU_01 (alcohols)? "))
                doc["gtu_02"] = input(_("GTU_02 (fuels and oils)? "))
                doc["gtu_03"] = input(_("GTU_03 (oils and greases)? "))
                doc["gtu_04"] = input(_("GTU_04 (tobacco and other smoking and vaping products)? "))
                doc["gtu_05"] = input(_("GTU_05 (waste and recyclable materials)? "))
                doc["gtu_06"] = input(_("GTU_06 (electronics, printing, stretch foil)? "))
                doc["gtu_07"] = input(_("GTU_07 (vehicles, parts, accessories)? "))
                doc["gtu_08"] = input(_("GTU_08 (metals)? "))
                doc["gtu_09"] = input(_("GTU_09 (pharmacy)? "))
                doc["gtu_10"] = input(_("GTU_10 (real estates)? "))
                doc["gtu_11"] = input(_("GTU_11 (greenhouse gases)? "))
                doc["gtu_12"] = input(_("GTU_12 (intangible services)? "))
                doc["gtu_13"] = input(_("GTU_13 (transport and storage services)? "))

                doc["sw"] = input(_("SW (mail order to other EU country)? "))
                doc["ee"] = input(_("EE (telecommunication, broadcasting or electronic services)? "))
                doc["tp"] = input(_("TP (related entity)? "))
                doc["tt_wnt"] = input(_("TT_WNT (EU purchase in traingle transaction, simplified procedure)? "))
                doc["tt_d"] = input(_("TT_D (delivery in traingle transaction, simplified procedure)? "))
                doc["mr_t"] = input(_("MR_T (VAT margin - tourism)? "))
                doc["mr_uz"] = input(_("MR_UZ (VAT margin - used goods, art, antiques, collectibles)? "))
                doc["i_42"] = input(_("I_42 (delivery to other EU country after import with procedure 42)? "))
                doc["i_63"] = input(_("I_63 (delivery to other EU country after import with procedure 63)? "))
                doc["b_spv"] = input(_("B_SPV (single purpose voucher)? "))
                doc["b_spv_dostawa"] = input(_("B_SPV_DOSTAWA (delivery based on single purpose voucher)? "))
                doc["b_mpv_prowizja"] = input(_("B_MPV_PROWIZJA (multi purpose voucher - brokerage)? "))
                doc["tax_base_amendment"] = input(_("Amendment (increasing or decreasing) related to bad debt relief? "))
                doc["k_10"] = input(_("K_10 - Net amount for tax exempt") + ": ")
                doc["k_11"] = input(_("K_11 - Sales abroad") + ": ")
                doc["k_12"] = input(_("K_12 - of which sales of services to the EU") + ": ")
                doc["k_13"] = input(_("K_13 - Net amount for tax 0%") + ": ")
                doc["k_14"] = input(_("K_14 - of which tax returned to tourist") + ": ")
                doc["k_15"] = input(_("K_15 - Net amount for tax 5%") + ": ")
                doc["k_16"] = input(_("K_16 - Tax amount (5%)") + ": ")
                doc["k_17"] = input(_("K_17 - Net amount for tax 7% or 8%") + ": ")
                doc["k_18"] = input(_("K_18 - Tax amount (7% or 8%)") + ": ")
                doc["k_19"] = input(_("K_19 - Net amount for tax 22% or 23%") + ": ")
                doc["k_20"] = input(_("K_20 - Tax amount (22% or 23%)") + ": ")
                doc["k_21"] = input(_("K_21 - Net amount sales of goods to the EU") + ": ")
                doc["k_22"] = input(_("K_22 - Net amount sales of goods exported") + ": ")
                doc["k_23"] = input(_("K_23 - Net amount purchase of goods from EU") + ": ")
                doc["k_24"] = input(_("K_24 - Tax amount (purchase of goods from EU)") + ": ")
                doc["k_25"] = input(_("K_25 - Net amount import in simplified procedure") + ": ")
                doc["k_26"] = input(_("K_26 - Tax amount (import in simplified procedure)") + ": ")
                doc["k_27"] = input(_("K_27 - Net amount import of services except acc. to  art. 28b (supplier paid tax in other country)") + ": ")
                doc["k_28"] = input(_("K_28 - Tax amount (import of services except acc. to art. 28b)") + ": ")
                doc["k_29"] = input(_("K_29 - Net amount import of services acc. to art. 28b (tax to be paid by buyer in Poland, most common case)") + ": ")
                doc["k_30"] = input(_("K_30 - Tax amount (import of services acc. to art. 28b)") + ": ")
                doc["k_31"] = input(_("K_31 - Net amount sales where tax will be paid by buyer") + ": ")
                doc["k_32"] = input(_("K_32 - Tax amount that will be paid by buyer") + ": ")
                doc["k_33"] = input(_("K_33 - Tax amount acc. to art.15 sec.5 (physical inventory e.g. on closure of business)") + ": ")
                doc["k_34"] = input(_("K_34 - Repayment of tax refunded or deducted on purchase of cash registers (e.g. closure of business, lack of service inspection)") + ": ")
                doc["k_35"] = input(_("K_35 - Tax amount purchase of means of transport from EU") + ": ")
                doc["k_36"] = input(_("K_36 - Tax amount acc. to art. 103 sec. 5aa (purchase of fuels from EU)") + ": ")
                doc["vat_margin"] = input(_("Gross amount of sales with VAT margin invoice") + ": ")
        else:
                return None

        return doc


def create_jpk_declaration_header():
        """
        Create Element containing header of declaration part of JPK

        Return Element containing all required declaration header data
        """

        # <tns:Naglowek>
        declaration_header_element = ET.Element("tns:Naglowek")

	# <tns:KodFormularzaDekl kodSystemowy="VAT-7 (21)" kodPodatku="VAT" rodzajZobowiazania="Z" wersjaSchemy="1-2E">VAT-7</tns:KodFormularzaDekl>
        decl_form_code_element = ET.SubElement(declaration_header_element, "tns:KodFormularzaDekl")
        decl_form_code_element.set("kodSystemowy", "VAT-7 (21)")
        decl_form_code_element.set("kodPodatku", "VAT")
        decl_form_code_element.set("rodzajZobowiazania", "Z")
        decl_form_code_element.set("wersjaSchemy", "1-2E")
        decl_form_code_element.text = "VAT-7"

	# <tns:WariantFormularzaDekl>21</tns:WariantFormularzaDekl>
        decl_form_variant = ET.SubElement(declaration_header_element, "tns:WariantFormularzaDekl")
        decl_form_variant.text = "21"

        return declaration_header_element        


def create_jpk_declaration(is_guidance_accepted, sum_of_field_k, sum_of_bad_debt_relief, forwarded_excess_of_input_tax = "0", amendment_reasons = ""):
        """
        Creates ElementTree.Element containing all required declaration data

        Arguments:
        - is_guidance_accepted: "1" if the user accepted the guidance (required)
        - sum_of_field_k - list containing sum of values of fields named
          tns:K_{number}
        - forwarded_excess_of_input_tax (string) - amount of excess of input tax
          over output tax carried forward from previous period

        Return Element containing all required declaration data
        """

        # TODO: Add code for fields:
        # P_49, P_50, P_52, P_54 up to P_61, P_63 up to P_69, P_ORDZU

        # IMPORTANT!
        # P_ fields must be integers. Rounding rule:
        # - decimal parts below 0.5 must be omitted (1.49 -> 1, 2.49 -> 2)
        # - decimal parts >= 0.5 must be rounded up (1.5 -> 2, 2.5 -> 3)
        # (!!!) But Python uses "banker's rounding":
        # - odds rounded "up": 1.5 -> 2, 3.5 -> 4
        # - evens rounded "down": 2.5 -> 2, 4.5 -> 4
        # Trick to avoid this: add something not changing rounded value!
        # so 0.001 should be good enough
        
        
        # <tns:Deklaracja>
        declaration_element = ET.Element("tns:Deklaracja")

        declaration_header_element = create_jpk_declaration_header()
        declaration_element.append(declaration_header_element)

        declaration_details_element = ET.SubElement(declaration_element, "tns:PozycjeSzczegolowe")

        # fields P_10-P_36 and P_40-P_47 are sum of K_ fields with the same number (P_10 = sum of all K_10, etc.)
        p_from_k = list(range(10, 37)) + list(range(40,48))
        p_value = {}

        for i in p_from_k:
                # (same fix for rounding issue is used for other fields below)
                p_value[i] = round(sum_of_field_k[i] + 0.00001)

        # field P_37 is a sum of output tax bases
        p_value[37] = sum_fields(p_value, [10, 11, 13, 15, 17, 19, 21, 22, 23, 25, 27, 29, 31])

        #field P_38 is a calculation of output tax and must exist
        # even if value is 0
        p_value[38] = sum_fields(p_value, [16, 18, 20, 24, 26, 28, 30, 32, 33, 34]) - sum_fields(p_value, [35, 36])

        # field P_39 is a forwarded excess of input tax from last month
        p_value[39] = int(forwarded_excess_of_input_tax)

        # field P_48 is a sum of input tax
        p_value[48] = sum_fields(p_value, [39, 41, 43, 44, 45, 46, 47])

        # TODO: fields that can be useless for me:
        # P_49 - purchase of cash registers - part aplicable for this period
        # P_50 - waived tax
        p_value[49] = 0
        p_value[50] = 0

        # field P_51 is for tax amount to be paid or 0
        p_value[51] = 0
        if p_value[38] > p_value[48]:
                p_value[51] = p_value[38] - sum_fields(p_value, [48, 49, 50])

        # TODO: fields that can be useless for me:
        # P_52 - purchase of cash registers - remaining part
        p_value[52] = 0

        # field P_53 is excess of input tax over output tax
        p_value[53] = 0
        if p_value[48] > p_value[38]:
                p_value[53] = p_value[48] - p_value[38] + p_value[52]

        # TODO: give the user below options:
        # P_54 - amount of P_53 to be returned on any below mentioned account
        # P_55 - return tax to VAT account ("1" if yes)
        # P_56-58 - reutrn to standard acount in 25/60/180 days ("1" if yes)
        # P_59 - use the amount towards future tax obligations ("1" if yes)
        # P_60 - amount if P_59 checked
        # P_61 - type of future tax obligations if P_59 checked

        # P_54 is used for calculation in P_62, but not implemented
        p_value[54] = 0

        # P_62 - excess of input tax over output tax to be carried forward to
        # next month
        p_value[62] = p_value[53] - p_value[54]

        # TODO: fields that can be useless for me:
        # (check if can be determined on the basis of processed documents)
        # P_63 - "1" if supplied tourism-related services w/ VAT margin invoice
        # P_64 - "1" if supplied second hand, art, etc. w/ VAT margin inoice
        # P_65 - "1" if some (specified) operations related to investment gold
        # P_66 - "1" if second in simplified procedure of triangular transaction
        # P_67 - "1" if used tax relief due to early payment from VAT account

        # P_68 and P_69 must be 0 or in minus
        # P_68 - sum of taxable base amendments (bad debt relief)
        # (using fix for "banker's rounding" issue as previously)
        p_value[68] = round(sum_of_bad_debt_relief["net"] + 0.00001)

        # P_69 - sum of output tax amendments (bad debt relief)
        # (using fix for "banker's rounding" issue as previously)
        p_value[69] = round(sum_of_bad_debt_relief["tax"] + 0.00001)

        # P_ORDZU - optional, description of reasons for amendments
        p_value["ORDZU"] = amendment_reasons

        # create P_{number} elements with calculated values
        for number, value in p_value.items():
                p = create_p_element(number, value)
                if p is not None:
                        declaration_details_element.append(p)

        # <tns:Pouczenia>1</tns:Pouczenia>
        guidance_element = ET.SubElement(declaration_element, "tns:Pouczenia")
        guidance_element.text = is_guidance_accepted

        return declaration_element


def create_p_element(number, value):
        """
        Creates ElementTree.Element of JPK for fields named tns:P_{number}

        Arguments:
        - value: the value to be set as text of Element
        - number: the number to be added to tns:P_... name

        Return Element P_{number} with given text (value)
        """

        p = ET.Element("tns:P_" + str(number))
        p.text = str(value)
        return p


def sum_fields(values, numbers):
        """
        Sum of values of fields with given numbers

        Arguments:
        - values: list of values
        - numbers: list of fields to sum

        Return sum of fields with given numbers
        """

        total = 0
        for i in numbers:
                total += values[i]

        return total
        

def initialize_list(list_name, number_of_fields, value):
        """
        Set given number of fields with given value to a list

        Arguments:
        - list_name: name of list to initialize
        - number_of_fields: number of fields to add
        - value: value to insert in fields
        """

        # in case if not empty list
        list_name.clear()

        for i in range(number_of_fields):
                list_name.append(value)


def show_xml(element_to_show):
        """
        Show formatted XML in console

        Arguments:
        - element_to_show: ElementTree.Element to show in console
        """

        from xml.dom import minidom
        print("\nXML:\n")
        print(minidom.parseString(element_to_show).toprettyxml(indent = "  "))


# for test
'''
create_jpk(
        is_guidance_accepted = "1",
        purpose = "1",
        tax_office_code = "0000",
        year = "2020",
        month = "1",
        is_natural_person = "1",
        first_name = "important",
        last_name = "person",
        date_of_birth = "1952-03-11",
        full_name = "0",
        tax_number = "0000000042",
        email = "important.person@earth.here",
        phone = "",
        input_tax_documents = [],
        output_tax_documents = [],
        forwarded_excess_of_input_tax = "0",
        amendment_reasons = "Amendment reasons test"
        )
#'''

# for release
if __name__ == '__main__':
    create_jpk()

#'''
