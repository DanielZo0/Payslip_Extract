import json
import csv
import pdfplumber
import re
from pathlib import Path
import os
import argparse

def load_extraction_keys():
    """
    Load the extraction keys from the JSON file.
    
    This function reads the mapping between display names and extraction pattern keys
    from the payslipextract_key.json file. If the file is not found, it uses default
    extraction keys.
    
    Returns:
        Dictionary mapping display keys to extraction pattern keys
    """
    try:
        with open('payslipextract_key.json', 'r') as f:
            return json.load(f)[0]
    except FileNotFoundError:
        print("Extraction keys file not found. Using default extraction keys.")
        # Default extraction keys if file not found
        return {
            "PE Number": "pe_extract",
            "Period From": "extract_period_from",
            "Period To": "extract_period_to",
            "Employee Name": "extract_nameandsurname",
            "ID Card Number": "id_extract",
            "Designation": "designation",
            "Monthly Basic Gross Salary": "extract_monthly_basic_gross_salary",
            "Net": "extract_net",
            "Gross": "extract_gross",
            "Commissions": "extract_commissions",
            "Car Cash Fringe Benefit": "extract_car_cash_fringe",
            "Mobile Allowance": "extract_mobile_allowance",
            "Pre-Tax Adjustment": "extract_pre_tax_adj",
            "Other Pre-Tax Adjustment": "extract_other_pre_tax_adj",
            "Government Bonus": "extract_gov_bonus",
            "FSS Main": "extract_fss_main",
            "Tax": "extract_tax",
            "Overtime 2 @ 15%": "extract_ot_2",
            "Overtime 1.5 @ 15%": "extract_ot15_15",
            "NI": "extract_ni"
        }

def standardize_date(date_str):
    """
    Standardize date format to DD-MMM-YY (e.g., 01-Jul-25)
    
    Args:
        date_str: The date string to standardize
        
    Returns:
        A standardized date string or "Not found" if parsing fails
    """
    if date_str == "Not found":
        return date_str
        
    # Common patterns to parse
    patterns = [
        # 01-Jul-25 format
        r'(\d{1,2})-([A-Za-z]{3})-(\d{2})',
        # 01/07/2025 format
        r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4}|\d{2})',
        # 1st July 2025 format
        r'(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4}|\d{2})',
        # July 31, 2025 format
        r'([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4}|\d{2})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            # Different pattern handling
            if len(match.groups()) == 3:
                if re.match(r'\d{1,2}-[A-Za-z]{3}-\d{2}', date_str):
                    # Already in our target format
                    day = match.group(1)
                    month = match.group(2)
                    year = match.group(3)
                elif re.match(r'\d{1,2}[/\-]\d{1,2}[/\-](\d{4}|\d{2})', date_str):
                    # DD/MM/YYYY format
                    day = match.group(1)
                    # Convert month number to abbreviated name
                    month_num = int(match.group(2))
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    month = month_names[month_num - 1]
                    # Get last 2 digits of year if 4-digit year
                    year = match.group(3)[-2:] if len(match.group(3)) == 4 else match.group(3)
                elif re.match(r'\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+(\d{4}|\d{2})', date_str, re.IGNORECASE):
                    # 1st July 2025 format
                    day = match.group(1).zfill(2)  # Ensure 2 digits
                    month = match.group(2)[:3]  # Use first 3 chars of month
                    year = match.group(3)[-2:] if len(match.group(3)) == 4 else match.group(3)
                else:
                    # July 31, 2025 format
                    day = match.group(2).zfill(2)  # Ensure 2 digits
                    month = match.group(1)[:3]  # Use first 3 chars of month
                    year = match.group(3)[-2:] if len(match.group(3)) == 4 else match.group(3)
                
                return f"{day}-{month}-{year}"
    
    # If no pattern matches, return the original string
    return date_str

