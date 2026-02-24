"""
Test script to verify sidecar can start
Run: python scripts/test_server.py
"""
import sys
import os

# Add sidecar to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sidecar"))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from config import settings
        print(f"  [OK] Config loaded: {settings.app_name}")
        
        from db.database import init_db
        print("  [OK] Database module imported")
        
        from routers import health, cases, analysis, policies, pack
        print("  [OK] All routers imported")
        
        from services import classify, quality, scoring, rag, pack_builder
        print("  [OK] All services imported")
        
        from main import app
        print(f"  [OK] FastAPI app loaded: {len(app.routes)} routes")
        
        print("\n[PASS] All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database():
    """Test database initialization"""
    import asyncio
    from db.database import init_db
    
    print("\nTesting database...")
    try:
        asyncio.run(init_db())
        print("  [OK] Database initialized")
        return True
    except Exception as e:
        print(f"  [FAIL] Database error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Pramana AI - Sidecar Verification")
    print("=" * 50 + "\n")
    
    all_passed = True
    all_passed &= test_imports()
    all_passed &= test_database()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("[PASS] All tests passed!")
        print("\nTo start the server, run:")
        print("  cd sidecar")
        print("  ../.venv/Scripts/python.exe -m uvicorn main:app --reload")
    else:
        print("[FAIL] Some tests failed")
    print("=" * 50)

