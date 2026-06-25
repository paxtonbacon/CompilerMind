# config.py
import os
import json
from pathlib import Path

DEEPSEEK_API_KEY = "your_key"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-v4-flash"

# ── 用户凭据（持久化到文件） ──
_CRED_FILE = Path(__file__).parent / ".credentials.json"

def _load_credentials():
    if _CRED_FILE.exists():
        try:
            return json.loads(_CRED_FILE.read_text())
        except Exception:
            pass
    return {"username": "com123", "password": "com123"}

def _save_credentials(data: dict):
    _CRED_FILE.write_text(json.dumps(data))

def get_credentials():
    return _load_credentials()

def update_credentials(new_username: str, new_password: str):
    _save_credentials({"username": new_username, "password": new_password})

MODEL_NAME = "deepseek-v4-flash"