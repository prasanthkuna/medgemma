
import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

CASES = {
    "AEGIS-001": "ba8ff704-6d05-4592-92bf-2c82ba958a77",
    "AEGIS-002": "a12d9236-f001-4b96-976b-34e267b69735",
    "AEGIS-003": "e8bff93f-d781-4cf2-9d4c-10805dc31420",
    "AEGIS-004": "c3af4562-d0a2-43a9-8cca-55ce88a03995"
}

def patch_case(case_id, payer_id):
    print(f"PATCHing case {case_id} to payer {payer_id}...")
    resp = requests.patch(f"{BASE_URL}/cases/{case_id}", json={"payer_id": payer_id})
    print(f"Response: {resp.status_code} - {resp.text}")

def analyze_case(case_id):
    print(f"Analyzing case {case_id}...")
    resp = requests.post(f"{BASE_URL}/analysis/{case_id}/analyze", timeout=60)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Error analyzing {case_id}: {resp.status_code} - {resp.text}")
        return None

def verify():
    # 1. Correct Case 002 Payer
    patch_case(CASES["AEGIS-002"], "icici_lombard")
    
    results = {}
    for name, cid in CASES.items():
        print(f"\n--- Testing {name} ---")
        res = analyze_case(cid)
        if res:
            print(f"SCORE: {res['score']} ({res['band']})")
            print(f"MISSING: {res['missing_items']}")
            print(f"QUALITY: {res['quality_issues']}")
            print(f"CONSISTENCY: {res['consistency_flags']}")
            results[name] = res
            
    print("\n" + "="*50)
    print("GAUNTLET RESULTS SUMMARY")
    print("="*50)
    for name, res in results.items():
        print(f"{name}: {res['score']} [{res['band']}]")
    print("="*50)

if __name__ == "__main__":
    verify()
