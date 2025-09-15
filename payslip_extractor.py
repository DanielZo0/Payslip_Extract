import json
import pdfplumber
import re
from pathlib import Path
import os

def load_extraction_keys():
    """Load the extraction keys from the JSON file."""
    with open('payslipextract_key.json', 'r') as f:
        return json.load(f)[0]

def extract_data_from_pdf(pdf_path):
    """Extract data from PDF using the defined extraction keys."""
    extracted_data = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        # Extract text from all pages
        for page in pdf.pages:
            text += page.extract_text()
        
        # Debug: Print extracted text
        print("\nExtracted text from PDF:")
        print("-" * 50)
        print(text)
        print("-" * 50)
        
        # Load extraction keys
        extraction_keys = load_extraction_keys()
        
        # Extract data based on patterns
        patterns = {
            'pe_extract': r'PE\s*No\.\s*(\d+)',
            'extract_period_from': r'From:\s*([0-9/]+)',
            'extract_period_to': r'To:\s*([0-9/]+)',
            'extract_nameandsurname': r'Limited - PE No\. \d+\n([A-Za-z\s]+?)(?:\n|$)',
            'id_extract': r'ID\s*Card:\s*([A-Z0-9]+)',
            'designation': r'Designation:\s*([^\n]+)',
            'extract_net': r'Net:\s*([\-\d,.]+)',
            'extract_gross': r'Gross:\s*([\-\d,.]+)',
            'extract_commissions': r'Commissions\s*([\-\d,.]+)',
            'extract_gov_bonus': r'Government Bonus\s*([\-\d,.]+)',
            'extract_fss_main': r'FSS Main\s*([\-\d,.]+)',
            'extract_ot_15': r'Tax On Overtime @ 15%:?\s*([\-\d,.]+)',
            'extract_ot_2': r'Overtime 2 @ 15%\s*\d*[.,]?\d*\s*([\-\d,.]+)',
            'extract_ni': r'NI\s*\d*[.,]?\d*\s*([\-\d,.]+)',
        }
        
        # Extract each field using the patterns
        # For fields that may appear multiple times, get the last match
        last_match_fields = ["extract_gross", "extract_net", "extract_ot_15", "extract_ot_2", "extract_ni", "extract_fss_main", "extract_commissions", "extract_gov_bonus"]
        for json_key, pattern_key in extraction_keys.items():
            if pattern_key in patterns:
                value = "Not found"
                if pattern_key in last_match_fields:
                    matches = re.findall(patterns[pattern_key], text, re.IGNORECASE)
                    if matches:
                        value = matches[-1].strip()
                else:
                    match = re.search(patterns[pattern_key], text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                extracted_data[json_key] = value
    
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
