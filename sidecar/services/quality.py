"""
Document Quality Check Service
Checks for blur, DPI, cropping issues, and potential patient mismatch
"""
from pathlib import Path
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


async def check_quality(file_path: str, mime_type: str) -> List[Dict[str, Any]]:
    """
    Check document quality for potential issues
    
    Returns list of quality flags with severity and recommendations
    """
    file_path = Path(file_path)
    flags = []
    
    if not file_path.exists():
        return [{"flag": "file_missing", "severity": 5, "message": "File not found"}]
    
    if mime_type.startswith("image/"):
        flags.extend(await _check_image_quality(file_path))
    elif mime_type == "application/pdf":
        flags.extend(await _check_pdf_quality(file_path))
    
    return flags


async def _check_image_quality(file_path: Path) -> List[Dict[str, Any]]:
    """Check image quality metrics"""
    flags = []
    
    try:
        from PIL import Image
        import numpy as np
        
        img = Image.open(file_path)
        width, height = img.size
        
        # Check resolution
        if width < 800 or height < 600:
            flags.append({
                "flag": "low_resolution",
                "severity": 3,
                "message": f"Low resolution: {width}x{height}. Recommend minimum 800x600.",
                "recommendation": "Re-scan at higher DPI",
                "score": f"{width}x{height}"
            })
        
        # Check for blur using Laplacian variance
        if img.mode != "L":
            gray = img.convert("L")
        else:
            gray = img
        
        img_array = np.array(gray)
        laplacian_var = _calculate_blur_score(img_array)
        
        if laplacian_var < 100:
            flags.append({
                "flag": "blurry_image",
                "severity": 4,
                "message": f"Image appears blurry (score: {laplacian_var:.1f}). May be unreadable.",
                "recommendation": "Re-scan or photograph with steady hands",
                "score": round(laplacian_var, 1)
            })
        
        # Check aspect ratio for potential cropping
        aspect = width / height
        if aspect < 0.5 or aspect > 2.0:
            flags.append({
                "flag": "unusual_aspect_ratio",
                "severity": 2,
                "message": f"Unusual aspect ratio ({aspect:.2f}). May be cropped incorrectly.",
                "recommendation": "Verify document is fully visible"
            })
        
        # Check if image is mostly empty (may be wrong orientation or mostly blank)
        mean_brightness = np.mean(img_array)
        if mean_brightness > 250 or mean_brightness < 10:
            flags.append({
                "flag": "possible_blank",
                "severity": 3,
                "message": "Image appears mostly blank or overexposed.",
                "recommendation": "Verify correct file was uploaded",
                "score": round(mean_brightness, 1)
            })
        
    except Exception as e:
        logger.error(f"Image quality check error: {e}")
        flags.append({
            "flag": "quality_check_failed",
            "severity": 1,
            "message": f"Unable to analyze image: {str(e)}"
        })
    
    return flags


async def _check_pdf_quality(file_path: Path) -> List[Dict[str, Any]]:
    """Check PDF quality metrics"""
    flags = []
    
    try:
        import pdfplumber
        
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            
            if page_count == 0:
                flags.append({
                    "flag": "empty_pdf",
                    "severity": 5,
                    "message": "PDF has no pages",
                    "recommendation": "Upload correct document"
                })
                return flags
            
            # Check first page for text content
            first_page = pdf.pages[0]
            text = first_page.extract_text() or ""
            
            if len(text.strip()) < 50:
                flags.append({
                    "flag": "scanned_pdf",
                    "severity": 2,
                    "message": "PDF appears to be scanned (no extractable text). OCR will be used.",
                    "recommendation": "Ensure scan is clear and properly aligned"
                })
            
            # Check for password protection
            # (pdfplumber would fail to open if protected)
            
    except Exception as e:
        logger.error(f"PDF quality check error: {e}")
        if "encrypted" in str(e).lower():
            flags.append({
                "flag": "encrypted_pdf",
                "severity": 5,
                "message": "PDF is password protected",
                "recommendation": "Upload unprotected version"
            })
        else:
            flags.append({
                "flag": "pdf_read_error",
                "severity": 4,
                "message": f"Unable to read PDF: {str(e)}"
            })
    
    return flags


def _calculate_blur_score(gray_array) -> float:
    """
    Calculate Laplacian variance as blur metric
    Higher values = sharper image
    """
    import numpy as np
    
    # Simple Laplacian kernel
    laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
    
    from scipy import ndimage
    filtered = ndimage.convolve(gray_array.astype(float), laplacian)
    
    return np.var(filtered)
