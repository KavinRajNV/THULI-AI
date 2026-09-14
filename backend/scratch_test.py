import openai, os
from dotenv import load_dotenv
load_dotenv('c:/Users/Lokesh S M/Desktop/SIH 2026/KISAN-AI/backend/.env')

client = openai.OpenAI(api_key=os.getenv('GROQ_API_KEY'), base_url='https://api.groq.com/openai/v1')
from services.ai_service import _build_user_message, SYSTEM_PROMPT

context = {
    "intents": ["general"],
    "weather": {
        "today": {"temp_c": 32.0, "rainfall_mm": 0.0, "humidity": 60, "condition": "(Advice: Irrigation can be considered based on soil moisture.)"},
        "tomorrow": {"chance_of_rain": 0, "rainfall_mm": 0.0, "condition": ""}
    }
}

user_message = _build_user_message("நாளைக்கு மழை வருமா?", {"language": "tamil"}, context)

response = client.chat.completions.create(
    model='openai/gpt-oss-120b',
    messages=[
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': user_message}
    ],
    temperature=0,
    max_tokens=200
)

print(f"Content: {repr(response.choices[0].message.content)}")
