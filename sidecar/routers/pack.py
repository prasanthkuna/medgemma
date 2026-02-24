"""
Pack router - Evidence Pack Builder
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import uuid
import json

from db.database import get_db
from config import settings
from services.pack_builder import build_evidence_pack

router = APIRouter()


class PackRequest(BaseModel):
    template_id: Optional[str] = None
    include_cover: bool = True
    include_checklist: bool = True
    include_watermark: bool = False
    watermark_text: str = "DRAFT"


@router.post("/{case_id}/generate")
async def generate_pack(case_id: str, request: PackRequest, db=Depends(get_db)):
    """Generate Evidence Pack PDF for a case"""
    # Verify case exists
    cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    case = await cursor.fetchone()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get case files
    cursor = await db.execute(
        "SELECT * FROM case_files WHERE case_id = ? ORDER BY doc_type",
        (case_id,)
    )
    files = [dict(f) for f in await cursor.fetchall()]
    
    if not files:
        raise HTTPException(status_code=400, detail="No files in case")
    
    # Get latest analysis for checklist
    cursor = await db.execute(
        "SELECT * FROM case_analysis WHERE case_id = ? ORDER BY created_at DESC LIMIT 1",
        (case_id,)
    )
    analysis = await cursor.fetchone()
    analysis_data = dict(analysis) if analysis else None
    
    # Get latest approved or drafted query draft
    cursor = await db.execute(
        """
        SELECT * FROM case_drafts 
        WHERE case_id = ? AND status IN ('query_drafted', 'approved') 
        ORDER BY created_at DESC LIMIT 1
        """,
        (case_id,)
    )
    draft_row = await cursor.fetchone()
    draft_data = dict(draft_row) if draft_row else None
    
    # Build the pack
    case_dict = dict(case)
    output_path = await build_evidence_pack(
        case_id=case_id,
        case_data=case_dict,
        files=files,
        analysis=analysis_data,
        draft=draft_data,
        include_cover=request.include_cover,
        include_checklist=request.include_checklist,
        watermark=request.watermark_text if request.include_watermark else None
    )
    
    # Calculate hash
    import hashlib
    with open(output_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    
    # Save output record
    output_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO case_outputs (id, case_id, output_type, path, sha256, metadata, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (output_id, case_id, "evidence_pack", str(output_path), sha256, json.dumps({"template_id": request.template_id}), datetime.now().isoformat())
    )
    
    # Update case status
    await db.execute(
        "UPDATE cases SET status = 'pack_generated', updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), case_id)
    )
    await db.commit()
    
    # Log audit event
    await db.execute(
        "INSERT INTO audit_events (id, case_id, action, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), case_id, "pack_generated", sha256, datetime.now().isoformat())
    )
    await db.commit()
    
    # Convert absolute output_path to relative path for the website
    # settings.data_root is mounted at /docs
    try:
        rel_path = output_path.relative_to(settings.data_root)
        url_path = f"/docs/{rel_path.as_posix()}"
    except ValueError:
        # Fallback if not within data_root for some reason
        url_path = f"/docs/cases/{case_id}/exports/{output_path.name}"
    
    return {
        "output_id": output_id,
        "path": url_path,
        "sha256": sha256
    }


@router.get("/{case_id}/exports")
async def get_exports(case_id: str, db=Depends(get_db)):
    """Get all exports for a case"""
    cursor = await db.execute(
        "SELECT * FROM case_outputs WHERE case_id = ? ORDER BY created_at DESC",
        (case_id,)
    )
    rows = await cursor.fetchall()
    
    exports = []
    for row in rows:
        export = dict(row)
        export["metadata"] = json.loads(export.get("metadata", "{}"))
        exports.append(export)
    
    return exports
