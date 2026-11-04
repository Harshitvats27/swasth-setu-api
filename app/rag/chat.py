import re

from app.rag.kb_search import search_kb
from app.rag.report_search import search_reports_multi
from app.search.rules import rule_urgency
from app.search.understand import MODEL, _get_client, understand_query

EMERGENCY_REPLY = (
    "This may be a medical emergency. Please call 108 or 112 now or go to the nearest hospital. "
    "यह आपातकाल हो सकता है। कृपया अभी 108 या 112 पर कॉल करें या नज़दीकी अस्पताल जाएँ।"
)

SYSTEM = """You are the Swasth Setu health information assistant for users in India.

You may get a REPORT CONTEXT (excerpts from the user's own uploaded medical reports, tagged with report type and page) or a KNOWLEDGE BASE CONTEXT (short health information pages from official sources). Use only the context that is given.

FORMAT
- Plain text only. Do not use markdown, asterisks, hashes or tables. Use short lines, and "-" at the start of a line for lists if needed.

ABOUT YOURSELF
- If the user asks who you are or what you can do, say: you are the Swasth Setu health assistant; you can read out what is written in their uploaded reports and give general health information from a small set of trusted pages; you cannot diagnose or recommend medicines.
- For greetings or thanks, reply politely and briefly and say what you can help with.

RULES FOR REPORT QUESTIONS
- Answer ONLY from the REPORT CONTEXT. Repeat names, values, units and ranges exactly as written, and mention the report type and page. Refer to a report only by the type in its tag, never by any ID or code that appears inside the text.
- When the user asks about a condition or topic (for example infection), FIRST list the matching result lines from the context (test name and value). THEN, only if the context has a separate explanatory sentence that adds something new, add one short line introduced as "the report also says". Never repeat a result line as an explanation, and never add an explanation just to fill space.
- Do NOT interpret results yourself. Never say a result is normal, abnormal, high, low, positive or negative, and never say an infection or disease is present or absent. You may repeat a flag or reference range only if the report itself prints it.
- Prefer the user's own result lines. Only if there are none, you may repeat explanatory text printed in the report, and you must say clearly that it is general text printed in the report, not the user's result.
- If the context does not contain the answer, say it is not in the uploaded reports. Never guess a value.
- Do not repeat the same line twice.
- End report answers by telling the user to discuss the report with their doctor.

RULES FOR GENERAL HEALTH QUESTIONS
- Answer ONLY from the KNOWLEDGE BASE CONTEXT, in simple words, and keep it short. Do not add medical facts from your own knowledge.
- Always include the warning signs or "when to see a doctor" points that appear in the context.
- If the KNOWLEDGE BASE CONTEXT has nothing relevant, say you do not have this information and suggest seeing a doctor or using the doctor search in the app. Do not guess.
- Never diagnose.
- NEVER mention any medicine, drug, drug class, painkiller, fever reducer, antibiotic, supplement, ointment or dose, not even over-the-counter ones, and never tell the user to check a label or dose. If the user asks what to take, say you cannot recommend medicines and that a doctor or pharmacist should advise them.
- If the user asks which kind of doctor to see, you may name the kind of doctor in plain words (for example general physician) and tell them to use the doctor search in the app.

LANGUAGE
- Follow the language instruction in brackets at the end of the user's message.
- Do not write any disclaimer line. The app already shows one."""

ROUTER_PROMPT = (
    "You route messages for a health app. Decide if the user is asking about THEIR OWN uploaded "
    "medical reports, lab results, test values, or what is written in their report.\n"
    "If yes, output exactly one line: REPORT: query1 | query2 | query3\n"
    "Each query is a short English search query (max 10 words) for a lab report. "
    "query1 is a literal English rewrite of the user's question. query2 and query3 look for the same topic "
    "using different likely test names or section names. "
    "Example for a question about infection: REPORT: infection | Widal typhoid antibody titer | WBC count CRP\n"
    "Otherwise output exactly one line: GENERAL: <short English search query, max 10 words, for a health "
    "information knowledge base>. This includes general health questions, symptoms, first aid, advice, "
    "which doctor to see, app help, greetings, and questions about the assistant itself. "
    "Example: GENERAL: what to do for fever"
)

