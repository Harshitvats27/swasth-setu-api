import json
import os

from dotenv import load_dotenv
from groq import Groq

from .rules import normalize
from .specialties import SPECIALTIES

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
URGENCY = ("routine", "urgent", "emergency")
_client = None
_cache: dict[str, dict] = {}

SYSTEM = f"""You help users of an Indian doctor-booking app.
The user describes a health problem in Hindi (Devanagari), Hinglish (Roman Hindi) or English, maybe with spelling mistakes.
Reply with JSON only:
{{"specializations": [up to 3, best first, ONLY from the allowed list], "urgency": "routine" | "urgent" | "emergency", "symptoms_en": [short English phrases]}}
Allowed specializations: {", ".join(SPECIALTIES)}.
Urgency: emergency = possible life threat (chest pain, breathing trouble, unconsciousness, heavy bleeding, stroke signs, poisoning, seizure). urgent = needs a doctor today (fracture, severe pain, injury). routine = everything else. If unsure, choose the higher urgency.
If nothing fits, use "General Medicine". Never give medical advice.
Examples:
"mere pet me dard hai" -> {{"specializations":["Gastroenterology","General Medicine"],"urgency":"routine","symptoms_en":["stomach pain"]}}
"meri taang tut gayi" -> {{"specializations":["Orthopedics"],"urgency":"urgent","symptoms_en":["broken leg"]}}
"seene me dard aur pasina" -> {{"specializations":["Cardiology","General Medicine"],"urgency":"emergency","symptoms_en":["chest pain","sweating"]}}
"bachche ko bukhar hai" -> {{"specializations":["Pediatrics"],"urgency":"routine","symptoms_en":["child fever"]}}"""


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"], timeout=8.0)
    return _client


def understand_query(text: str) -> dict | None:
    """Returns {'specializations', 'urgency', 'symptoms_en'} or None if the LLM failed."""
    key = normalize(text)
    if key in _cache:
        return _cache[key]
    try:
        resp = _get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": text[:300]},
            ],
            temperature=0,
            max_completion_tokens=500,
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        raw = json.loads(resp.choices[0].message.content)
    except Exception as e:
        print("understand_query failed:", repr(e))
        return None

    allowed = {s.lower(): s for s in SPECIALTIES}
    specs: list[str] = []
    items = raw.get("specializations", [])
    for s in items if isinstance(items, list) else []:
        s = allowed.get(str(s).strip().lower())
        if s and s not in specs:
            specs.append(s)
    urgency = raw.get("urgency")
    symptoms = raw.get("symptoms_en", [])
    result = {
        "specializations": specs[:3] or ["General Medicine"],
        "urgency": urgency if urgency in URGENCY else "routine",
        "symptoms_en": [str(x)[:60] for x in symptoms][:5] if isinstance(symptoms, list) else [],
    }
    if len(_cache) < 500:
        _cache[key] = result
    return result