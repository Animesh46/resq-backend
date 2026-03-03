from fastapi import APIRouter
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging

genai.configure(api_key=os.getenv("AIzaSyBjuQTDPhOVN7MTYzbIzHVpPkveBKNjg34"))
load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy initialization
_gemini_client = None

def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                _gemini_client = genai.Client(api_key=api_key)
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.error(f"Gemini client init failed: {e}")
                _gemini_client = False  # Mark as failed
        else:
            logger.warning("GEMINI_API_KEY not set")
            _gemini_client = False
    return _gemini_client if _gemini_client is not False else None


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    location: str
    disaster: str
    message: str
    history: list[ChatMessage] | None = None  # Conversation history for context
    language: str = "en"  # user's preferred response language (e.g. 'hi','ta','en')


SYSTEM_PROMPT = """You are ResQ AI, a compassionate and knowledgeable disaster emergency assistant. 
Your role is to help users:
- Understand disaster risks and warnings
- Get personalized safety advice for their location and situation
- Learn survival steps and essential supplies needed
- Know when and how to contact emergency services
- Make informed decisions during crises

Guidelines:
- Be calm, clear, and practical in all advice
- Avoid exaggeration; stick to facts
- Always recommend official authorities (112 in India, 911 in US, etc.)
- Prioritize life safety above everything else
- If unsure, acknowledge the limitation and suggest official sources
- Be empathetic; people may be scared or confused
- Keep responses concise but complete
- Include actionable steps when possible

The user may ask about:
- Their current situation and risk level
- Specific disasters (flood, cyclone, earthquake, etc.)
- Preparedness and supplies
- Evacuation routes and shelters
- Family/group safety planning
- Any concern related to disaster resilience

Always contextualize advice based on their location and the disaster type they mention."""


async def get_llm_response(user_message: str, location: str, disaster: str, history: list[ChatMessage] | None = None) -> str:
    """Call Gemini API to generate intelligent, conversational response."""
    gemini_client = get_gemini_client()
    if not gemini_client:
        return None  # Fallback to offline mode
    
    try:
        # Build full conversation with system context
        context = f"[Location: {location}, Disaster Type: {disaster}]"
        full_prompt = f"{SYSTEM_PROMPT}\n\n{context}\n\nUser message: {user_message}"
        
        # Call Gemini with available model
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_prompt
        )
        
        return response.text if response and response.text else None
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None


