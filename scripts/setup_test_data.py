"""
Test Data Setup Script for Pramana AI
Downloads MTSamples, generates synthetic demo cases, and creates sample documents

Run: python scripts/setup_test_data.py
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
DEMO_DIR = DATA_DIR / "demo"
POLICIES_DIR = DATA_DIR / "policies"
RAW_DIR = DATA_DIR / "raw"


def setup_directories():
    """Create all required directories"""
    print("[1/6] Setting up directories...")
    
    dirs = [
        DEMO_DIR / "case_001_cardio_perfect",
        DEMO_DIR / "case_002_ortho_blurry",
        DEMO_DIR / "case_003_cardio_icu",
        DEMO_DIR / "case_004_mixed_patient",
        DEMO_DIR / "stickers",
        POLICIES_DIR,
        RAW_DIR / "mtsamples",
    ]
    
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {d.relative_to(PROJECT_ROOT)}")
    
    print()


def download_mtsamples():
    """Download MTSamples dataset from Kaggle"""
    print("[2/6] Downloading MTSamples dataset...")
    
    mtsamples_dir = RAW_DIR / "mtsamples"
    csv_file = mtsamples_dir / "mtsamples.csv"
    
    if csv_file.exists():
        print(f"  [SKIP] Already downloaded: {csv_file.name}")
        return True
    
    # Check if kaggle is installed
    try:
        import kaggle
        print("  [OK] Kaggle API available")
    except ImportError:
        print("  [WARN] Kaggle not installed. Install with: pip install kaggle")
        print("  [INFO] You can manually download from: https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions")
        return False
    
    # Check for kaggle.json
    kaggle_config = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_config.exists():
        print("  [WARN] Kaggle credentials not found at ~/.kaggle/kaggle.json")
        print("  [INFO] Get your API token from: https://www.kaggle.com/settings -> API -> Create New Token")
        print("  [INFO] Save it to: ~/.kaggle/kaggle.json")
        return False
    
    # Download dataset
    try:
        print("  [INFO] Downloading dataset (this may take a minute)...")
        subprocess.run([
            sys.executable, "-m", "kaggle", "datasets", "download",
            "-d", "tboyle10/medicaltranscriptions",
            "-p", str(mtsamples_dir),
            "--unzip"
        ], check=True, capture_output=True)
        print(f"  [OK] Downloaded to {mtsamples_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [FAIL] Download failed: {e}")
        return False


def download_policy_pdfs():
    """Download sample TPA policy PDFs"""
    print("[3/6] Downloading sample policy PDFs...")
    
    # These are publicly available policy documents
    policies = {
        "sample_health_policy.txt": """
SAMPLE HEALTH INSURANCE POLICY DOCUMENT
========================================

This is a sample policy document for testing purposes.

SECTION 1: COVERAGE
- Hospitalization expenses covered up to policy limit
- Pre-hospitalization: 30 days prior to admission
- Post-hospitalization: 60 days after discharge

SECTION 2: REQUIRED DOCUMENTS
For reimbursement claims, the following documents are mandatory:
1. Original hospital bills with itemized breakup
2. Discharge summary with diagnosis and treatment details
3. Doctor's prescription and progress notes
4. Lab and investigation reports
5. Pharmacy bills with serial numbers (if implants used)
6. Implant stickers with serial numbers for cardio/ortho cases

SECTION 3: IMPLANT CLAIMS
For cardiac stent or orthopedic implant claims:
- Original implant sticker MUST be attached
- Serial number must match pharmacy invoice
- OT notes must mention implant details
- Pre-authorization required for procedures > Rs. 2,00,000

SECTION 4: ICU COVERAGE
- ICU charges covered as per policy terms
- Daily ICU chart with vital signs required
- Nursing notes for each ICU day mandatory
- Justification needed for ICU stay > 3 days

SECTION 5: CLAIM SUBMISSION
- Submit within 15 days of discharge
- Incomplete documents will result in query
- All documents must have patient name matching

SECTION 6: QUERY RESOLUTION
- Respond to queries within 7 days
- Provide supporting evidence with citations
- Late responses may result in claim denial
""",
        "cardio_guidelines.txt": """