HINGLISH_WORDS = {
    "kya", "hai", "hain", "mein", "meri", "mera", "mere", "kitna", "kitni", "kitne", "karna", "karne",
    "chahiye", "batao", "bata", "dikhao", "ka", "ke", "ko", "se", "nahi", "nahin", "hoga", "hota",
    "hoti", "kaise", "kab", "kaun", "kyun", "kyu", "aur", "toh", "raha", "rahi", "rahe", "likha",
    "dard", "bukhar", "dawai", "dawa", "lena", "sakta", "sakte", "sakti", "mujhe", "hum", "aap",
    "tu", "tum", "kon", "h", "hu", "hun", "ho", "yeh", "ye", "bhai", "yaar", "nhi", "bhi", "koi",
    "kuch", "liye", "lun", "dun", "gaya", "gayi", "jal", "leni", "lene", "kare", "karun", "kaunsi",
    "kaunsa", "kahan", "kidhar", "wala", "wali", "mera", "apna", "apni", "pet", "sir", "haath",
}

EXPLANATORY = re.compile(r"may indicate|suggests|in general|can indicate|may be due", re.I)

CHEST_WORDS = {"chaati", "chhati", "chati", "chhaati", "seene", "seena", "sine", "chest", "heart"}
PAIN_WORDS = {
    "dard", "dukh", "dukhe", "dukhta", "dukhti", "dukhna", "pain", "painful", "bhaari", "bhari",
    "jakad", "jakdan", "pressure", "jalan", "tightness", "dabav",
}
BREATH_WORDS = {"saans", "sans", "breath", "breathing", "breathe"}
BREATH_PROBLEM = {"nahi", "nahin", "dikkat", "takleef", "phool", "ruk", "difficulty", "cant", "cannot", "trouble", "short"}
FAINT_WORDS = {"behosh", "bayhosh", "unconscious", "fainted"}


def _extra_emergency(question: str) -> bool:
    """Extra keyword safety net on top of rule_urgency (not complete)."""
    q = question.lower()
    words = set(re.findall(r"[a-z]+", q))
    if words & CHEST_WORDS and words & PAIN_WORDS:
        return True
    if words & BREATH_WORDS and words & BREATH_PROBLEM:
        return True
    if words & FAINT_WORDS:
        return True
    return "heart attack" in q or "dil ka daura" in q


