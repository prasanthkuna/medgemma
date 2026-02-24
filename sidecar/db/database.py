"""
Pramana AI - Database Setup
SQLite with async support
"""
import aiosqlite
from pathlib import Path
from config import settings

DATABASE_PATH = settings.db_path


async def get_db():
    """Get database connection"""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """Initialize database schema"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'tpa', 'doctor', 'viewer')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Cases table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                case_number TEXT,
                patient_alias TEXT,
                lane TEXT NOT NULL CHECK (lane IN ('cardio', 'ortho')),
                payer_id TEXT,
                tpa_id TEXT,
                status TEXT DEFAULT 'new' CHECK (status IN ('new', 'analyzed', 'in_review', 'pack_generated', 'query_drafted', 'closed')),
                readiness_score INTEGER,
                readiness_band TEXT CHECK (readiness_band IN ('GREEN', 'AMBER', 'RED')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Case files table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS case_files (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                path TEXT NOT NULL,
                filename TEXT NOT NULL,
                sha256 TEXT,
                mime_type TEXT,
                doc_type TEXT,
                doc_type_confidence REAL,
                quality_flags TEXT,
                page_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Case analysis results
        await db.execute("""
            CREATE TABLE IF NOT EXISTS case_analysis (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                score INTEGER,
                band TEXT,
                missing_items TEXT,
                quality_issues TEXT,
                consistency_flags TEXT,
                citations TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Case outputs (generated PDFs)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS case_outputs (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                output_type TEXT NOT NULL CHECK (output_type IN ('evidence_pack', 'reply_pdf', 'checklist', 'audit_snapshot', 'batch_report')),
                path TEXT NOT NULL,
                sha256 TEXT,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Policies table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS policies (
                id TEXT PRIMARY KEY,
                payer_id TEXT NOT NULL,
                version TEXT,
                source_files TEXT,
                index_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Templates table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                payer_id TEXT NOT NULL,
                lane TEXT NOT NULL,
                version TEXT,
                template_json TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Audit events table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                case_id TEXT REFERENCES cases(id),
                user_id TEXT,
                action TEXT NOT NULL,
                payload TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Case drafts (persists AI-generated query responses)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS case_drafts (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                query_text TEXT,
                transcript TEXT,
                draft_json TEXT,
                status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'sent')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                approved_at DATETIME
            )
        """)
        
        # Create indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_cases_payer ON cases(payer_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_case_files_case ON case_files(case_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_events(case_id, created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_case_drafts_case ON case_drafts(case_id)")
        
        await db.commit()