CARDIAC PROCEDURE CLAIM GUIDELINES
==================================

Required Documents for Cardiac Stent Claims:

1. MANDATORY DOCUMENTS
   - Discharge Summary with procedure details
   - Angiography report (pre-procedure)
   - Stent implant sticker with visible serial number
   - OT Notes mentioning stent type and quantity
   - Pharmacy bill with stent serial number
   - Cardiologist notes and recommendations
   
2. FOR ICU STAYS
   - Daily ICU monitoring charts
   - Nursing notes
   - Vital signs record
   
3. COVERAGE LIMITS
   - Drug-eluting stent: Up to Rs. 40,000 per stent
   - Bare metal stent: Up to Rs. 20,000 per stent
   - Maximum 3 stents per procedure covered
   
4. PRE-AUTHORIZATION
   - Required for all CABG procedures
   - Required if total cost > Rs. 3,00,000
   
5. COMMON DENIAL REASONS
   - Missing or blurry stent sticker
   - Serial number mismatch between sticker and bill
   - Incomplete ICU documentation for >2 day stays
   - Missing angiography report
""",
        "ortho_guidelines.txt": """
ORTHOPEDIC IMPLANT CLAIM GUIDELINES
===================================

Required Documents for Orthopedic Implant Claims:

1. MANDATORY DOCUMENTS
   - Discharge Summary with procedure details
   - X-ray pre and post surgery
   - Implant sticker with visible serial number
   - OT Notes mentioning implant specifications
   - Pharmacy bill with implant serial number
   - Orthopedic surgeon's notes
   
2. IMPLANT TYPES COVERED
   - Joint replacement (hip, knee, shoulder)
   - Fracture fixation (plates, screws, rods)
   - Spinal fusion hardware
   
3. COVERAGE LIMITS
   - Knee replacement: Up to Rs. 1,20,000 per knee
   - Hip replacement: Up to Rs. 1,50,000
   - Fracture fixation: As per itemized billing
   
4. DOCUMENTATION STANDARDS
   - Implant sticker must be clearly photographed
   - All 4 corners visible
   - Serial number legible
   - No tears or damage to sticker
   
5. COMMON DENIAL REASONS
   - Blurry or partially visible sticker
   - Missing implant serial number
   - Mismatch between OT notes and implant type
   - Incomplete physiotherapy notes (if claimed)
"""
    }
    
    for filename, content in policies.items():
        file_path = POLICIES_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  [OK] Created {filename}")
    
    print()


def generate_demo_documents():
    """Generate synthetic demo documents for each case"""
    print("[4/6] Generating synthetic demo documents...")
    
    # Case 1: Perfect Cardio Case (GREEN score expected)
    case1_docs = {
        "discharge_summary.txt": """
DISCHARGE SUMMARY
=================
Hospital: Apollo Hospitals, Hyderabad
Patient: Mr. Ramesh Kumar (Alias: RK-2024-001)
DOB: 15-Mar-1965
Admission Date: 15-Jan-2024
Discharge Date: 18-Jan-2024
IPD No.: APH/2024/1234

DIAGNOSIS:
- Triple vessel coronary artery disease
- Hypertension

PROCEDURE PERFORMED:
- Percutaneous Coronary Intervention (PCI)
- Drug-eluting stent to LAD and RCA (2 stents)

STENT DETAILS:
- Stent 1: XIENCE Sierra 3.5mm x 28mm, Serial: XS-2024-78901
- Stent 2: XIENCE Sierra 3.0mm x 18mm, Serial: XS-2024-78902

HOSPITAL COURSE:
Patient admitted via emergency with chest pain. Angiography showed
triple vessel disease. Successful PCI performed on 16-Jan-2024.
Post-procedure recovery uneventful. Discharged in stable condition.

DISCHARGE MEDICATIONS:
1. Aspirin 75mg OD
2. Clopidogrel 75mg OD
3. Atorvastatin 40mg HS
4. Metoprolol 25mg BD

TREATING PHYSICIAN:
Dr. Suresh Reddy, MD DM (Cardiology)
""",
        "admission_note.txt": """
ADMISSION NOTE
==============
Date: 15-Jan-2024, Time: 14:30
Patient: Mr. Ramesh Kumar
MRD: APH/2024/1234

