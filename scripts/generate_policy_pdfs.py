
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from pathlib import Path

def create_policy_pdf(output_path, title, content_lines):
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    
    header_style = ParagraphStyle(
        "Header", parent=styles["Heading1"],
        fontSize=18, textColor=HexColor("#1a365d"),
        alignment=TA_CENTER, spaceAfter=10
    )
    
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading2"],
        fontSize=14, textColor=HexColor("#2b6cb0"),
        alignment=TA_CENTER, spaceAfter=20
    )
    
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, leading=14, spaceAfter=10
    )
    
    story = [
        Paragraph(title, header_style),
        HRFlowable(width="100%", thickness=1, color=HexColor("#2b6cb0")),
        Spacer(1, 10)
    ]
    
    for line in content_lines:
        if line.startswith("# "):
            story.append(Paragraph(line[2:], styles["Heading2"]))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], styles["Heading3"]))
        else:
            story.append(Paragraph(line, body_style))
            
    doc.build(story)

# 1. Star Health Cardio Guidelines
star_cardio_content = [
    "# STAR HEALTH - CARDIAC POLICY 2026",
    "## 1. Scope of Coverage",
    "This policy covers inpatient cardiac procedures including PCI (Percutaneous Coronary Intervention) and CABG.",
    "## 2. Mandatory Documentation",
    "- Detailed Discharge Summary with TIMI flow results.",
    "- Original Stent Implant Sticker (Must be clear and legible).",
    "- Pre-procedure Angiography and Post-procedure ECG.",
    "## 3. Financial Limits",
    "- Drug Eluting Stents (DES) are covered up to Rs. 45,000 per stent.",
    "- Total procedure cap for single-vessel PCI: Rs. 1,80,000.",
    "## 4. Requirement for ICU Stay",
    "ICU stays longer than 24 hours must be accompanied by nursing notes and vital monitoring charts every 4 hours."
]

# 2. ICICI Lombard Ortho Guidelines
icici_ortho_content = [
    "# ICICI LOMBARD - ORTHOPEDIC GUIDELINES",
    "## 1. Total Knee Arthroplasty (TKA)",
    "TKA is considered medically necessary for patients with Grade III or IV Osteoarthritis.",
    "## 2. THE 3-MONTH RULE (Mandatory)",
    "IMPORTANT: Claims for elective TKA will only be approved if there is documented evidence of **at least 3 months of failed conservative management**, including physical therapy, weight management, and NSAIDs.",
    "## 3. Evidence Requirements",
    "- Clear photo of the implant sticker (All 4 corners must be visible).",
    "- Pre-op and Post-op X-rays.",
    "- Physiotherapy assessment pre-surgery."
]

policy_dir = Path("data/policies")
(policy_dir / "Star Health Insurance" / "pdfs").mkdir(parents=True, exist_ok=True)
(policy_dir / "ICICI Lombard" / "pdfs").mkdir(parents=True, exist_ok=True)

create_policy_pdf(policy_dir / "Star Health Insurance" / "pdfs" / "StarHealth_Cardio_2026.pdf", "Star Health Insurance", star_cardio_content)
create_policy_pdf(policy_dir / "ICICI Lombard" / "pdfs" / "ICICI_Ortho_Guidelines.pdf", "ICICI Lombard", icici_ortho_content)

print("✅ Policy PDFs generated successfully.")
