"""
Generates 'bad' test documents to exercise the non-green Cloud Flow paths:
  - BAD_zero_consumption.pdf : valid layout, Consumption = 0.00  -> Yellow (value not > 0)
  - BAD_flyer.pdf            : promotional flyer, no reading fields -> Red (AI finds no Client ID)

Same layout as the training PDFs so the AI Builder model reads the meter-reading one.
Send these as email attachments to the monitored inbox to test the flow end-to-end.
"""

import os
from datetime import datetime
from fpdf import FPDF

OUTPUT_DIR = os.getenv('OUTPUT_DIR', '../3_Dokumenty_Testowe')


class EnergyReportPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'EnergoSmart - Monthly Energy Report', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, f'Generated: {datetime.now().strftime("%Y-%m-%d")}', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def make_zero_consumption():
    """Valid meter-reading layout but consumption = 0.00 -> Yellow path."""
    pdf = EnergyReportPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'Client: Hotel_99', 0, 1)
    pdf.cell(0, 8, 'Sector: Hotel', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.ln(3)

    pdf.cell(70, 8, 'Reading Date:', 1)
    pdf.cell(0, 8, '2026-05-22', 1, 1)
    pdf.cell(70, 8, 'Consumption (kWh):', 1)
    pdf.cell(0, 8, '0.00', 1, 1)
    pdf.cell(70, 8, 'Monthly Avg (kWh):', 1)
    pdf.cell(0, 8, '5210.40', 1, 1)

    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, 'Previous Readings (Reference)', 0, 1)
    pdf.set_font('Arial', '', 9)
    for date, val in [('2026-05-15', '5102.30'), ('2026-05-08', '4998.10'),
                      ('2026-05-01', '5301.55'), ('2026-04-24', '4877.20')]:
        pdf.cell(60, 7, date, 1)
        pdf.cell(0, 7, val, 1, 1)

    path = f"{OUTPUT_DIR}/BAD_zero_consumption.pdf"
    pdf.output(path)
    return path


def make_flyer():
    """Promotional flyer with no reading fields -> Red path (no Client ID found)."""
    pdf = EnergyReportPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 20)
    pdf.ln(20)
    pdf.cell(0, 15, 'MEGA PROMOCJA WIOSENNA!', 0, 1, 'C')
    pdf.set_font('Arial', '', 14)
    pdf.ln(5)
    pdf.cell(0, 10, 'Tylko teraz: panele fotowoltaiczne -40%', 0, 1, 'C')
    pdf.cell(0, 10, 'Zadzwon i odbierz darmowa wycene!', 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 8,
                   'Skontaktuj sie z naszym doradca, aby dowiedziec sie wiecej o '
                   'naszej ofercie. Oferta ograniczona czasowo. Promocja nie laczy '
                   'sie z innymi rabatami.')

    path = f"{OUTPUT_DIR}/BAD_flyer.pdf"
    pdf.output(path)
    return path


if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    p1 = make_zero_consumption()
    p2 = make_flyer()
    print(f'[OK] Yellow test (zero consumption): {p1}')
    print(f'[OK] Red test (flyer / no reading):  {p2}')
