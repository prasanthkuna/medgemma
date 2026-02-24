"""Quick test: Analyze all 4 demo cases and print scores."""
import requests, json

cases = requests.get("http://127.0.0.1:8000/api/cases").json()
print(f"Found {len(cases)} cases\n")

for c in cases:
    cid = c["id"]
    cn = c["case_number"]
    patient = c.get("patient_alias", "?")
    r = requests.post(f"http://127.0.0.1:8000/api/analysis/{cid}/analyze")
    if r.status_code == 200:
        d = r.json()
        flags = [f["type"] for f in d.get("consistency_flags", [])]
        missing = [m["item"] for m in d.get("missing_items", [])]
        print(f"{cn} ({patient}):")
        print(f"  Score: {d['score']} | Band: {d['band']}")
        if missing:
            print(f"  Missing: {missing}")
        if flags:
            print(f"  Flags: {flags}")
        print()
    else:
        print(f"{cn}: ERROR {r.status_code}")
        print(f"  {r.text[:300]}")
        print()
