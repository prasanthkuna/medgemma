"""
Cases router - Case management API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import uuid
import hashlib
import shutil
from pathlib import Path

from db.database import get_db
from config import settings

router = APIRouter()


# === Pydantic Models ===

class CaseCreate(BaseModel):
    case_number: Optional[str] = None
    patient_alias: Optional[str] = None
    lane: str  # cardio | ortho
    payer_id: Optional[str] = None
    tpa_id: Optional[str] = None


class CaseUpdate(BaseModel):
    status: Optional[str] = None
    payer_id: Optional[str] = None
    tpa_id: Optional[str] = None


class CaseResponse(BaseModel):
    id: str
    case_number: Optional[str]
    patient_alias: Optional[str]
    lane: str
    payer_id: Optional[str]
    tpa_id: Optional[str]
    status: str
    readiness_score: Optional[int]
    readiness_band: Optional[str]
    created_at: str
    updated_at: str
    file_count: Optional[int] = 0


class CaseFileResponse(BaseModel):
    id: str
    filename: str
    doc_type: Optional[str]
    doc_type_confidence: Optional[float]
    quality_flags: Optional[str]
    page_count: Optional[int]


# === Endpoints ===

@router.post("", response_model=CaseResponse)
async def create_case(case: CaseCreate, db=Depends(get_db)):
    """Create a new case"""
    case_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    await db.execute(
        """
        INSERT INTO cases (id, case_number, patient_alias, lane, payer_id, tpa_id, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?)
        """,
        (case_id, case.case_number, case.patient_alias, case.lane, case.payer_id, case.tpa_id, now, now)
    )
    await db.commit()
    
    # Create case folder
    case_folder = settings.cases_dir / case_id
    case_folder.mkdir(parents=True, exist_ok=True)
    (case_folder / "raw").mkdir(exist_ok=True)
    (case_folder / "working").mkdir(exist_ok=True)
    (case_folder / "exports").mkdir(exist_ok=True)
    
    # Log audit event
    await db.execute(
        "INSERT INTO audit_events (id, case_id, action, created_at) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), case_id, "case_created", now)
    )
    await db.commit()
    
    return CaseResponse(
        id=case_id,
        case_number=case.case_number,
        patient_alias=case.patient_alias,
        lane=case.lane,
        payer_id=case.payer_id,
        tpa_id=case.tpa_id,
        status="new",
        readiness_score=None,
        readiness_band=None,
        created_at=now,
        updated_at=now
    )


@router.get("")
async def list_cases(
    lane: Optional[str] = None,
    payer_id: Optional[str] = None,
    status: Optional[str] = None,
    db=Depends(get_db)
):
    """List all cases with optional filters"""
    query = "SELECT c.*, COUNT(cf.id) as file_count FROM cases c LEFT JOIN case_files cf ON c.id = cf.case_id WHERE 1=1"
    params = []
    
    if lane:
        query += " AND c.lane = ?"
        params.append(lane)
    if payer_id:
        query += " AND c.payer_id = ?"
        params.append(payer_id)
    if status:
        query += " AND c.status = ?"
        params.append(status)
    
    query += " GROUP BY c.id ORDER BY c.updated_at DESC"
    
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    
    return [dict(row) for row in rows]


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str, db=Depends(get_db)):
    """Get a specific case"""
    cursor = await db.execute(
        """
        SELECT c.*, COUNT(cf.id) as file_count 
        FROM cases c 
        LEFT JOIN case_files cf ON c.id = cf.case_id 
        WHERE c.id = ?
        GROUP BY c.id
        """,
        (case_id,)
    )
    row = await cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return dict(row)


@router.patch("/{case_id}")
async def update_case(case_id: str, case: CaseUpdate, db=Depends(get_db)):
    """Update case status or metadata"""
    updates = []
    params = []
    
    if case.status:
        updates.append("status = ?")
        params.append(case.status)
    if case.payer_id:
        updates.append("payer_id = ?")
        params.append(case.payer_id)
    if case.tpa_id:
        updates.append("tpa_id = ?")
        params.append(case.tpa_id)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(case_id)
    
    await db.execute(
        f"UPDATE cases SET {', '.join(updates)} WHERE id = ?",
        params
    )
    await db.commit()
    
    return {"message": "Case updated"}


@router.get("/{case_id}/files", response_model=List[CaseFileResponse])
async def get_case_files(case_id: str, db=Depends(get_db)):
    """Get all files for a case"""
    cursor = await db.execute(
        "SELECT * FROM case_files WHERE case_id = ? ORDER BY created_at",
        (case_id,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.get("/{case_id}/audit")
async def get_case_audit(case_id: str, db=Depends(get_db)):
    """Get chronological audit timeline for a case"""
    cursor = await db.execute(
        "SELECT * FROM audit_events WHERE case_id = ? ORDER BY created_at ASC",
        (case_id,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.post("/{case_id}/files")
async def upload_file(case_id: str, file: UploadFile = File(...), db=Depends(get_db)):
    """Upload a file to a case"""
    # Verify case exists
    cursor = await db.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Save file - strip any subdirectory from filename (webkitdirectory sends paths)
    file_id = str(uuid.uuid4())
    # Robustly get basename to handle both Chrome/Windows and other browser path formats
    safe_filename = file.filename.replace('\\', '/').split('/')[-1]
    case_folder = settings.cases_dir / case_id / "raw"
    case_folder.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    file_path = case_folder / safe_filename
    
    # Calculate hash and save
    content = await file.read()
    sha256 = hashlib.sha256(content).hexdigest()
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Determine mime type
    mime_type = file.content_type or "application/octet-stream"
    
    # Insert file record
    await db.execute(
        """
        INSERT INTO case_files (id, case_id, path, filename, sha256, mime_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (file_id, case_id, str(file_path), safe_filename, sha256, mime_type, datetime.now().isoformat())
    )
    await db.commit()
    
    return {
        "id": file_id,
        "filename": safe_filename,
        "sha256": sha256,
        "mime_type": mime_type
    }

