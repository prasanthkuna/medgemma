# PRD — **Pramana AI**

**Offline Claim Readiness Copilot** (same product for Google Pramana AI hackathon + Hyderabad hospital pilots)
**Build stack:** **Tauri (desktop)** + **SvelteKit (UI, TS)** + **Python/FastAPI sidecar** + **Ollama/vLLM (local models)** + **FAISS (local RAG)** + **SQLite (audit/state)** + **MediaPipe (scan quality)**

---

## 1) Product summary

**Pramana AI** is an **offline-first desktop app** that helps hospitals reduce avoidable claim queries/denials by ensuring **claim evidence completeness + consistency** *before submission*.

**Inputs**

* Case folder containing: PDFs (scanned/typed), images (stickers/bills), optional audio dictations
* Payer/policy PDFs (for local RAG)

**Outputs**

* **Clean-Claim Readiness Score (0–100)**
* **Missing / Weak Evidence Checklist** (role-mapped: TPA desk / doctor / nurse / stores)
* **Evidence Pack PDF** (payer-ordered, merged, indexed)
* **Query Reply Draft PDF** (voice → transcript → payer-ready text), **approval required**
* **Local audit log** (immutable event history + file hashes)

**Key constraint**

* **Air-gapped capable**: no network required, no PHI sent to cloud.

---

## 2) Target users

1. **TPA Desk Executive**: build packs, clear queries fast
2. **RCM/Billing Manager**: reduce rework, improve first-pass clean claims
3. **Resident/Consultant Doctor**: dictate justifications quickly
4. **CFO/COO**: improve cashflow + reduce avoidable leakage with low risk
5. **IT/CISO**: minimal install footprint, offline/on-prem, auditable

---

## 3) Primary use-cases

### UC1: “Rejected Claims Autopsy” (No install resistance path)

* Hospital shares last month’s **50 rejected/queried** IPD cases as folders
* Aegis runs locally on operator laptop
* Output: **Failure-mode report + preventable checklists + templates**

### UC2: “Live Clean-Claim Lane” (1 machine inside billing room)

* Daily exports (folder dumps) from Cardio/Ortho lane
* Aegis produces evidence packs + query drafts + weekly summary report

### UC3: “Doctor Dictation Justification”

* Query arrives: “justify ICU day 3”
* Doctor dictates; Aegis outputs payer-ready justification draft + attachments list

---

## 4) Scope (v1 “Golden Wedge”)

**Department lanes:** **Cardiology + Orthopedics IPD** only
**Claim types:** implant/stent cases, ICU/LOS sensitive cases
**Non-goals (v1)**

* No portal automation / auto-submit
* No HIS integration required
* No “predict outcome” guarantee; only **risk flags + evidence requirements**

---

## 5) Product differentiators (USPs)

1. **Clinical Consistency Auditor** (billed vs evidence mismatch)
2. **Sticker & Scan Verification** (blur/quality + OCR serial + bill match)
3. **Polyglot Dictation → Formal Payer English** (approval gated)
4. **Evidence Pack Builder** (payer-ordered + indexed)
5. **Policy RAG with strict citations** (offline)

---

## 6) User journeys

### Journey A — TPA Desk: Build evidence pack

1. Create/select case
2. Drag-drop case folder
3. Auto doc-type detection + scan quality flags
4. Choose payer template + lane (Cardio/Ortho)
5. Review Readiness Score + checklist
6. Click **Generate Evidence Pack**
7. Export pack PDF + checklist + audit snapshot

### Journey B — Doctor: Voice justification

1. Case shows “Query pending”
2. Doctor records voice (in-app)
3. Transcribe (MedASR) → draft (Pramana AI)
4. Review → approve
5. Export reply PDF + attachments checklist

### Journey C — RCM/CFO: Batch audit

1. Import multiple case folders
2. Run batch analysis
3. Export report (PDF + CSV): root causes, missing-doc frequency, readiness trend

---

## 7) Functional requirements

### 7.1 Case Management

* Create case with:

  * Case ID (hospital internal) + optional patient alias
  * Lane (Cardio/Ortho)
  * Payer/TPA
  * Status: New / In Review / Pack Generated / Query Drafted / Closed
* Local filesystem reference for documents (no forced duplication)

**Acceptance**

* Create case < 3 seconds
* Case loads reliably with 50+ docs

---

