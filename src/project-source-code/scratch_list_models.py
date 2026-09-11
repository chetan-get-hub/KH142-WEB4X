import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path.cwd() / ".env"
load_dotenv(dotenv_path=env_path, override=True)

raw_key = os.getenv("GEMINI_API_KEY", "").strip("\"' ")

from google import genai
client = genai.Client(api_key=raw_key)

try:
    print("Listing available models for this API key:")
    for m in client.models.list():
        if "generateContent" in (m.supported_actions or []):
            print(f"- {m.name} (display: {m.display_name})")
except Exception as e:
    print(f"List models error: {e}")

# Try gemini-2.0-flash or gemini-2.0-flash-exp or gemini-1.5-flash-latest or gemini-2.5-flash
test_models = ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash-8b", "gemini-1.5-pro", "gemini-2.5-flash", "gemini-3.6-flash"]
for t_model in test_models:
    try:
        res = client.models.generate_content(model=t_model, contents="Respond with the single word OK.")
        print(f"SUCCESS with model: {t_model} -> Response: {res.text.strip()}")
        break
    except Exception as err:
        print(f"Failed with model {t_model}: {err}")
