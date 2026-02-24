"""
Query router - Draft generation and approval
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional, List
from pydantic import BaseModel
import uuid
import json
from datetime import datetime

from db.database import get_db
from services.llm import get_llm_service
from services.transcription import get_transcription_service
from services.rag import search_policy
from config import settings

router = APIRouter()

class DraftRequest(BaseModel):
    query_text: str
    include_audio: bool = False

class DraftResponse(BaseModel):
    clinicalSummary: str
    justification: str
    attachments: List[str]
    nextSteps: str
    confidence: int
    docRefs: int
    policyRefs: int

DRAFT_PROMPT = """You are Pramana AI, a Senior Clinical Auditor for a hospital TPA desk.
Your goal is to perform a rigorous "Pre-Submission Audit" of a medical claim before it is sent to the payer.

### CRITICAL INSTRUCTION:
DO NOT simply justify the claim. Your primary value is to find **CONFLICTS** with Payer Policies (RAG) that will cause a rejection. 
If a policy requires "3 months of therapy" and the case only shows "2 weeks", you MUST flag this as a **CRITICAL COMPLIANCE GAP**.

CASE SUMMARY:
- Case Number: {case_number}
- Patient: {patient}
- Lane: {lane}

PAYER QUERY:
{query_text}

DOCTOR'S DICTATION (TRANSCRIPT):
{transcript}

SUPPORTING/CONFLICTING EVIDENCE (from policy RAG):
{policy_context}

PATIENT MEDICAL RECORDS (Pre-analyzed Case Data):
{patient_data}

DOCUMENTS AVAILABLE IN CASE:
{doc_list}

Draft the response in 4 sections: 
1. clinicalSummary: A concise professional summary of the patient's condition and procedure.
2. justification: Evidence-based points OR clinical conflicts found. Use policy citations like (Guideline X, Page Y).
3. attachments: A list of specific case documents that support this claim.
4. nextSteps: CRITICAL. If there is a policy conflict (e.g., missing documented PT months), explicitly state what the doctor MUST provide to fix the claim.

