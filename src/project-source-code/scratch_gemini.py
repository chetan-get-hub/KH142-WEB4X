import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path.cwd() / ".env"
load_dotenv(dotenv_path=env_path, override=True)

raw_key = os.getenv("GEMINI_API_KEY", "")
clean_key = raw_key.strip("\"' ")
print(f"Key configured: {bool(clean_key)}, length: {len(clean_key)}, starts with: {clean_key[:6] if clean_key else 'None'}")

if clean_key:
    try:
        from google import genai
        client = genai.Client(api_key=clean_key)
        # Try tiny test
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Respond with the single word OK."
        )
        print(f"Gemini 2.5 Flash Response: {response.text.strip()}")
    except Exception as e:
        print(f"Gemini 2.5 Flash Error: {e}")
        # Try gemini-1.5-flash if 2.5 is not accessible
        try:
            from google import genai
            client = genai.Client(api_key=clean_key)
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents="Respond with the single word OK."
            )
            print(f"Gemini 1.5 Flash Response: {response.text.strip()}")
        except Exception as e2:
            print(f"Gemini 1.5 Flash Error: {e2}")
