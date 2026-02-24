# TRD — **Pramana AI** (Offline Claim Readiness Copilot)

**Build stack:** Tauri (Rust shell) + SvelteKit/TypeScript UI + Python/FastAPI sidecar + Ollama/vLLM (local models) + FAISS (local policy RAG) + SQLite (state/audit) + MediaPipe (image quality/crop) + PDF toolchain (pypdf/pikepdf)

---

## 0) Objectives

### Technical goals

* Fully offline, air-gapped capable (no outbound network by default)
* Deterministic exports: Evidence Pack PDF + Index + Checklist + Reply PDF
* Human-in-the-loop gating for any AI-generated reply
* Strong auditability: every action traceable with file hashes

### Non-goals (v1)

* No insurer portal automation
* No HIS integration required
* No promise of “no denials”; output is “risk flags + evidence gaps + citations”

---

## 1) System architecture

### 1.1 High-level

**Desktop App (Tauri)**

* Hosts UI (SvelteKit) in OS WebView
* Starts & supervises local Python sidecar
* Provides secure IPC between UI and sidecar
* Manages file system permissions and app updates

**Local Sidecar (FastAPI)**

* Document ingest + classification
* Scan quality checks + sticker verification pipeline
* Policy PDF indexing + retrieval (FAISS)
* LLM orchestration (Ollama/vLLM) for extraction/drafting
* PDF merging + index generation
* SQLite persistence and audit logging

**Model Runtime**

* Ollama (default) for Pramana AI multimodal + text
* Optional vLLM for GPU nodes (pilot hardening)

---

## 2) Deployment topology

### 2.1 Supported install modes

* **Mode A: Operator laptop (Phase 0)**: app runs on your device; hospital provides case folders
* **Mode B: Single billing PC (Phase 1)**: installed on one machine in RCM/TPA room
* **Mode C: Internal VM/Workstation (Phase 2)**: hospital IT deploys inside intranet, still offline

### 2.2 OS support

* Windows 10/11 (primary)
* macOS (secondary)
* Linux (optional)

---

## 3) Security requirements

### 3.1 Network policy

* Default: **no outbound network**
* Allow-list only (optional): update checks (disabled in hospital mode)
* UI must display an “Offline Verified” indicator when network is disabled

### 3.2 Data handling

* Primary storage: local filesystem + SQLite metadata
* No telemetry by default
* Optional encrypted store:

  * encrypt SQLite + sensitive caches using OS keychain derived key

### 3.3 Roles & permissions

* Roles: `admin`, `tpa`, `doctor`, `viewer`
* Enforced on sidecar endpoints (JWT stored locally)
* Audit events include user id + role at event time

### 3.4 Audit trail

* Append-only audit events:

  * hash of input files (SHA-256)
  * hash of exported PDFs (SHA-256)
  * model id/version + template version + policy index version
  * timestamps, actor, action, parameters

---

## 4) Data model

### 4.1 Local filesystem layout

Configurable `DATA_ROOT/`:

```
DATA_ROOT/
  cases/
    <case_id>/
      raw/                 # original imported docs (optional copy)
      working/             # normalized/cropped images, temp text extracts
      exports/             # evidence pack, reply PDFs, checklists
      cache/               # OCR outputs, embeddings, thumbnails
  policies/
    <payer_id>/
      pdfs/
      faiss_index/
      metadata.json
  templates/
    payer_templates.json
    hospital_overrides.json
  logs/
    app.log
  db/
    aegis.sqlite
```

### 4.2 SQLite schema (v1)

**users**

* `id TEXT PK`
* `name TEXT`
* `role TEXT`
* `created_at DATETIME`

**cases**

* `id TEXT PK`
* `lane TEXT` (cardio|ortho)
* `payer_id TEXT`
* `tpa_id TEXT NULL`
* `status TEXT`
* `created_at DATETIME`
* `updated_at DATETIME`

**case_files**

* `id TEXT PK`
* `case_id TEXT FK`
* `path TEXT`
* `sha256 TEXT`
* `mime TEXT`
* `doc_type TEXT NULL`
* `doc_type_conf REAL`
* `quality_flags_json TEXT` (JSON)
* `created_at DATETIME`

**case_outputs**

* `id TEXT PK`
* `case_id TEXT FK`
* `type TEXT` (evidence_pack|reply_pdf|checklist|audit_snapshot|batch_report)
* `path TEXT`
* `sha256 TEXT`
* `meta_json TEXT`
* `created_at DATETIME`

**policies**

* `id TEXT PK` (payer_id)
* `version TEXT`
* `source_files_json TEXT`
* `index_path TEXT`
* `created_at DATETIME`

**templates**

* `id TEXT PK` (payer_id + lane)
* `version TEXT`
* `template_json TEXT`
* `updated_at DATETIME`

**audit_events**

