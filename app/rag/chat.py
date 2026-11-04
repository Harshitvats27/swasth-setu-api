import re

from app.rag.report_search import search_reports_multi
from app.search.rules import rule_urgency
from app.search.understand import MODEL, _get_client, understand_query

EMERGENCY_REPLY = (
    "This may be a medical emergency. Please call 108 or 112 now or go to the nearest hospital. "
    "यह आपातकाल हो सकता है। कृपया अभी 108 या 112 पर कॉल करें या नज़दीकी अस्पताल जाएँ।"
)

SYSTEM = """You are the Swasth Setu health information assistant for users in India.

You may get a REPORT CONTEXT: excerpts from the user's own uploaded medical reports, each tagged with the report type and page.

RULES FOR REPORT QUESTIONS
- Answer ONLY from the REPORT CONTEXT. Repeat names, values, units and ranges exactly as written, and mention the report type and page. Refer to a report only by the type in its tag, never by any ID or code that appears inside the text.
- Do NOT interpret results yourself. Never say a result is normal, abnormal, high, low, positive or negative, and never say an infection or disease is present or absent. You may repeat a flag or reference range only if the report itself prints it.
- Prefer the user's own result lines (test name, value, unit, reference range). Only if there are none, you may repeat explanatory text printed in the report, and you must say clearly that it is general text printed in the report, not the user's result.
- If the context has both the user's result lines and general explanatory text, answer with the result lines and do NOT quote the explanatory text unless the user asks what it means.
- If the context does not contain the answer, say it is not in the uploaded reports. Never guess a value.
- Do not repeat the same line twice.
- End by telling the user to discuss the report with their doctor.

RULES FOR GENERAL QUESTIONS
- Answer briefly in simple words and say it is general information.
- Never diagnose.
- NEVER mention any medicine, drug, drug class, painkiller, fever reducer, antibiotic, supplement, ointment or dose, not even over-the-counter ones, and never tell the user to check a label or dose. If the user asks what to take, say you cannot recommend medicines and that a doctor or pharmacist should advise them. Suggest only non-drug care such as rest, fluids and monitoring.
- Say when to see a doctor, and mention the doctor search in the app if relevant.

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
    "Otherwise (general health question, symptoms, advice, app help, greeting), output exactly: GENERAL"
)

HINGLISH_WORDS = {
    "kya", "hai", "hain", "mein", "meri", "mera", "mere", "kitna", "kitni", "kitne", "karna", "karne",
    "chahiye", "batao", "bata", "dikhao", "ka", "ke", "ko", "se", "nahi", "nahin", "hoga", "hota",
    "hoti", "kaise", "kab", "kaun", "kyun", "kyu", "aur", "toh", "raha", "rahi", "rahe", "likha",
    "dard", "bukhar", "dawai", "dawa", "lena", "sakta", "sakte", "sakti", "mujhe", "hum", "aap",
}


def _language_suffix(question: str) -> str:
    if any("\u0900" <= ch <= "\u097f" for ch in question):
        return "\n\n[Reply in Hindi, written in Devanagari script.]"
    words = set(re.findall(r"[a-z]+", question.lower()))
    if words & HINGLISH_WORDS:
        return ("\n\n[Reply in simple Hinglish, written in Roman letters, not Devanagari. "
                "Write your own sentences in Hinglish. Keep test names, numbers and any text "
                "copied from the report exactly as printed.]")
    return "\n\n[Reply in English.]"


def _route(question: str) -> tuple[bool, list[str]]:
    """Returns (is_report_question, list_of_english_search_queries)."""
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
            return True, queries or [question]
        if text.upper().startswith("GENERAL"):
            return False, []
        return True, [question]
    except Exception as e:
        print("route failed:", repr(e))
        return True, [question]


def answer(uid: str, question: str, history: list[dict] | None = None) -> dict:
    if rule_urgency(question) == "emergency":
        return {"answer": EMERGENCY_REPLY, "urgency": "emergency", "sources": [], "specialties": []}

    info = understand_query(question)
    urgency = info.get("urgency", "routine") if info else "routine"
    specialties = (info.get("specialties") or []) if info else []

    is_report, queries = _route(question)

    hits = []
    if is_report:
        try:
            hits = search_reports_multi(uid, queries, k=10)
        except Exception as e:
            print("report search failed:", repr(e))

    system = SYSTEM
    if hits:
        ctx = "\n\n".join(
            f"[{i + 1}] Report type: {h.get('type') or h.get('title', '')}, page {h.get('page')}\n{h.get('text', '')}"
            for i, h in enumerate(hits)
        )
        system += "\n\nREPORT CONTEXT:\n" + ctx
    elif is_report:
        system += "\n\nREPORT CONTEXT: (nothing relevant found in the user's uploaded reports)"
    else:
        system += "\n\nREPORT CONTEXT: (not needed for this question)"

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
    for h in hits:
        label = h.get("type") or h.get("title", "")
        key = (label, h.get("page"))
        if key not in seen:
            seen.add(key)
            sources.append({"title": label, "page": h.get("page")})

    return {"answer": text, "urgency": urgency, "sources": sources, "specialties": specialties}