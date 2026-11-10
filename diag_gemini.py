import os, json, urllib.request, urllib.error
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

key = os.getenv("GEMINI_API_KEY", "").strip()
print("Model in .env:", repr(os.getenv("GEMINI_MODEL")))
print("Key length:", len(key), "| starts with:", key[:4])
print()

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=key, timeout=30, max_retries=0,
)

candidates = [
    "gemini-2.5-flash",
    "models/gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3-flash-preview",
]

print("--- OpenAI-compatible endpoint ---")
for m in candidates:
    try:
        r = client.chat.completions.create(
            model=m, messages=[{"role": "user", "content": "Say hi"}], max_tokens=20
        )
        print("OK  ", m, "->", (r.choices[0].message.content or "").strip())
    except Exception as e:
        body = getattr(e, "body", None)
        if body is None:
            try:
                body = e.response.text
            except Exception:
                body = None
        print("FAIL", m, "|", type(e).__name__, "|", str(e)[:150], "| body:", body)

print()
print("--- Native Gemini endpoint ---")
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
payload = {"contents": [{"parts": [{"text": "Say hi"}]}]}
req = urllib.request.Request(
    url, data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "x-goog-api-key": key},
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("NATIVE OK:", resp.read()[:300].decode("utf-8", "ignore"))
except urllib.error.HTTPError as e:
    print("NATIVE FAIL:", e.code, e.read()[:500].decode("utf-8", "ignore"))
except Exception as e:
    print("NATIVE ERROR:", type(e).__name__, e)