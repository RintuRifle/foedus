"""Test the brochure upload with the working model."""
import requests

# Register fresh user
res = requests.post("http://localhost:8000/api/v1/auth/register", json={
    "email": "test_modelfix@sme.in",
    "password": "password123",
    "full_name": "Model Fix Test",
    "company_name": "Test Co"
})
if res.status_code == 400:
    res = requests.post("http://localhost:8000/api/v1/auth/login", json={
        "email": "test_modelfix@sme.in",
        "password": "password123"
    })

print("Auth status:", res.status_code)
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

with open("sample_brochure_nexasolar.pdf", "rb") as f:
    upload_res = requests.post(
        "http://localhost:8000/api/v1/company/onboard-brochure",
        headers=headers,
        files={"file": f}
    )

print("Upload status:", upload_res.status_code)
import json
print("Response:", json.dumps(upload_res.json(), indent=2))