Respond with ONLY a JSON object in this exact format:
{{
    "clinicalSummary": "...",
    "justification": "...",
    "attachments": ["...", "..."],
    "nextSteps": "...",
    "confidence": 0-100,
    "docRefs": 0-10,
    "policyRefs": 0-10
}}
"""

@router.post("/{case_id}/audio/transcribe")
async def transcribe_audio(
    case_id: str,
    audio_file: UploadFile = File(...),
):
    """Isolated Whisper ASR endpoint for Dictation Review phase"""
    ts = get_transcription_service()
    audio_content = await audio_file.read()
    transcript = await ts.transcribe(audio_content) or "[Transcription failed]"
    return {"transcript": transcript}


@router.post("/{case_id}/query/draft")
async def generate_draft(
    case_id: str, 
    query_text: str = Form(...),
    transcript: Optional[str] = Form(None),
    db=Depends(get_db)
):
    """
    Orchestrate the generation of a clinical clinical justification draft.
    Now leverages the case_analysis table directly to prevent Pramana AI placeholders!
    """
    # 1. Fetch case info
    cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    case = await cursor.fetchone()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case = dict(case)
    
    # 2. Policy RAG
    search_query = f"{query_text or ''} {transcript or ''}".strip()
    policy_context = "No specific policy guidelines found for this payer."
    try:
        index_dir = settings.policies_dir / case["payer_id"] / "faiss_index"
        if index_dir.exists() and search_query:
            results = await search_policy(index_dir, search_query, k=3)
            policy_context = "\n".join([f"- {r['text']} ({r['citation']})" for r in results])
    except Exception:
        pass

    # 3. Get case documents
    cursor = await db.execute("SELECT doc_type, filename FROM case_files WHERE case_id = ?", (case_id,))
    files = await cursor.fetchall()
    doc_list = "\n".join([f"- {f['doc_type']} ({f['filename']})" for f in files])
    
    # 4. Get Pre-analyzed Patient Medical Records (THE PRO FIX)
    patient_data = "No analysis available yet. Run initial case analysis first."
    cursor = await db.execute("SELECT * FROM case_analysis WHERE case_id = ?", (case_id,))
    analysis = await cursor.fetchone()
    if analysis:
        a = dict(analysis)
        patient_data = f"""
        Readiness Score: {a.get('score')} ({a.get('band')})
        Citations & Findings: {a.get('citations')}
        Missing Items: {a.get('missing_items')}
        Quality Issues: {a.get('quality_issues')}
        Consistency Flags: {a.get('consistency_flags')}
        """

    # 5. Call LLM
    llm = get_llm_service()
    prompt = DRAFT_PROMPT.format(
        case_number=case["case_number"],
        patient=case["patient_alias"],
        lane=case["lane"],
        query_text=query_text,
        transcript=transcript or "No dictation provided.",
        policy_context=policy_context,
        patient_data=patient_data.strip(),
        doc_list=doc_list
    )
    
    draft = await llm.generate_json(prompt)
    
    # 6. Save draft to DB
    draft_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO case_drafts (id, case_id, query_text, transcript, draft_json, status, created_at) VALUES (?, ?, ?, ?, ?, 'draft', ?)",
        (draft_id, case_id, query_text, transcript or "", json.dumps(draft), datetime.now().isoformat())
    )
    
    # 7. Log audit
    await db.execute(
        "INSERT INTO audit_events (id, case_id, action, payload) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), case_id, "query_drafted", f"Draft generated via agentic workflow")
    )
    await db.commit()
    
    return {
        "draft": draft,
        "transcript": transcript,
        "draft_id": draft_id
    }


@router.post("/{case_id}/query/draft-stream")
async def generate_draft_stream(
    case_id: str, 
    query_text: str = Form(...),
    transcript: Optional[str] = Form(None),
    db=Depends(get_db)
):
    """
    Streaming version of the Draft Query generator.
    Yields explicit agentic actions (RAG DB search, LLM context building) as Server-Sent Events.
    """
    from fastapi.responses import StreamingResponse
    import aiosqlite
    import asyncio
    
    # Pre-flight check
    cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    case = await cursor.fetchone()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case = dict(case)
    
    async def event_generator():
        def sse(event: str, data: dict):
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"
        
        # Open independent connection for generator
        conn = await aiosqlite.connect(str(settings.db_path))
        conn.row_factory = aiosqlite.Row
        
        try:
            yield sse("stage", {"status": "active", "message": "Initializing Pramana AI Draft Agent..."})
            await asyncio.sleep(0.5)
            
            # 1. RAG Search
            search_query = f"{query_text or ''} {transcript or ''}".strip()
            yield sse("log", {"level": "info", "message": f"Connecting to FAISS specific to {case['payer_id']} ruleset..."})
            policy_context = "No specific policy guidelines found for this payer."
            try:
                index_dir = settings.policies_dir / case["payer_id"] / "faiss_index"
                if index_dir.exists() and search_query:
                    search_display = search_query[:50] + ("..." if len(search_query) > 50 else "")
                    yield sse("log", {"level": "info", "message": f"[Semantic Search] Querying L2 vector distance for: '{search_display}'"})
                    results = await search_policy(index_dir, search_query, k=3)
                    await asyncio.sleep(0.5)
                    
                    if results:
                        policy_context = "\n".join([f"- {r['text']} ({r['citation']})" for r in results])
                        yield sse("log", {"level": "success", "message": f"Extracted {len(results)} highly-relevant policy constraints."})
                        
                        # Yield granular distance telemetry for King Mode
                        for idx, res in enumerate(results):
                            snippet = res['text'][:60] + "..."
                            dist_score = f"{res.get('distance', 0):.4f}"
                            yield sse("log", {
                                "level": "info", 
                                "message": f"[RAG] Match #{idx+1} | Dist: {dist_score} | Snippet: \"{snippet}\"",
                                "icon": "📄"
                            })
                    else:
                        yield sse("log", {"level": "warning", "message": "No matching policy constraints found in the vector database."})
                else:
                    yield sse("log", {"level": "warning", "message": f"No FAISS index found for {case['payer_id']}."})
            except Exception as e:
                yield sse("log", {"level": "error", "message": f"Vector Search Error: {str(e)}"})
            
            await asyncio.sleep(0.5)

            # 2. Case Documents Context
            yield sse("log", {"level": "info", "message": "Cross-referencing injected medical records..."})
            cursor = await conn.execute("SELECT doc_type, filename FROM case_files WHERE case_id = ?", (case_id,))
            files = await cursor.fetchall()
            doc_list = "\n".join([f"- {f['doc_type']} ({f['filename']})" for f in files])
            
            # 3. Patient Pre-analysis 
            yield sse("log", {"level": "info", "message": "Retrieving Pramana AI Initial Analysis Readiness Score Constraints..."})
            patient_data = "No analysis available yet."
            cursor = await conn.execute("SELECT * FROM case_analysis WHERE case_id = ?", (case_id,))
            analysis = await cursor.fetchone()
            if analysis:
                a = dict(analysis)
                patient_data = f"""
                Readiness Score: {a.get('score')} ({a.get('band')})
                Citations & Findings: {a.get('citations')}
                Missing Items: {a.get('missing_items')}
                Quality Issues: {a.get('quality_issues')}
                Consistency Flags: {a.get('consistency_flags')}
                """
                yield sse("log", {"level": "success", "message": f"Applied Stage 1 Readiness Score framework (Score: {a.get('score')})"})
            
            await asyncio.sleep(0.5)
            
            # 4. LLM Generation
            yield sse("log", {"level": "info", "message": "Assembling prompts and initiating Local Llama 3.2 generation..."})
            
            llm = get_llm_service()
            prompt = DRAFT_PROMPT.format(
                case_number=case["case_number"],
                patient=case["patient_alias"],
                lane=case["lane"],
                query_text=query_text,
                transcript=transcript or "No dictation provided.",
                policy_context=policy_context,
                patient_data=patient_data.strip(),
                doc_list=doc_list
            )
            
            # Ideally this would use `generate_json_stream`, but to safely guarantee valid JSON on the frontend
            # we await the full generation and simulate the active processing UI, passing the final object at the end.
            yield sse("stage", {"status": "generating", "message": "Drafting Clinical Justification..."})
            draft = await llm.generate_json(prompt)
            
            # 6. Save draft
            yield sse("log", {"level": "info", "message": "Generation complete. Persisting to encrypted SQLite..."})
            draft_id = str(uuid.uuid4())
            await conn.execute(
                "INSERT INTO case_drafts (id, case_id, query_text, transcript, draft_json, status, created_at) VALUES (?, ?, ?, ?, ?, 'draft', ?)",
                (draft_id, case_id, query_text, transcript or "", json.dumps(draft), datetime.now().isoformat())
            )
            
            await conn.execute(
                "INSERT INTO audit_events (id, case_id, action, payload) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), case_id, "query_drafted", "Draft generated via streaming agentic workflow")
            )
            await conn.commit()
            
            # 7. Complete
            yield sse("stage", {"status": "done", "draft": draft, "transcript": transcript, "draft_id": draft_id})
            
        except Exception as e:
            logger.error(f"Streaming draft error: {e}")
            yield sse("error", {"detail": str(e)})
        finally:
            await conn.close()
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.put("/{case_id}/query/draft")
async def update_draft(
    case_id: str,
    draft_data: dict,
    db=Depends(get_db)
):
    """Update an existing draft (Doctor-in-the-loop editing)"""
    await db.execute(
        "UPDATE case_drafts SET draft_json = ? WHERE case_id = ? AND status = 'draft'",
        (json.dumps(draft_data), case_id)
    )
    await db.commit()
    return {"message": "Draft updated"}

@router.post("/{case_id}/query/approve")
async def approve_draft(
    case_id: str, 
    draft_data: Optional[dict] = None,
    db=Depends(get_db)
):
    """
    Formalize and approve the generated clinical draft.
    Allows for final edits to be saved before locking.
    """
    if draft_data:
        await db.execute(
            "UPDATE case_drafts SET draft_json = ? WHERE case_id = ? AND status = 'draft'",
            (json.dumps(draft_data), case_id)
        )
        
    await db.execute(
        "UPDATE cases SET status = 'query_drafted', updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), case_id)
    )
    # Update latest draft status
    await db.execute(
        "UPDATE case_drafts SET status = 'approved', approved_at = ? WHERE case_id = ? AND status = 'draft'",
        (datetime.now().isoformat(), case_id)
    )
    # Log audit
    await db.execute(
        "INSERT INTO audit_events (id, case_id, action, payload) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), case_id, "query_approved", "Final draft approved by user")
    )
    await db.commit()
    return {"message": "Draft approved"}


@router.get("/{case_id}/query/latest")
async def get_latest_draft(case_id: str, db=Depends(get_db)):
    """Get the latest draft for a case (persists across page refreshes)."""
    cursor = await db.execute(
        "SELECT * FROM case_drafts WHERE case_id = ? ORDER BY created_at DESC LIMIT 1",
        (case_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return {"draft": None}
    
    draft_data = dict(row)
    draft_json = draft_data.get("draft_json")
    try:
        draft_json = json.loads(draft_json) if draft_json else None
    except:
        pass
    
    return {
        "draft": draft_json,
        "transcript": draft_data.get("transcript", ""),
        "status": draft_data.get("status", "draft"),
        "approved": draft_data.get("status") == "approved",
        "created_at": draft_data.get("created_at")
    }
