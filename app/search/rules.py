import re
import unicodedata
from rapidfuzz.distance import OSA


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).lower()
    t = t.replace("'", "").replace("’", "")
    # replace punctuation by hand: Python's \w breaks Hindi matras
    t = re.sub(r"[!\"#$%&()*+,\-./:;<=>?@\[\]\\^_`{|}~।॥]", " ", t)
    t = re.sub(r"(.)\1{2,}", r"\1", t)          # dardddd -> dard
    return re.sub(r"\s+", " ", t).strip()


CHEST = {"seene", "seena", "sine", "sina", "chhati", "chati", "chhaati",
         "chest", "dil", "heart", "hriday"}
PAIN = {"dard", "pain", "jakad", "jakda", "bhari", "bhaari", "dabav",
        "pressure", "tight", "tightness", "jalan"}
BREATH = {"saans", "sans", "saas", "breath", "breathe", "breathing"}
TROUBLE = {"nahi", "nhi", "dikkat", "takleef", "takleef", "problem",
           "difficulty", "trouble", "cant", "cannot", "phool", "ruk"}
BLEED = {"khoon", "khun", "blood", "bleeding"}
HEAVY = {"bahut", "zyada", "jyada", "heavy", "severe", "nahi", "ruk", "rukna"}
SINGLE = {"behosh", "behoosh", "unconscious", "seizure", "seizures", "daura",
          "lakwa", "stroke", "zeher", "zehar", "poison", "overdose", "accident"}

DEVANAGARI = [normalize(p) for p in [
    "सीने में दर्द", "सीने मे दर्द", "छाती में दर्द", "छाती मे दर्द",
    "सांस नहीं", "साँस नहीं", "सांस लेने में तकलीफ", "साँस लेने में तकलीफ",
    "बेहोश", "दिल का दौरा", "हार्ट अटैक", "खून बह", "खून नहीं रुक",
    "ज़हर", "जहर", "लकवा", "दौरा",
]]


def _near(word: str, vocab: set[str]) -> bool:
    for v in vocab:
        allowed = 0 if len(v) <= 3 else 1 if len(v) <= 7 else 2
        if OSA.distance(word, v) <= allowed:   # allows typos and swapped letters
            return True
    return False


def _any(words: list[str], vocab: set[str]) -> bool:
    return any(_near(w, vocab) for w in words)


def rule_urgency(text: str) -> str | None:
    t = normalize(text)
    if any(p in t for p in DEVANAGARI):
        return "emergency"
    w = t.split()
    if _any(w, SINGLE):
        return "emergency"
    if _any(w, CHEST) and _any(w, PAIN):
        return "emergency"
    if _any(w, BREATH) and _any(w, TROUBLE):
        return "emergency"
    if _any(w, BLEED) and _any(w, HEAVY):
        return "emergency"
    return None