CHIEF COMPLAINT:
Chest pain and breathlessness for 2 days

HISTORY OF PRESENT ILLNESS:
65-year-old male, known hypertensive, presented with
retrosternal chest pain radiating to left arm.
ECG showed ST depression in anterior leads.

VITALS ON ADMISSION:
- BP: 160/100 mmHg
- HR: 88 bpm
- SpO2: 96% on room air
- Temp: 98.4 F

PLAN:
- Admit to CCU
- Stat Troponin, 2D Echo
- Coronary Angiography tomorrow

Admitting Physician: Dr. Suresh Reddy
""",
        "ot_note.txt": """
OPERATION THEATRE NOTE
======================
Date: 16-Jan-2024
Patient: Mr. Ramesh Kumar
IPD: APH/2024/1234

PROCEDURE: Percutaneous Coronary Intervention (PCI)

PRE-OP DIAGNOSIS: Triple vessel CAD

ANESTHESIA: Local with conscious sedation

PROCEDURE DETAILS:
1. Right radial artery access obtained
2. CAG confirmed 90% LAD lesion, 80% RCA lesion
3. Wiring done successfully
4. Pre-dilatation with 2.5mm balloon
5. STENT DEPLOYMENT:
   - LAD: XIENCE Sierra 3.5x28mm (Serial: XS-2024-78901)
   - RCA: XIENCE Sierra 3.0x18mm (Serial: XS-2024-78902)
6. Post-dilatation with NC balloon
7. TIMI 3 flow achieved in both vessels

BLOOD LOSS: Minimal
COMPLICATIONS: None

SURGEON: Dr. Suresh Reddy, MD DM Cardiology
""",
        "pharmacy_bill.txt": """
PHARMACY BILL
=============
Hospital: Apollo Hospitals, Hyderabad
Patient: Mr. Ramesh Kumar
IPD: APH/2024/1234
Bill No.: PH-2024-5678
Date: 18-Jan-2024

ITEMS:
------
1. XIENCE Sierra DES 3.5x28mm
   Serial No.: XS-2024-78901
   Qty: 1
   Rate: Rs. 38,000
   Amount: Rs. 38,000

2. XIENCE Sierra DES 3.0x18mm
   Serial No.: XS-2024-78902
   Qty: 1
   Rate: Rs. 35,000
   Amount: Rs. 35,000

3. Guide catheter 6F
   Qty: 2
   Rate: Rs. 2,500
   Amount: Rs. 5,000

4. PTCA Balloon 2.5x15mm
   Qty: 1
   Rate: Rs. 8,000
   Amount: Rs. 8,000

5. Guidewire 0.014"
   Qty: 2
   Rate: Rs. 3,000
   Amount: Rs. 6,000

SUBTOTAL: Rs. 92,000
GST (5%): Rs. 4,600
TOTAL: Rs. 96,600

Verified by: Hospital Pharmacy
""",
        "lab_report.txt": """
LABORATORY REPORT
=================
Patient: Mr. Ramesh Kumar
IPD: APH/2024/1234
Date: 15-Jan-2024

CARDIAC MARKERS:
- Troponin I: 2.8 ng/mL (Normal: <0.04)
- CK-MB: 45 U/L (Normal: <25)
- NT-proBNP: 450 pg/mL

COMPLETE BLOOD COUNT:
- Hemoglobin: 13.2 g/dL
- WBC: 8,500 /cumm
- Platelets: 2.2 lakhs/cumm

RENAL FUNCTION:
- Creatinine: 1.0 mg/dL
- Urea: 32 mg/dL

LIPID PROFILE:
- Total Cholesterol: 245 mg/dL
- LDL: 168 mg/dL
- HDL: 38 mg/dL
- Triglycerides: 195 mg/dL

COAGULATION:
- PT/INR: 12.5/1.0
- aPTT: 32 sec

Pathologist: Dr. Lakshmi Rao, MD Pathology
"""
    }
    
    # Write Case 1 documents
    case1_dir = DEMO_DIR / "case_001_cardio_perfect"
    for filename, content in case1_docs.items():
        with open(case1_dir / filename, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"  [OK] case_001_cardio_perfect: {len(case1_docs)} documents")
    
    # Case 2: Ortho with Blurry Sticker (AMBER score expected)
    case2_docs = {
        "discharge_summary.txt": """
