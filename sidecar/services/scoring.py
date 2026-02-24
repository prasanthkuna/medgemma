"""
Readiness Scoring Engine
Template-driven scoring per TRD specifications
"""
from typing import Dict, Any, List
import json
import logging
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

# Default template per PRD Section 8
DEFAULT_TEMPLATE = {
    "cardio": {
        "required_docs": [
            {"type": "discharge_summary", "weight": 15, "owner": "tpa"},
            {"type": "admission_note", "weight": 10, "owner": "tpa"},
            {"type": "ot_note", "weight": 10, "owner": "doctor"},
            {"type": "implant_sticker", "weight": 20, "owner": "stores"},
            {"type": "pharmacy_bill", "weight": 15, "owner": "tpa"},
        ],
        "sticker_required": True,
        "sticker_weight": 20
    },
    "ortho": {
        "required_docs": [
            {"type": "discharge_summary", "weight": 15, "owner": "tpa"},
            {"type": "admission_note", "weight": 10, "owner": "tpa"},
            {"type": "ot_note", "weight": 10, "owner": "doctor"},
            {"type": "implant_sticker", "weight": 20, "owner": "stores"},
            {"type": "pharmacy_bill", "weight": 15, "owner": "tpa"},
        ],
        "sticker_required": True,
        "sticker_weight": 20
    }
}

# Score bands per PRD
SCORE_BANDS = {
    "GREEN": (80, 100),
    "AMBER": (50, 79),
    "RED": (0, 49)
}


