## Screens count (pro)

**9 primary screens + 12 system dialogs/modals** (keeps it enterprise-grade but minimal).

Primary screens:

1. Login
2. Case List
3. Case Workbench
4. Evidence Pack Builder
5. Query Reply (Voice → Draft → Approve)
6. Policy Library (RAG + citations)
7. Templates (Payer/Lane rules + overrides)
8. Batch Audit (Imports + analytics + reports)
9. Settings & Admin (Users/Roles, storage, runtime)

System dialogs/modals (core):

* New Case, Import Folder, File Preview, Classify Override, Flag Dismiss Reason, Add Missing Doc Task, Export Options, Approval Confirm, Policy Upload, Template Version Diff, Offline/Network Status, Diagnostics Bundle.

---

# UX Doc — **Pramana AI** (Offline Claim Readiness Copilot)

## 1) UX goals

* **Zero IT friction:** works offline, folder-in → pack-out.
* **TPA-first speed:** everything reachable in **≤2 clicks** from Case Workbench.
* **Doctor-friendly:** voice-first, <60 seconds to produce a draft.
* **CFO-friendly:** batch audit report and weekly lane summary.
* **CISO-friendly:** clear “offline verified”, no cloud, audit trail visible.

---

## 2) Personas & permissions

### Roles

* **Admin:** templates, policies, users, settings, diagnostics.
* **TPA:** create/import cases, run analysis, build packs, draft replies, export.
* **Doctor:** record audio, review/edit draft, approve (optional), export reply.
* **Viewer:** read-only dashboards/reports.

### Permission highlights

* Only Admin edits **Templates / Policy Library**.
* Only TPA/Doctor can **Approve**.
* Viewer cannot export packs or replies.

---

## 3) Navigation & information architecture

**Left rail (persistent):**

* Cases
* Batch Audit
* Policies
* Templates
* Reports (optional tab inside Batch Audit)
* Settings

**Top bar (persistent):**

* Offline Verified indicator (green/amber)
* Active Lane: Cardio / Ortho
* Search (case id / payer / tag)
* Quick Actions: New Case, Import Folder
* User menu (role, logout)

---

## 4) Core workflows (step-by-step)

### Flow A — “One case → evidence pack” (TPA)

1. **New Case** → choose Lane + Payer
2. **Import Folder** (drop/choose)
3. Auto **Analyze** (or manual)
4. Review **Readiness Score** + Missing Checklist
5. Fix items (upload/add tasks)
6. **Generate Evidence Pack**
7. Export PDF pack + checklist + audit snapshot

Success metric: TPA can generate a payer-ordered pack in **<3 minutes** after import.

---

### Flow B — “Query reply via voice” (Doctor + TPA)

1. TPA pastes query text into **Query Reply** screen
2. Doctor taps **Record** (or uploads audio)
3. App shows transcript + structured draft
4. Doctor edits (optional)
5. **Approve** → export Reply PDF + attachments checklist

Success metric: draft in **<60 seconds**, export in **<2 minutes**.

---

### Flow C — “Denied claims autopsy” (RCM/CFO)

1. Batch Audit → import folder containing multiple cases
2. Run batch → “failure modes” & readiness distribution
3. Export PDF report + CSV

Success metric: produces a credible report without integration.

---

## 5) Screen-by-screen UX spec

## Screen 1 — Login

**Goal:** quick access without enterprise auth friction.

**Components**

* Username
* PIN/password (local)
* “Hospital Mode” banner (offline-only, no updates)
* “Demo/Hackathon Mode” toggle (loads demo dataset)

**States**

* First-run: “Create Admin”
* Locked out after N attempts

---

## Screen 2 — Case List (Home)

**Goal:** worklist + triage.

**Top filters**

* Lane (Cardio/Ortho)
* Status (New/In Review/Ready/Exported/Closed)
* Score band (Green/Amber/Red)
* Payer
* “Has Query”
* “Has Sticker Risk”

**Table columns**

* Case ID
* Lane
* Payer
* Score (0–100)
* Critical flags count
* Last updated
* Owner (optional)
* Actions: Open, Generate Pack (if ready), Draft Reply

**Empty state**

* “Import a case folder to begin” + “Use demo dataset”

---

## Screen 3 — Case Workbench (Primary)

**Goal:** 90% of daily work happens here.

**Layout (3-pane)**

### Left: Documents panel

* Document list grouped by detected type
* Each item shows:

  * icon, doc type, confidence
  * flags (blur, low DPI, mismatch)
  * page count
* Actions:

  * Preview
  * Override type
  * Replace file
  * Mark as “Verified”

### Center: Readiness panel

* **Readiness Score** (0–100) + band
* “Top fixes” (max 5)
* Missing/Weak checklist with:

  * item name
  * owner role (TPA/Doctor/Nurse/Stores)
  * severity
  * “Mark done” / “Attach file” / “Assign”
* Risk Flags section:

  * “Clinical inconsistency”
  * “Sticker not verified”
  * “Identity mismatch”
  * each flag shows: Why + Fix + Evidence links

### Right: Actions panel

* Analyze / Re-analyze
* Generate Evidence Pack
* Draft Query Reply
* Export Checklist
* Export Audit Snapshot
* Case Status dropdown

