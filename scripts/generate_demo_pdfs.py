"""
Pramana AI — Professional Demo PDF Generator
Generates realistic Indian hospital medical documents as PDFs
with controlled error injection for sabotage testing.

Cases:
  case_001_cardio_perfect  → GREEN score (all docs present + clear)
  case_002_ortho_blurry    → AMBER score (blurry implant sticker)
  case_003_cardio_icu      → RED   score (missing ICU/progress notes)
  case_004_mixed_patient   → RED   score (Patient A + Patient B docs mixed)

Run: python scripts/generate_demo_pdfs.py
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add sidecar to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sidecar"))

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, gray, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image as RLImage
)
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

DEMO_DIR = Path(__file__).parent.parent / "data" / "demo"

# ─── Hospital Branding ───────────────────────────────────────────
HOSPITAL_NAME = "Apollo Hospitals, Jubilee Hills"
HOSPITAL_ADDR = "Road No. 72, Jubilee Hills, Hyderabad, Telangana 500033"
HOSPITAL_PHONE = "+91-40-2360-7777"
HOSPITAL_REG = "NABH Accredited | Reg No: TS/MC/2019/4521"

styles = getSampleStyleSheet()

HEADER_STYLE = ParagraphStyle(
    "HospitalHeader", parent=styles["Heading1"],
    fontSize=16, textColor=HexColor("#1a365d"),
    spaceAfter=2, alignment=TA_CENTER
)
SUBHEADER_STYLE = ParagraphStyle(
    "SubHeader", parent=styles["Normal"],
    fontSize=8, textColor=gray, alignment=TA_CENTER, spaceAfter=6
)
TITLE_STYLE = ParagraphStyle(
    "DocTitle", parent=styles["Heading2"],
    fontSize=14, textColor=HexColor("#2d3748"),
    spaceBefore=12, spaceAfter=8, alignment=TA_CENTER
)
BODY_STYLE = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontSize=10, leading=14, spaceAfter=6
)
LABEL_STYLE = ParagraphStyle(
    "Label", parent=styles["Normal"],
    fontSize=9, textColor=HexColor("#4a5568"), leading=12
)
SECTION_STYLE = ParagraphStyle(
    "SectionHead", parent=styles["Heading3"],
    fontSize=11, textColor=HexColor("#2b6cb0"),
    spaceBefore=10, spaceAfter=4
)


def hospital_header():
    """Standard hospital header elements"""
    return [
        Paragraph(HOSPITAL_NAME, HEADER_STYLE),
        Paragraph(f"{HOSPITAL_ADDR}<br/>{HOSPITAL_PHONE} | {HOSPITAL_REG}", SUBHEADER_STYLE),
        HRFlowable(width="100%", thickness=1, color=HexColor("#2b6cb0")),
        Spacer(1, 6)
    ]


def patient_info_table(patient_name, age, gender, mrn, admission_date, 
                       payer="Star Health Insurance", policy_no="SHI-2025-987654",
                       consultant="Dr. Rajesh Kumar, MD, DM (Cardiology)"):
    """Standard patient info block"""
    data = [
        ["Patient Name:", patient_name, "MRN:", mrn],
        ["Age/Gender:", f"{age} / {gender}", "Admission:", admission_date],
        ["Consultant:", consultant, "Payer:", payer],
        ["Ward:", "ICU → General Ward", "Policy No:", policy_no],
    ]
    t = Table(data, colWidths=[80, 170, 70, 170])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), HexColor("#4a5568")),
        ("TEXTCOLOR", (2, 0), (2, -1), HexColor("#4a5568")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f7fafc")),
    ]))
    return t


# ═══════════════════════════════════════════════════════════════════
#  CASE 001 — Perfect Cardio (GREEN)
# ═══════════════════════════════════════════════════════════════════
def generate_case_001():
    case_dir = DEMO_DIR / "case_001_cardio_perfect"
    case_dir.mkdir(parents=True, exist_ok=True)
    patient = "Ramesh Kumar Sharma"
    mrn = "APH-2025-10234"
    age = "62"
    admission = "15-Jan-2026"
    discharge = "22-Jan-2026"

    # ── Discharge Summary ──
    doc = SimpleDocTemplate(str(case_dir / "discharge_summary.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("DISCHARGE SUMMARY", TITLE_STYLE))
    story.append(patient_info_table(patient, age, "Male", mrn, admission))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Diagnosis", SECTION_STYLE))
    story.append(Paragraph(
        "Triple Vessel Disease (TVD) with Left Main involvement. "
        "Underwent Percutaneous Coronary Intervention (PCI) with Drug-Eluting Stent (DES) "
        "to LAD and LCx. Hypertension Stage II. Type 2 Diabetes Mellitus.", BODY_STYLE))
    story.append(Paragraph("History of Present Illness", SECTION_STYLE))
    story.append(Paragraph(
        f"Mr. {patient}, a {age}-year-old male, was admitted on {admission} with complaints of "
        "retrosternal chest pain radiating to the left arm for 2 hours, associated with profuse "
        "sweating and breathlessness (NYHA Class III). ECG showed ST elevation in leads V1-V4. "
        "Troponin I elevated at 12.5 ng/mL (normal <0.04). Patient was immediately taken up for "
        "primary PCI after informed consent.", BODY_STYLE))
    story.append(Paragraph("Procedure Details", SECTION_STYLE))
    story.append(Paragraph(
        "Coronary Angiography revealed 95% stenosis in proximal LAD, 80% stenosis in mid LCx, "
        "and 70% stenosis in RCA. PCI performed to LAD with Xience Sierra DES (3.0 x 28mm, "
        "Serial: XS-2025-78432) and to LCx with Xience Sierra DES (2.75 x 18mm, Serial: XS-2025-78433). "
        "Post-dilation performed with non-compliant balloon. TIMI 3 flow achieved in both vessels. "
        "No complications. Procedure duration: 45 minutes. Contrast used: 180 mL Iohexol.", BODY_STYLE))
    story.append(Paragraph("ICU Course (3 days)", SECTION_STYLE))
    story.append(Paragraph(
        "Post-PCI, patient was monitored in Cardiac ICU for 3 days. Day 1: Stable hemodynamics, "
        "Heparin infusion continued. Day 2: Sheath removed, ambulation started. Day 3: Shifted to "
        "general ward. No arrhythmias, no access site complications.", BODY_STYLE))
    story.append(Paragraph("Discharge Medications", SECTION_STYLE))
    meds = [
        ["Medication", "Dose", "Frequency", "Duration"],
        ["Tab. Aspirin", "75 mg", "Once daily", "Lifelong"],
        ["Tab. Clopidogrel", "75 mg", "Once daily", "12 months"],
        ["Tab. Atorvastatin", "40 mg", "Once daily (HS)", "Lifelong"],
        ["Tab. Metoprolol", "25 mg", "Twice daily", "As advised"],
        ["Tab. Ramipril", "5 mg", "Once daily", "As advised"],
        ["Tab. Metformin", "500 mg", "Twice daily", "As advised"],
    ]
    mt = Table(meds, colWidths=[130, 60, 100, 100])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2b6cb0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#f7fafc")]),
    ]))
    story.append(mt)
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        f"<b>Discharge Date:</b> {discharge} | <b>Condition at Discharge:</b> Stable, afebrile, "
        "ambulatory | <b>Follow-up:</b> OPD after 7 days with repeat ECG", BODY_STYLE))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Dr. Rajesh Kumar, MD, DM (Cardiology)", BODY_STYLE))
    story.append(Paragraph("Reg. No: TS-MC-24567 | Apollo Hospitals, Jubilee Hills", LABEL_STYLE))
    doc.build(story)
    print(f"  ✅ discharge_summary.pdf")

    # ── Admission Note ──
    doc = SimpleDocTemplate(str(case_dir / "admission_note.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("ADMISSION NOTE", TITLE_STYLE))
    story.append(patient_info_table(patient, age, "Male", mrn, admission))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Chief Complaints", SECTION_STYLE))
    story.append(Paragraph(
        "Acute onset retrosternal chest pain for 2 hours, radiating to left arm. "
        "Associated with diaphoresis and dyspnea at rest.", BODY_STYLE))
    story.append(Paragraph("Vitals on Admission", SECTION_STYLE))
    vitals = [
        ["BP", "HR", "SpO2", "Temp", "RR", "GCS"],
        ["160/100 mmHg", "98 bpm", "94% (RA)", "98.4°F", "22/min", "15/15"],
    ]
    vt = Table(vitals, colWidths=[80]*6)
    vt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#e2e8f0")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, HexColor("#e2e8f0")),
    ]))
    story.append(vt)
    story.append(Paragraph("Past History", SECTION_STYLE))
    story.append(Paragraph(
        "Known case of Hypertension (10 years) on Tab. Amlodipine 5mg OD. "
        "Type 2 DM (8 years) on Tab. Metformin 500mg BD. No prior cardiac events. "
        "No surgical history. Non-smoker. Occasional alcohol.", BODY_STYLE))
    story.append(Paragraph("Plan", SECTION_STYLE))
    story.append(Paragraph(
        "Admit to Cardiac ICU. Start IV Heparin, dual antiplatelet loading (Aspirin 325mg + "
        "Clopidogrel 300mg). Urgent Coronary Angiography + PCI as indicated.", BODY_STYLE))
    doc.build(story)
    print(f"  ✅ admission_note.pdf")

    # ── OT Note ──
    doc = SimpleDocTemplate(str(case_dir / "ot_note.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("OPERATION THEATRE NOTE — Cath Lab", TITLE_STYLE))
    story.append(patient_info_table(patient, age, "Male", mrn, admission))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Procedure: PCI with DES to LAD and LCx", SECTION_STYLE))
    story.append(Paragraph(
        "<b>Date:</b> 15-Jan-2026 | <b>Time:</b> 14:30 – 15:15 IST<br/>"
        "<b>Operator:</b> Dr. Rajesh Kumar | <b>Anaesthesia:</b> Local + Conscious Sedation<br/>"
        "<b>Access:</b> Right Radial Artery (6F sheath)", BODY_STYLE))
    story.append(Paragraph("Findings", SECTION_STYLE))
    story.append(Paragraph(
        "• LAD: 95% stenosis in proximal segment, thrombus noted<br/>"
        "• LCx: 80% stenosis in mid segment<br/>"
        "• RCA: 70% stenosis (not intervened — medical management)<br/>"
        "• LV Function: LVEF 45% by ventriculography", BODY_STYLE))
    story.append(Paragraph("Implant Details", SECTION_STYLE))
    implants = [
        ["Stent", "Size", "Serial Number", "Vessel", "Deployment"],
        ["Xience Sierra DES", "3.0 x 28mm", "XS-2025-78432", "LAD", "14 atm"],
        ["Xience Sierra DES", "2.75 x 18mm", "XS-2025-78433", "LCx", "12 atm"],
    ]
    it = Table(implants, colWidths=[100, 70, 100, 50, 70])
    it.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2b6cb0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e0")),
    ]))
    story.append(it)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<b>Complications:</b> None | <b>Estimated Blood Loss:</b> Nil<br/>"
        "<b>Post-Procedure:</b> Hemostasis achieved by radial compression band. "
        "Patient shifted to CICU in stable condition.", BODY_STYLE))
    doc.build(story)
    print(f"  ✅ ot_note.pdf")

    # ── Pharmacy Bill ──
    doc = SimpleDocTemplate(str(case_dir / "pharmacy_bill.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("PHARMACY & CONSUMABLES BILL", TITLE_STYLE))
    story.append(patient_info_table(patient, age, "Male", mrn, admission))
    story.append(Spacer(1, 12))
    items = [
        ["S.No", "Item Description", "Qty", "Unit Price (₹)", "Total (₹)"],
        ["1", "Xience Sierra DES 3.0x28mm (S/N: XS-2025-78432)", "1", "45,000", "45,000"],
        ["2", "Xience Sierra DES 2.75x18mm (S/N: XS-2025-78433)", "1", "42,000", "42,000"],
        ["3", "6F Radial Sheath", "1", "1,200", "1,200"],
        ["4", "Guide Catheter JL 3.5", "1", "2,500", "2,500"],
        ["5", "PTCA Guidewire (BMW Universal)", "2", "3,500", "7,000"],
        ["6", "NC Balloon 3.0x12mm", "1", "8,000", "8,000"],
        ["7", "Iohexol 350 (Contrast Media) 100mL", "2", "1,800", "3,600"],
        ["8", "Inj. Heparin 5000 IU/mL", "4", "85", "340"],
        ["9", "Tab. Clopidogrel 75mg x 30", "1", "450", "450"],
        ["10", "Tab. Aspirin 75mg x 30", "1", "120", "120"],
        ["", "", "", "Sub-Total", "1,10,210"],
        ["", "", "", "GST (5%)", "5,510"],
        ["", "", "", "GRAND TOTAL", "₹1,15,720"],
    ]
    bt = Table(items, colWidths=[30, 220, 30, 80, 80])
    bt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2b6cb0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [white, HexColor("#f7fafc")]),
        ("FONTNAME", (3, -2), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (3, -1), (-1, -1), HexColor("#f0fff4")),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
    ]))
    story.append(bt)
    doc.build(story)
    print(f"  ✅ pharmacy_bill.pdf")

    # ── Lab Report ──
    doc = SimpleDocTemplate(str(case_dir / "lab_report.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("LABORATORY INVESTIGATION REPORT", TITLE_STYLE))
    story.append(patient_info_table(patient, age, "Male", mrn, admission))
    story.append(Spacer(1, 12))
    labs = [
        ["Test", "Result", "Unit", "Reference Range", "Flag"],
        ["Troponin I", "12.5", "ng/mL", "<0.04", "⬆ HIGH"],
        ["CK-MB", "85", "U/L", "0-25", "⬆ HIGH"],
        ["Hemoglobin", "13.2", "g/dL", "13.0-17.0", "Normal"],
        ["WBC Count", "9,800", "/µL", "4,000-11,000", "Normal"],
        ["Platelet Count", "2,10,000", "/µL", "1,50,000-4,00,000", "Normal"],
        ["Creatinine", "1.1", "mg/dL", "0.7-1.3", "Normal"],
        ["BUN", "18", "mg/dL", "7-20", "Normal"],
        ["HbA1c", "7.8", "%", "<6.5", "⬆ HIGH"],
        ["FBS", "145", "mg/dL", "70-100", "⬆ HIGH"],
        ["Total Cholesterol", "245", "mg/dL", "<200", "⬆ HIGH"],
        ["LDL", "165", "mg/dL", "<100", "⬆ HIGH"],
        ["HDL", "38", "mg/dL", ">40", "⬇ LOW"],
        ["Triglycerides", "210", "mg/dL", "<150", "⬆ HIGH"],
        ["PT/INR", "1.0", "", "0.9-1.1", "Normal"],
    ]
    lt = Table(labs, colWidths=[100, 60, 50, 110, 70])
    lt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2b6cb0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#f7fafc")]),
    ]))
    # Color-code flags
    for i in range(1, len(labs)):
        if "HIGH" in labs[i][4]:
            lt.setStyle(TableStyle([("TEXTCOLOR", (4, i), (4, i), HexColor("#e53e3e"))]))
        elif "LOW" in labs[i][4]:
            lt.setStyle(TableStyle([("TEXTCOLOR", (4, i), (4, i), HexColor("#dd6b20"))]))
    story.append(lt)
    doc.build(story)
    print(f"  ✅ lab_report.pdf")

    # ── Stent Sticker Image (clear) ──
    generate_sticker_image(
        case_dir / "stent_sticker.jpg",
        brand="XIENCE Sierra",
        serial="XS-2025-78432",
        size="3.0 x 28mm",
        lot="LOT-2025A-4521",
        blur=False
    )
    print(f"  ✅ stent_sticker.jpg (clear)")


# ═══════════════════════════════════════════════════════════════════
#  CASE 002 — Ortho Blurry Sticker (AMBER)
# ═══════════════════════════════════════════════════════════════════
def generate_case_002():
    case_dir = DEMO_DIR / "case_002_ortho_blurry"
    case_dir.mkdir(parents=True, exist_ok=True)
    patient = "Lakshmi Devi Reddy"
    mrn = "APH-2025-10567"
    age = "58"
    admission = "18-Jan-2026"

    # ── Discharge Summary ──
    doc = SimpleDocTemplate(str(case_dir / "discharge_summary.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("DISCHARGE SUMMARY", TITLE_STYLE))
    story.append(patient_info_table(patient, age, "Female", mrn, admission,
                 consultant="Dr. Suresh Babu, MS, MCh (Ortho)"))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Diagnosis", SECTION_STYLE))
    story.append(Paragraph(
        "Osteoarthritis Right Knee (Kellgren-Lawrence Grade IV). "
        "Underwent Total Knee Replacement (TKR) — Right side. "
        "Implant: Smith & Nephew JOURNEY II BCS.", BODY_STYLE))
    story.append(Paragraph("Procedure", SECTION_STYLE))
    story.append(Paragraph(
        "Right Total Knee Arthroplasty under spinal anaesthesia. "
        "Medial parapatellar approach. Implant: Smith & Nephew JOURNEY II BCS "
        "(Femoral: Size 5, Serial: SN-JII-2025-34521; Tibial: Size 4, Serial: SN-JII-2025-34522; "
        "Poly Insert: 10mm, Serial: SN-JII-2025-34523). "
        "Tourniquet time: 65 minutes. EBL: ~200mL. Drain placed.", BODY_STYLE))
    story.append(Paragraph(
        f"<b>Discharge Date:</b> 25-Jan-2026 | <b>Condition:</b> Stable, weight-bearing with walker",
        BODY_STYLE))
    doc.build(story)
    print(f"  ✅ discharge_summary.pdf")

    # ── OT Note ──
    doc = SimpleDocTemplate(str(case_dir / "ot_note.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("OPERATION THEATRE NOTE", TITLE_STYLE))
    story.append(patient_info_table(patient, age, "Female", mrn, admission,
                 consultant="Dr. Suresh Babu, MS, MCh (Ortho)"))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<b>Procedure:</b> Right Total Knee Arthroplasty<br/>"
        "<b>Date:</b> 19-Jan-2026 | <b>Duration:</b> 90 minutes<br/>"
        "<b>Implant:</b> Smith & Nephew JOURNEY II BCS<br/>"
        "<b>Serial Numbers:</b> Femoral SN-JII-2025-34521, Tibial SN-JII-2025-34522, "
        "Poly SN-JII-2025-34523", BODY_STYLE))
    doc.build(story)
    print(f"  ✅ ot_note.pdf")

    # ── Pharmacy Bill ──
    doc = SimpleDocTemplate(str(case_dir / "pharmacy_bill.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("PHARMACY & CONSUMABLES BILL", TITLE_STYLE))
    story.append(patient_info_table(patient, age, "Female", mrn, admission,
                 consultant="Dr. Suresh Babu, MS, MCh (Ortho)"))
    story.append(Spacer(1, 12))
    items = [
        ["S.No", "Item Description", "Qty", "Unit Price (₹)", "Total (₹)"],
        ["1", "S&N JOURNEY II BCS Femoral (S/N: SN-JII-2025-34521)", "1", "85,000", "85,000"],
        ["2", "S&N JOURNEY II BCS Tibial (S/N: SN-JII-2025-34522)", "1", "55,000", "55,000"],
        ["3", "Poly Insert 10mm (S/N: SN-JII-2025-34523)", "1", "25,000", "25,000"],
        ["4", "Bone Cement (Palacos R+G) 40g", "2", "4,500", "9,000"],
        ["", "", "", "GRAND TOTAL", "₹1,74,000"],
    ]
    bt = Table(items, colWidths=[30, 220, 30, 80, 80])
    bt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2b6cb0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e0")),
        ("FONTNAME", (3, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
    ]))
    story.append(bt)
    doc.build(story)
    print(f"  ✅ pharmacy_bill.pdf")

    # ── BLURRY Implant Sticker (this is the sabotage!) ──
    generate_sticker_image(
        case_dir / "implant_sticker.jpg",
        brand="JOURNEY II BCS",
        serial="SN-JII-2025-34521",
        size="Femoral Size 5",
        lot="LOT-SN-2025B-8832",
        blur=True  # ← SABOTAGE: intentionally blurry
    )
    print(f"  ⚠️ implant_sticker.jpg (BLURRY — sabotage)")


# ═══════════════════════════════════════════════════════════════════
#  CASE 003 — Missing ICU Notes (RED)
# ═══════════════════════════════════════════════════════════════════
def generate_case_003():
    case_dir = DEMO_DIR / "case_003_cardio_icu"
    case_dir.mkdir(parents=True, exist_ok=True)
    patient = "Venkatesh Rao"
    mrn = "APH-2025-10892"
    age = "55"
    admission = "10-Jan-2026"

    # ── Discharge Summary (mentions 5-day ICU stay!) ──
    doc = SimpleDocTemplate(str(case_dir / "discharge_summary.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("DISCHARGE SUMMARY", TITLE_STYLE))
    story.append(patient_info_table(patient, age, "Male", mrn, admission))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Diagnosis", SECTION_STYLE))
    story.append(Paragraph(
        "Acute Anterior Wall STEMI. Underwent Primary PCI with DES to LAD. "
        "Post-procedure cardiogenic shock requiring IABP support for 48 hours. "
        "Ventilatory support for 3 days.", BODY_STYLE))
    story.append(Paragraph("ICU Course (5 days)", SECTION_STYLE))
    story.append(Paragraph(
        "Patient was in Cardiac ICU for 5 days post-PCI due to cardiogenic shock. "
        "Day 1-2: IABP support + Inotropes (Dobutamine + Noradrenaline). Mechanically ventilated. "
        "Day 3: IABP weaned, extubated. Day 4: Inotropes tapered. "
        "Day 5: Shifted to step-down unit. ICU daily vitals and progress notes were maintained. "
        "<b>Total ICU stay: 5 days.</b>", BODY_STYLE))
    story.append(Paragraph(
        "<b>Discharge Date:</b> 20-Jan-2026 | <b>Total LOS:</b> 10 days", BODY_STYLE))
    doc.build(story)
    print(f"  ✅ discharge_summary.pdf")

    # ── Admission Note ──
    doc = SimpleDocTemplate(str(case_dir / "admission_note.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("ADMISSION NOTE", TITLE_STYLE))
    story.append(patient_info_table(patient, age, "Male", mrn, admission))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Acute onset severe chest pain for 1 hour. ECG: ST elevation V1-V6. "
        "Hemodynamically unstable — BP 80/50 mmHg. Plan: Emergency PCI.", BODY_STYLE))
    doc.build(story)
    print(f"  ✅ admission_note.pdf")

    # ── Stent Sticker ──
    generate_sticker_image(
        case_dir / "stent_sticker.jpg",
        brand="Resolute Onyx DES",
        serial="RO-2025-99123",
        size="3.5 x 30mm",
        lot="LOT-MED-2025C",
        blur=False
    )
    print(f"  ✅ stent_sticker.jpg")

    # ── Pharmacy Bill ──
    doc = SimpleDocTemplate(str(case_dir / "pharmacy_bill.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("PHARMACY & CONSUMABLES BILL", TITLE_STYLE))
    story.append(patient_info_table(patient, age, "Male", mrn, admission))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "1. Resolute Onyx DES 3.5x30mm (S/N: RO-2025-99123) — ₹48,000<br/>"
        "2. IABP Balloon Catheter — ₹65,000<br/>"
        "3. Ventilator consumables (3 days) — ₹15,000<br/>"
        "4. ICU charges (5 days) — ₹1,25,000<br/>"
        "<b>Grand Total: ₹2,53,000</b>", BODY_STYLE))
    doc.build(story)
    print(f"  ✅ pharmacy_bill.pdf")

    # ── NOTE: MISSING icu_chart.pdf and progress_notes.pdf ──
    # This is intentional for sabotage testing!
    print(f"  🚨 MISSING: icu_chart.pdf (SABOTAGE — 5-day ICU but no chart)")
    print(f"  🚨 MISSING: progress_notes.pdf (SABOTAGE — no daily notes)")


# ═══════════════════════════════════════════════════════════════════
#  CASE 004 — Mixed Patient Docs (RED)
# ═══════════════════════════════════════════════════════════════════
def generate_case_004():
    case_dir = DEMO_DIR / "case_004_mixed_patient"
    case_dir.mkdir(parents=True, exist_ok=True)
    patient_a = "Priya Menon"
    patient_b = "Suresh Nair"  # WRONG patient!
    mrn_a = "APH-2025-11001"
    mrn_b = "APH-2025-11045"  # Different MRN!
    admission = "20-Jan-2026"

    # ── Discharge Summary (Patient A) ──
    doc = SimpleDocTemplate(str(case_dir / "discharge_summary.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("DISCHARGE SUMMARY", TITLE_STYLE))
    story.append(patient_info_table(patient_a, "45", "Female", mrn_a, admission,
                 payer="ICICI Lombard", consultant="Dr. Suresh Babu, MS, MCh (Ortho)"))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Diagnosis", SECTION_STYLE))
    story.append(Paragraph(
        "Fracture Neck of Femur (Right). Underwent Bipolar Hemiarthroplasty.", BODY_STYLE))
    story.append(Paragraph(
        f"Patient {patient_a} (MRN: {mrn_a}) admitted with right hip fracture after fall. "
        "Underwent Bipolar Hemiarthroplasty under spinal anaesthesia. "
        "Post-op recovery uneventful. Discharged 27-Jan-2026.", BODY_STYLE))
    doc.build(story)
    print(f"  ✅ discharge_summary.pdf (Patient A: {patient_a})")

    # ── Lab Report (WRONG PATIENT B!) — SABOTAGE ──
    doc = SimpleDocTemplate(str(case_dir / "lab_report.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("LABORATORY INVESTIGATION REPORT", TITLE_STYLE))
    # NOTE: This is Patient B's info!
    story.append(patient_info_table(patient_b, "67", "Male", mrn_b, "22-Jan-2026",
                 payer="Star Health", consultant="Dr. Rajesh Kumar, MD, DM (Cardiology)"))
    story.append(Spacer(1, 12))
    labs = [
        ["Test", "Result", "Reference", "Flag"],
        ["Hemoglobin", "14.5 g/dL", "13.0-17.0", "Normal"],
        ["Creatinine", "0.9 mg/dL", "0.7-1.3", "Normal"],
        ["Blood Group", "A+ve", "", ""],
    ]
    lt = Table(labs, colWidths=[120, 80, 100, 80])
    lt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2b6cb0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, HexColor("#e2e8f0")),
    ]))
    story.append(lt)
    doc.build(story)
    print(f"  ⚠️ lab_report.pdf (WRONG PATIENT: {patient_b} / MRN: {mrn_b} — SABOTAGE)")

    # ── OT Note (Patient A) ──
    doc = SimpleDocTemplate(str(case_dir / "ot_note.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("OPERATION THEATRE NOTE", TITLE_STYLE))
    story.append(patient_info_table(patient_a, "45", "Female", mrn_a, admission,
                 consultant="Dr. Suresh Babu, MS, MCh (Ortho)"))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<b>Procedure:</b> Right Bipolar Hemiarthroplasty<br/>"
        "<b>Date:</b> 21-Jan-2026<br/>"
        "<b>Implant:</b> Johnson & Johnson Bipolar Prosthesis", BODY_STYLE))
    doc.build(story)
    print(f"  ✅ ot_note.pdf (Patient A: {patient_a})")

    # ── Pharmacy Bill (Patient A) ──
    doc = SimpleDocTemplate(str(case_dir / "pharmacy_bill.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = hospital_header()
    story.append(Paragraph("PHARMACY & CONSUMABLES BILL", TITLE_STYLE))
    story.append(patient_info_table(patient_a, "45", "Female", mrn_a, admission,
                 payer="ICICI Lombard", consultant="Dr. Suresh Babu, MS, MCh (Ortho)"))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "1. J&J Bipolar Prosthesis — ₹35,000<br/>"
        "2. Bone Cement — ₹4,500<br/>"
        "<b>Grand Total: ₹39,500</b>", BODY_STYLE))
    doc.build(story)
    print(f"  ✅ pharmacy_bill.pdf (Patient A: {patient_a})")


# ═══════════════════════════════════════════════════════════════════
#  STICKER IMAGE GENERATOR
# ═══════════════════════════════════════════════════════════════════
def generate_sticker_image(output_path, brand, serial, size, lot, blur=False):
    """Generate a realistic medical implant sticker image"""
    width, height = 600, 350
    img = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([5, 5, width-6, height-6], outline="#1a365d", width=3)
    draw.rectangle([10, 10, width-11, height-11], outline="#2b6cb0", width=1)

    # Use default font (cross-platform)
    try:
        font_large = ImageFont.truetype("arial.ttf", 22)
        font_medium = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 13)
        font_serial = ImageFont.truetype("arialbd.ttf", 20)
    except (OSError, IOError):
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large
        font_serial = font_large

    # Header
    draw.rectangle([10, 10, width-11, 55], fill="#1a365d")
    draw.text((20, 18), f"MEDICAL DEVICE — {brand}", fill="white", font=font_large)

    # Content
    y = 75
    draw.text((30, y), "Manufacturer:", fill="#4a5568", font=font_small)
    draw.text((160, y), "Abbott / Smith & Nephew", fill="#2d3748", font=font_medium)
    y += 35
    draw.text((30, y), "Product:", fill="#4a5568", font=font_small)
    draw.text((160, y), f"{brand} — {size}", fill="#2d3748", font=font_medium)
    y += 35
    draw.text((30, y), "Serial Number:", fill="#4a5568", font=font_small)
    draw.text((160, y), serial, fill="#e53e3e", font=font_serial)
    y += 35
    draw.text((30, y), "Lot Number:", fill="#4a5568", font=font_small)
    draw.text((160, y), lot, fill="#2d3748", font=font_medium)
    y += 35
    draw.text((30, y), "Sterilization:", fill="#4a5568", font=font_small)
    draw.text((160, y), "EtO Sterilized | Use by: 2027-12", fill="#2d3748", font=font_medium)

    # CE mark area
    draw.rectangle([10, height-55, width-11, height-11], fill="#f7fafc", outline="#cbd5e0")
    draw.text((20, height-45), "CE 0123 | FDA 510(k) Cleared | REF: " + lot[:12],
              fill="#718096", font=font_small)

    # Barcode simulation
    for i in range(40):
        x = 400 + i * 4
        h = random.randint(40, 80)
        w = random.choice([1, 2, 3])
        draw.rectangle([x, 90, x+w, 90+h], fill="black")

    if blur:
        # Apply heavy Gaussian blur to simulate bad photo
        img = img.filter(ImageFilter.GaussianBlur(radius=6))
        # Add slight rotation
        img = img.rotate(3, fillcolor="#FFFFFF", expand=False)

    img.save(str(output_path), quality=85)


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("Pramana AI — Professional Demo PDF Generator")
    print("=" * 60)
    print()

    print("📁 Case 001: Perfect Cardio (GREEN target)")
    generate_case_001()
    print()

    print("📁 Case 002: Ortho Blurry Sticker (AMBER target)")
    generate_case_002()
    print()

    print("📁 Case 003: Missing ICU Notes (RED target)")
    generate_case_003()
    print()

    print("📁 Case 004: Mixed Patient Docs (RED target)")
    generate_case_004()
    print()

    print("=" * 60)
    print("✅ All demo cases generated in:", DEMO_DIR)
    print("=" * 60)
