from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.firebase import db

UID = "Fb5BTQM0TMSEm3ASqHwo1wigwnY2"   # wahi jo test_chat.py mein hai

docs = (
    db.collection("report_chunks")
    .where(filter=FieldFilter("uid", "==", UID))
    .where(filter=FieldFilter("page", "==", 2))
    .stream()
)
seen = set()
for d in docs:
    t = d.to_dict().get("text", "")
    key = " ".join(t.split())
    if key in seen:
        continue
    seen.add(key)
    if "SEROLOGY" in t or "Antigen" in t:
        print("-----", len(t), "chars")
        print(t)