def extract_data_from_pdf(pdf_path):
    """
    Extract data from PDF using the defined extraction keys.
    
    This function handles multiple payslip formats and uses different regex patterns
    based on the detected format. Special handling is applied for PE number 492953 payslips.
    
    Args:
        pdf_path: Path to the PDF file to extract data from
        
    Returns:
        Dictionary containing the extracted data with standardized keys
    """
    extracted_data = {}
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

        extraction_keys = load_extraction_keys()

        # Define base patterns that are common across all formats
        base_patterns = {
            'pe_extract': r'PE\s*No\.\s*(\d+)',
            'id_extract': r'ID\s*(?:No|Card):?\s*([A-Z0-9]+)',
            'designation': r'(?:Employment Status|Designation)\s*:\s*([^\n]+)',
            'extract_tax': r'Tax(?:\s*\(FSS\)|\s*Amount|\s*:)?(?:\s*\(|\s*)([\-\d,.]+)(?:\)|)',
            'extract_gov_bonus': r'Government\s*Bonus:?\s*([\-\d,.]+)',
            'extract_fss_main': r'FSS\s*Main[:\s]*([\-\d,.]+)',
            'extract_car_cash_fringe': r'Car\s*Cash\s*Fringe\s*Benefit:?\s*([\-\d,.]+)',
            'extract_mobile_allowance': r'Mobile\s*Allowance:?\s*([\-\d,.]+)',
            'extract_pre_tax_adj': r'(?:Pre-Tax\s*Adjustment|Pre-Tax\s*Adj):?\s*([\-\d,.]+)',
            'extract_other_pre_tax_adj': r'Other\s*Pre-Tax\s*Adjustments?:?\s*([\-\d,.]+)',
            'extract_monthly_basic_gross_salary': r'(?:Monthly\s*)?Basic\s*(?:Gross\s*Salary|month)\s*([\-\d,.]+)',
        }
        
        # Heuristic: If text contains 'Employee Name' or 'Gross Pay', use alternate patterns
        if re.search(r'Employee Name|Gross Pay', text, re.IGNORECASE):
            # Add format-specific patterns to the base patterns
            patterns = base_patterns.copy()
            patterns.update({
                'extract_period_from': r'From:\s*([0-9\-]+[A-Za-z]+\-\d+)', 
                'extract_period_to': r'To:(?:\s*|\n)([0-9\-/\w]+)|Period of [^u]*until ([0-9\-/A-Za-z\d]+)',
                'extract_nameandsurname': r'(?:31-Aug-25|Period of)(?:\s*)([A-Za-z\s\']+?)(?:\n|Period|\s+Hours)',
                'extract_net': r'Net\s*Value:?\s*([\-\d,.]+)',
                'extract_gross': r'Gross\s*Value:?\s*([\-\d,.]+)',
                'extract_commissions': r'(?:Commissions?\s*/?\s*Perf\s*Bonus|Commission)(?:s)?\s*(?:\/?\s*Perf\s*Bonus)?:?\s*([\-\d,.]+)',
                'extract_car_cash_fringe': r'Car\s*Cash\s*Fringe\s*Benefit:?\s*([\-\d,.]+)',
                'extract_mobile_allowance': r'Mobile\s*Allowance:?\s*([\-\d,.]+)',
                'extract_pre_tax_adj': r'(?:Pre-Tax\s*Adjustment|Pre-Tax\s*Adj):?\s*([\-\d,.]+)',
                'extract_other_pre_tax_adj': r'Other\s*Pre-Tax\s*Adjustments?:?\s*([\-\d,.]+)',
                'extract_ot_2': r'Overtime\s*(?:paid\s*)?(?:at\s*)?1:2\.0\s*([\-\d,.]+)',
                'extract_ot15_15': r'Overtime\s*(?:paid\s*)?(?:at\s*)?1:1\.5\s*([\-\d,.]+)',
                'extract_ni': r'(?:Employee\'s\s*N\.I\.\s*Share|National\s*Insurance)(?:\s*\(Employee\'s\s*Share\))?:?\s*\(?([\-\d,.]+)\)?',
            })
        else:
            # Add format-specific patterns to the base patterns
            patterns = base_patterns.copy()
            patterns.update({
                'extract_period_from': r'From:\s*([0-9/\-]+[A-Za-z]*\-?[0-9]*)',
                'extract_period_to': r'To:\s*([0-9/\-]+[A-Za-z]*\-?[0-9]*)|Period of [^u]*until ([0-9\-/A-Za-z\d]+)',
                'extract_nameandsurname': r'(?:Limited - PE No\. \d+\n|Surname\s+)([A-Za-z\s\']+?)(?:\n|$)',
                'extract_net': r'Net\s*(?:Value)?:?\s*([\-\d,.]+)',
                'extract_gross': r'Gross\s*(?:Value)?:?\s*([\-\d,.]+)',
                'extract_commissions': r'Commissions?(?:\s*/?\s*Perf\s*Bonus)?:?\s*([\-\d,.]+)',
                'extract_car_cash_fringe': r'Car\s*Cash\s*Fringe\s*Benefit:?\s*([\-\d,.]+)',
                'extract_mobile_allowance': r'Mobile\s*Allowance:?\s*([\-\d,.]+)',
                'extract_pre_tax_adj': r'(?:Pre-Tax\s*Adjustment|Pre-Tax\s*Adj):?\s*([\-\d,.]+)',
                'extract_other_pre_tax_adj': r'Other\s*Pre-Tax\s*Adjustments?:?\s*([\-\d,.]+)',
                'extract_ot_2': r'Overtime(?:\s*paid\s*at)?\s*(?:2|1:2\.0)(?:\s*@\s*15%)?:?\s*([\-\d,.]+)',
                'extract_ot15_15': r'Overtime(?:\s*paid\s*at)?\s*(?:1\.5|1:1\.5)(?:\s*@\s*15%)?:?[^\d]*([\d,.]+)(?:[^\d]+([\d,.]+))?',
                'extract_ni': r'(?:Employee\'s\s*N\.I\.\s*Share|National\s*Insurance|NI)(?:\s*\(Employee\'s\s*Share\))?:?\s*\d*[.,]?\d*\s*\(?([\-\d,.]+)\)?',
            })

        last_match_fields = ["extract_gross", "extract_net", "extract_ot_15", "extract_ot_2", "extract_ni", "extract_tax", 
                     "extract_commissions", "extract_gov_bonus", "extract_car_cash_fringe", "extract_mobile_allowance", 
                     "extract_pre_tax_adj", "extract_other_pre_tax_adj", "extract_monthly_basic_gross_salary"]
        # Map display keys to snake_case keys for output
        key_map = {
            "PE Number": "pe_number",
            "Period From": "period_from",
            "Period To": "period_to",
            "Employee Name": "employee_name",
            "ID Card Number": "id_card_number",
            "Designation": "designation",
            "Monthly Basic Gross Salary": "monthly_basic_gross_salary",
            "Net": "net_pay",
            "Gross": "gross_pay",
            "Commissions": "commissions",
            "Car Cash Fringe Benefit": "car_cash_fringe_benefit",
            "Mobile Allowance": "mobile_allowance",
            "Pre-Tax Adjustment": "pre_tax_adjustment",
            "Other Pre-Tax Adjustment": "other_pre_tax_adjustment",
            "Government Bonus": "government_bonus",
            "FSS Main": "fss_main",
            "Tax": "tax",
            "Overtime 2 @ 15%": "overtime_2_15",
            "Overtime 1.5 @ 15%": "overtime_1_5_15",
            "NI": "ni"
        }
        # Check for special PE number patterns first to set flags
        pe_pattern = patterns.get('pe_extract')
        if pe_pattern:
            pe_matches = re.findall(pe_pattern, text, re.IGNORECASE | re.MULTILINE)
            if pe_matches:
                if pe_matches[0] == '492953':
                    extracted_data['pe_number_is_492953'] = True
                elif pe_matches[0] == '330782':
                    extracted_data['pe_number_is_330782'] = True
        
        for display_key, pattern_key in extraction_keys.items():
            if pattern_key in patterns:
                value = "Not found"
                matches = re.findall(patterns[pattern_key], text, re.IGNORECASE | re.MULTILINE)
                if pattern_key == "extract_ot15_15" and matches:
                    flat_matches = [m for tup in matches for m in tup if m]
                    try:
                        value = max(flat_matches, key=lambda x: float(x.replace(",", "")))
                        value = value.strip()
                    except Exception:
                        value = flat_matches[-1].strip() if flat_matches else "Not found"
                elif pattern_key in ["extract_tax", "extract_ni"] and matches:
                    # Remove parentheses and extra spaces for tax and NI values
                    raw_value = matches[-1].strip()
                    value = re.sub(r'[\(\)]', '', raw_value).strip()
                elif pattern_key == "extract_nameandsurname" and matches:
                    # PRIORITY 1: Use the filename for name extraction - most reliable
                    pdf_filename = os.path.basename(pdf_path)
                    name_from_filename = re.match(r'([A-Za-z\s\']+)\s+payslip', pdf_filename)
                    if name_from_filename:
                        value = name_from_filename.group(1).strip()
                        
                    # PRIORITY 2: Try to get from Surname and Name fields
                    else:
                        surname_match = re.search(r'Surname\s+([A-Za-z\s\']+)', text, re.IGNORECASE)
                        name_match = re.search(r'Name\s+([A-Za-z\s\']+)', text, re.IGNORECASE)
                        
                        if surname_match and name_match:
                            value = f"{name_match.group(1).strip()} {surname_match.group(1).strip()}"
                            
                        # PRIORITY 3: Try to find name after period date
                        else:
                            period_name_match = re.search(r'31-Aug-25\s*([A-Za-z\s\']+?)(?:\n|$)', text)
                            if period_name_match and period_name_match.group(1).strip():
                                value = period_name_match.group(1).strip()
                                
                            # PRIORITY 4: Try to find name in "Period of" section    
                            else:
                                period_of_match = re.search(r'Period of[^H]*until.*\n.*\n([A-Za-z\s\']+?)(?:\n|Period|\s+Hours)', text)
                                if period_of_match and period_of_match.group(1).strip():
                                    value = period_of_match.group(1).strip()
                                    
                                # PRIORITY 5: Use matches from the regex pattern
                                else:
                                    if isinstance(matches[0], tuple):
                                        # Handle tuples from multiple capturing groups
                                        name_found = False
                                        for match_tuple in matches:
                                            for group in match_tuple:
                                                if group and group.strip():
                                                    value = group.strip()
                                                    name_found = True
                                                    break
                                            if name_found:
                                                break
                                    else:
                                        value = matches[-1].strip() if matches else "Not found"
                elif pattern_key == "extract_period_to":
                    # First try the direct To: pattern
                    to_match = re.search(r'To:\s*([0-9/\-]+[A-Za-z]+\-?[0-9]+)', text)
                    if to_match and to_match.group(1).strip():
                        value = to_match.group(1).strip()
                    else:
                        # Try to find it in the Period section
                        period_match = re.search(r'Period of .* until (.*?) Hours', text)
                        if period_match:
                            value = period_match.group(1).strip()
                        else:
                            # Special case for PE 330782 payslips where the date is at the end of the document
                            # Look for date formats like "31-Jul-25" near the end of the document
                            pe_match = re.search(r'PE\s*No\.\s*(\d+)', text, re.IGNORECASE)
                            if pe_match and pe_match.group(1) == "330782":
                                # Try to find a standalone date at the end of the document
                                end_date_match = re.search(r'(?:^|\n)(\d{1,2}-[A-Za-z]+-\d{2})(?:$|\n)', text)
                                if end_date_match:
                                    value = end_date_match.group(1).strip()
                elif pattern_key in last_match_fields:
                    if matches:
                        value = matches[-1].strip()
                else:
                    match = re.search(patterns[pattern_key], text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        # Get the first non-empty group
                        for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                            try:
                                if match.group(i) and match.group(i).strip():
                                    value = match.group(i).strip()
                                    break
                            except IndexError:
                                continue
                # Special handling for period values to normalize format
                if pattern_key in ["extract_period_from", "extract_period_to"] and value != "Not found":
                    # Fix for double dashes issue in dates like "01--Aug-25"
                    while "--" in value:
                        value = value.replace("--", "-")
                    
                    # Standardize date format
                    value = standardize_date(value)
                
                # Special handling for FSS Main field for PE number 492953
                if pattern_key == 'pe_extract' and value == '492953':
                    # Flag to ensure the FSS Main field is extracted
                    extracted_data['pe_number_is_492953'] = True
                    
                    # Check if it's missing month-year information
                    if re.match(r'^[\d\-]+$', value) and len(value) <= 3:
                        # Default month for payslips
                        month_year = "Aug-25"  
                        value = f"{value}-{month_year}"
                    
                    # If it's just a day or only contains digits and dashes
                    if len(value) <= 2 or re.match(r'^[\d\-]+$', value):
                        # Try different methods to find the month and year
                        month_match = re.search(r'Month\s+([\w\-]+)', text)
                        period_match = re.search(r'Period of\s+([0-9]+[a-zA-Z]{2}|[0-9]+[a-zA-Z]{3})\s+([A-Za-z]+)\s+(\d{4})', text)
                        
                        # Extract month from text directly if available
                        if "Aug-25" in text:
                            month = "Aug-25"
                            if value and value != "":
                                value = f"{value}-{month.split('-')[0]}-{month.split('-')[1]}"
                            else:
                                value = month
                        elif month_match:
                            month = month_match.group(1).strip()
                            if value and value != "":
                                value = f"{value}-{month}"
                            elif month:
                                value = month
                        elif period_match:
                            # Extract from "Period of 1st Aug 2025" format
                            month = period_match.group(2).strip()[:3]
                            year = period_match.group(3).strip()[-2:]
                            if value and value != "":
                                value = f"{value}-{month}-{year}"
                            else:
                                value = f"{period_match.group(1)}-{month}-{year}"
                
                # Use snake_case key for output
                output_key = key_map.get(display_key, display_key)
                extracted_data[output_key] = value
    
    # Special handling for PE number 492953 payslips
    if 'pe_number_is_492953' in extracted_data:
        # Enhanced ID Card extraction for 492953 payslips if not already found
        if extracted_data.get('id_card_number') == "Not found":
            id_match = re.search(r'ID Card:?\s*([A-Z0-9]+)', text, re.IGNORECASE)
            if id_match:
                extracted_data['id_card_number'] = id_match.group(1).strip()
        
        # Enhanced Designation extraction for 492953 payslips if not already found
        if extracted_data.get('designation') == "Not found":
            designation_match = re.search(r'Designation:\s*([^\n]+)', text, re.IGNORECASE)
            if designation_match:
                extracted_data['designation'] = designation_match.group(1).strip()
        
        # Enhanced Monthly Basic Gross Salary extraction for 492953 payslips
        if extracted_data.get('monthly_basic_gross_salary') == "Not found":
            basic_match = re.search(r'Monthly\s*Basic\s*Gross\s*Salary\s*([\d,.]+)', text, re.IGNORECASE)
            if basic_match:
                extracted_data['monthly_basic_gross_salary'] = basic_match.group(1).strip()
            else:
                # Try alternative pattern
                alt_basic_match = re.search(r'Basic\s*Gross\s*Salary\s*([\d,.]+)', text, re.IGNORECASE)
                if alt_basic_match:
                    extracted_data['monthly_basic_gross_salary'] = alt_basic_match.group(1).strip()
                else:
                    # Look for "Basic month" which often contains this value
                    basic_month_match = re.search(r'Basic\s*month\s*([\d,.]+)', text, re.IGNORECASE)
                    if basic_month_match:
                        extracted_data['monthly_basic_gross_salary'] = basic_month_match.group(1).strip()
        
        # Enhanced Period To extraction for 492953 payslips
        if extracted_data.get('period_to') == "Not found":
            # Pattern 1: Direct format
            period_to_match = re.search(r'To:\s*([0-9/\-]+[A-Za-z]*\-?[0-9]*)', text, re.IGNORECASE)
            if period_to_match and period_to_match.group(1):
                extracted_data['period_to'] = period_to_match.group(1).strip()
            else:
                # Pattern 2: Look for date format in leave details
                leave_date_match = re.search(r'(\d{2}/\d{2}/\d{4}|\d{2}-[A-Za-z]+-\d{2,4})', text, re.IGNORECASE)
                if leave_date_match:
                    extracted_data['period_to'] = leave_date_match.group(1).strip()
                # Pattern 3: Find month-end date from the period
                elif 'period_from' in extracted_data and extracted_data['period_from'] != "Not found":
                    period_from = extracted_data['period_from']
                    # Try to extract month and year
                    month_match = re.search(r'(\d{2})[/-](\d{2})[/-](\d{4}|\d{2})', period_from)
                    if month_match:
                        # If in format MM/DD/YYYY or similar
                        month = int(month_match.group(2) if len(month_match.groups()) >= 2 else month_match.group(1))
                        year = int(month_match.group(3))
                        if year < 100:
                            year += 2000  # Adjust for 2-digit year
                        
                        # Determine the last day of the month
                        if month in [4, 6, 9, 11]:
                            last_day = 30
                        elif month == 2:
                            # Handle February (leap year check)
                            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                                last_day = 29
                            else:
                                last_day = 28
                        else:
                            last_day = 31
                        
                        # Format as DD/MM/YYYY initially
                        date_str = f"{last_day}/{'0' + str(month) if month < 10 else month}/{year}"
                        # Then standardize to our consistent format
                        extracted_data['period_to'] = standardize_date(date_str)
        
        # Remove the temporary flag
        extracted_data.pop('pe_number_is_492953')
    
    # Special handling for PE number 330782 payslips (similar to 4C's payslips)
    if 'pe_number_is_330782' in extracted_data:
        # Enhanced Tax extraction for 330782 payslips
        if extracted_data.get('tax') == "Not found":
            # Try to find tax in different formats that may exist in these payslips
            tax_match = re.search(r'Tax:?\s*([\d,.]+)', text, re.IGNORECASE)
            if tax_match:
                extracted_data['tax'] = tax_match.group(1).strip()
            else:
                # Try alternative pattern - Tax can appear in different formats in these payslips
                alt_tax_match = re.search(r'(?:Tax|FSS)\s*Amount:?\s*([\d,.]+)', text, re.IGNORECASE)
                if alt_tax_match:
                    extracted_data['tax'] = alt_tax_match.group(1).strip()
        
        # Enhanced Monthly Basic Gross Salary extraction for 330782 payslips
        if extracted_data.get('monthly_basic_gross_salary') == "Not found":
            basic_match = re.search(r'Monthly\s*Basic\s*Gross\s*Salary\s*([\d,.]+)', text, re.IGNORECASE)
            if basic_match:
                extracted_data['monthly_basic_gross_salary'] = basic_match.group(1).strip()
            else:
                # Try alternative pattern
                alt_basic_match = re.search(r'Basic\s*Gross\s*Salary\s*([\d,.]+)', text, re.IGNORECASE)
                if alt_basic_match:
                    extracted_data['monthly_basic_gross_salary'] = alt_basic_match.group(1).strip()
                else:
                    # Look for "Basic month" which often contains this value
                    basic_month_match = re.search(r'Basic\s*month\s*([\d,.]+)', text, re.IGNORECASE)
                    if basic_month_match:
                        extracted_data['monthly_basic_gross_salary'] = basic_month_match.group(1).strip()
        
        # Enhanced Period To extraction for 330782 payslips
        if extracted_data.get('period_to') == "Not found":
            # Look for a standalone date near the end of the document - common in these payslips
            end_date_match = re.search(r'(?:^|\n)(\d{1,2}-[A-Za-z]+-\d{2})(?:$|\n)', text)
            if end_date_match:
                extracted_data['period_to'] = end_date_match.group(1).strip()
            elif 'period_from' in extracted_data and extracted_data['period_from'] != "Not found":
                # If we still can't find it, but we have period_from, assume it's the end of the month
                # Extract month and year from period_from
                from_match = re.search(r'(\d{1,2})-([A-Za-z]+)-(\d{2})', extracted_data['period_from'])
                if from_match:
                    month = from_match.group(2)
                    year = from_match.group(3)
                    
                    # Determine the last day of the month
                    month_map = {
                        'Jan': 31, 'Feb': 28, 'Mar': 31, 'Apr': 30, 'May': 31, 'Jun': 30, 
                        'Jul': 31, 'Aug': 31, 'Sep': 30, 'Oct': 31, 'Nov': 30, 'Dec': 31
                    }
                    
                    # Handle February in leap years
                    if month == 'Feb' and int('20' + year) % 4 == 0 and (int('20' + year) % 100 != 0 or int('20' + year) % 400 == 0):
                        last_day = 29
                    else:
                        last_day = month_map.get(month, 30)  # Default to 30 if month not found
                        
                    extracted_data['period_to'] = f"{last_day}-{month}-{year}"
        
        # Remove the temporary flag
        extracted_data.pop('pe_number_is_330782')
    
    # Special handling for Monthly Basic Gross Salary - this is important to ensure this field is extracted
    # First try the exact line with "Monthly Basic Gross Salary"
    monthly_basic_found = False
    for line in text.split('\n'):
        if 'monthly basic gross salary' in line.lower():
            value_match = re.search(r'(\d+[.,]\d+)', line)
            if value_match:
                extracted_data['monthly_basic_gross_salary'] = value_match.group(1).strip()
                monthly_basic_found = True
                break
    
    # If still not found, try "Basic month"
    if not monthly_basic_found:
        for line in text.split('\n'):
            if 'basic month' in line.lower():
                value_match = re.search(r'(\d+[.,]\d+)', line)
                if value_match:
                    extracted_data['monthly_basic_gross_salary'] = value_match.group(1).strip()
                    monthly_basic_found = True
                    break
    
    # If still not found, look for "Basic" with a number
    if not monthly_basic_found:
        for line in text.split('\n'):
            if 'basic' in line.lower() and re.search(r'\d+[.,]\d+', line):
                value_match = re.search(r'(\d+[.,]\d+)', line)
                if value_match:
                    extracted_data['monthly_basic_gross_salary'] = value_match.group(1).strip()
                    break
    
    return extracted_data

def save_to_csv(data_list, csv_path):
    """Save extracted data to a CSV file."""
    if not data_list:
        return
    
    # Get headers from the first item
    fieldnames = list(data_list[0].keys())
    
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for data in data_list:
            writer.writerow(data)
    
    print(f"CSV data saved to: {csv_path}")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Extract data from payslip PDFs.')
    parser.add_argument('--input-dir', '-i', default='input', help='Directory containing PDF files')
    parser.add_argument('--output-dir', '-o', default='output', help='Directory to store output files')
    parser.add_argument('--csv-filename', default='all_payslips.csv', help='Name of the CSV file')
    parser.add_argument('--no-csv', action='store_true', help='Disable CSV output')
    parser.add_argument('--no-json', action='store_true', help='Disable individual JSON output')
    return parser.parse_args()

def main():
    """
    Main function that processes payslip PDFs and generates output files.
    
    This function:
    1. Parses command-line arguments
    2. Finds all PDF files in the input directory and its subdirectories
    3. Processes each PDF to extract structured data
    4. Saves individual JSON files for each payslip (unless disabled)
    5. Compiles all data into a single CSV file (unless disabled)
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Get input and output directories
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    # Find all PDF files in the input directory
    pdf_files = list(input_dir.rglob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in the input directory ({input_dir}) or its subfolders.")
        return

    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # List to store all extracted data for CSV output
    all_extracted_data = []

    # Process each PDF file
    for pdf_file in pdf_files:
        print(f"\nProcessing: {pdf_file}")
        try:
            extracted_data = extract_data_from_pdf(pdf_file)
            
            # Add to the list for CSV output
            all_extracted_data.append(extracted_data)

            # Save extracted data to JSON file (unless disabled)
            if not args.no_json:
                output_file = output_dir / f"{pdf_file.stem}_extracted.json"
                with open(output_file, 'w') as f:
                    json.dump(extracted_data, f, indent=4)
                print(f"Data extracted successfully. Output saved to: {output_file}")
            else:
                print("Data extracted successfully. JSON output disabled.")

        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")
    
    # Save all extracted data to a single CSV file (unless disabled)
    if all_extracted_data and not args.no_csv:
        csv_output_path = output_dir / args.csv_filename
        save_to_csv(all_extracted_data, csv_output_path)

if __name__ == "__main__":
    main()
