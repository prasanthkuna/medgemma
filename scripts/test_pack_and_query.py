"""Test evidence pack generation and query reply copilot."""
import requests, json

BASE = "http://127.0.0.1:8000"

cases = requests.get(f"{BASE}/api/cases").json()
case_001 = next(c for c in cases if c["case_number"] == "AEGIS-001")
cid = case_001["id"]
print(f"Testing with AEGIS-001 (ID: {cid})\n")

# Test 1: Generate Evidence Pack
print("=" * 50)
print("TEST 1: Evidence Pack Generation")
print("=" * 50)
try:
    r = requests.post(f"{BASE}/api/pack/{cid}/generate", json={
        "include_cover": True,
        "include_checklist": True,
        "include_watermark": True,
        "watermark_text": "DEMO"
    })
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"Output ID: {d.get('output_id')}")
        print(f"Path: {d.get('path')}")
        print(f"SHA256: {d.get('sha256', 'N/A')[:16]}...")
    else:
        print(f"Error: {r.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")

print()

# Test 2: Query Reply Draft (no audio, just text)
print("=" * 50)
print("TEST 2: Query Reply Copilot")
print("=" * 50)
try:
    r = requests.post(
        f"{BASE}/api/cases/{cid}/query/draft",
        data={"query_text": "Please provide clinical justification for the PCI procedure including medical necessity and prior conservative management attempts."}
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"Draft preview: {str(d.get('draft', ''))[:300]}...")
        if d.get("transcript"):
            print(f"Transcript: {d['transcript'][:200]}")
    else:
        print(f"Error: {r.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")

print()

# Test 3: Get Exports
print("=" * 50)
print("TEST 3: Get Exports")
print("=" * 50)
try:
    r = requests.get(f"{BASE}/api/pack/{cid}/exports")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        exports = r.json()
        print(f"Export count: {len(exports)}")
        for ex in exports:
            print(f"  - {ex.get('output_type')}: {ex.get('path', 'N/A')[:80]}")
    else:
        print(f"Error: {r.text[:300]}")
except Exception as e:
    print(f"Exception: {e}")
