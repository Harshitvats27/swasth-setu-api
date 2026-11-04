from app.rag.kb_search import search_kb

for q in [
    "what to do for fever",
    "how to make ORS for diarrhoea",
    "burn first aid",
    "high blood pressure symptoms",
    "chest pain",
    "who won the cricket match",
]:
    print("\nQ:", q)
    for r in search_kb(q):
        print(round(r["distance"], 3), r["file"], "|", r["text"][:70].replace("\n", " | "))