@router.post("/")
async def disaster_chat(req: ChatRequest):
    """Smart conversational chat endpoint with optional Gemini LLM."""
    
    # Try LLM first
    gemini_client = get_gemini_client()
    if gemini_client:
        reply = await get_llm_response(
            user_message=req.message,
            location=req.location,
            disaster=req.disaster,
            history=req.history or []
        )
        if reply:
            return {"reply": reply}
    
    # Fallback: Generate smart conversational response based on intent
    message_lower = req.message.lower() if req.message else ""
    location = req.location or "your area"
    disaster = req.disaster or "general"
    
    # Determine city name to use for vulnerability lookup
    from modules.location_intelligence import resolve_city_input

    def extract_city(text: str) -> str | None:
        if not text:
            return None
        low = text.lower()
        from modules.location_intelligence import LOCATION_VULNERABILITIES
        for city in LOCATION_VULNERABILITIES.keys():
            if city in low:
                return city
        return None

    raw_city = extract_city(req.message) or None
    # if location string contains letters, treat it as city too
    if not raw_city and req.location and any(c.isalpha() for c in req.location):
        raw_city = req.location.split(',')[0].strip().lower()

    if raw_city:
        city = resolve_city_input(raw_city)
    else:
        city = "general"

    approx_note = ""
    if raw_city and city != raw_city and city != "general":
        approx_note = f"(using data for {city.title()} based on '{raw_city}')"

    # Detect intent from user message
    is_asking_affected_areas = any(w in message_lower for w in ["where", "affected", "impact", "zone", "area", "location", "avoid", "place"])
    is_asking_evacuation = any(w in message_lower for w in ["go", "evacuate", "leave", "shelter", "safe"])
    is_asking_supplies = any(w in message_lower for w in ["supplies", "pack", "bring", "prepare", "kit", "need"])
    is_asking_steps = any(w in message_lower for w in ["do", "should", "how", "what", "steps", "action"])
    
    # Build natural response
    reply_lines = []
    
    # Greeting
    location_str = f"in {city.title()}" if city and city != "general" else "in your area"
    if approx_note:
        reply_lines.append(approx_note)
    if req.message:
        reply_lines.append(f"Based on {disaster.upper()} risk {location_str}:")
    else:
        reply_lines.append(f"{disaster.upper()} Safety Information for {location_str}:")
    reply_lines.append("")
    
    # Address affected areas if asked
    if is_asking_affected_areas or not req.message:
        reply_lines.append(f"**❌ Areas to AVOID in {city.title()}:**")
        from modules.location_intelligence import get_vulnerable_areas
        vulnerable = await get_vulnerable_areas(city, disaster)
        for area in vulnerable[:5]:
            reply_lines.append(f"  • {area}")
        reply_lines.append("")
    
    # Address evacuation/shelter if asked
    if is_asking_evacuation:
        reply_lines.append("**✅ Safe LOCATIONS to Go:**")
        from modules.location_intelligence import get_safe_locations
        safe = await get_safe_locations(city, disaster)
        for place in safe[:4]:
            reply_lines.append(f"  • {place}")
        reply_lines.append("  • Contact 112 for nearest government shelter")
        reply_lines.append("")
    
    # Address immediate steps
    if is_asking_steps or not req.message:
        reply_lines.append("**Immediate Steps:**")
        steps = _get_action_steps(disaster)
        for i, step in enumerate(steps[:5], 1):
            reply_lines.append(f"{i}. {step}")
        reply_lines.append("")
    
    # Address supplies if asked
    if is_asking_supplies or not req.message:
        reply_lines.append("**Essential Supplies:**")
        supplies = ["Water (3 days)", "Non-perishable food", "First aid kit", "Flashlight + batteries", "Phone + charger", "Important documents"]
        for supply in supplies:
            reply_lines.append(f"• {supply}")
        reply_lines.append("")
    
    # Always add emergency contacts
    reply_lines.append("**Get Help:**")
    reply_lines.append("📞 Call 112 (India) — National Emergency")
    reply_lines.append("📞 Local disaster management office")
    reply_lines.append("📍 Ask locals for nearest shelter")
    
    final = "\n".join(reply_lines)
    # translate if requested
    if req.language and req.language.lower() != "en":
        try:
            from modules.gemini import translate_text
            final = await translate_text(final, req.language)
        except Exception:
            pass
    return {"reply": final}


def _get_affected_areas(disaster: str) -> list[str]:
    """Return affected areas based on disaster type."""
    areas = {
        "flood": ["Low-lying areas", "River/drainage channels", "Basements and ground floors", "Areas near water bodies"],
        "cyclone": ["Coastal zones", "Exposed areas", "Weakly-built structures", "High-rise buildings (wind risk)"],
        "earthquake": ["Older buildings", "Near cliffs/slopes", "Dense urban areas", "Areas near fault lines"],
        "heatwave": ["Open areas without shade", "Urban concrete zones", "Places without cooling", "Outdoor work zones"],
        "wildfire": ["Forested/vegetated areas", "Hillside communities", "Areas with dry brush", "Downwind zones"],
    }
    return areas.get(disaster.lower(), ["Areas closest to the center", "Dense populations", "Areas with poor infrastructure"])


def _get_action_steps(disaster: str) -> list[str]:
    """Return action steps based on disaster type."""
    steps = {
        "flood": [
            "Move to higher ground immediately",
            "Don't cross flooded areas — currents are dangerous",
            "If trapped, signal from roof or window",
            "Turn off electricity at main switch",
            "Keep important documents in waterproof bags"
        ],
        "cyclone": [
            "Stay indoors — away from windows",
            "Secure all loose outdoor items",
            "Do NOT venture out during the storm",
            "Keep emergency contacts ready",
            "Listen to official alerts from IMD/authorities"
        ],
        "earthquake": [
            "DROP, COVER, HOLD ON under sturdy table",
            "Stay away from windows and falling objects",
            "If outdoors, move away from buildings",
            "After shaking stops, evacuate carefully",
            "Expect aftershocks — stay alert"
        ],
        "heatwave": [
            "Stay in shade or cool places",
            "Drink water constantly — don't wait until thirsty",
            "Avoid going out during peak heat (11 AM - 4 PM)",
            "Check on elderly neighbors regularly",
            "Use cooling centers in your community"
        ],
        "general": [
            "Stay calm and follow official instructions",
            "Move to safety if directed",
            "Keep emergency contacts accessible",
            "Monitor official news and alerts",
            "Help others if you can"
        ]
    }
    return steps.get(disaster.lower(), steps["general"])