def _is_result_chunk(text: str) -> bool:
    """Result-like chunk: most lines contain numbers and it is not explanatory text."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines or EXPLANATORY.search(text):
        return False
    with_digit = sum(1 for l in lines if re.search(r"\d", l))
    return with_digit / len(lines) >= 0.6


def _close_hits(items: list[dict], margin: float = 0.12) -> list[dict]:
    """Keep only hits whose distance is close to the best match (used for the sources list)."""
    ds = [h.get("distance") for h in items if h.get("distance") is not None]
    if not ds:
        return items
    best = min(ds)
    return [h for h in items if h.get("distance") is None or h["distance"] <= best + margin]


def _language_suffix(question: str) -> str:
    if any("\u0900" <= ch <= "\u097f" for ch in question):
        return "\n\n[Reply in Hindi, written in Devanagari script.]"
    words = set(re.findall(r"[a-z]+", question.lower()))
    if words & HINGLISH_WORDS:
        return ("\n\n[Reply in simple Hinglish, written in Roman letters, not Devanagari. "
                "Write your own sentences in Hinglish. Keep test names, numbers and any text "
                "copied from the report exactly as printed.]")
    return "\n\n[Reply in English.]"


def _route(question: str) -> tuple[bool, list[str], str]:
    """Returns (is_report_question, report_search_queries, kb_search_query)."""
    try:
        r = _get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": ROUTER_PROMPT},
                {"role": "user", "content": question[:500]},
            ],
            temperature=0,
            max_completion_tokens=300,
            reasoning_effort="low",
        )
        text = (r.choices[0].message.content or "").strip()
        if text.upper().startswith("REPORT:"):
            queries = [q.strip() for q in text[7:].split("|") if q.strip()][:3]
            return True, queries or [question], ""
        if text.upper().startswith("GENERAL"):
            q = text.split(":", 1)[1].strip() if ":" in text else ""
            return False, [], q or question
        return False, [], question
    except Exception as e:
        print("route failed:", repr(e))
        return False, [], question


def answer(uid: str, question: str, history: list[dict] | None = None) -> dict:
    if rule_urgency(question) == "emergency" or _extra_emergency(question):
        return {"answer": EMERGENCY_REPLY, "urgency": "emergency", "sources": [], "specialties": []}

    info = understand_query(question)
    urgency = info.get("urgency", "routine") if info else "routine"
    specialties = []
    if info and info.get("symptoms_en"):
        specialties = list(info.get("specializations") or [])

    if urgency == "emergency":
        return {"answer": EMERGENCY_REPLY, "urgency": "emergency", "sources": [], "specialties": []}

    is_report, queries, kb_query = _route(question)
    if is_report:
        specialties = []   # no "Find a doctor" button on questions about the user's own report

    hits, kb_hits = [], []
    if is_report:
        try:
            hits = search_reports_multi(uid, queries, k=10)
        except Exception as e:
            print("report search failed:", repr(e))
        # result-like chunks first, then by distance (sort is stable)
        hits.sort(key=lambda h: (not _is_result_chunk(h.get("text", "")), h.get("distance", 1.0)))
    else:
        try:
            kb_hits = search_kb(kb_query or question, k=4)
        except Exception as e:
            print("kb search failed:", repr(e))

    system = SYSTEM
    if is_report:
        if hits:
            ctx = "\n\n".join(
                f"[{i + 1}] Report type: {h.get('type') or h.get('title', '')}, page {h.get('page')}\n{h.get('text', '')}"
                for i, h in enumerate(hits)
            )
            system += "\n\nREPORT CONTEXT:\n" + ctx
        else:
            system += "\n\nREPORT CONTEXT: (nothing relevant found in the user's uploaded reports)"
    else:
        if kb_hits:
            ctx = "\n\n".join(f"[{i + 1}] {h.get('text', '')}" for i, h in enumerate(kb_hits))
            system += "\n\nKNOWLEDGE BASE CONTEXT:\n" + ctx
        else:
            system += "\n\nKNOWLEDGE BASE CONTEXT: (nothing relevant found)"

    messages = [{"role": "system", "content": system}]
    for m in (history or [])[-6:]:
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
            messages.append({"role": m["role"], "content": m["content"][:500]})
    messages.append({"role": "user", "content": question[:500] + _language_suffix(question)})

    text = ""
    try:
        for attempt in range(2):
            resp = _get_client().chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.2,
                max_completion_tokens=1500,
                reasoning_effort="low",
                timeout=40.0,
            )
            choice = resp.choices[0]
            text = (choice.message.content or "").strip()
            if text:
                break
            print("empty answer, finish_reason:", choice.finish_reason)
    except Exception as e:
        print("chat failed:", repr(e))
        return {"answer": "Sorry, the assistant is busy. Please try again in a minute.",
                "urgency": urgency, "sources": [], "specialties": specialties}

    if not text:
        text = "Sorry, I could not prepare an answer this time. Please try again."

    seen, sources = set(), []
    if is_report:
        for h in _close_hits(hits):
            label = h.get("type") or h.get("title", "")
            key = (label, h.get("page"))
            if key not in seen:
                seen.add(key)
                sources.append({"title": label, "page": h.get("page"), "url": None})
    else:
        for h in _close_hits(kb_hits):
            key = h.get("file")
            if key in seen:
                continue
            seen.add(key)
            src = str(h.get("source", ""))
            sources.append({"title": h.get("title", ""), "page": None, "url": src if src.startswith("http") else None})

    return {"answer": text, "urgency": urgency, "sources": sources, "specialties": specialties}