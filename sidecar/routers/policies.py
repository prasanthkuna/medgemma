"""
Policies router - Policy PDF upload and RAG search
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional
from datetime import datetime
import uuid
import json
from pathlib import Path

from db.database import get_db
from config import settings
from services.rag import index_policy, search_policy

router = APIRouter()


@router.post("/{payer_id}/upload")
async def upload_policy(payer_id: str, file: UploadFile = File(...), db=Depends(get_db)):
    """Upload a policy PDF for a payer"""
    policy_folder = settings.policies_dir / payer_id / "pdfs"
    policy_folder.mkdir(parents=True, exist_ok=True)
    
    file_path = policy_folder / file.filename
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Check if policy record exists
    cursor = await db.execute("SELECT id FROM policies WHERE payer_id = ?", (payer_id,))
    existing = await cursor.fetchone()
    
    if existing:
        # Update existing policy
        cursor = await db.execute("SELECT source_files FROM policies WHERE payer_id = ?", (payer_id,))
        row = await cursor.fetchone()
        source_files = json.loads(dict(row).get("source_files", "[]"))
        if file.filename not in source_files:
            source_files.append(file.filename)
        
        await db.execute(
            "UPDATE policies SET source_files = ?, version = ? WHERE payer_id = ?",
            (json.dumps(source_files), datetime.now().strftime("%Y%m%d%H%M%S"), payer_id)
        )
    else:
        # Create new policy record
        await db.execute(
            "INSERT INTO policies (id, payer_id, version, source_files, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), payer_id, datetime.now().strftime("%Y%m%d%H%M%S"), json.dumps([file.filename]), datetime.now().isoformat())
        )
    
    await db.commit()
    
    return {"message": f"Policy PDF uploaded for {payer_id}", "filename": file.filename}


@router.post("/{payer_id}/index")
async def build_policy_index(payer_id: str, db=Depends(get_db)):
    """Build FAISS index for a payer's policy documents"""
    policy_folder = settings.policies_dir / payer_id / "pdfs"
    
    if not policy_folder.exists():
        raise HTTPException(status_code=404, detail="No policy documents found for this payer")
    
    pdf_files = list(policy_folder.glob("*.pdf"))
    if not pdf_files:
        raise HTTPException(status_code=404, detail="No PDF files found")
    
    # Build index
    index_path = await index_policy(payer_id, pdf_files)
    
    # Update policy record with index path
    await db.execute(
        "UPDATE policies SET index_path = ? WHERE payer_id = ?",
        (str(index_path), payer_id)
    )
    await db.commit()
    
    return {"message": f"Index built for {payer_id}", "index_path": str(index_path), "documents": len(pdf_files)}


@router.get("/{payer_id}/index-stream")
async def build_policy_index_stream(payer_id: str, db=Depends(get_db)):
    """
    SSE stream for policy vectorization telemetry.
    Replaces simulated frontend logs with real-time backend yield.
    """
    from fastapi.responses import StreamingResponse
    from services.rag import index_policy_stream
    import aiosqlite
    
    policy_folder = settings.policies_dir / payer_id / "pdfs"
    if not policy_folder.exists() or not list(policy_folder.glob("*.pdf")):
        raise HTTPException(status_code=404, detail="No policy documents found")

    pdf_files = list(policy_folder.glob("*.pdf"))

    async def event_generator():
        def sse(event: str, data: dict):
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        conn = await aiosqlite.connect(str(settings.db_path))
        try:
            async for event in index_policy_stream(payer_id, pdf_files):
                yield sse("log", event)
                
                if event["step"] == "complete":
                    # Final DB update
                    await conn.execute(
                        "UPDATE policies SET index_path = ? WHERE payer_id = ?",
                        (event["index_path"], payer_id)
                    )
                    await conn.commit()
                    yield sse("complete", event)
                    
        except Exception as e:
            yield sse("error", {"message": str(e)})
        finally:
            await conn.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{payer_id}/search")
async def search_policies(payer_id: str, q: str, k: int = 5, db=Depends(get_db)):
    """Search policy documents with citations"""
    cursor = await db.execute("SELECT index_path FROM policies WHERE payer_id = ?", (payer_id,))
    row = await cursor.fetchone()
    
    if not row or not dict(row).get("index_path"):
        raise HTTPException(status_code=404, detail="Policy index not found. Please build index first.")
    
    index_path = Path(dict(row)["index_path"])
    
    results = await search_policy(index_path, q, k)
    
    return {
        "query": q,
        "results": results
    }


@router.get("")
async def list_policies(db=Depends(get_db)):
    """List all indexed policies"""
    cursor = await db.execute("SELECT * FROM policies ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    
    policies = []
    for row in rows:
        policy = dict(row)
        policy["source_files"] = json.loads(policy.get("source_files", "[]"))
        policies.append(policy)
    
    return policies

@router.delete("/{payer_id}")
async def delete_policy(payer_id: str, db=Depends(get_db)):
    """Delete a policy and all its files from disk"""
    import shutil
    
    # 1. Delete from DB
    await db.execute("DELETE FROM policies WHERE payer_id = ?", (payer_id,))
    await db.commit()
    
    # 2. Delete from Disk
    policy_folder = settings.policies_dir / payer_id
    if policy_folder.exists() and policy_folder.is_dir():
        try:
            shutil.rmtree(policy_folder)
        except Exception as e:
            # Revert or log error, but keep going for DB
            pass
            
    return {"message": f"Successfully deleted policy {payer_id}"}
