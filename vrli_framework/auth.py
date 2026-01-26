# auth.py
import requests
import sys
import urllib3
from config import VRLI_HOST

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_token(username, password):
    url = f"https://{VRLI_HOST}:9543/api/v2/sessions"
    try:
        r = requests.post(url, 
            json={"username": username, "password": password, "provider": "ActiveDirectory"}, 
            headers={"Content-Type": "application/json"}, verify=False)
        r.raise_for_status()
        return r.json().get("sessionId")
    except Exception as e:
        sys.stderr.write(f"[-] Auth Error: {e}\n"); return None
