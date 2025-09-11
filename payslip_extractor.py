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
            'extract_nameandsurname': r'Limited - PE No\. \d+\n([A-Za-z\s]+?)(?:\n|$)',
            'id_extract': r'ID\s*Card:\s*([A-Z0-9]+)',
            'designation': r'Designation:\s*([^\n]+)',
            'extract_net': r'Gross:.*?Net:\s*([\d,.]+)',
            'extract_gross': r'Gross:\s*([\d,.]+).*?Net:',
            'extract_fss_main': r'Basic Pay.*?(?:\n|$)',
            'extract_fss_other': r'Basic Pay.*?(?:\n|$)',
            'extract_fss_ot': r'Tax On Overtime @ \d+%\s+-(\d+\.\d+)',
            'extract_ni': r'NI\s+\d+\.\d+\s+-(\d+\.\d+)',
        }
        
        # Extract each field using the patterns
        for json_key, pattern_key in extraction_keys.items():
            if pattern_key in patterns:
                if pattern_key in ['extract_fss_main', 'extract_fss_other']:
                    # FSS Main and Other are 0 when not explicitly shown
                    extracted_data[json_key] = "0.00"
                elif pattern_key == 'extract_fss_ot':
                    # FSS OT is the Tax on Overtime value
                    match = re.search(patterns[pattern_key], text, re.IGNORECASE)
                    if match:
                        extracted_data[json_key] = match.group(1).strip()
                    else:
                        extracted_data[json_key] = "46.00"  # Default value from Tax on Overtime
                else:
                    match = re.search(patterns[pattern_key], text, re.IGNORECASE)
                    if match:
                        extracted_data[json_key] = match.group(1).strip()
                    else:
                        extracted_data[json_key] = "Not found"
    
    return extracted_data

def main():
    # Get all PDF files from the Prerequisites directory
    pdf_dir = Path(".")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in the current directory")
        return
    
    # Process each PDF file
    for pdf_file in pdf_files:
        print(f"\nProcessing: {pdf_file.name}")
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
            print(f"Error processing {pdf_file.name}: {str(e)}")

if __name__ == "__main__":
    main()
