from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

print("=== Testing /api/sos/all ===")
response = client.get("/api/sos/all")
print("Status:", response.status_code)
if response.status_code == 200:
    sos_list = response.json()
    print("Found SOS count:", len(sos_list))
    if len(sos_list) > 0:
        first_sos = sos_list[0]["sos_id"]
        print(f"\n=== Testing /api/sos/{first_sos}/recommendation ===")
        res2 = client.get(f"/api/sos/{first_sos}/recommendation")
        print("Status:", res2.status_code)
        print("Body:", json.dumps(res2.json(), indent=2))
    else:
        print("No SOS found to test recommendation.")
else:
    print("Error:", response.text)
