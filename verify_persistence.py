import time
import subprocess
import httpx
import sys
import os
import signal

BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = "/v1"

def wait_for_server(retries=10, delay=2):
    url = f"{BASE_URL}/health"
    print(f"Waiting for server at {url}...")
    for i in range(retries):
        try:
            resp = httpx.get(url)
            if resp.status_code == 200:
                print("✅ Server is up!")
                return True
        except httpx.ConnectError:
            pass
        except Exception as e:
            print(f"Connect error: {e}")
            pass
        time.sleep(delay)
    print("❌ Server failed to start.")
    return False

def run_verification():
    # 1. Start Server (First Run)
    print("\n--- [Step 1] Starting Server (Initial) ---")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "DB_ECHO": "True"} # Enable echo to see SQL
    )
    
    try:
        if not wait_for_server():
            server_logs = proc.communicate(timeout=2)
            print("Server Stdout:", server_logs[0].decode())
            print("Server Stderr:", server_logs[1].decode())
            raise Exception("Server start failed")

        # 2. Register User
        print("\n--- [Step 2] Registering User (Persistence Test) ---")
        reg_payload = {
            "email": "persist_hub@test.com",
            "username": "persist_hub",
            "password": "securePassword123",
            "role": "HUB_OWNER"
        }
        reg_url = f"{BASE_URL}{API_PREFIX}/auth/register"
        resp = httpx.post(reg_url, json=reg_payload)
        
        if resp.status_code == 400 and "already registered" in resp.text:
            print("⚠️ User already exists (persistence working from previous run?)")
        elif resp.status_code == 201:
            print("✅ User Registered Successfully")
            print(resp.json())
        else:
            print(f"❌ Registration Failed: {resp.status_code} {resp.text}")
            raise Exception("Registration failed")

    finally:
        print("\n--- [Step 3] Stopping Server ---")
        proc.send_signal(signal.SIGTERM)
        proc.wait()
    
    time.sleep(2) # Wait for port release

    # 3. Restart Server
    print("\n--- [Step 4] Restarting Server (Verification) ---")
    proc2 = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )

    try:
        if not wait_for_server():
            raise Exception("Server restart failed")

        # 4. Login
        print("\n--- [Step 5] Logging In (Post-Restart) ---")
        login_payload = {
            "username": "persist_hub",
            "password": "securePassword123"
        }
        login_url = f"{BASE_URL}{API_PREFIX}/auth/login"
        resp = httpx.post(login_url, json=login_payload)
        
        if resp.status_code == 200:
            print("✅ Login Successful (User Persisted!)")
            token_data = resp.json()
            token = token_data["access_token"]
            print(f"Token: {token[:20]}...")
            
            # 5. Verify /me
            print("\n--- [Step 6] Verifying Identity ---")
            me_url = f"{BASE_URL}{API_PREFIX}/auth/me"
            resp = httpx.get(me_url, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                print("✅ Identity Verified")
                print(resp.json())
            else:
                print(f"❌ Identity Check Failed: {resp.status_code}")
        else:
            print(f"❌ Login Failed (Persistence Issue?): {resp.status_code} {resp.text}")
            raise Exception("Login failed after restart")

    finally:
        print("\n--- [Step 7] Stopping Server ---")
        proc2.send_signal(signal.SIGTERM)
        proc2.wait()

if __name__ == "__main__":
    run_verification()
