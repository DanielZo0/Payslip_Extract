# Payslip Extractor


This project extracts structured data from payslip PDF files and outputs the results as JSON files.

## Features
- Batch processing of multiple payslip PDFs
- Recursively scans the `input/` folder and all subfolders for PDF files
- Extracts key fields such as:
  - PE Number
  - Period From / To
  - Employee Name
  - ID Card Number
  - Designation
  - Net / Gross
  - Commissions
  - Government Bonus
  - FSS Main
  - Tax On Overtime @ 15%
  - Overtime 2 @ 15%
  - Overtime 1.5 @ 15% (selects the largest value if multiple are present)
  - NI
- Outputs results to the `output/` directory

## Requirements
- Python 3.12+
- See `requirements.txt` for dependencies

## Setup
1. Clone the repository:
   ```sh
   git clone https://github.com/DanielZo0/Payslip_Extract.git
   cd Payslip_Extract
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

## Multi-Format Extraction
This script automatically detects and extracts data from both original and alternate payslip formats (e.g., files in `input/4C's/`). The output JSON structure remains consistent regardless of input format.

## Testing
Unit tests are provided in `test_payslip_extractor.py` to verify extraction for both formats. Run tests with:
```sh
python -m unittest test_payslip_extractor.py
```
3. Place your payslip PDF files in the `input/` folder (or any subfolder).

## Usage
Run the extractor script:
```sh
python payslip_extractor.py
```
Extracted JSON files will be saved in the `output/` folder.

## Customization
- Extraction keys are defined in `payslipextract_key.json`.
- Update regex patterns in `payslip_extractor.py` if your payslip format changes.

## Output
Each processed PDF generates a corresponding JSON file in `output/` with extracted fields.

## License
MIT
