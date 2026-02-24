
import asyncio
import uuid
import json
import hashlib
from pathlib import Path
from datetime import datetime
import aiosqlite
import sys
import os

# Add sidecar to path to import config
sys.path.append(os.path.abspath("sidecar"))
from config import settings

async def get_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

async def seed_data():
    print(f"Seeding demo data into {settings.db_path}...")
    
    # Path to demo data
    demo_root = Path("data/demo")
    manifest_path = Path("data/test_data_manifest.json")
    
    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}")
        return

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    async with aiosqlite.connect(settings.db_path) as db:
        # 1. Clear existing data (for clean state)
        await db.execute("DELETE FROM cases")
        await db.execute("DELETE FROM case_files")
        await db.execute("DELETE FROM audit_events")
        await db.execute("DELETE FROM case_analysis")
        
        # 2. Add a default admin user
        admin_id = str(uuid.uuid4())
        await db.execute(
            "INSERT OR IGNORE INTO users (id, name, role) VALUES (?, ?, ?)",
            (admin_id, "System Admin", "admin")
        )

        for case_dir_name, case_meta in manifest["cases"].items():
            case_path = demo_root / case_dir_name
            if not case_path.exists():
                print(f"Warning: Case directory {case_path} not found, skipping.")
                continue

            case_id = f"case-{case_dir_name.lower().replace('_', '-')}"
            case_number = f"CASE-{case_dir_name.split('_')[1]}-{datetime.now().year}"
            patient_alias = case_dir_name.split('_')[-1].replace('_', ' ').capitalize() + " Patient"
            
            print(f"Importing {case_dir_name}...")
            
            # Insert case
            await db.execute(
                """
                INSERT INTO cases (id, case_number, patient_alias, lane, payer_id, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (case_id, case_number, patient_alias, case_meta["lane"], "ICICI Lombard", "new")
            )

            # Import files
            for file_path in case_path.glob("*"):
                if file_path.is_file():
                    file_id = str(uuid.uuid4())
                    sha = await get_sha256(file_path)
                    
                    # Basic doc type mapping from filename
                    doc_type = "other"
                    name_lower = file_path.name.lower()
                    if "discharge" in name_lower: doc_type = "discharge_summary"
                    elif "admission" in name_lower: doc_type = "admission_note"
                    elif "progress" in name_lower: doc_type = "progress_note"
                    elif "ot_note" in name_lower or "operation" in name_lower: doc_type = "ot_note"
                    elif "sticker" in name_lower: doc_type = "implant_sticker"
                    elif "bill" in name_lower: doc_type = "pharmacy_bill"
                    elif "lab" in name_lower: doc_type = "lab_report"
                    elif "radiology" in name_lower: doc_type = "radiology_report"
                    
                    # Mime type mapping
                    mime_type = "text/plain"
                    if name_lower.endswith(".pdf"): mime_type = "application/pdf"
                    elif name_lower.endswith((".jpg", ".jpeg")): mime_type = "image/jpeg"
                    elif name_lower.endswith(".png"): mime_type = "image/png"
                    
                    await db.execute(
                        """
                        INSERT INTO case_files (id, case_id, path, filename, sha256, mime_type, doc_type, doc_type_confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (file_id, case_id, str(file_path.absolute()), file_path.name, sha, mime_type, doc_type, 1.0)
                    )

            # Log audit event
            await db.execute(
                "INSERT INTO audit_events (id, case_id, user_id, action, payload) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), case_id, admin_id, "case_imported", f"Imported from {case_dir_name}")
            )

        await db.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_data())