**Key interactions**

* Drag-drop adds files
* Clicking any checklist item highlights missing doc type slot
* One-click jump from “Sticker risk” to Sticker Verification detail

**States**

* “Analyzing…” progress with per-step ticks (Docs, Quality, Sticker, Policy)
* Offline verified badge always visible
* Warning if no policy loaded for payer (still allows pack generation)

---

## Screen 4 — Evidence Pack Builder

**Goal:** deterministic payer-ready PDF pack.

**Inputs**

* Payer Template selector (with version)
* Lane selector
* Include cover page (on/off)
* Include checklist (on/off)
* Ordering preview (drag reorder, admin can save as override)

**Preview**

* Index table:

  * doc type
  * selected file(s)
  * page range (computed after build)
* Missing required docs banner (blocks “Final Pack” export; allows “Draft Pack” export)

**Outputs**

* Build Pack (Draft)
* Build Pack (Final) — only if score threshold met or missing items acknowledged
* Export pack + index + attachments checklist

---

## Screen 5 — Query Reply (Voice → Draft → Approve)

**Goal:** remove friction, enforce safety.

**Panels**

* Query input (paste)
* Context selector:

  * Attach relevant docs toggles (default auto-selected)
* Voice recorder:

  * Record / Stop
  * Playback
  * Language hint dropdown (Telugu/Hindi/English/Mixed)
* Transcript viewer (editable)
* Draft reply editor:

  * structured sections:

    * Clinical Summary
    * Justification
    * Attachment references
    * Next steps
* Confidence + grounding:

  * “Doc references found: X”
  * “Policy citations: Y”
* Approval controls:

  * Draft → Review → Approve
  * “Requires manual verification” checkbox appears if low confidence

**Export**

* Export Reply PDF
* Export as portal-ready text (copy)

**Guardrails**

* Cannot export Final without Approve
* Low confidence forces a confirmation step

---

## Screen 6 — Policy Library (Offline RAG)

**Goal:** admin-only truth source, citation-first.

**Features**

* Upload payer PDFs
* Index build status
* Search box
* Results show:

  * snippet
  * pdf name
  * page number
  * “Use in checklist” button (adds rule to template)

**States**

* Index not built: big CTA “Build Index”
* Versioning: show current vs previous

---

## Screen 7 — Templates (Payer/Lane Rules)

**Goal:** editable “policy-to-checklist” layer.

**Template view**

* Required docs list (per lane)
* Optional docs
* Common queries mapping → required evidence
* Score weights
* Thresholds (blur, DPI, sticker required)

**Hospital overrides**

* Add/remove items
* Local naming conventions
* Export/import template JSON (for portability)

**Versioning**

* Save as version
* “Diff view” between versions

---

## Screen 8 — Batch Audit (Autopsy)

**Goal:** convert “no-install resistance” into a yes.

**Inputs**

* Import folder containing multiple case folders
* Lane & payer mapping rules (auto-detect + manual mapping)
* Run audit (job)

**Outputs**

* Summary cards:

  * Top missing docs
  * Top quality failures
  * Sticker failures
  * Identity mismatch frequency
* Charts:

  * readiness score distribution
  * failures by payer
  * failures by lane
* Export:

  * PDF report
  * CSV table
  * “Pilot recommendation” 1-pager

---

## Screen 9 — Settings & Admin

**Sections**

* Users & roles
* Storage paths
* Hospital Mode toggle (locks updates, disables network)
* Model runtime:

  * Ollama endpoint
  * Model installed status
  * “Offline model import”
* OCR settings:

  * enable/disable
  * thresholds
* Diagnostics:

  * export debug bundle (logs + versions + config redacted)

---

## 6) Micro UX standards (pro polish)

* **Keyboard shortcuts**

  * New case: Ctrl+N
  * Import: Ctrl+I
  * Analyze: Ctrl+Enter
  * Generate pack: Ctrl+P
  * Draft reply: Ctrl+R
* **One-click fixes**

  * “Rescan required” with instructions
  * “Wrong patient doc” → mark as removed + reason
* **Progress transparency**

  * Stepwise progress: classify → quality → sticker → policy → score
* **No surprise automation**

  * all outputs clearly labeled Draft/Final
* **Always visible trust**

  * Offline Verified badge
  * Audit trail icon per action

---

## 7) Visual design system

* Clinical clean theme:

  * neutral background, high contrast text
  * severity colors only for flags (Red/Amber/Green)
* Typography:

  * 1 header style, 2 body sizes, consistent spacing
* Components:

  * badges, chips, tables, collapsible panels, toasts
* Accessibility:

  * keyboard navigable
  * minimum contrast standards

---

## 8) Error states (must-have)

* Policy not loaded → show warning; allow non-policy pack generation
* OCR failed → show actionable fallback (“manual verify”)
* Model not available → disable AI features; allow pack builder and checklist manually
* Corrupt PDFs → attempt repair; if fails, flag “replace file”
* Storage full → block exports; show cleanup path

---

## 9) Demo/Hackathon mode (same UX, safe)

* “Demo dataset” button creates:

  * sabotaged folder cases
  * preloaded policies
* UI shows “Demo Mode” watermark
* Exports include “Sample Data” label

---