### 7.2 Document Ingest

Supported formats:

* PDF, JPG, PNG (DOCX optional later)

Features:

* Folder import (bulk)
* Single-file add/remove
* Duplicate detection (hash-based)

**Acceptance**

* Import 100MB folder without crash
* No network calls during ingest

---

### 7.3 Document Type Classification (offline)

Classify into types:

* Discharge summary
* Admission note
* Progress notes
* OT note
* Implant/stent sticker
* Pharmacy bill
* ICU chart/vitals summary (basic)
* Lab reports
* Radiology report
* ID/insurance card (optional)

Output:

* Doc type + confidence (Low/Med/High)
* Manual override by user

**Acceptance**

* Shows confidence + allows override
* Overrides persist to improve future heuristics (local)

---

### 7.4 Scan Quality & Integrity Checks

* Blur detection
* Low DPI warning
* Cropping/sides cut off warning (heuristic)
* Wrong orientation
* “Mixed patient” suspicion:

  * mismatch in visible names/IDs when extractable
  * different MRN format pattern

**Acceptance**

* Flags appear within 30 seconds for typical case
* False positives can be dismissed with reason (logged)

---

### 7.5 Sticker & Scan Verification (Cardio/Ortho)

Inputs:

* Sticker image(s)
* Pharmacy bill PDF/image
* OT note PDF/image

Processing:

* MediaPipe crop/rectify sticker region
* Blur score + readability score
* OCR serial/lot (best-effort)
* Cross-check: serial present in pharmacy bill text OR OT note mention

Outputs:

* Status: Verified / Not Found / Unreadable Scan
* Evidence link: “Serial found on page X of bill”

**Acceptance**

* For readable sticker, serial extracted and shown
* If unreadable, actionable fix text shown (“re-scan sticker close-up”)

---

### 7.6 Payer Templates + Checklist Engine

Local template library:

* Per payer + lane required documents list
* Ordering for pack
* Common query types → required evidence

Hospital override UI:

* Add/remove required docs
* Rename doc categories
* Configure “minimum evidence” for ICU/LOS

Outputs:

* Missing/weak evidence checklist with owner role (TPA/Doctor/Nurse/Stores)
* Readiness score impact shown per missing item

**Acceptance**

* Admin-only edit
* Export checklist PDF

---

### 7.7 Policy RAG (offline, citations required)

* Upload payer policy PDFs
* Chunk + index in FAISS
* Retrieval shown with citations (doc name + chunk)
* Any recommendation that uses policy must show citations

**Acceptance**

* No “policy says X” without citation
* Works offline; index persists locally

---

### 7.8 Clinical Consistency Auditor (agentic, but safe)

Checks (v1):

* Procedure billed (from bill/summary) vs missing implant evidence
* ICU days count vs missing vitals/notes evidence
* Length of stay vs missing progress notes/discharge rationale
* “Required doc for lane” missing but claim marked “ready”

Outputs:

* **Risk Flags** with:

  * What mismatch
  * What evidence missing
  * Where it should exist
  * Suggested remediation steps

**Acceptance**

* Output is phrased as “risk/needs evidence”, not deterministic denial prediction
* Each flag links to relevant doc pages if available

---

### 7.9 Query Reply Copilot (voice + text, approval gated)

Inputs:

* Query text (paste)
* Case documents
* Optional audio dictation

Outputs:

* Draft reply with sections:

  * Clinical summary
  * Justification points
  * Referenced attachments list
  * “If missing evidence” callouts

Workflow:

* Draft → Review → Approve → Export (mandatory)

Safety:

* Low confidence → requires additional human confirmation checkbox
* Shows citations to case docs (page refs) when possible

**Acceptance**

* Cannot export “final” without approval
* Audit logs capture approver + timestamp

---

### 7.10 Evidence Pack Builder (PDF)

* Cover page (case meta)
* Index with doc types + page ranges
* Merge documents in payer-defined order
* Optional watermark: Confidential/Draft
* Export artifacts:

  * Evidence Pack PDF
  * Attachments checklist PDF
  * Audit snapshot PDF

**Acceptance**

* Index page ranges correct
* Pack generation for 60 pages: < 90 seconds typical CPU

---

### 7.11 Batch Audit Mode

* Import multiple cases
* Produce analytics:

  * Top missing doc categories
  * Top scan quality issues
  * Top query drivers (from query text classification)
  * Readiness score distribution
