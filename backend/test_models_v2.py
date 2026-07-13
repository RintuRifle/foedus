"""Test which Gemini models actually work with this API key."""
import asyncio
from google import genai
from app.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

MODELS_TO_TRY = [
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]

async def test_model(name):
    try:
        resp = client.models.generate_content(
            model=name,
            contents="Say hello in one word.",
        )
        print(f"  ✅ {name}: {resp.text.strip()[:50]}")
        return True
    except Exception as e:
        err = str(e)[:80]
        print(f"  ❌ {name}: {err}")
        return False

async def main():
    print("Testing models...\n")
    for m in MODELS_TO_TRY:
        ok = await test_model(m)
        if ok:
            print(f"\n🎯 WINNER: {m}")
            return
        await asyncio.sleep(1)  # avoid burst
    print("\n⚠️  No model worked!")

asyncio.run(main())
