"""
Document Classification Service
Uses Pramana AI/Gemma3 for medical document type classification
"""
import ollama
from pathlib import Path
from typing import Dict, Any
import logging

from config import settings

logger = logging.getLogger(__name__)

# Document type definitions per TRD
DOC_TYPES = [
    "discharge_summary",
    "admission_note",
    "progress_note",
    "ot_note",
    "implant_sticker",
    "pharmacy_bill",
    "icu_chart",
    "lab_report",
    "radiology_report",
    "insurance_card",
    "other"
]

CLASSIFICATION_PROMPT = """You are a medical document classifier for Indian hospital insurance claims.

Analyze the following document content and classify it into exactly ONE of these categories:
- discharge_summary: Patient discharge documentation
- admission_note: Initial admission records
- progress_note: Daily patient progress updates
- ot_note: Operation theatre / surgical notes
- implant_sticker: Implant/stent labels with serial numbers
- pharmacy_bill: Pharmacy receipts and drug bills
- icu_chart: ICU vital signs and monitoring charts
- lab_report: Laboratory test results
- radiology_report: X-ray, CT, MRI reports
- insurance_card: ID or insurance cards
- other: Documents that don't fit other categories

Document content (first 2000 characters):
{content}

Respond with ONLY a JSON object in this exact format:
{{"doc_type": "category_name", "confidence": 0.0-1.0, "reason": "brief explanation"}}
"""


async def classify_document(file_path: str, mime_type: str) -> Dict[str, Any]:
    """
    Classify a document using LLM analysis
    
    Args:
        file_path: Path to the document
        mime_type: MIME type of the document
        
    Returns:
        Dict with doc_type, confidence, and reason
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return {"doc_type": "other", "confidence": 0.0, "reason": "File not found"}
    
    # Extract text content based on file type
    content = ""
    
    if mime_type == "application/pdf":
        content = await _extract_pdf_text(file_path)
    elif mime_type.startswith("image/"):
        # For images, use multimodal analysis or OCR
        content = await _analyze_image(file_path)
    else:
        content = "Unable to extract content from this file type"
    
    if not content or len(content.strip()) < 10:
        # Fallback: use filename heuristics
        return _classify_by_filename(file_path.name)
    
    # Call LLM for classification
    try:
        response = ollama.chat(
            model=settings.default_model,
            messages=[{
                "role": "user",
                "content": CLASSIFICATION_PROMPT.format(content=content[:2000])
            }],
            format="json"
        )
        
        result = response["message"]["content"]
        import json
        parsed = json.loads(result)
        
        # Validate doc_type
        if parsed.get("doc_type") not in DOC_TYPES:
            parsed["doc_type"] = "other"
        
        return {
            "doc_type": parsed.get("doc_type", "other"),
            "confidence": float(parsed.get("confidence", 0.5)),
            "reason": parsed.get("reason", "")
        }
        
    except Exception as e:
        logger.error(f"Classification error: {e}")
        return _classify_by_filename(file_path.name)


async def _extract_pdf_text(file_path: Path) -> str:
    """Extract text from PDF using pdfplumber"""
    try:
        import pdfplumber
        
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages[:3]):  # First 3 pages
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
        
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""


async def _analyze_image(file_path: Path) -> str:
    """
    Analyze image: extract metadata + filename-based content description.
    Returns a text description the LLM can classify.
    """
    try:
        from PIL import Image
        img = Image.open(file_path)
        width, height = img.size
        mode = img.mode
        fmt = img.format or file_path.suffix.upper()
        
        # Build descriptive text from image properties + filename
        name_lower = file_path.stem.lower().replace("_", " ").replace("-", " ")
        lines = [
            f"Image file: {file_path.name}",
            f"Dimensions: {width}x{height} pixels, Mode: {mode}, Format: {fmt}",
        ]
        
        # Filename-based content hints for medical documents
        if any(k in name_lower for k in ["sticker", "implant", "stent", "device"]):
            lines.append("Content: Medical device implant sticker/label with serial number and manufacturer info")
        elif any(k in name_lower for k in ["xray", "x ray", "radiograph"]):
            lines.append("Content: Radiological X-ray image")
        elif any(k in name_lower for k in ["ecg", "ekg", "electrocardiogram"]):
            lines.append("Content: ECG/EKG electrocardiogram tracing")
        elif any(k in name_lower for k in ["mri", "ct scan", "ct_scan"]):
            lines.append("Content: Medical imaging scan (MRI/CT)")
        elif any(k in name_lower for k in ["lab", "report", "test"]):
            lines.append("Content: Laboratory test report")
        elif any(k in name_lower for k in ["insurance", "card", "id"]):
            lines.append("Content: Insurance or identification card")
        elif any(k in name_lower for k in ["bill", "pharmacy", "invoice"]):
            lines.append("Content: Pharmacy or medical bill/invoice")
        elif any(k in name_lower for k in ["discharge", "summary"]):
            lines.append("Content: Patient discharge summary document")
        else:
            lines.append(f"Content: Medical document image named '{file_path.stem}'")
        
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Image analysis failed for {file_path}: {e}")
        return f"[Image file: {file_path.name}]"


def _classify_by_filename(filename: str) -> Dict[str, Any]:
    """Fallback classification using filename patterns"""
    filename_lower = filename.lower()
    
    patterns = {
        "discharge": ("discharge_summary", 0.7),
        "admission": ("admission_note", 0.7),
        "progress": ("progress_note", 0.6),
        "ot_note": ("ot_note", 0.7),
        "operation": ("ot_note", 0.6),
        "surgical": ("ot_note", 0.6),
        "sticker": ("implant_sticker", 0.8),
        "implant": ("implant_sticker", 0.7),
        "stent": ("implant_sticker", 0.7),
        "pharmacy": ("pharmacy_bill", 0.8),
        "bill": ("pharmacy_bill", 0.5),
        "icu": ("icu_chart", 0.7),
        "vitals": ("icu_chart", 0.6),
        "lab": ("lab_report", 0.7),
        "test": ("lab_report", 0.5),
        "xray": ("radiology_report", 0.8),
        "x-ray": ("radiology_report", 0.8),
        "ct_scan": ("radiology_report", 0.8),
        "mri": ("radiology_report", 0.8),
        "radiology": ("radiology_report", 0.7),
        "insurance": ("insurance_card", 0.7),
        "id_card": ("insurance_card", 0.7),
    }
    
    for pattern, (doc_type, confidence) in patterns.items():
        if pattern in filename_lower:
            return {
                "doc_type": doc_type,
                "confidence": confidence,
                "reason": f"Matched filename pattern: {pattern}"
            }
    
    return {"doc_type": "other", "confidence": 0.3, "reason": "No pattern matched"}
