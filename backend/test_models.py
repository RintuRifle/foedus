import asyncio
from google import genai
from app.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)
models = client.models.list()
for m in models:
    print(m.name)
