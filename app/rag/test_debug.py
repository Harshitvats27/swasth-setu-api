from app.rag.chat import _route
from app.rag.report_search import search_reports_multi

UID = "Fb5BTQM0TMSEm3ASqHwo1wigwnY2"   # wahi jo test_chat.py mein hai
q = "meri report me infection ke baare me kya likha hai"

q = "meri report me infection ke baare me kya likha hai"

is_report, queries = _route(q)
print("route:", is_report, "| queries:", queries)
for h in search_reports_multi(UID, queries, k=6):
    print(round(h["distance"], 3), "page", h["page"], "|", h["text"][:120].replace("\n", " | "))