@router.put("/{case_id}")
async def update_case_status(case_id: str, payload: dict = Body(...), db=Depends(get_db)):
    """Update general case status"""
    status = payload.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Missing status")
        
    await db.execute("UPDATE cases SET status = ? WHERE id = ?", (status, case_id))
    await db.execute(
        "INSERT INTO audit_events (id, case_id, action, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), case_id, "case_status_updated", status, datetime.now().isoformat())
    )
    await db.commit()
    return {"message": f"Case updated to {status}"}

@router.delete("/{case_id}/files/{file_id}")
async def delete_case_file(case_id: str, file_id: str, db=Depends(get_db)):
    """Delete a specific file from a case"""
    cursor = await db.execute("SELECT path, filename FROM case_files WHERE id = ? AND case_id = ?", (file_id, case_id))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = Path(dict(row)["path"])
    
    # Delete from DB
    await db.execute("DELETE FROM case_files WHERE id = ?", (file_id,))
    
    # Log audit
    await db.execute(
        "INSERT INTO audit_events (id, case_id, action, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), case_id, "file_deleted", dict(row)["filename"], datetime.now().isoformat())
    )
    await db.commit()
    
    # Delete from disk
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            # We don't fail the request if disk deletion fails, just log it
            print(f"Warning: Failed to delete physical file {file_path}: {e}")
            
    return {"message": "File deleted successfully"}


@router.post("/{case_id}/import-folder")
async def import_folder(case_id: str, folder_path: str, db=Depends(get_db)):
    """Import all files from a folder (called via Tauri file dialog)"""
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Invalid folder path")
    
    imported = []
    case_folder = settings.cases_dir / case_id / "raw"
    case_folder.mkdir(parents=True, exist_ok=True)
    
    for file_path in folder.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in [".pdf", ".jpg", ".jpeg", ".png"]:
            file_id = str(uuid.uuid4())
            dest_path = case_folder / file_path.name
            
            # Copy file
            shutil.copy2(file_path, dest_path)
            
            # Calculate hash
            with open(dest_path, "rb") as f:
                sha256 = hashlib.sha256(f.read()).hexdigest()
            
            # Check for duplicate
            cursor = await db.execute(
                "SELECT id FROM case_files WHERE case_id = ? AND sha256 = ?",
                (case_id, sha256)
            )
            if await cursor.fetchone():
                dest_path.unlink()  # Remove duplicate
                continue
            
            # Insert record
            mime_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else f"image/{file_path.suffix[1:].lower()}"
            await db.execute(
                """
                INSERT INTO case_files (id, case_id, path, filename, sha256, mime_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (file_id, case_id, str(dest_path), file_path.name, sha256, mime_type, datetime.now().isoformat())
            )
            imported.append(file_path.name)
    
    await db.commit()
    
    # Log audit event
    await db.execute(
        "INSERT INTO audit_events (id, case_id, action, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), case_id, "folder_imported", str(len(imported)), datetime.now().isoformat())
    )
    await db.commit()
    
    return {"imported": len(imported), "files": imported}


@router.delete("/{case_id}")
async def delete_case(case_id: str, db=Depends(get_db)):
    """Delete a case and all associated data (files, audit events, disk folder)"""
    cursor = await db.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Case not found")

    # Cascade delete
    await db.execute("DELETE FROM case_files WHERE case_id = ?", (case_id,))
    await db.execute("DELETE FROM audit_events WHERE case_id = ?", (case_id,))
    await db.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    await db.commit()

    # Remove folder from disk
    case_folder = settings.cases_dir / case_id
    if case_folder.exists():
        shutil.rmtree(case_folder, ignore_errors=True)

    return {"message": "Case deleted", "id": case_id}


@router.post("/smart-scan")
async def smart_scan(file: UploadFile = File(...)):
    """Quick-scan a PDF to extract patient metadata for auto-filling case creation.
    Reads the first page and extracts patient name, department/lane, and payer."""
    import tempfile, re
    
    content = await file.read()
    result = {"patient_name": "", "lane": "cardio", "payer": "", "filename": file.filename}
    
    try:
        import pdfplumber
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        with pdfplumber.open(tmp_path) as pdf:
            if pdf.pages:
                text = pdf.pages[0].extract_text() or ""
                
                # Extract patient name
                name_match = re.search(r"Patient\s*Name\s*:?\s*([A-Z][a-zA-Z\s\.]+?)(?:\n|MRN|Age|Gender|$)", text)
                if name_match:
                    result["patient_name"] = name_match.group(1).strip()
                
                # Extract payer
                payer_match = re.search(r"(?:Payer|Insurance|Insurer)\s*:?\s*([A-Za-z\s]+?)(?:\n|Policy|$)", text)
                if payer_match:
                    result["payer"] = payer_match.group(1).strip()
                
                # Detect lane from department/consultant
                text_lower = text.lower()
                if any(k in text_lower for k in ["cardiology", "cardiac", "cardio", "stent", "pci", "cabg", "angioplasty"]):
                    result["lane"] = "cardio"
                elif any(k in text_lower for k in ["ortho", "orthop", "joint", "knee", "hip", "fracture", "tkr", "thr"]):
                    result["lane"] = "ortho"
        
        Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Smart scan failed: {e}")
    
    return result