* Exports:

  * PDF report + CSV

**Acceptance**

* Batch of 50 cases completes without crash
* Export completes < 2 minutes for typical sets

---

### 7.12 Audit Trail & Roles

Roles:

* Admin, TPA, Doctor, Viewer

Audit events:

* Import, classify override, flag dismiss, draft, approve, export
* File hashes (SHA-256)
* Model version + template version + policy index version

**Acceptance**

* “Audit” tab per case shows full timeline
* Export audit snapshot possible

---

## 8) Readiness Score (v1 rubric)

Score components (configurable per payer/lane):

* Required docs present (40)
* Scan quality OK (20)
* Sticker verification (20) [lane-specific]
* ICU/LOS evidence present (10) [if applicable]
* Consistency checks pass (10)

Output:

* Score + Green/Amber/Red label
* Top 5 actions to improve score

---

## 9) UI screens (v1)

1. **Case List**

* search/filter by payer, lane, status, score band

2. **Case Workbench**

* left: docs list + type + flags + confidence
* center: score + checklist + risk flags
* right: actions (pack, draft reply, exports)

3. **Query Reply**

* query input + audio record + draft + approval controls

4. **Templates**

* payer/lane template editor + overrides

5. **Policy Library**

* upload PDFs + search + citations viewer

6. **Batch Audit**

* import cases + results + export report

7. **Settings**

* model/runtime config + storage paths + roles

---

## 10) Technical requirements

### Desktop

* Tauri app communicates with local FastAPI over localhost
* No outbound network calls unless user explicitly enables “update check”

### Model runtime

* Default: Ollama local
* Optional: vLLM for GPU setups
* Support CPU fallback with acceptable latency

### Storage

* SQLite: users, cases metadata, audit events, templates versions
* FAISS: policy index
* Files stored on disk (configurable directory)

### Security

* Local-only by default
* Optional encryption for stored outputs/cache
* No telemetry by default
* Admin can “wipe” case and all artifacts

---

## 11) Deployment strategy for hospital reality (no-install resistance)

**Phase 0 (demo/audit):** runs on your laptop; hospital shares de-identified folders
**Phase 1 (pilot):** install on **one dedicated billing/RCM machine**
**Phase 2 (hardening):** hospital IT deploys on internal PC/VM (still offline)

Installer requirements:

* Windows signed installer (for smoother IT acceptance)
* Portable mode (optional) for quick pilots

---

## 12) Metrics (local, exportable)

Process KPIs:

* Readiness score trend
* Missing docs per case
* Sticker verification success rate
* Draft-to-approve time
* Packs generated count
* “Issues caught pre-export” count (proxy for queries deflected)

Outcome KPIs (tracked by hospital externally initially):

* Query rate per 100 claims (lane)
* Denial rate (lane)
* Pending aging

---

## 13) Hackathon packaging (same product)

* **Kaggle notebook**: core pipeline (RAG + scoring + citations) reproducible
* **Demo video**: Wi-Fi off + sabotaged folder + offline reasoning + exports
* “Hackathon Mode” toggle: loads demo data + hides PHI fields

---

## 14) Milestones

### M1 — MVP (7–10 days)

* Case ingest, doc classification (basic), checklist, pack builder, local audit log

### M2 — Hackathon-ready (14–18 days)

* Policy RAG with citations
* Sabotaged dataset demo flow
* Offline demo video

### M3 — Pilot-ready (24–30 days)

* Sticker verification (blur + OCR + bill match)
* Voice dictation + approval workflow
* Batch audit report exports

---

## 15) Risks & mitigations

* **Policy ambiguity** → citations-only + “risk flags” language
* **Scan/OCR variability** → quality scoring + rescan guidance
* **Doctor adoption** → voice-first, <60s flow, minimal clicks
* **Hardware constraints** → smaller model config + CPU mode
* **Hospital install resistance** → Phase 0 audit on your laptop, Phase 1 single machine

---

## 16) Acceptance checklist (pilot entry)

* Runs offline for 2 hours with Wi-Fi disabled
* Produces payer-ordered pack with index
* Flags at least 3 sabotage cases:

  * blurry sticker
  * mixed patient doc
  * missing ICU justification evidence
* Generates a query draft and forces approval before export
* Exports batch audit report for 50 cases

---
