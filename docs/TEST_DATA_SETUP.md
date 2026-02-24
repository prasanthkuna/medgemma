# Test Data Setup Guide for Pramana AI

This guide helps you download and set up test data for the hackathon demo and Hyderabad pilot demonstrations.

---

## 📥 Data Sources

### 1. Medical Transcriptions (MTSamples)
**URL:** https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions
**License:** CC0 Public Domain
**Contains:** ~5,000 medical transcriptions including discharge summaries, operation notes, progress notes

**Download:**
```bash
# Option A: Kaggle CLI (requires kaggle.json)
pip install kaggle
kaggle datasets download -d tboyle10/medicaltranscriptions -p data/raw/mtsamples

# Option B: Manual download from Kaggle website
# Go to URL above → Download → Extract to data/raw/mtsamples/
```

---

### 2. MIMIC-III Clinical Notes (for deeper testing)
**URL:** https://physionet.org/content/mimiciii/
**License:** Requires PhysioNet credentialing (CITI training)
**Contains:** Real de-identified ICU clinical notes, discharge summaries

> [!CAUTION]
> MIMIC requires ~2-3 days for credential approval. Use MTSamples for initial development.

---

### 3. Sample Insurance Policy PDFs (for RAG testing)
**Sources (Indian TPA):**
- ICICI Lombard Health Policy: https://www.icicilombard.com/docs/default-source/health-insurance/health-policy-wordings.pdf
- Star Health Policy: https://www.starhealth.in/sites/default/files/policy-document/family-health-optima.pdf
- HDFC Ergo Health: https://www.hdfcergo.com/docs/default-source/individual-health-insurance/optima-secure-pw.pdf

```bash
# Create policies folder
mkdir -p data/policies

# Download sample policies (run manually or script)
curl -o data/policies/icici_health.pdf "https://www.icicilombard.com/docs/default-source/health-insurance/health-policy-wordings.pdf"
```

---

### 4. Synthetic "Sabotaged" Test Cases (WE CREATE THESE)

Since no public dataset exists for implant sticker images, we'll create synthetic test cases:

#### Case 1: "Perfect Cardio Case" (GREEN score)
```
data/demo/case_001_cardio_perfect/
├── discharge_summary.pdf      # Clear, complete
├── admission_note.pdf         # Present
├── ot_note.pdf               # Mentions stent
├── stent_sticker.jpg         # Clear image, serial visible
├── pharmacy_bill.pdf         # Serial number matches
└── lab_reports.pdf           # Complete set
```

#### Case 2: "Blurry Sticker" (AMBER score - sticker issue)
```
data/demo/case_002_ortho_blurry/
├── discharge_summary.pdf
├── implant_sticker.jpg       # Intentionally blurred
├── pharmacy_bill.pdf         # Has serial number
└── ot_note.pdf
```

#### Case 3: "Missing ICU Notes" (RED score - evidence gap)
```
data/demo/case_003_cardio_icu/
├── discharge_summary.pdf     # Mentions 5-day ICU stay
├── admission_note.pdf
├── stent_sticker.jpg
└── pharmacy_bill.pdf
# MISSING: icu_chart.pdf, progress_notes.pdf
```

#### Case 4: "Wrong Patient Doc" (RED score - identity mismatch)
```
data/demo/case_004_mixed_patient/
├── discharge_summary.pdf     # Patient A
├── lab_reports.pdf           # Patient B (different name!)
├── pharmacy_bill.pdf
└── ot_note.pdf
```

---

## 🛠️ Create Synthetic Documents

### Generate Sample Implant Sticker Images
I'll create realistic sticker images using Python:

```python
# Run: python scripts/generate_stickers.py
# Creates: data/demo/stickers/
# - clear_stent_sticker.jpg
# - blurry_stent_sticker.jpg  
# - rotated_implant_sticker.jpg
```

### Generate Sample Medical PDFs
```python
# Run: python scripts/generate_demo_docs.py
# Creates sample discharge summaries, OT notes, etc.
# With realistic Indian hospital formatting
```

---

## 📁 Final Data Structure

```
c:\Users\PrashanthKuna\samples\medgemma\
├── data/
│   ├── raw/
│   │   └── mtsamples/           # Downloaded transcriptions
│   ├── policies/
│   │   ├── icici_health.pdf     # TPA policy docs
│   │   ├── star_health.pdf
│   │   └── hdfc_ergo.pdf
│   └── demo/
│       ├── case_001_cardio_perfect/
│       ├── case_002_ortho_blurry/
│       ├── case_003_cardio_icu/
│       ├── case_004_mixed_patient/
│       └── stickers/
│           ├── clear_stent.jpg
│           └── blurry_implant.jpg
```

---

## ✅ Quick Setup Commands

```powershell
# Navigate to project
cd c:\Users\PrashanthKuna\samples\medgemma

# Activate venv
.venv\Scripts\Activate.ps1

# Install kaggle CLI
pip install kaggle

# Configure Kaggle API (put kaggle.json in ~/.kaggle/)
# Get from: https://www.kaggle.com/settings → API → Create New Token

# Download MTSamples
kaggle datasets download -d tboyle10/medicaltranscriptions -p data/raw/mtsamples --unzip

# Create demo folder structure
mkdir -p data/demo/case_001_cardio_perfect
mkdir -p data/demo/case_002_ortho_blurry
mkdir -p data/demo/case_003_cardio_icu
mkdir -p data/demo/case_004_mixed_patient
mkdir -p data/policies
```

---

## Next Steps

1. **Download MTSamples** from Kaggle
2. **Download policy PDFs** from TPA websites
3. **Run generation scripts** (I'll create these) for synthetic demo cases
4. **Proceed to Day 1** implementation
