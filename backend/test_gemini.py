import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    print("X GEMINI_API_KEY is missing from .env")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")

questions = [
    "What is the capital of Tamil Nadu?",
    "What is the primary crop grown in the Cauvery delta region?",
    "Translate 'agriculture' into Tamil."
]

print("Testing Gemini Flash Latest API Key...\n")

for q in questions:
    print(f"Q: {q}")
    try:
        response = model.generate_content(q)
        print(f"A: {response.text.strip()}\n")
    except Exception as e:
        print(f"X Error calling Gemini: {e}\n")
