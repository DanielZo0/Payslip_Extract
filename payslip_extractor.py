import json
import pdfplumber
import re
from pathlib import Path
import os

def load_extraction_keys():
    """Load the extraction keys from the JSON file."""
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
            "Net": "extract_net",
            "Gross": "extract_gross",
            "Commissions": "extract_commissions",
            "Government Bonus": "extract_gov_bonus",
            "Tax": "extract_tax",
            "Overtime 2 @ 15%": "extract_ot_2",
            "Overtime 1.5 @ 15%": "extract_ot15_15",
            "NI": "extract_ni"
        }

def extract_data_from_pdf(pdf_path):
    """Extract data from PDF using the defined extraction keys."""
    extracted_data = {}
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

        print("\nExtracted text from PDF:")
        print("-" * 50)
        print(text)
        print("-" * 50)

        extraction_keys = load_extraction_keys()

        # Define improved patterns for alternate payslip structure
        alternate_patterns = {
            'pe_extract': r'PE\s*No\.\s*(\d+)',
            'extract_period_from': r'From:\s*([0-9\-]+[A-Za-z]+\-\d+)', 
            'extract_period_to': r'To:(?:\s*|\n)([0-9\-/\w]+)|Period of [^u]*until ([0-9\-/A-Za-z\d]+)',
            'extract_nameandsurname': r'(?:31-Aug-25|Period of)(?:\s*)([A-Za-z\s\']+?)(?:\n|Period|\s+Hours)',
            'id_extract': r'ID\s*No\s*([A-Z0-9]+)',
            'designation': r'Employment Status\s*:\s*([^\n]+)',
            'extract_net': r'Net\s*Value:?\s*([\-\d,.]+)',
            'extract_gross': r'Gross\s*Value:?\s*([\-\d,.]+)',
            'extract_commissions': r'(?:Commissions?\s*/?\s*Perf\s*Bonus|Commission)(?:s)?\s*(?:\/?\s*Perf\s*Bonus)?:?\s*([\-\d,.]+)',
            'extract_gov_bonus': r'Government\s*Bonus:?\s*([\-\d,.]+)',
            'extract_tax': r'Tax(?:\s*\(FSS\)|\s*:)?(?:\s*\(|\s*)([\-\d,.]+)(?:\)|)',
            'extract_ot_2': r'Overtime\s*(?:paid\s*)?(?:at\s*)?1:2\.0\s*([\-\d,.]+)',
            'extract_ot15_15': r'Overtime\s*(?:paid\s*)?(?:at\s*)?1:1\.5\s*([\-\d,.]+)',
            'extract_ni': r'(?:Employee\'s\s*N\.I\.\s*Share|National\s*Insurance)(?:\s*\(Employee\'s\s*Share\))?:?\s*\(?([\-\d,.]+)\)?',
        }

        # Heuristic: If text contains 'Employee Name' or 'Gross Pay', use alternate patterns
        if re.search(r'Employee Name|Gross Pay', text, re.IGNORECASE):
            patterns = alternate_patterns
        else:
            patterns = {
                'pe_extract': r'PE\s*No\.\s*(\d+)',
                'extract_period_from': r'From:\s*([0-9/\-]+[A-Za-z]*\-?[0-9]*)',
                'extract_period_to': r'To:\s*([0-9/\-]+[A-Za-z]*\-?[0-9]*)|Period of [^u]*until ([0-9\-/A-Za-z\d]+)',
                'extract_nameandsurname': r'(?:Limited - PE No\. \d+\n|Surname\s+)([A-Za-z\s\']+?)(?:\n|$)',
                'id_extract': r'ID\s*No\s*([A-Z0-9]+)',
                'designation': r'Employment Status\s*:\s*([^\n]+)',
                'extract_net': r'Net\s*(?:Value)?:?\s*([\-\d,.]+)',
                'extract_gross': r'Gross\s*(?:Value)?:?\s*([\-\d,.]+)',
                'extract_commissions': r'Commissions?(?:\s*/?\s*Perf\s*Bonus)?:?\s*([\-\d,.]+)',
                'extract_gov_bonus': r'Government Bonus:?\s*([\-\d,.]+)',
                'extract_tax': r'Tax(?:\s*\(FSS\)|\s*:)?(?:\s*\(|\s*)([\-\d,.]+)(?:\)|)',
                'extract_ot_2': r'Overtime(?:\s*paid\s*at)?\s*(?:2|1:2\.0)(?:\s*@\s*15%)?:?\s*([\-\d,.]+)',
                'extract_ot15_15': r'Overtime(?:\s*paid\s*at)?\s*(?:1\.5|1:1\.5)(?:\s*@\s*15%)?:?[^\d]*([\d,.]+)(?:[^\d]+([\d,.]+))?',
                'extract_ni': r'(?:Employee\'s\s*N\.I\.\s*Share|National\s*Insurance|NI)(?:\s*\(Employee\'s\s*Share\))?:?\s*\d*[.,]?\d*\s*\(?([\-\d,.]+)\)?',
            }

        last_match_fields = ["extract_gross", "extract_net", "extract_ot_15", "extract_ot_2", "extract_ni", "extract_tax", "extract_commissions", "extract_gov_bonus"]
        # Map display keys to snake_case keys for output
        key_map = {
            "PE Number": "pe_number",
            "Period From": "period_from",
            "Period To": "period_to",
            "Employee Name": "employee_name",
            "ID Card Number": "id_card_number",
            "Designation": "designation",
            "Net": "net_pay",
            "Gross": "gross_pay",
            "Commissions": "commissions",
            "Government Bonus": "government_bonus",
            "Tax": "tax",
            "Overtime 2 @ 15%": "overtime_2_15",
            "Overtime 1.5 @ 15%": "overtime_1_5_15",
            "NI": "ni"
        }
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
                        print(f"Extracted name from filename: {value}")
                        
                    # PRIORITY 2: Try to get from Surname and Name fields
                    else:
                        surname_match = re.search(r'Surname\s+([A-Za-z\s\']+)', text, re.IGNORECASE)
                        name_match = re.search(r'Name\s+([A-Za-z\s\']+)', text, re.IGNORECASE)
                        
                        if surname_match and name_match:
                            value = f"{name_match.group(1).strip()} {surname_match.group(1).strip()}"
                            print(f"Extracted name from Surname/Name fields: {value}")
                            
                        # PRIORITY 3: Try to find name after period date
                        else:
                            period_name_match = re.search(r'31-Aug-25\s*([A-Za-z\s\']+?)(?:\n|$)', text)
                            if period_name_match and period_name_match.group(1).strip():
                                value = period_name_match.group(1).strip()
                                print(f"Extracted name from period date: {value}")
                                
                            # PRIORITY 4: Try to find name in "Period of" section    
                            else:
                                period_of_match = re.search(r'Period of[^H]*until.*\n.*\n([A-Za-z\s\']+?)(?:\n|Period|\s+Hours)', text)
                                if period_of_match and period_of_match.group(1).strip():
                                    value = period_of_match.group(1).strip()
                                    print(f"Extracted name from Period of section: {value}")
                                    
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
                                    print(f"Extracted name from regex matches: {value}")
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
    return extracted_data

def main():
    # Change working directory to 'input' and recursively find all PDF files
    input_dir = Path("input")
    pdf_files = list(input_dir.rglob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in the input directory or its subfolders.")
        return

    # Process each PDF file
    for pdf_file in pdf_files:
        print(f"\nProcessing: {pdf_file}")
        try:
            extracted_data = extract_data_from_pdf(pdf_file)

            # Create output directory if it doesn't exist
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)

            # Save extracted data to JSON file
            output_file = output_dir / f"{pdf_file.stem}_extracted.json"
            with open(output_file, 'w') as f:
                json.dump(extracted_data, f, indent=4)

            print(f"Data extracted successfully. Output saved to: {output_file}")

        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")

if __name__ == "__main__":
    main()
