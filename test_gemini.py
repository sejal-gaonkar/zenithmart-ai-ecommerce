import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
print("Model:", os.getenv("GEMINI_MODEL"))
print("Key found:", bool(os.getenv("GEMINI_API_KEY")))

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv("GEMINI_API_KEY"),
    timeout=20,
)
try:
    r = client.chat.completions.create(
        model=os.getenv("GEMINI_MODEL"),
        messages=[{"role": "user", "content": "Say hello"}],
    )
    print("REPLY:", r.choices[0].message.content)
except Exception as e:
    print("ERROR:", type(e).__name__, str(e)[:400])