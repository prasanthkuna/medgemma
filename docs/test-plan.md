### Validation (what’s correct / what to fix)

✅ Correct

* Dataset includes **16 name sets** + **100 clinical note templates** curated from **MIMIC-IV discharge summaries**. ([physionet.org][1])
* Templates mark PHI using placeholders like `**NAME-{number}{gender}**`, plus `**AGE**`, `**DATE**`, `**HOSPITAL**`, `**ID**`, etc. ([physionet.org][1])
* Notes are populated and released as **`notes-input.jsonl` (16,000 notes)** with labels in **`notes-label.jsonl`**. ([physionet.org][1])
* Templates were curated from discharge records from **Beth Israel Lahey Health (2017–2019)**; the study references a **pre-release** of MIMIC-IV at the time. ([physionet.org][1])

⚠️ Fix

* “16 name sets × 100 templates = 1,600 notes” is **not** what they ship; they explicitly provide **16,000 notes** in `notes-input.jsonl`. ([physionet.org][1])

---

## Upgraded pro plan (better than your current plan)

### Goal

Build a **realistic “Rejected/Queried IP case folder” benchmark** (offline) that lets you demo:

1. missing evidence detection, 2) patient-mixup guard, 3) legibility/scan quality, 4) payer-ready pack + drafted reply **with citations**.

### Phase 1 — Build a “Claims Folder Factory” (1 dataset → many case folders)

Use this PhysioNet dataset as the **core discharge summary** source. ([physionet.org][1])
Generate folders like a real TPA audit pack:

**Folder structure (per case)**

* `01_Discharge_Summary.pdf` (from template)
* `02_Procedure_Note.pdf` (optional: extracted section duplicated as separate doc)
* `03_Implant_Details.pdf` (synthetic doc you generate)
* `04_ICU_Daily_Notes.pdf` (synthetic doc you generate)
* `05_Labs_Imaging.pdf` (optional)
* `06_Billing_Sheet.xlsx` (synthetic)

**Controlled error injection (so you can score + show metrics)**

* Missing implant evidence: remove/alter `**ID**`/device identifiers in the implant doc. ([physionet.org][1])
* Wrong patient mixed in: swap page 2–3 from another case (header mismatch).
* ICU/LOS gaps: remove “ICU indication / daily progress” section.
* Illegible scan: degrade only the implant page (blur/rotation/cutoff).

Output: **50–200 case folders** with known “ground-truth” error labels.

### Phase 2 — Add 1 real-world dataset to make it undeniable

Pick one (best ROI → effort):

**A) MIMIC-IV-Note (real discharge summaries & other notes)**
Use it to diversify writing styles and sections (credentialed). ([physionet.org][1])

**B) eICU-CRD (ICU documentation patterns)**
Use it to generate stronger ICU/LOS justification checklists (credentialed). ([physionet.org][1])

### Phase 3 — Claims-side realism (payer readiness)

Add **SynPUF (synthetic Medicare claims)** to generate “claim metadata” (diagnosis/procedure codes, length-of-stay signals) without PHI, so your “payer checklist” looks real. ([physionet.org][1])

### Phase 4 — Your win condition: measurable scoring + leaderboard-style slide

For each case type, report:

* **Evidence missing detection:** precision/recall
* **Patient mix-up detection:** detection rate + false positives
* **Legibility detection:** pass/fail accuracy
* **Pack generation:** time to generate + % auto-index correct
* **Query reply grounding:** % citations that point to correct page/section

---

## Best “online real data” to add (shortlist)

* **MIMIC-IV-Note** (clinical notes realism) ([physionet.org][1])
* **eICU-CRD** (ICU/LOS evidence patterns) ([physionet.org][1])
* **SynPUF (CMS synthetic claims)** (claims realism, payer-side fields) ([physionet.org][1])
* **Synthea** (fast synthetic EHR to generate extra documents as PDFs) ([physionet.org][1])

If you paste your current “payer checklist” fields (implant/stent, ICU, LOS, discharge, identity), I’ll output a locked **gold-label schema + error-injection matrix + the exact 3 demo cases** to run live.

[1]: https://physionet.org/content/discharge-summary-templates/1.0/ "Annotated MIMIC-IV discharge summaries for a study on deidentification of names v1.0"
