import requests
import base64
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000/api"
PC_NAME = "SIMULATION_TEST_PC"

def register():
    print(f"Registering {PC_NAME}...")
    res = requests.post(f"{BASE_URL}/register", json={"pc_name": PC_NAME})
    print(res.json())

def send_file_result():
    print("Sending File List result...")
    # Matches the format central_client.py would send
    fake_files = {
        "path": "C:\\Fake\\Directoy",
        "items": [
            {"name": "secret_plans.txt", "type": "file", "size": 1024},
            {"name": "passwords.txt", "type": "file", "size": 2048},
            {"name": "Windows", "type": "dir", "size": 0}
        ]
    }
    # central_client sends str() of the dict
    result_text = str(fake_files)
    
    res = requests.post(f"{BASE_URL}/result", json={
        "pc_name": PC_NAME, 
        "result": result_text
    })
    print("Files Result Sent:", res.json())

def send_screenshot():
    print("Sending Screenshot...")
    # Create a tiny 1x1 white pixel png
    pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR4nGP6DwABBAEKKQV8CAAAAABJRU5ErkJggg==")
    b64 = base64.b64encode(pixel).decode('utf-8')
    
    res = requests.post(f"{BASE_URL}/screenshot_capture/{PC_NAME}", json={
        "image": b64
    })
    print("Screenshot Sent:", res.json())

if __name__ == "__main__":
    register()
    time.sleep(2)
    send_file_result()
    time.sleep(2)
    send_screenshot()