DISCHARGE SUMMARY
=================
Hospital: KIMS Hospital, Hyderabad
Patient: Mrs. Padma Devi (Alias: PD-2024-002)
Admission: 10-Jan-2024
Discharge: 15-Jan-2024

DIAGNOSIS: Left hip osteoarthritis, severe

PROCEDURE: Total Hip Replacement (Left)

IMPLANT USED:
- Acetabular Cup: Zimmer 54mm
- Femoral Stem: Zimmer Size 12
- Serial: ZM-2024-HIP-4567

COURSE: Uncomplicated recovery

Dr. Mahesh Sharma, MS Ortho
""",
        "ot_note.txt": """
OT NOTE
=======
Patient: Mrs. Padma Devi
Date: 11-Jan-2024

PROCEDURE: Left Total Hip Replacement

Implant: Zimmer Hip System
Serial: ZM-2024-HIP-4567

Approach: Posterolateral
Blood loss: 400ml
Duration: 2 hours

Surgeon: Dr. Mahesh Sharma
""",
        "pharmacy_bill.txt": """
PHARMACY BILL
=============
Patient: Mrs. Padma Devi
Bill: PH-K-2024-789
Date: 15-Jan-2024

Hip Replacement System (Zimmer)
Serial: ZM-2024-HIP-4567
Amount: Rs. 1,45,000

Bone Cement: Rs. 12,000
Sutures: Rs. 3,500

TOTAL: Rs. 1,60,500
""",
        "blurry_sticker_note.txt": """
NOTE: The implant sticker image in this case is intentionally
blurry to simulate a common claim issue where the sticker
photograph is not clearly captured.

Expected AI Response:
- Flag quality issue for sticker
- Request re-scan or clearer image
- Reduce readiness score to AMBER
"""
    }
    
    case2_dir = DEMO_DIR / "case_002_ortho_blurry"
    for filename, content in case2_docs.items():
        with open(case2_dir / filename, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"  [OK] case_002_ortho_blurry: {len(case2_docs)} documents")
    
    # Case 3: Cardio with Missing ICU Notes (RED score expected)
    case3_docs = {
        "discharge_summary.txt": """
DISCHARGE SUMMARY
=================
Hospital: Yashoda Hospitals, Hyderabad
Patient: Mr. Venkat Rao (Alias: VR-2024-003)
Admission: 05-Jan-2024
Discharge: 12-Jan-2024

DIAGNOSIS: Acute MI with cardiogenic shock

PROCEDURE: Emergency PCI + IABP

ICU STAY: 5 DAYS (06-Jan to 10-Jan)

Stent: Resolute Onyx 3.5x38mm
Serial: RO-2024-12345

Note: Patient required prolonged ICU care due to shock.
Recovery gradual but satisfactory.

Dr. Krishna Murthy, DM Cardiology
""",
        "admission_note.txt": """
ADMISSION NOTE
==============
Date: 05-Jan-2024
Patient: Mr. Venkat Rao

EMERGENCY ADMISSION
Massive anterior wall MI with cardiogenic shock.
Intubated in ER. Shifted to CCU urgently.
IABP inserted for hemodynamic support.
""",
        "pharmacy_bill.txt": """
PHARMACY BILL
=============
Patient: Mr. Venkat Rao
Date: 12-Jan-2024

Resolute Onyx DES 3.5x38mm
Serial: RO-2024-12345
Amount: Rs. 42,000

IABP Catheter: Rs. 65,000
ICU Consumables: Rs. 28,000

TOTAL: Rs. 1,35,000
""",
        "missing_docs_note.txt": """
NOTE: This case is intentionally MISSING the following documents
that should be present for a 5-day ICU stay claim:

MISSING:
1. ICU charts (daily vital signs)
2. Progress notes (day-wise)
3. Nursing notes
4. Ventilator records (if applicable)

