import os
import io

# Setup test environment variables BEFORE importing config
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["GOOGLE_API_KEY"] = "test-fake-key"
os.environ["MAX_UPLOAD_MB"] = "1"

from fastapi.testclient import TestClient
from app import app
from config import settings

client = TestClient(app)

def main():
    print(f"Max Upload Bytes Configured: {settings.max_upload_bytes}")
    
    print("\n--- Test 1: CORS Headers Validation ---")
    res = client.options("/upload", headers={
        "Origin": "http://evil-cors-domain.com",
        "Access-Control-Request-Method": "POST"
    })
    print(f"Evil Origin Response Status: {res.status_code}")
    if "evil-cors-domain.com" not in res.headers.get("access-control-allow-origin", ""):
        print("PASS: Evil origin blocked by CORS")
    else:
        print("FAIL: Evil origin allowed")

    res = client.options("/upload", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST"
    })
    print(f"Allowed Origin Response Status: {res.status_code}")
    if res.headers.get("access-control-allow-origin") == "http://localhost:5173":
        print("PASS: Allowed origin correctly set in CORS headers")
    else:
        print("FAIL: Allowed origin not returned")
        
    print("\n--- Test 2: Upload File Security (Size limit) ---")
    row = b'a,b,c\n'
    large_file_content = b'col1,col2,col3\n' + row * (1024 * 1024 // len(row) * 2) # 2 MB
    res = client.post("/upload", files={"file": ("large.csv", io.BytesIO(large_file_content), "text/csv")})
    print(f"Large Upload Status: {res.status_code}")
    if res.status_code == 413 or (res.status_code == 400 and "exceeds maximum allowed limit" in res.text):
        print("PASS: Large upload blocked (size limit enforced)")
    else:
        print(f"FAIL: Large upload returned {res.status_code}, response: {res.text}")
        
    print("\n--- Test 3: Upload Binary File (Magic Bytes) ---")
    binary_file_content = b"\x4d\x5a" + b"b" * 100
    res = client.post("/upload", files={"file": ("evil.csv", io.BytesIO(binary_file_content), "text/csv")})
    print(f"Binary Upload Status: {res.status_code}")
    if res.status_code == 400 and "binary or executable type" in res.text:
        print("PASS: Binary upload blocked")
    else:
        print(f"FAIL: Binary upload returned {res.status_code}, response: {res.text}")

    print("\n--- Test 4: Dataset UUID Isolation ---")
    valid_csv = b"col1,col2\n1,2\n3,4"
    res = client.post("/upload", files={"file": ("data.csv", io.BytesIO(valid_csv), "text/csv")})
    if res.status_code == 200:
        dataset_id = res.json().get("dataset_id")
        print(f"Upload successful, UUID: {dataset_id}")
        
        res = client.post("/chat", json={"question": "sum col1", "dataset_id": "data.csv"})
        print(f"Legacy filename lookup status: {res.status_code}")
        if res.status_code in (404, 422, 400):
            print("PASS: Filename-based lookup successfully blocked")
        else:
            print(f"FAIL: Filename-based lookup allowed, status: {res.status_code}")
    else:
        print(f"FAIL: Valid upload failed with {res.status_code}, {res.text}")

if __name__ == "__main__":
    main()
