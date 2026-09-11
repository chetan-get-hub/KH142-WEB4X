import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path.cwd() / ".env"
load_dotenv(dotenv_path=env_path, override=True)

raw_key = os.getenv("GEMINI_API_KEY", "").strip("\"' ")

from google import genai
client = genai.Client(api_key=raw_key)

try:
    res = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Say 'HELLO DC4X'"
    )
    print(f"GEMINI-3.6-FLASH SUCCESS: {res.text.strip()}")
except Exception as e:
    print(f"GEMINI-3.6-FLASH FAILED: {e}")