Expected AI Response:
- Detect 5-day ICU mentioned in discharge summary
- Flag missing ICU documentation
- Request: "5 days ICU stay mentioned but no ICU charts provided"
- Readiness score: RED
"""
    }
    
    case3_dir = DEMO_DIR / "case_003_cardio_icu"
    for filename, content in case3_docs.items():
        with open(case3_dir / filename, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"  [OK] case_003_cardio_icu: {len(case3_docs)} documents")
    
    # Case 4: Mixed Patient Documents (RED score expected)
    case4_docs = {
        "discharge_summary.txt": """
DISCHARGE SUMMARY
=================
Patient: Mr. Suresh Babu (SB-2024-004)
Admission: 20-Jan-2024
Discharge: 24-Jan-2024

DIAGNOSIS: Knee osteoarthritis
PROCEDURE: Right Total Knee Replacement

Implant: Smith & Nephew Legion
Serial: SN-2024-TKR-9999

Dr. Rajesh Kumar, MS Ortho
""",
        "lab_report_WRONG_PATIENT.txt": """
LABORATORY REPORT
=================
Patient: Mrs. LAKSHMI RANI  <<< DIFFERENT PATIENT NAME
MRD: YH/2024/DIFFERENT
Date: 20-Jan-2024

NOTE: This is intentionally a document from a DIFFERENT patient
to simulate the common error of mixing up patient files.

Hemoglobin: 11.5 g/dL
WBC: 7,200/cumm
Platelets: 2.8 lakhs

Expected AI Response:
- Detect patient name mismatch
- Flag: "Lab report patient name does not match"
- Mark as HIGH PRIORITY consistency error
- Readiness: RED
""",
        "pharmacy_bill.txt": """
PHARMACY BILL
=============
Patient: Mr. Suresh Babu
IPD: SB-2024-004
Date: 24-Jan-2024

TKR System (Smith & Nephew Legion)
Serial: SN-2024-TKR-9999
Amount: Rs. 1,15,000

TOTAL: Rs. 1,15,000
""",
        "ot_note.txt": """
OT NOTE
=======
Patient: Mr. Suresh Babu
Date: 21-Jan-2024

PROCEDURE: Right Total Knee Replacement

Implant: Smith & Nephew Legion System
Serial: SN-2024-TKR-9999

