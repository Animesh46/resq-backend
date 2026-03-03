"""Translation router using Gemini."""
from fastapi import APIRouter
from models import TranslateRequest
from modules.gemini import translate_text

router = APIRouter()

@router.post("/")
async def translate(req: TranslateRequest):
    translated = await translate_text(req.text, req.target_language)
    return {"original": req.text, "translated": translated, "language": req.target_language}

@router.post("/batch")
async def translate_batch(texts: list[str], target_language: str):
    import asyncio
    translated = await asyncio.gather(*[translate_text(t, target_language) for t in texts])
    return {"translated": list(translated), "language": target_language}
