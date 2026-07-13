import asyncio
from app.services.llm_service import llm_service

async def test():
    try:
        print("Calling LLM...")
        res = await llm_service.call_plain("Say hello")
        print("Success:", res)
    except Exception as e:
        print("Error:", repr(e))

asyncio.run(test())
