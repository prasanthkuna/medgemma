import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.colors import HexColor

def create_policy_pdf(filename, title, payer_id, content_paragraphs):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )

    styles = getSampleStyleSheet()
    
    # Custom Styles to look like a real enterprise document
    styles.add(ParagraphStyle(
        name='PremiumTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#0f172a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='PremiumBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        spaceAfter=14,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    ))

    Story = []

    # Title Page
    Story.append(Spacer(1, 100))
    Story.append(Paragraph(f"MEDICAL NECESSITY GUIDELINES", styles["PremiumTitle"]))
    Story.append(Spacer(1, 20))
    Story.append(Paragraph(title, styles["PremiumTitle"]))
    Story.append(Spacer(1, 40))
    Story.append(Paragraph(f"Payer ID: {payer_id.upper()}", styles["PremiumBody"]))
    Story.append(Paragraph("Effective Date: January 1, 2026", styles["PremiumBody"]))
    Story.append(Paragraph("CONFIDENTIAL & PROPRIETARY", styles["PremiumBody"]))
    Story.append(PageBreak())

    # Content
    for para in content_paragraphs:
        if para.startswith("##"):
            # Header
            Story.append(Paragraph(para.replace("##", "").strip(), styles["Heading2"]))
            Story.append(Spacer(1, 10))
        else:
            Story.append(Paragraph(para, styles["PremiumBody"]))

    doc.build(Story)
    print(f"✅ Generated pro-tier policy PDF: {filename}")

if __name__ == "__main__":
    # --- 1. Cardio Guidelines ---
    cardio_content = [
        "## 1. Scope of Coverage",
        "These guidelines dictate the medical necessity criteria for cardiovascular interventions, including PTCA, CABG, and diagnostic catheterization.",
        
        "## 2. ICU Length of Stay (LOS) Criteria",
        "For cardiac procedures involving drug-eluting stents (PTCA) or arterial bypass (CABG), ICU monitoring is mandatory for a minimum of 48 hours post-procedure as per NABH and specific payer guidelines. Length of stay exceeding 5 days for an uncomplicated PTCA requires detailed justification, including daily progress notes and specialist recommendations.",
        "Crucially, if a patient experiences post-operative complications such as arrhythmias, hypotension requiring inotropic support, or bleeding, an extended ICU stay of up to 7 days is considered medically necessary and must be documented in the discharge summary.",
        
        "## 3. Required Documentation",
        "Claims will be denied if the following documents are not present in the utilization review packet:",
        "1. Discharge Summary",
        "2. Admission Note",
        "3. Operation Theater (OT) Note",
        "4. Implant Sticker (Required for all stent placements to verify LOT and Serial numbers)",
        "5. Pharmacy Bill",
        
        "## 4. Quality Assurance of Documents",
        "Implant stickers must be clearly visible, with the serial number and lot number readable. Blurred, distorted, or completely illegible stickers require re-submission with enhanced imagery, or the surgical component of the claim (CPT code 92928) will be categorically denied."
    ]
    
    # --- 2. Ortho Guidelines ---
    ortho_content = [
        "## 1. Overview of Orthopedic Medical Necessity",
        "This document establishes the clinical pathways and authorization requirements for major joint replacements, including Total Knee Arthroplasty (TKA) and Total Hip Arthroplasty (THA).",
        
        "## 2. Conservative Therapy Trials",
        "Prior to the authorization of elective TKA, the patient must have documented evidence of failing at least 6 months of conservative therapy. This includes physical therapy, NSAID regimens, and intra-articular corticosteroid injections.",
        
        "## 3. Mandatory Audit Documentation",
        "To satisfy the post-payment audit criteria, the provider must submit the following suite of documents:",
        "- Discharge Summary",
        "- Admission Note",
        "- Operation Theater (OT) Note",
        "- Implant Sticker (Strict adherence required. Must show manufacturer details, lot, and expiration.)",
        "- Pharmacy and Consumables Bill",
        
        "## 4. Implant Sticker Verification Clause",
        "Under Section 4(B) of the Orthopedic Fraud Prevention Act, the presence of a physically legible Implant Sticker on the operative report or implant log is non-negotiable. If the sticker is missing, blurred, or severed, the cost of the prosthesis will be deducted from the DRG payment."
    ]

    base_dir = "C:/Users/PrashanthKuna/samples/medgemma/data/policies"
    
    # Star Health Insurance -> Cardio Guidelines
    create_policy_pdf(
        os.path.join(base_dir, "Star Health Insurance", "pdfs", "StarHealth_Cardio_Guidelines_2026.pdf"),
        "Cardiovascular Intervention Policy",
        "Star Health Insurance",
        cardio_content
    )
    
    # ICICI Lombard -> Ortho Guidelines
    create_policy_pdf(
        os.path.join(base_dir, "ICICI Lombard", "pdfs", "ICICI_Orthopedic_Joint_Guidelines_2026.pdf"),
        "Total Joint Replacement Policy",
        "ICICI Lombard",
        ortho_content
    )

