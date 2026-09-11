import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path.cwd() / ".env"
load_dotenv(dotenv_path=env_path, override=True)

raw_key = os.getenv("GEMINI_API_KEY", "").strip("\"' ")

from google import genai
client = genai.Client(api_key=raw_key)

models_to_test = ["gemini-2.0-flash", "gemini-2.0-flash-lite-preview-02-05", "gemini-1.5-flash", "gemini-1.5-pro"]
for m in models_to_test:
    try:
        res = client.models.generate_content(
            model=m,
            contents="Say 'HELLO DC4X'"
        )
        print(f"MODEL {m} SUCCESS: {res.text.strip()}")
        break
    except Exception as e:
        print(f"MODEL {m} FAILED: {e}")