Duration: 2.5 hours
Blood loss: 300ml
Complications: None
"""
    }
    
    case4_dir = DEMO_DIR / "case_004_mixed_patient"
    for filename, content in case4_docs.items():
        with open(case4_dir / filename, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"  [OK] case_004_mixed_patient: {len(case4_docs)} documents")
    
    print()


def generate_sticker_images():
    """Generate synthetic implant sticker images"""
    print("[5/6] Generating synthetic sticker images...")
    
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        
        stickers_dir = DEMO_DIR / "stickers"
        
        def create_sticker(filename, serial, product, blur=False, rotate=0):
            """Create a synthetic implant sticker image"""
            # Create image
            width, height = 400, 200
            img = Image.new("RGB", (width, height), color="white")
            draw = ImageDraw.Draw(img)
            
            # Draw border
            draw.rectangle([5, 5, width-5, height-5], outline="black", width=2)
            
            # Add company logo area
            draw.rectangle([10, 10, 100, 50], fill="#E0E0E0")
            draw.text((30, 20), "MEDTECH", fill="black")
            
            # Product name
            draw.text((120, 20), product, fill="black")
            
            # Serial number (larger, prominent)
            draw.rectangle([10, 60, width-10, 100], fill="#FFFFD0")
            draw.text((20, 65), f"S/N: {serial}", fill="black")
            
            # Additional details
            draw.text((20, 110), "REF: MT-2024-001", fill="gray")
            draw.text((20, 130), "LOT: L2024-01-15", fill="gray")
            draw.text((20, 150), "EXP: 2026-01", fill="gray")
            
            # Barcode area (simulated)
            for i in range(50):
                if random.random() > 0.5:
                    x = 200 + i * 3
                    draw.line([(x, 110), (x, 170)], fill="black", width=2)
            
            # Apply blur if requested
            if blur:
                img = img.filter(ImageFilter.GaussianBlur(radius=3))
            
            # Apply rotation if requested
            if rotate != 0:
                img = img.rotate(rotate, expand=True, fillcolor="white")
            
            # Save
            img.save(stickers_dir / filename)
        
        # Create clear stent sticker
        create_sticker(
            "clear_stent_sticker.jpg",
            "XS-2024-78901",
            "XIENCE Sierra DES 3.5x28mm"
        )
        print("  [OK] clear_stent_sticker.jpg")
        
        # Create blurry sticker
        create_sticker(
            "blurry_implant_sticker.jpg",
            "ZM-2024-HIP-4567",
            "Zimmer Hip System",
            blur=True
        )
        print("  [OK] blurry_implant_sticker.jpg")
        
        # Create rotated sticker
        create_sticker(
            "rotated_sticker.jpg",
            "SN-2024-TKR-9999",
            "S&N Legion TKR",
            rotate=15
        )
        print("  [OK] rotated_sticker.jpg")
        
        # Copy to respective case folders
        import shutil
        shutil.copy(stickers_dir / "clear_stent_sticker.jpg", 
                    DEMO_DIR / "case_001_cardio_perfect" / "stent_sticker.jpg")
        shutil.copy(stickers_dir / "blurry_implant_sticker.jpg", 
                    DEMO_DIR / "case_002_ortho_blurry" / "implant_sticker.jpg")
        print("  [OK] Copied stickers to case folders")
        
    except ImportError:
        print("  [WARN] Pillow not available. Creating placeholder files instead.")
        stickers_dir = DEMO_DIR / "stickers"
        for name in ["clear_stent_sticker.txt", "blurry_implant_sticker.txt"]:
            with open(stickers_dir / name, "w") as f:
                f.write(f"Placeholder for {name}\nInstall Pillow to generate actual images.")
            print(f"  [OK] Created placeholder: {name}")
    
    print()


def create_summary():
    """Create a summary of all test data"""
    print("[6/6] Creating test data summary...")
    
    summary = {
        "created_at": datetime.now().isoformat(),
        "cases": {
            "case_001_cardio_perfect": {
                "lane": "cardio",
                "expected_score": "GREEN",
                "description": "Complete cardio case with 2 stents, all docs present"
            },
            "case_002_ortho_blurry": {
                "lane": "ortho",
                "expected_score": "AMBER",
                "description": "Hip replacement with blurry sticker image"
            },
            "case_003_cardio_icu": {
                "lane": "cardio",
                "expected_score": "RED",
                "description": "5-day ICU stay but missing ICU documentation"
            },
            "case_004_mixed_patient": {
                "lane": "ortho",
                "expected_score": "RED",
                "description": "TKR case with mismatched patient documents"
            }
        },
        "policies": list(POLICIES_DIR.glob("*.txt")),
        "mtsamples": (RAW_DIR / "mtsamples" / "mtsamples.csv").exists()
    }
    
    # Convert paths to strings for JSON
    summary["policies"] = [str(p.name) for p in summary["policies"]]
    
    with open(DATA_DIR / "test_data_manifest.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"  [OK] Created test_data_manifest.json")
    print()


def main():
    print("=" * 60)
    print("Pramana AI - Test Data Setup")
    print("=" * 60 + "\n")
    
    setup_directories()
    mtsamples_ok = download_mtsamples()
    download_policy_pdfs()
    generate_demo_documents()
    generate_sticker_images()
    create_summary()
    
    print("=" * 60)
    print("TEST DATA SETUP COMPLETE!")
    print("=" * 60)
    print("\nSummary:")
    print(f"  - Demo cases: 4 (in data/demo/)")
    print(f"  - Policy docs: 3 (in data/policies/)")
    print(f"  - Sticker images: 3 (in data/demo/stickers/)")
    print(f"  - MTSamples: {'Downloaded' if mtsamples_ok else 'Manual download needed'}")
    
    if not mtsamples_ok:
        print("\n[!] To download MTSamples manually:")
        print("    1. Go to: https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions")
        print("    2. Download and extract to: data/raw/mtsamples/")
    
    print("\n[NEXT] Run the sidecar server:")
    print("  cd sidecar")
    print("  ../.venv/Scripts/python.exe -m uvicorn main:app --reload")
    print("=" * 60)


if __name__ == "__main__":
    main()
