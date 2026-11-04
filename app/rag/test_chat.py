from app.rag.chat import answer

UID = "Fb5BTQM0TMSEm3ASqHwo1wigwnY2"    # wahi jo test_search mein tha
   # wahi jo pehle tha

for q in [
    "bukhar me kya karna chahiye",
    "ORS kaise banate hain",
    "jal gaya hun haath, kya karun",
    "who won the cricket match",
    "tu kon h",
    "mujhe kaunsi dawai leni chahiye bukhar me",
    "hemoglobin kitna hai meri report me",
    "chaati dukhe h meri",
]:
    r = answer(UID, q)
    print("\nQ:", q)
    print("A:", r["answer"])
    print("sources:", [(s["title"], s["page"]) for s in r["sources"]], "| urgency:", r["urgency"], "| specialties:", r["specialties"])