import asyncio
from modules import gemini

async def run():
    print("translating to hindi:")
    res = await gemini.translate_text("Hello world", "hi")
    print(res)

    print("translating to english (no-op):")
    res2 = await gemini.translate_text("Bonjour", "en")
    print(res2)

if __name__ == "__main__":
    asyncio.run(run())
