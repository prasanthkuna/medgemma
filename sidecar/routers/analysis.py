"""
Analysis router - Document classification, scoring, and consistency checks
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import asyncio
import uuid
import json
import time

from db.database import get_db
from services.classify import classify_document
from services.quality import check_quality
from services.scoring import calculate_readiness_score

router = APIRouter()


class AnalysisResponse(BaseModel):
    case_id: str
    score: int
    band: str  # GREEN, AMBER, RED
    missing_items: list
    quality_issues: list
    consistency_flags: list
    citations: dict


@router.post("/{case_id}/analyze")
async def analyze_case(case_id: str, background_tasks: BackgroundTasks, db=Depends(get_db)):
    """
    Execute a comprehensive clinical audit analysis on a medical case.
    
    The audit pipeline consists of:
    1. Document Classification: Pramana AI identifies the record type (Discharge, Lab, PT, etc.).
    2. Quality Assurance: Detects imaging issues (blur, low-res) that impact auditability.
    3. Clinical Reasoning: Calculates a 'Readiness Score' by cross-referencing records 
       with payer-specific clinical policies in the RAG layer.
    
    Returns a structured AnalysisResponse with medical necessity findings and audit flags.
    """
    # Verify case exists
    cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    case = await cursor.fetchone()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get all files for the case
    cursor = await db.execute("SELECT * FROM case_files WHERE case_id = ?", (case_id,))
    files = await cursor.fetchall()
    
    if not files:
        raise HTTPException(status_code=400, detail="No files in case to analyze")
    
    # Run classification and quality checks on each file
    for file in files:
        file_dict = dict(file)
        
        # 1. Classify if missing
        if not file_dict.get("doc_type") or file_dict.get("doc_type") == "other":
            classification = await classify_document(file_dict["path"], file_dict["mime_type"])
            await db.execute(
                "UPDATE case_files SET doc_type = ?, doc_type_confidence = ? WHERE id = ?",
                (classification["doc_type"], classification["confidence"], file_dict["id"])
            )
        
        # 2. Always run quality check during explicit /analyze call
        quality = await check_quality(file_dict["path"], file_dict["mime_type"])
        await db.execute(
            "UPDATE case_files SET quality_flags = ? WHERE id = ?",
            (json.dumps(quality), file_dict["id"])
        )
    
    await db.commit()
    
    # Re-fetch files with classifications
    cursor = await db.execute("SELECT * FROM case_files WHERE case_id = ?", (case_id,))
    files = [dict(f) for f in await cursor.fetchall()]
    
    # Calculate readiness score
    lane = dict(case)["lane"]
    payer_id = dict(case).get("payer_id", "default")
    
    result = await asyncio.to_thread(calculate_readiness_score, files, lane, payer_id)
    
    # Save analysis result
    analysis_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO case_analysis (id, case_id, score, band, missing_items, quality_issues, consistency_flags, citations, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            analysis_id,
            case_id,
            result["score"],
            result["band"],
            json.dumps(result["missing_items"]),
            json.dumps(result["quality_issues"]),
            json.dumps(result["consistency_flags"]),
            json.dumps(result["citations"]),
            datetime.now().isoformat()
        )
    )
    
    # Update case with score
    await db.execute(
        "UPDATE cases SET readiness_score = ?, readiness_band = ?, status = 'in_review', updated_at = ? WHERE id = ?",
        (result["score"], result["band"], datetime.now().isoformat(), case_id)
    )
    await db.commit()
    
    # Log audit event
    await db.execute(
        "INSERT INTO audit_events (id, case_id, action, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), case_id, "analysis_completed", str(result["score"]), datetime.now().isoformat())
    )
    await db.commit()
    
    return result


@router.get("/{case_id}/analysis")
async def get_analysis(case_id: str, db=Depends(get_db)):
    """Get the latest analysis for a case"""
    cursor = await db.execute(
        "SELECT * FROM case_analysis WHERE case_id = ? ORDER BY created_at DESC LIMIT 1",
        (case_id,)
    )
    row = await cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="No analysis found for this case")
    
    analysis = dict(row)
    
    # Parse JSON fields
    analysis["missing_items"] = json.loads(analysis["missing_items"] or "[]")
    analysis["quality_issues"] = json.loads(analysis["quality_issues"] or "[]")
    analysis["consistency_flags"] = json.loads(analysis["consistency_flags"] or "[]")
    analysis["citations"] = json.loads(analysis["citations"] or "{}")
    
    return analysis


@router.get("/{case_id}/results")
async def get_analysis_results(case_id: str, db=Depends(get_db)):
    """
    Retrieve unified case telemetry for the Aegis Dashboard.
    
    Combines core file metadata with the latest AI-generated audit results, 
    including missing medical necessity items and clinical quality red-flags.
    """
    # 1. Get files
    cursor = await db.execute(
        "SELECT * FROM case_files WHERE case_id = ? ORDER BY created_at",
        (case_id,)
    )
    files = [dict(row) for row in await cursor.fetchall()]
    
    # 2. Get latest analysis
    cursor = await db.execute(
        "SELECT * FROM case_analysis WHERE case_id = ? ORDER BY created_at DESC LIMIT 1",
        (case_id,)
    )
    analysis_row = await cursor.fetchone()
    
    if not analysis_row:
        # Return files only if no analysis yet
        return {
            "files": files,
            "score": None,
            "band": None,
            "missing_items": [],
            "quality_issues": [],
            "consistency_flags": [],
            "citations": {}
        }
    
    analysis = dict(analysis_row)
    return {
        "files": files,
        "score": analysis["score"],
        "band": analysis["band"],
        "missing_items": json.loads(analysis["missing_items"] or "[]"),
        "quality_issues": json.loads(analysis["quality_issues"] or "[]"),
        "consistency_flags": json.loads(analysis["consistency_flags"] or "[]"),
        "citations": json.loads(analysis["citations"] or "{}")
    }


@router.post("/{case_id}/files/{file_id}/override-type")
async def override_doc_type(case_id: str, file_id: str, doc_type: str, db=Depends(get_db)):
    """Manually override document type classification"""
    await db.execute(
        "UPDATE case_files SET doc_type = ?, doc_type_confidence = 1.0 WHERE id = ? AND case_id = ?",
        (doc_type, file_id, case_id)
    )
    await db.commit()
    
    # Log audit event
    await db.execute(
        "INSERT INTO audit_events (id, case_id, action, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), case_id, "doc_type_override", f"{file_id}:{doc_type}", datetime.now().isoformat())
    )
    await db.commit()
    
    return {"message": "Document type updated"}


@router.post("/{case_id}/analyze-stream")
async def analyze_case_stream(case_id: str, db=Depends(get_db)):
    """
    SSE streaming analysis — emits real-time events for the cinematic pipeline UI.
    Each pipeline stage (classify, quality, score) emits progress events.
    """
    import logging
    import aiosqlite
    from config import settings
    logger = logging.getLogger("aegis.pipeline")

    # Pre-validate case exists (using injected db which is still valid here)
    cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    case = await cursor.fetchone()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    cursor = await db.execute("SELECT * FROM case_files WHERE case_id = ?", (case_id,))
    files = await cursor.fetchall()
    if not files:
        raise HTTPException(status_code=400, detail="No files in case to analyze")

    # Snapshot data before returning StreamingResponse (db may close after return)
    file_list = [dict(f) for f in files]
    case_dict = dict(case)

    async def event_stream():
        def sse(event: str, data: dict):
            payload = json.dumps(data)
            logger.info(f"  {data.get('icon', '▸')} {data.get('message', event)}")
            return f"event: {event}\ndata: {payload}\n\n"

        # Open our OWN db connection inside the generator
        conn = await aiosqlite.connect(str(settings.db_path))
        conn.row_factory = aiosqlite.Row

        try:
            total_files = len(file_list)
            pipeline_start = time.time()

            # ── Stage 1: Document Classification ──
            print(f"\n🔥 [Pramana AI Core] Initializing Pipeline Analysis for Case: {case_id}")
            print(f"🔥 [Pramana AI Core] Loading {total_files} document streams...")
            logger.info(f"\n{'='*60}")
            logger.info(f"🧠 PRAMANA AI ANALYSIS PIPELINE — Case {case_id[:8]}")
            logger.info(f"{'='*60}")
            logger.info(f"📁 {total_files} file(s) to process\n")

            yield sse("stage", {"stage": "classify", "status": "active", "total": total_files,
                                "icon": "🧠", "message": f"Stage 1/3: Classifying {total_files} documents..."})

            for i, f in enumerate(file_list):
                fname = f.get("filename", "unknown")
                t0 = time.time()

                if not f.get("doc_type") or f.get("doc_type") == "other":
                    classification = await classify_document(f["path"], f["mime_type"])
                    await conn.execute(
                        "UPDATE case_files SET doc_type = ?, doc_type_confidence = ? WHERE id = ?",
                        (classification["doc_type"], classification["confidence"], f["id"])
                    )
                    f["doc_type"] = classification["doc_type"]
                    elapsed = time.time() - t0
                    print(f"🔥 [Pramana AI Core] Vision parsing {fname} -> {classification['doc_type']} [{classification['confidence']:.0%}]")
                    logger.info(f"  📄 {fname} → {classification['doc_type']} ({classification['confidence']:.0%}) [{elapsed:.1f}s]")
                    yield sse("classify_result", {
                        "file": fname, "doc_type": classification["doc_type"],
                        "confidence": classification["confidence"], "index": i + 1, "total": total_files,
                        "elapsed": round(elapsed, 1),
                        "icon": "🧠", "message": f"[Vision] {fname} → {classification['doc_type']} (Confidence: {classification['confidence']:.2f})"
                    })
                else:
                    logger.info(f"  📄 {fname} → {f['doc_type']} (cached)")
                    yield sse("classify_result", {
                        "file": fname, "doc_type": f["doc_type"],
                        "confidence": 1.0, "index": i + 1, "total": total_files,
                        "elapsed": 0, "cached": True,
                        "icon": "✅", "message": f"{fname} → {f['doc_type']} (cached)"
                    })

            await conn.commit()
            yield sse("stage", {"stage": "classify", "status": "done",
                                "icon": "✅", "message": "Classification complete"})

            # ── Stage 2: Quality Scan ──
            logger.info(f"\n  🔍 Stage 2/3: Quality Scan")
            yield sse("stage", {"stage": "quality", "status": "active", "total": total_files,
                                "icon": "🔍", "message": "Stage 2/3: Scanning document quality..."})

            for i, f in enumerate(file_list):
                fname = f.get("filename", "unknown")
                t0 = time.time()
                quality = await check_quality(f["path"], f["mime_type"])
                await conn.execute(
                    "UPDATE case_files SET quality_flags = ? WHERE id = ?",
                    (json.dumps(quality), f["id"])
                )
                elapsed = time.time() - t0
                
                # Emit granular quality telemetry
                for flag in quality:
                    score_info = f" (Score: {flag['score']})" if "score" in flag else ""
                    severity_icon = "🔴" if flag["severity"] >= 4 else "🟡"
                    yield sse("log", {
                        "level": "warning" if flag["severity"] >= 3 else "info",
                        "message": f"[Audit] {fname}: {flag['flag'].replace('_', ' ').title()}{score_info}",
                        "icon": severity_icon
                    })

                issues = len([q for q in quality if q.get("severity", 0) >= 3])
                status_icon = "⚠️" if issues else "✅"
                logger.info(f"  {status_icon} {fname}: {issues} issue(s) [{elapsed:.1f}s]")
                yield sse("quality_result", {
                    "file": fname, "issues": issues, "flags": quality,
                    "index": i + 1, "total": total_files, "elapsed": round(elapsed, 1),
                    "icon": status_icon, "message": f"{fname}: {issues} quality flag(s) detected"
                })

            await conn.commit()
            yield sse("stage", {"stage": "quality", "status": "done",
                                "icon": "✅", "message": "Quality scan complete"})

            # ── Stage 3: Readiness Scoring ──
            logger.info(f"\n  🧮 Stage 3/3: Readiness Scoring")
            yield sse("stage", {"stage": "score", "status": "active",
                                "icon": "🧮", "message": "Stage 3/3: Clinical Auditor reasoning..."})
            
            yield sse("log", {"level": "info", "message": f"[Audit] Cross-referencing {total_files} files with {case_dict.get('payer_id', 'standard')} policy...", "icon": "🔍"})
            await asyncio.sleep(0.5)
            yield sse("log", {"level": "info", "message": f"[Audit] Lane: {case_dict['lane'].title()} | Rule Engine: FAISS Hybrid RAG", "icon": "🛰️"})

            # Re-fetch files with updated classifications
            cursor2 = await conn.execute("SELECT * FROM case_files WHERE case_id = ?", (case_id,))
            updated_files = [dict(row) for row in await cursor2.fetchall()]

            t0 = time.time()
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(calculate_readiness_score, updated_files, case_dict["lane"], case_dict.get("payer_id", "default"), case_dict),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("⚠️ Scoring timed out after 30s — using fast fallback")
                # Fallback: simple score based on doc count
                doc_types = {f.get("doc_type") for f in updated_files if f.get("doc_type")}
                fast_score = min(100, len(doc_types) * 20)
                fast_band = "GREEN" if fast_score >= 80 else "AMBER" if fast_score >= 50 else "RED"
                result = {"score": fast_score, "band": fast_band, "missing_items": [], "quality_issues": [], "consistency_flags": [], "citations": {}}
            except Exception as score_err:
                logger.error(f"❌ Scoring error: {score_err}", exc_info=True)
                doc_types = {f.get("doc_type") for f in updated_files if f.get("doc_type")}
                fast_score = min(100, len(doc_types) * 20)
                fast_band = "GREEN" if fast_score >= 80 else "AMBER" if fast_score >= 50 else "RED"
                result = {"score": fast_score, "band": fast_band, "missing_items": [], "quality_issues": [], "consistency_flags": [], "citations": {}}
            score_elapsed = time.time() - t0

            # Save analysis
            analysis_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO case_analysis (id, case_id, score, band, missing_items, quality_issues, consistency_flags, citations, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (analysis_id, case_id, result["score"], result["band"],
                  json.dumps(result["missing_items"]), json.dumps(result["quality_issues"]),
                  json.dumps(result["consistency_flags"]), json.dumps(result["citations"]),
                  datetime.now().isoformat()))

            # Update case — use 'in_review' which is in the CHECK constraint
            await conn.execute(
                "UPDATE cases SET readiness_score = ?, readiness_band = ?, status = 'in_review', updated_at = ? WHERE id = ?",
                (result["score"], result["band"], datetime.now().isoformat(), case_id)
            )
            await conn.commit()

            # Log audit
            await conn.execute(
                "INSERT INTO audit_events (id, case_id, action, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), case_id, "analysis_completed", str(result["score"]), datetime.now().isoformat())
            )
            await conn.commit()

            total_elapsed = time.time() - pipeline_start
            band_emoji = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}.get(result["band"], "⚪")

            logger.info(f"\n{'─'*60}")
            logger.info(f"  {band_emoji} SCORE: {result['score']}/100 → {result['band']} band")
            logger.info(f"  ⏱️  Total pipeline: {total_elapsed:.1f}s")
            logger.info(f"{'─'*60}\n")

            yield sse("stage", {"stage": "score", "status": "done",
                                "icon": "✅", "message": f"Score: {result['score']}/100"})
            yield sse("complete", {
                "score": result["score"], "band": result["band"],
                "missing_items": result["missing_items"],
                "quality_issues": result["quality_issues"],
                "consistency_flags": result["consistency_flags"],
                "elapsed": round(total_elapsed, 1),
                "icon": band_emoji, "message": f"Analysis complete: {result['score']}/100 → {result['band']}"
            })

        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}", exc_info=True)
            yield sse("error", {"icon": "❌", "message": f"Pipeline error: {str(e)}"})
        finally:
            await conn.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
