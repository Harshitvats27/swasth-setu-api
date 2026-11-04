from app.rag.report_search import search_reports

UID = "Fb5BTQM0TMSEm3ASqHwo1wigwnY2"   # report_chunks ke kisi doc ke uid field se

for q in ["hemoglobin level", "blood sugar", "infection"]:
    print("\nQ:", q)
    for r in search_reports(UID, q):
        print(round(r["distance"], 3), r["title"], "page", r["page"], "|", r["text"][:80].replace("\n", " "))