* `id TEXT PK`
* `case_id TEXT NULL`
* `user_id TEXT`
* `action TEXT`
* `payload_json TEXT`
* `created_at DATETIME`

Indexes:

* `cases(payer_id, lane, status)`
* `case_files(case_id)`
* `audit_events(case_id, created_at)`

---

## 5) Core services (sidecar)

### 5.1 Ingest service

* Create case
* Import folder (PDF/images/audio)
* Normalize filenames and persist `case_files`

### 5.2 Doc classification service

* For each file:

  * extract lightweight features:

    * PDF text snippets (if digital)
    * rendered thumbnails (first page)
    * OCR text (when needed, local)
  * run Pramana AI classification prompt OR heuristic fallback
* Save `doc_type`, `doc_type_conf`

Doc types (v1):

* discharge_summary, admission_note, progress_note, ot_note,
* implant_sticker, pharmacy_bill, icu_chart, lab_report, radiology_report, other

### 5.3 Scan quality service

* Blur detection:

  * Laplacian variance or MediaPipe-based quality
* Low resolution:

  * pixel dims threshold
* Skew/crop risk:

  * detect extreme margins / rotated text blocks (heuristic)
* Outputs `quality_flags_json`

### 5.4 Sticker verification service (Cardio/Ortho)

Pipeline:

1. Detect sticker region (MediaPipe / contour heuristics)
2. Crop + de-skew + enhance (no aggressive beautification)
3. Quality score
4. OCR serial/lot (local OCR)
5. Search for extracted serial in:

   * pharmacy_bill extracted text
   * ot_note extracted text
6. Emit status:

   * VERIFIED / NOT_FOUND / UNREADABLE / NO_STICKER_DETECTED
7. Persist result in case analysis JSON and influence readiness score

### 5.5 Policy indexing + retrieval (FAISS)

* Ingest payer PDF(s)
* Chunking:

  * page-aware, 300–800 tokens with overlap
* Embedding:

  * local embedding model (small, CPU-friendly) or Pramana AI text embeddings if available
* Store:

  * FAISS index + chunk metadata (payer_id, pdf_name, page_num, chunk_text)
* Retrieval API returns:

  * topK chunks + citations (pdf + page + chunk id)

### 5.6 Reasoning + drafting (LLM orchestrator)

* Single orchestration layer for:

  * evidence checklist generation
  * clinical consistency flags
  * query reply drafting
* Constraints:

  * must cite case doc page refs when used
  * must cite policy chunks when used
  * outputs in JSON schema to reduce hallucination

---

## 6) APIs (FastAPI)

Base: `http://127.0.0.1:<port>/api`

### 6.1 Auth

* `POST /auth/login` → `{token}`
* local-only; admin seeds first user

### 6.2 Cases

* `POST /cases` create case
* `GET /cases?lane=&payer_id=&status=&q=`
* `GET /cases/{id}`
* `PATCH /cases/{id}` status updates
* `POST /cases/{id}/import-folder` (path selection via Tauri FS dialog)
* `POST /cases/{id}/import-files`

### 6.3 Analysis

* `POST /cases/{id}/analyze`

  * runs classification + quality + sticker verify + checklist + score
* `GET /cases/{id}/analysis` returns:

  * score, flags, checklist, citations

### 6.4 Query drafting

* `POST /cases/{id}/query/draft`

  * inputs: query_text, optional audio_file_id
* `POST /cases/{id}/query/approve`

  * persists approval event, generates reply PDF
* `GET /cases/{id}/query/status`

### 6.5 Evidence pack

* `POST /cases/{id}/pack/generate`

  * inputs: payer_template_id, ordering, include_checklist
* `GET /cases/{id}/exports`

### 6.6 Policies

* `POST /policies/{payer_id}/upload`
* `POST /policies/{payer_id}/index`
* `GET /policies/{payer_id}/search?q=...&k=5`

### 6.7 Templates

* `GET /templates?payer_id=&lane=`
* `PUT /templates/{id}` (admin only)
* `GET /templates/{id}/version`

### 6.8 Batch audit

* `POST /batch/import-folder`
* `POST /batch/run`
* `GET /batch/{job_id}`
* `POST /batch/{job_id}/export`

All endpoints must:

* validate role
* log audit event

---

## 7) IPC & process supervision (Tauri)

### 7.1 Sidecar lifecycle

* On app start:

  * allocate port
  * spawn python sidecar
  * wait for health: `GET /health`
* On app exit:

  * graceful shutdown endpoint or kill process

### 7.2 File selection

* UI cannot read arbitrary disk paths directly
* Use Tauri file dialog:

  * user selects folder
  * Tauri passes canonical path to sidecar
  * sidecar reads under allowlisted paths

### 7.3 Updates

* Disabled by default in “Hospital Mode”
* Enabled in “Dev Mode” with signature verification

---

## 8) UI technical spec (SvelteKit)

### 8.1 Routes

