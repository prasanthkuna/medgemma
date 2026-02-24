"""
Evidence Pack Builder Service
Merges documents into payer-ordered PDF with cover and index
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json

from pypdf import PdfReader, PdfWriter
from config import settings

logger = logging.getLogger(__name__)

# Document ordering per payer preferences (extensible)
DEFAULT_DOC_ORDER = [
    "insurance_card",
    "admission_note",
    "discharge_summary",
    "ot_note",
    "implant_sticker",
    "pharmacy_bill",
    "lab_report",
    "radiology_report",
    "icu_chart",
    "progress_note",
    "other"
]


async def build_evidence_pack(
    case_id: str,
    case_data: Dict[str, Any],
    files: List[Dict[str, Any]],
    analysis: Optional[Dict[str, Any]] = None,
    draft: Optional[Dict[str, Any]] = None,
    include_cover: bool = True,
    include_checklist: bool = True,
    watermark: Optional[str] = None
) -> Path:
    """
    Build Evidence Pack PDF
    
    Args:
        case_id: Case identifier
        case_data: Case metadata
        files: List of case files with doc_type
        analysis: Analysis results for checklist
        draft: The approved query draft (transcript, response, query)
        include_cover: Include cover page
        include_checklist: Include checklist at end
        watermark: Optional watermark text (e.g., "DRAFT")
        
    Returns:
        Path to generated PDF
    """
    output_dir = settings.cases_dir / case_id / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"evidence_pack_{timestamp}.pdf"
    
    # Sort files by document type order
    sorted_files = sorted(
        files,
        key=lambda f: (
            DEFAULT_DOC_ORDER.index(f.get("doc_type", "other"))
            if f.get("doc_type") in DEFAULT_DOC_ORDER
            else len(DEFAULT_DOC_ORDER)
        )
    )
    
    # Build index data
    index_data = []
    current_page = 1
    
    if include_cover:
        current_page += 1  # Cover page
    
    current_page += 1  # Index page
    
    for f in sorted_files:
        file_path = Path(f.get("path", ""))
        if file_path.suffix.lower() == ".pdf" and file_path.exists():
            try:
                reader = PdfReader(str(file_path))
                page_count = len(reader.pages)
                
                index_data.append({
                    "doc_type": f.get("doc_type", "other").replace("_", " ").title(),
                    "filename": f.get("filename"),
                    "start_page": current_page,
                    "end_page": current_page + page_count - 1,
                    "page_count": page_count
                })
                
                current_page += page_count
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    
    # Generate cover page
    cover_pdf = None
    if include_cover:
        cover_pdf = await _generate_cover_page(case_data, output_dir)
    
    # Generate index page
    index_pdf = await _generate_index_page(index_data, case_data, output_dir)
    
    # Generate draft page
    draft_pdf = None
    if draft:
        draft_pdf = await _generate_draft_page(draft, output_dir)
    
    # Merge all PDFs using PdfWriter
    writer = PdfWriter()
    
    def append_pdf(pdf_path):
        """Helper to append all pages from a PDF to the writer"""
        try:
            reader = PdfReader(str(pdf_path))
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            logger.error(f"Error appending {pdf_path}: {e}")
    
    if cover_pdf and cover_pdf.exists():
        append_pdf(cover_pdf)
    
    if draft_pdf and draft_pdf.exists():
        append_pdf(draft_pdf)
    
    if index_pdf.exists():
        append_pdf(index_pdf)
    
    for f in sorted_files:
        file_path = Path(f.get("path", ""))
        if file_path.suffix.lower() == ".pdf" and file_path.exists():
            append_pdf(file_path)
    
    # Generate checklist page
    if include_checklist and analysis:
        checklist_pdf = await _generate_checklist_page(analysis, output_dir)
        if checklist_pdf.exists():
            append_pdf(checklist_pdf)
    
    # Write merged PDF
    with open(output_path, "wb") as f:
        writer.write(f)
    
    # Apply watermark if specified
    if watermark:
        await _apply_watermark(output_path, watermark)
    
    logger.info(f"Evidence pack generated: {output_path}")
    
    return output_path


async def _generate_cover_page(case_data: Dict[str, Any], output_dir: Path) -> Path:
    """Generate cover page PDF using reportlab or simple text"""
    cover_path = output_dir / "temp_cover.pdf"
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        
        from reportlab.lib.colors import HexColor
        c = canvas.Canvas(str(cover_path), pagesize=A4)
        width, height = A4
        
        # Aegis Brand Colors
        brand_bg = HexColor("#0f172a") # Slate 900
        brand_teal = HexColor("#14b8a6") # Teal 500
        brand_text_light = HexColor("#94a3b8") # Slate 400
        
        # Draw dark background
        c.setFillColor(brand_bg)
        c.rect(0, 0, width, height, fill=1)
        
        # Title
        c.setFillColor(brand_teal)
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(width/2, height - 3*inch, "MEDICAL EVIDENCE PACK")
        
        # Subtitle
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica", 14)
        c.drawCentredString(width/2, height - 3.5*inch, "Aegis AI Copilot - Authenticated Export")
        
        # Divider
        c.setStrokeColor(brand_teal)
        c.setLineWidth(2)
        c.line(2*inch, height - 4*inch, width - 2*inch, height - 4*inch)
        
        # Case details
        c.setFillColor(brand_text_light)
        c.setFont("Helvetica", 12)
        y = height - 5*inch
        
        details = [
            f"Case: {case_data.get('case_number', case_data.get('id', 'N/A'))}",
            f"Lane: {case_data.get('lane', 'N/A').upper()}",
            f"Payer: {case_data.get('payer_id', 'N/A')}",
            f"AI Readiness Score: {case_data.get('readiness_score', 'N/A')} / 100",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        for detail in details:
            c.drawCentredString(width/2, y, detail)
            y -= 0.5*inch
        
        # Footer
        c.setFillColor(brand_teal)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width/2, 1.5*inch, "AEGIS LOCAL")
        c.setFillColor(brand_text_light)
        c.setFont("Helvetica", 9)
        c.drawCentredString(width/2, 1.1*inch, "Offline Claim Readiness Copilot")
        
        c.save()
        return cover_path
        
    except ImportError:
        # Fallback: create simple text file (would need conversion)
        logger.warning("reportlab not installed, skipping cover page")
        return Path("")


async def _generate_index_page(index_data: List[Dict], case_data: Dict, output_dir: Path) -> Path:
    """Generate index/table of contents page"""
    index_path = output_dir / "temp_index.pdf"
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        
        from reportlab.lib.colors import HexColor
        c = canvas.Canvas(str(index_path), pagesize=A4)
        width, height = A4
        brand_teal = HexColor("#14b8a6")
        brand_indigo = HexColor("#6366f1")
        brand_text_dark = HexColor("#334155")
        
        # Title
        c.setFillColor(brand_indigo)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width/2, height - 1*inch, "TABLE OF CONTENTS")
        
        # Table headers
        c.setFillColor(brand_teal)
        c.setFont("Helvetica-Bold", 11)
        y = height - 1.8*inch
        
        # Header background
        c.rect(0.5*inch, y - 0.15*inch, width - 1*inch, 0.4*inch, fill=0)
        
        c.drawString(0.75*inch, y, "Document Type")
        c.drawString(4*inch, y, "Filename")
        c.drawString(6.5*inch, y, "Pages")
        
        # Table content
        c.setFillColor(brand_text_dark)
        c.setFont("Helvetica", 10)
        y -= 0.5*inch
        
        for i, item in enumerate(index_data):
            if y < 1*inch:
                c.showPage()
                y = height - 1*inch
                c.setFont("Helvetica", 10)
            
            # Draw row separator line conditionally
            if i > 0:
                c.setStrokeColor(HexColor("#e2e8f0"))
                c.setLineWidth(0.5)
                c.line(0.5*inch, y + 0.2*inch, width - 0.5*inch, y + 0.2*inch)
                
            c.drawString(0.75*inch, y, item["doc_type"][:30])
            c.drawString(4*inch, y, item["filename"][:35] if item["filename"] else "")
            c.drawString(6.5*inch, y, f"{item['start_page']}-{item['end_page']}")
            y -= 0.3*inch
        
        c.save()
        return index_path
        
    except ImportError:
        logger.warning("reportlab not installed, skipping index page")
        return Path("")


async def _generate_draft_page(draft: Dict[str, Any], output_dir: Path) -> Path:
    """Generate doctor query draft page"""
    draft_path = output_dir / "temp_draft.pdf"
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        import textwrap
        
        c = canvas.Canvas(str(draft_path), pagesize=A4)
        width, height = A4
        brand_teal = HexColor("#14b8a6")
        brand_indigo = HexColor("#6366f1")
        brand_text_dark = HexColor("#1e293b")
        brand_red = HexColor("#ef4444")
        brand_blue = HexColor("#3b82f6")
        
        # Title
        c.setFillColor(brand_indigo)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width/2, height - 1*inch, "CLINICAL RESPONSE DRAFT")
        
        y = height - 1.8*inch
        
        # Helper for wrapping text
        def draw_wrapped_text(c, text, x, y, max_width, line_height=14):
            lines = textwrap.wrap(text, width=max_width)
            for line in lines:
                if y < 1*inch:
                    c.showPage()
                    y = height - 1*inch
                    c.setFont("Helvetica", 10)
                c.drawString(x, y, line)
                y -= line_height
            return y - line_height

        # Query
        if draft.get("query_text"):
            c.setFillColor(brand_teal)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(0.75*inch, y, "Payer Query:")
            y -= 0.3*inch
            c.setFont("Helvetica", 10)
            c.setFillColor(brand_red)
            y = draw_wrapped_text(c, draft["query_text"], 1*inch, y, 90)
            c.setFillColor(brand_text_dark)
            y -= 0.2*inch
            
        # Transcript
        if draft.get("transcript") and draft["transcript"] != "[Transcription failed]":
            c.setFillColor(brand_teal)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(0.75*inch, y, "Doctor's Voice Note (Dictation):")
            y -= 0.3*inch
            c.setFont("Helvetica-Oblique", 10)
            c.setFillColor(brand_blue)
            y = draw_wrapped_text(c, f'"{draft["transcript"]}"', 1*inch, y, 90)
            c.setFillColor(brand_text_dark)
            y -= 0.2*inch

        # Draft Payload (Response)
        if draft.get("draft_json"):
            draft_payload = draft["draft_json"]
            if isinstance(draft_payload, str):
                import json
                try:
                    draft_payload = json.loads(draft_payload)
                except:
                    draft_payload = {}
                    
            if draft_payload.get("clinicalSummary"):
                c.setFillColor(brand_teal)
                c.setFont("Helvetica-Bold", 11)
                c.drawString(0.75*inch, y, "Clinical Summary:")
                y -= 0.3*inch
                c.setFillColor(brand_text_dark)
                c.setFont("Helvetica", 10)
                y = draw_wrapped_text(c, draft_payload["clinicalSummary"], 1*inch, y, 90)
                y -= 0.2*inch
                
            if draft_payload.get("justification"):
                c.setFillColor(brand_teal)
                c.setFont("Helvetica-Bold", 11)
                c.drawString(0.75*inch, y, "Clinical Justification:")
                y -= 0.3*inch
                c.setFillColor(brand_text_dark)
                c.setFont("Helvetica", 10)
                y = draw_wrapped_text(c, draft_payload["justification"], 1*inch, y, 90)
                
        c.save()
        return draft_path
        
    except ImportError:
        logger.warning("reportlab not installed, skipping draft page")
        return Path("")


async def _generate_checklist_page(analysis: Dict[str, Any], output_dir: Path) -> Path:
    """Generate checklist summary page"""
    checklist_path = output_dir / "temp_checklist.pdf"
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        c = canvas.Canvas(str(checklist_path), pagesize=A4)
        width, height = A4
        brand_teal = HexColor("#14b8a6")
        brand_indigo = HexColor("#6366f1")
        brand_text_dark = HexColor("#1e293b")
        brand_red = HexColor("#ef4444")
        brand_amber = HexColor("#f59e0b")
        brand_green = HexColor("#10b981")
        
        # Title
        c.setFillColor(brand_indigo)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width/2, height - 1*inch, "CHECKLIST SUMMARY")
        
        # Score
        score = analysis.get("score", 0)
        band = analysis.get("band", "RED")
        
        c.setFillColor(brand_text_dark)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(0.75*inch, height - 1.8*inch, f"Readiness Score: {score}/100 ")
        
        # Band color
        band_col = brand_red if band == "RED" else (brand_amber if band == "AMBER" else brand_green)
        c.setFillColor(band_col)
        c.drawString(3.5*inch, height - 1.8*inch, f"({band})")
        
        # Missing items
        c.setFillColor(brand_teal)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0.75*inch, height - 2.5*inch, "Missing/Weak Evidence:")
        
        c.setFillColor(brand_text_dark)
        c.setFont("Helvetica", 10)
        y = height - 2.9*inch
        
        missing = analysis.get("missing_items", [])
        if isinstance(missing, str):
            missing = json.loads(missing)
        
        for item in missing[:10]:
            if y < 1*inch:
                break
            text = f"• {item.get('item', 'Unknown')} (Owner: {item.get('owner', 'TPA')})"
            c.drawString(1*inch, y, text)
            y -= 0.3*inch
        
        c.save()
        return checklist_path
        
    except ImportError:
        logger.warning("reportlab not installed, skipping checklist page")
        return Path("")


async def _apply_watermark(pdf_path: Path, watermark_text: str):
    """Apply watermark to all pages"""
    # TODO: Implement watermark using pypdf
    logger.info(f"Watermark '{watermark_text}' would be applied to {pdf_path}")
