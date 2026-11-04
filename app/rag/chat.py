from app.rag.report_search import search_reports
from app.search.rules import rule_urgency
from app.search.understand import MODEL, _get_client, understand_query

EMERGENCY_REPLY = (
    "This may be a medical emergency. Please call 108 or 112 now or go to the nearest hospital. "
    "यह आपातकाल हो सकता है। कृपया अभी 108 या 112 पर कॉल करें या नज़दीकी अस्पताल जाएँ।"
)

SYSTEM = """You are the Swasth Setu health information assistant for users in India.

You may get a REPORT CONTEXT: excerpts from the user's own uploaded medical reports, each tagged with the report title and page.

RULES FOR REPORT QUESTIONS
- Answer ONLY from the REPORT CONTEXT. Repeat names, values, units and ranges exactly as written, and mention the report title and page.
- Do NOT interpret results yourself. Never say a result is normal, abnormal, high, low, positive or negative, and never say an infection or disease is present or absent. You may repeat a flag or reference range only if the report itself prints it.
- Prefer the user's own result lines (test name, value, unit, reference range). Only if there are none, you may repeat explanatory text printed in the report, and you must say clearly that it is general text printed in the report, not the user's result.
- If the context has both the user's result lines and general explanatory text, answer with the result lines and do NOT quote the explanatory text unless the user asks what it means.
- If the context does not contain the answer, say it is not in the uploaded reports. Never guess a value.
- End by telling the user to discuss the report with their doctor.

RULES FOR GENERAL QUESTIONS
- Answer briefly in simple words and say it is general information.
- Never diagnose. Never suggest medicine names, doses or treatments. For medicine questions, explain in general terms and tell the user to ask a doctor or pharmacist.
- Say when to see a doctor, and mention the doctor search in the app if relevant.

LANGUAGE
- Follow the LANGUAGE NOTE at the end of this prompt for the language and script of your reply.
- Do not write any disclaimer line. The app already shows one."""


def _english_query(question: str) -> str:
    try:
        r = _get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": (
                    "Rewrite the user's message as a short English search query (max 15 words) "
                    "for finding it in a medical lab report. Add likely lab test names or synonyms "
                    "(for example, for infection: Widal, typhoid, antibody titer, culture, WBC, CRP). "
                    "Output only the query.")},
                {"role": "user", "content": question[:500]},
            ],
            temperature=0,
            max_completion_tokens=200,
            reasoning_effort="low",
        )
        return (r.choices[0].message.content or "").strip() or question
    except Exception as e:
        print("query rewrite failed:", repr(e))
        return question


def answer(uid: str, question: str, history: list[dict] | None = None) -> dict:
    if rule_urgency(question) == "emergency":
        return {"answer": EMERGENCY_REPLY, "urgency": "emergency", "sources": [], "specialties": []}

    info = understand_query(question)
    urgency = info.get("urgency", "routine") if info else "routine"
    specialties = (info.get("specialties") or []) if info else []

    try:
        hits = search_reports(uid, _english_query(question), k=6)
    except Exception as e:
        print("report search failed:", repr(e))
        hits = []

    system = SYSTEM
    if hits:
        ctx = "\n\n".join(
            f"[{i + 1}] Report: {h['title']}, page {h['page']}\n{h['text']}" for i, h in enumerate(hits)
        )
        system += "\n\nREPORT CONTEXT:\n" + ctx
    else:
        system += "\n\nREPORT CONTEXT: (nothing relevant found in the user's uploaded reports)"

    has_devanagari = any("\u0900" <= ch <= "\u097f" for ch in question)
    if has_devanagari:
        system += "\n\nLANGUAGE NOTE: The user wrote in Hindi. Reply in Hindi using Devanagari script."
    else:
        system += ("\n\nLANGUAGE NOTE: Reply using ONLY Latin (Roman) letters and never Devanagari. "
                   "If the user wrote English, reply in English. If the user wrote Hindi in Roman letters "
                   "(Hinglish), write your own sentences in simple Hinglish. "
                   "Keep test names, numbers and any text copied from the report exactly as printed.")

    messages = [{"role": "system", "content": system}]
    for m in (history or [])[-6:]:
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
            messages.append({"role": m["role"], "content": m["content"][:500]})
    messages.append({"role": "user", "content": question[:500]})

    try:
        resp = _get_client().chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.2,
            max_completion_tokens=700,
            reasoning_effort="low",
        )
        text = resp.choices[0].message.content or ""
    except Exception as e:
        print("chat failed:", repr(e))
        return {"answer": "Sorry, the assistant is busy. Please try again in a minute.",
                "urgency": urgency, "sources": [], "specialties": specialties}

    seen, sources = set(), []
    for h in hits:
        key = (h["title"], h["page"])
        if key not in seen:
            seen.add(key)
            sources.append({"title": h["title"], "page": h["page"]})

    return {"answer": text, "urgency": urgency, "sources": sources, "specialties": specialties}