def calculate_readiness_score(
    files: List[Dict[str, Any]],
    lane: str,
    payer_id: str = "default",
    case_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Calculate readiness score based on:
    - Required docs present (40 points)
    - Scan quality OK (20 points)
    - Sticker verification (20 points) [lane-specific]
    - ICU/LOS evidence present (10 points) [if applicable]
    - Consistency checks pass (10 points)
    """
    # Load template (or use default)
    template = DEFAULT_TEMPLATE.get(lane, DEFAULT_TEMPLATE["cardio"])
    
    score = 0
    max_score = 100
    missing_items = []
    quality_issues = []
    consistency_flags = []
    
    # Get doc types present
    doc_types_present = {f.get("doc_type") for f in files if f.get("doc_type")}
    
    # --- Score Component 1: Required Documents (40 points) ---
    docs_score = 0
    docs_max = 40
    
    for req in template["required_docs"]:
        doc_type = req["type"]
        if doc_type in doc_types_present:
            # Find the file corresponding to this doc_type
            matching_files = [f for f in files if f.get("doc_type") == doc_type]
            if matching_files:
                f = matching_files[0] # Take the first one for patient check
                # Simple heuristic for patient name check
                extracted_text = ""
                if "path" in f and Path(f["path"]).suffix.lower() == ".pdf":
                    try:
                        import pdfplumber
                        with pdfplumber.open(f["path"]) as pdf:
                            if len(pdf.pages) > 0:
                                extracted_text = pdf.pages[0].extract_text() or ""
                    except Exception as e:
                        logger.warning(f"Failed to read pdf for patient check: {e}")
                
                # Simple identity check
                patient_name = case_data.get("patient_alias", "") if case_data else ""
                
                # If patient name has multiple words and is extracted properly, verify at least first name or last name
                # For robust checking, just check if the lowercased name appears in the lowercased text
                if patient_name and extracted_text:
                    parts = patient_name.lower().split()
                    if not any(part in extracted_text.lower() for part in parts if len(part) > 2):
                        print(f"⚠️ [Pramana AI Core] Identity Audit Failed: '{patient_name}' not verified in {doc_type}")
                        consistency_flags.append({
                            "type": "patient_alias_mismatch",
                            "severity": 3,
                            "message": f"Identity mismatch in {doc_type}: Patient name '{patient_name}' not clearly found on document."
                        })
            
            docs_score += (req["weight"] / sum(r["weight"] for r in template["required_docs"])) * docs_max
        else:
            print(f"⚠️ [Pramana AI Core] Policy Audit: Missing required document '{doc_type}'")
            missing_items.append({
                "item": doc_type,
                "impact": round((req["weight"] / sum(r["weight"] for r in template["required_docs"])) * docs_max),
                "owner": "hospital",
                "citation": req.get("citation", "Standard claim requirement")
            })
    
    score += int(docs_score)
    
    # --- Score Component 2: Scan Quality (20 points) ---
    quality_score = 20
    
    for f in files:
        quality_flags = f.get("quality_flags")
        if quality_flags:
            flags = json.loads(quality_flags) if isinstance(quality_flags, str) else quality_flags
            for flag in flags:
                severity = flag.get("severity", 1)
                if severity >= 4:
                    print(f"❌ [Pramana AI Core] Image Quality Alert: {flag.get('flag')} in {f.get('filename')}")
                    quality_score -= 10
                    quality_issues.append({
                        "file_id": f.get("id"),
                        "filename": f.get("filename"),
                        "flag": flag.get("flag"),
                        "severity": severity,
                        "message": flag.get("message")
                    })
                elif severity >= 3:
                    print(f"⚠️ [Pramana AI Core] Image Quality Warning: {flag.get('flag')} in {f.get('filename')}")
                    quality_score -= 5
                    quality_issues.append({
                        "file_id": f.get("id"),
                        "filename": f.get("filename"),
                        "flag": flag.get("flag"),
                        "severity": severity,
                        "message": flag.get("message")
                    })
    
    score += max(0, quality_score)
    
    # --- Score Component 3: Sticker Verification (20 points) ---
    if template.get("sticker_required"):
        if "implant_sticker" in doc_types_present:
            # Check sticker quality
            sticker_files = [f for f in files if f.get("doc_type") == "implant_sticker"]
            sticker_ok = True
            
            for sf in sticker_files:
                flags = sf.get("quality_flags")
                if flags:
                    flags = json.loads(flags) if isinstance(flags, str) else flags
                    for flag in flags:
                        if flag.get("severity", 0) >= 4:
                            sticker_ok = False
                            consistency_flags.append({
                                "type": "sticker_quality",
                                "severity": 4,
                                "message": "Implant sticker may be unreadable",
                                "evidence_links": [sf.get("filename")]
                            })
            
            if sticker_ok:
                score += 20
            else:
                score += 10  # Partial credit
        else:
            missing_items.append({
                "item": "Implant Sticker",
                "owner": "stores",
                "severity": 5,
                "impact": 20
            })
    else:
        score += 20  # Lane doesn't require sticker
    
    # --- Score Component 4: ICU/LOS Evidence (10 points) ---
    icu_score = 10
    icu_keywords = ["icu", "intensive care", "ventilat", "iabp", "inotrope", 
                     "mechanical ventilation", "critical care", "ccicu", "micu", "sicu"]
    icu_mentioned = False
    
    # Check if discharge summary mentions ICU/ventilator
    for f in files:
        if f.get("doc_type") == "discharge_summary":
            # Try to extract text from the file
            file_path = Path(f.get("path", ""))
            if file_path.exists() and file_path.suffix.lower() == ".pdf":
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        text = ""
                        for page in pdf.pages[:3]:
                            text += (page.extract_text() or "").lower()
                    if any(kw in text for kw in icu_keywords):
                        icu_mentioned = True
                        logger.info("ICU/ventilator mention found in discharge summary")
                except Exception as e:
                    logger.warning(f"Could not read discharge summary for ICU check: {e}")
    
    if icu_mentioned:
        # ICU was mentioned — verify supporting docs exist
        icu_evidence = {"icu_chart", "progress_note"}
        icu_docs_present = doc_types_present & icu_evidence
        if not icu_docs_present:
            icu_score = 0
            missing_items.append({
                "item": "ICU Chart / Progress Notes",
                "owner": "nurse",
                "severity": 5,
                "impact": 10
            })
            consistency_flags.append({
                "type": "icu_evidence_gap",
                "severity": 5,
                "message": "Discharge summary mentions ICU stay but no ICU chart or progress notes found",
                "evidence_links": ["discharge_summary"]
            })
        elif len(icu_docs_present) == 1:
            icu_score = 5  # Partial — only one of the two evidence types
            consistency_flags.append({
                "type": "icu_partial_evidence",
                "severity": 3,
                "message": f"ICU mentioned but only {list(icu_docs_present)[0].replace('_', ' ')} found. Consider adding more evidence.",
                "evidence_links": list(icu_docs_present)
            })
    # else: no ICU mentioned, full 10 points (not applicable)
    
    score += icu_score
    
    # --- Score Component 5: Consistency Checks (10 points) ---
    consistency_score = 10
    
    # Extract patient names/MRNs from PDF text across documents
    patient_identifiers = []
    for f in files:
        file_path = Path(f.get("path", ""))
        if file_path.exists() and file_path.suffix.lower() == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    first_page = pdf.pages[0].extract_text() or ""
                    # Look for "Patient Name:" patterns
                    import re
                    name_matches = re.findall(r"Patient\s*Name\s*:?\s*([A-Z][a-zA-Z\s]+?)(?:\n|MRN|Age|$)", first_page)
                    mrn_matches = re.findall(r"MRN\s*:?\s*([A-Z0-9\-]+)", first_page)
                    if name_matches:
                        patient_identifiers.append({
                            "file": f.get("filename"),
                            "name": name_matches[0].strip(),
                            "mrn": mrn_matches[0].strip() if mrn_matches else None
                        })
            except Exception:
                pass
    
    # Check for mismatches
    if len(patient_identifiers) >= 2:
        names = set(p["name"] for p in patient_identifiers)
        mrns = set(p["mrn"] for p in patient_identifiers if p["mrn"])
        
        if len(names) > 1:
            consistency_score = 0
            consistency_flags.append({
                "type": "patient_identity_mismatch",
                "severity": 5,
                "message": f"CRITICAL: Multiple patient names detected across documents: {', '.join(names)}. Possible wrong-patient mix-up!",
                "evidence_links": [p["file"] for p in patient_identifiers]
            })
        elif len(mrns) > 1:
            consistency_score = 3
            consistency_flags.append({
                "type": "mrn_mismatch",
                "severity": 4,
                "message": f"Different MRN numbers detected: {', '.join(mrns)}. Verify patient identity.",
                "evidence_links": [p["file"] for p in patient_identifiers]
            })
    
    score += consistency_score
    
    # Determine band
    final_score = min(100, max(0, score))
    band = "RED"
    for band_name, (low, high) in SCORE_BANDS.items():
        if low <= final_score <= high:
            band = band_name
            break
    
    # Generate top fixes
    all_issues = sorted(
        missing_items + quality_issues,
        key=lambda x: x.get("severity", 0) + x.get("impact", 0),
        reverse=True
    )
    top_fixes = all_issues[:5]
    
    return {
        "score": final_score,
        "band": band,
        "missing_items": missing_items,
        "quality_issues": quality_issues,
        "consistency_flags": consistency_flags,
        "top_fixes": top_fixes,
        "citations": {
            "policy": [],
            "case_docs": []
        }
    }
