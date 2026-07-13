import asyncio
import json
import uuid
import time
import requests
import sys

BASE_URL = "http://localhost:8001/api/v1"

def run_test():
    print("🚀 Starting Foedus E2E Test Workflow...")
    
    # 1. Register User
    print("\n[1] Registering User...")
    user_data = {
        "email": f"test_{int(time.time())}@sme.in",
        "password": "password123",
        "full_name": "Test SME Corporation"
    }
    
    # Wait for server to be up
    for _ in range(5):
        try:
            requests.get("http://localhost:8001/health")
            break
        except requests.exceptions.ConnectionError:
            print("  Waiting for server...")
            time.sleep(2)
            
    res = requests.post(f"{BASE_URL}/auth/register", json=user_data)
    if res.status_code != 201:
        print(f"❌ Failed to register: {res.text}")
        sys.exit(1)
        
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ User registered. Token acquired.")
    
    # 2. Get Feed
    print("\n[2] Fetching Tenders Feed...")
    res = requests.get(f"{BASE_URL}/tenders/search", headers=headers)
    if res.status_code != 200:
        print(f"❌ Failed to fetch feed: {res.text}")
        sys.exit(1)
        
    tenders = res.json()
    if not tenders:
        print("⚠️ No tenders found in DB. Running scraper manually via script is required first.")
        # We can simulate one for the test if needed.
        sys.exit(1)
        
    tender = tenders["items"][0]
    tender_id = tender["tender"]["id"]
    print(f"✅ Found {len(tenders)} tenders. Selected Tender: {tender["tender"]["title"]} ({tender_id})")
    
    # 3. Start Evaluation
    print("\n[3] Starting Evaluation Pipeline...")
    res = requests.post(f"{BASE_URL}/evaluations/start", json={"tender_id": tender_id}, headers=headers)
    if res.status_code != 202:
        print(f"❌ Failed to start evaluation: {res.text}")
        sys.exit(1)
        
    job_id = res.json()["job_id"]
    print(f"✅ Evaluation started! Job ID: {job_id}")
    
    # 4. Poll Status
    print("\n[4] Polling Evaluation Status...")
    while True:
        res = requests.get(f"{BASE_URL}/evaluations/{job_id}/status", headers=headers)
        if res.status_code != 200:
            print(f"❌ Failed to poll status: {res.text}")
            sys.exit(1)
            
        status = res.json()
        state = status["status"]
        progress = status["progress_pct"]
        agent = status["current_agent"]
        
        print(f"   ⏳ Status: {state} | Progress: {progress}% | Agent: {agent}")
        
        if state in ["completed", "failed"]:
            break
            
        time.sleep(3)
        
    if state == "failed":
        print(f"❌ Evaluation failed: {status.get('error_log')}")
        sys.exit(1)
        
    print("✅ Evaluation completed successfully!")
    
    # 5. Get Report (Optional, depends if endpoint exists)
    print("\n🎉 Test Finished Successfully!")

if __name__ == "__main__":
    run_test()
