from app.rag.chat import answer

UID = "Fb5BTQM0TMSEm3ASqHwo1wigwnY2"    # wahi jo test_search mein tha

for q in [
    "meri report me infection ke baare me kya likha hai",
    "hemoglobin kitna hai meri report me",
    "bukhar me kya karna chahiye",
    "seene me dard hai",
]:
    r = answer(UID, q)
    print("\nQ:", q)
    print("A:", r["answer"])
    print("sources:", r["sources"], "| urgency:", r["urgency"], "| specialties:", r["specialties"])