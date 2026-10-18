import getpass
import requests

BASE_URL = "http://127.0.0.1:8010"

username = input("Admin username: ")
password = getpass.getpass("Admin password: ")

try:
    response = requests.post(
        f"{BASE_URL}/auth/login-json",
        json={"username": username, "password": password},
        timeout=10,
    )

    if response.status_code != 200:
        print("Login failed:", response.status_code, response.text)
        raise SystemExit(1)

    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{BASE_URL}/audit",
        headers=headers,
        timeout=10,
    )

    print("Audit endpoint status:", response.status_code)

    if response.status_code == 200:
        data = response.json()
        print("Audit records found:", data["count"])

        for log in data["logs"][:10]:
            print({
                "user_id": log["user_id"],
                "server": log["server_name"],
                "tool": log["tool_name"],
                "duration_ms": log["duration_ms"],
                "outcome": log["outcome"],
                "timestamp": log["timestamp"],
                "error_message": log["error_message"],
            })
    else:
        print("Audit request failed:", response.text)

except requests.RequestException as exc:
    print("Connection error:", exc)