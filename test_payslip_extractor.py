import unittest
from pathlib import Path
from payslip_extractor import extract_data_from_pdf

class TestPayslipExtraction(unittest.TestCase):
    def test_original_format(self):
        # Use a sample original payslip PDF path
        pdf_path = Path('input/07. July/Andres Gabriel Suarez Jimenez payslip July 2025.pdf')
        data = extract_data_from_pdf(pdf_path)
        self.assertIn('pe_number', data)
        self.assertIn('net_pay', data)
        self.assertIsInstance(data, dict)

    def test_alternate_format(self):
        # Use a sample alternate payslip PDF path
        pdf_path = Path("input/4C's/PAMA/Amanda Attard payslip August 2025.pdf")
        data = extract_data_from_pdf(pdf_path)
        self.assertIn('pe_number', data)
        self.assertIn('net_pay', data)
        self.assertIsInstance(data, dict)

if __name__ == '__main__':
    unittest.main()
