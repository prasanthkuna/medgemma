"""
Pramana AI — Initialize Demo Cases into SQLite
Seeds the database with the 4 flagship demo cases and their files.

Run from project root: python scripts/init_live_cases.py
"""
import asyncio
import uuid
import json
import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime
import aiosqlite
import sys
import os

# Add sidecar to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sidecar"))
from config import settings
from db.database import init_db


async def get_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def detect_mime(file_path: Path) -> str:
    """Detect MIME type from file extension"""
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        return mime
    ext = file_path.suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".txt": "text/plain",
    }.get(ext, "application/octet-stream")


def classify_by_filename(filename: str) -> tuple:
    """Classify document type from filename → (doc_type, confidence)"""
    name = filename.lower()
    patterns = {
        "discharge": ("discharge_summary", 0.95),
        "admission": ("admission_note", 0.95),
        "progress": ("progress_note", 0.85),
        "ot_note": ("ot_note", 0.95),
        "operation": ("ot_note", 0.85),
        "sticker": ("implant_sticker", 0.95),
        "implant": ("implant_sticker", 0.90),
        "stent": ("implant_sticker", 0.90),
        "pharmacy": ("pharmacy_bill", 0.95),
        "bill": ("pharmacy_bill", 0.80),
        "icu": ("icu_chart", 0.90),
        "lab": ("lab_report", 0.90),
        "xray": ("radiology_report", 0.90),
        "mri": ("radiology_report", 0.90),
        "radiology": ("radiology_report", 0.85),
        "ecg": ("lab_report", 0.85),
        "insurance": ("insurance_card", 0.85),
    }
    for pattern, (doc_type, conf) in patterns.items():
        if pattern in name:
            return doc_type, conf
    return "other", 0.5


# ── Case Definitions ──
DEMO_CASES = [
    {
        "folder": "case_001_cardio_perfect",
        "case_number": "AEGIS-001",
        "patient_alias": "Ramesh Kumar Sharma",
        "lane": "cardio",
        "payer_id": "star_health",
        "tpa_id": None,
        "status": "new",
        "description": "Perfect cardio case — all docs present, clear sticker"
    },
    {
        "folder": "case_002_ortho_blurry",
        "case_number": "AEGIS-002",
        "patient_alias": "Lakshmi Devi Reddy",
        "lane": "ortho",
        "payer_id": "united_healthcare",
        "tpa_id": None,
        "status": "new",
        "description": "Ortho case with intentionally blurry implant sticker"
    },
    {
        "folder": "case_003_cardio_icu",
        "case_number": "AEGIS-003",
        "patient_alias": "Venkatesh Rao",
        "lane": "cardio",
        "payer_id": "medicare",
        "tpa_id": None,
        "status": "new",
        "description": "Cardio case: 5-day ICU stay but MISSING icu_chart and progress_notes"
    },
    {
        "folder": "case_004_mixed_patient",
        "case_number": "AEGIS-004",
        "patient_alias": "Priya Menon",
        "lane": "ortho",
        "payer_id": "icici_lombard",
        "tpa_id": None,
        "status": "new",
        "description": "Mixed patient docs — lab_report belongs to a different patient"
    },
]


async def init_live_data():
    print(f"🔧 Initializing Pramana AI demo data...")
    print(f"   Database: {settings.db_path}")
    print()

    # Ensure DB schema exists
    await init_db()

    demo_root = settings.demo_dir  # data/demo/

    async with aiosqlite.connect(settings.db_path) as db:
        # 1. Full Reset
        print("🗑️  Purging existing data...")
        await db.execute("DELETE FROM case_analysis")
        await db.execute("DELETE FROM case_outputs")
        await db.execute("DELETE FROM case_files")
        await db.execute("DELETE FROM audit_events")
        await db.execute("DELETE FROM cases")

        # 2. Setup System Admin
        admin_id = "sys-admin-aegis"
        await db.execute(
            "INSERT OR REPLACE INTO users (id, name, role) VALUES (?, ?, ?)",
            (admin_id, "Chief Medical Auditor", "admin")
        )

        # 3. Seed Demo Cases
        total_files = 0
        for case_def in DEMO_CASES:
            case_dir = demo_root / case_def["folder"]
            if not case_dir.exists():
                print(f"   ❌ Folder not found: {case_dir}")
                continue

            case_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            await db.execute(
                """
                INSERT INTO cases (id, case_number, patient_alias, lane, payer_id, tpa_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (case_id, case_def["case_number"], case_def["patient_alias"],
                 case_def["lane"], case_def["payer_id"], case_def["tpa_id"],
                 case_def["status"], now, now)
            )

            # Index all files in the folder
            supported_exts = {".pdf", ".jpg", ".jpeg", ".png", ".txt"}
            files_indexed = 0

            for file_path in sorted(case_dir.iterdir()):
                if file_path.suffix.lower() not in supported_exts:
                    continue
                if file_path.is_dir():
                    continue

                file_id = str(uuid.uuid4())
                sha = await get_sha256(file_path)
                mime = detect_mime(file_path)
                doc_type, confidence = classify_by_filename(file_path.name)

                # Count pages for PDFs
                page_count = None
                if mime == "application/pdf":
                    try:
                        import pdfplumber
                        with pdfplumber.open(file_path) as pdf:
                            page_count = len(pdf.pages)
                    except Exception:
                        page_count = 1

                await db.execute(
                    """
                    INSERT INTO case_files (id, case_id, path, filename, sha256, mime_type, doc_type, doc_type_confidence, page_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (file_id, case_id, str(file_path.absolute()), file_path.name,
                     sha, mime, doc_type, confidence, page_count, now)
                )
                files_indexed += 1

            # Log audit event
            await db.execute(
                "INSERT INTO audit_events (id, case_id, user_id, action, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), case_id, admin_id, "case_imported",
                 json.dumps({"folder": case_def["folder"], "files": files_indexed}), now)
            )

            total_files += files_indexed
            print(f"   ✅ {case_def['case_number']} ({case_def['patient_alias']}) — {files_indexed} files | {case_def['description']}")

        await db.commit()

    print()
    print(f"🎉 Done! Seeded {len(DEMO_CASES)} cases with {total_files} total files.")
    print(f"   Start backend:  cd sidecar && python main.py")
    print(f"   Start frontend: cd ui && npm run dev")


if __name__ == "__main__":
    asyncio.run(init_live_data())
