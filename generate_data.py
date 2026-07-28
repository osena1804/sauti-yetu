import sys
sys.path.insert(0, "src")
import gemma_client as gc
import pandas as pd
from datetime import datetime, timedelta, timezone

raw_complaints = [
    ("Huku Mtopanga barabara zimeharibika kabisa, gari hazipiti tangu wiki mbili.", 14),
    ("Kuna moshi mzito kutoka kwa kiwanda karibu na Changamwe, watoto wanashindwa kupumua vizuri.", 9),
    ("Water hasn't reached our estate in Bamburi for 5 days, tunateseka sana.", 5),
    ("Taka zimejaa kwa mtaro wetu Likoni, harufu mbaya na mbu wengi.", 20),
    ("Sisi hapa Nyali hatuna shida kubwa lakini taa za barabarani hazifanyi kazi usiku.", 3),
    ("Emergency! Kuna dampo la takataka linalowaka Kisauni, moshi unaingia nyumbani.", 1),
    ("Shule ya msingi Mwembe Tayari haina choo kinachofanya kazi, watoto wanaumia.", 30),
    ("Hospitali ya Port Reitz haina dawa za malaria tangu mwezi jana.", 25),
    ("Barabara ya Mikindani ina mashimo makubwa, pikipiki zinaanguka kila siku.", 12),
    ("Wizi wa mara kwa mara Miritini, hakuna doria ya polisi usiku.", 8),
    ("Sewage inatiririka mtaani Tudor, watoto wanacheza karibu na maji machafu.", 6),
    ("Kiwanda cha saruji Changamwe kinatoa vumbi jingi, nyumba zote zina rangi nyeupe.", 45),
    ("Daraja la Nyali limebomoka kidogo, ni hatari kwa magari makubwa.", 2),
    ("Hakuna maji safi ya kunywa Bombolulu kwa wiki tatu, tunanunua maji ya chupa.", 21),
    ("Clinic ya Junda haina wafanyakazi wa kutosha, foleni ni ndefu sana asubuhi.", 15),
    ("There is illegal dumping happening every night near Mwembe Tayari market, it's becoming a health hazard.", 18),
    ("Air quality karibu na bandari ni mbaya, lorry nyingi zinapita na kutoa moshi mweusi.", 10),
    ("Small pothole near Bamburi beach road, not urgent but should be fixed eventually.", 40),
    ("Kuna maji taka yanayotoka kwenye choo cha jumuiya Kongowea, harufu inaenea mtaa mzima.", 11),
    ("Streetlights in Shanzu have been off for two months, women feel unsafe walking at night.", 60),
]

rows = []
for text, days_ago in raw_complaints:
    result = gc.classify_complaint(text)
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    result["timestamp"] = ts.isoformat()
    rows.append(result)

df = pd.DataFrame(rows)[["category", "urgency", "ward", "english_summary", "raw_text", "timestamp"]]
df.to_csv("data/synthetic_complaints.csv", index=False)
print(df[["category", "urgency", "ward", "english_summary"]].to_string())
print(f"\nSaved {len(df)} synthetic complaints to data/synthetic_complaints.csv")