* `/login`
* `/cases`
* `/cases/:id` (Workbench)
* `/cases/:id/query`
* `/templates`
* `/policies`
* `/batch`
* `/settings`

### 8.2 State model

* Local store:

  * auth token
  * active case
  * analysis cache
* All critical data persisted in SQLite via sidecar

### 8.3 Workbench layout

Left: files list

* file type, flags, confidence, override control

Center: Readiness panel

* score, Green/Amber/Red
* checklist with owner + severity
* risk flags with “why” and “fix”

Right: Actions

* Analyze, Generate Pack, Draft Reply, Export

---

## 9) Scoring engine (deterministic + configurable)

### 9.1 Template-driven scoring

Weights stored in template JSON:

* required docs presence
* scan quality thresholds
* sticker verification
* ICU justification evidence
* consistency checks

### 9.2 Score output schema

```
{
  "score": 0-100,
  "band": "GREEN|AMBER|RED",
  "missing": [{ "item": "...", "owner": "...", "severity": 1-5, "impact": 0-20 }],
  "quality": [{ "file_id": "...", "flag": "...", "severity": 1-5 }],
  "consistency": [{ "type": "...", "severity": 1-5, "evidence_links": [...] }],
  "citations": { "policy": [...], "case_docs": [...] }
}
```

---

## 10) Prompting & output constraints

### 10.1 JSON-first prompting

All LLM calls must request strict JSON output:

* classification
* checklist generation
* drafting reply
* consistency flagging

### 10.2 Grounding rules

* Any policy assertion must cite retrieved chunk ids
* Any clinical evidence claim must point to case doc page references or mark as “not found”

### 10.3 Safety guardrails

* Always include disclaimer header in drafts: “Draft for review”
* Enforce manual approval before export

---

## 11) OCR & PDF processing

### 11.1 PDF text extraction

* If digital: extract text via pypdf
* If scanned: render pages to images + OCR selected pages only

### 11.2 PDF merging & indexing

* Normalize page size/orientation (best effort)
* Generate cover page + index with accurate page ranges
* Merge in payer order; attach checklist at end optionally

---

## 12) Performance targets

### 12.1 Single case (typical)

* Import 30–60 pages: < 15s
* Analyze:

  * classification + quality: < 30–60s CPU
  * sticker verify: < 15–30s
  * score + checklist: < 20–40s
* Evidence pack generation: < 60–90s CPU

### 12.2 Batch mode

* 50 cases overnight on CPU without crash
* Resume from partial progress

---

## 13) Logging & diagnostics

* Logs: JSON lines + rotation
* Per-case trace id
* “Export debug bundle”:

  * config (redacted)
  * logs (selected)
  * template version
  * model version
  * index metadata

---

## 14) Testing strategy

### 14.1 Unit tests (Python)

* template parsing
* scoring math
* OCR extraction sanity
* pack builder page range correctness
* FAISS indexing/retrieval determinism

### 14.2 Integration tests

* end-to-end: import → analyze → pack generate → export
* offline validation: ensure no outbound network calls (mock net)
* permission tests for roles

### 14.3 Golden test dataset

* “Sabotaged folder” set:

  * blurry sticker
  * identity mismatch
  * missing discharge summary
  * ICU query requiring justification

Expected outputs:

* specific flags, score band, export files existence

---

## 15) Build & packaging

### 15.1 Dev workflow

* `ui/` SvelteKit
* `desktop/` Tauri config
* `sidecar/` Python FastAPI
* `models/` scripts for pulling Ollama model

### 15.2 Packaging

* Tauri bundling for OS installer
* Python sidecar packaged as:

  * embedded venv or PyInstaller onefile (preferred: one-dir for reliability)
* Include a “Model Setup” screen:

  * detect Ollama installed
  * detect model present
  * offline model import supported (file path)

### 15.3 Config

* `config.json` local:

  * data root path
  * hospital mode toggle
  * model runtime config (ollama base url)
  * OCR toggle + quality thresholds
  * logging level

---

## 16) Acceptance criteria (release gate)

* Works with Wi-Fi disabled, confirmed by:

  * “Offline Verified” indicator
  * no outbound connections during test run
* Generates:

  * evidence pack PDF with correct index
  * reply PDF only after approval
  * checklist PDF
* Sticker verification produces Verified/Unreadable states with actionable guidance
* Audit log shows complete timeline + hashes for all exports
* Batch audit exports PDF+CSV for 50 cases

---

## 17) Implementation backlog (v1 order)

1. Case ingest + SQLite + audit logging
2. PDF merge + index + checklist export
3. Doc classification + manual override
4. Scan quality flags
5. Template engine + readiness scoring
6. Policy ingest + FAISS index + citation search
7. Consistency auditor (rule-first, then LLM assist)
8. Voice dictation + draft/review/approve
9. Sticker pipeline (MediaPipe + OCR + bill match)
10. Batch audit job system + reports

---
