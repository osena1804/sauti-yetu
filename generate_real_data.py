import sys
sys.path.insert(0, "src")
import gemma_client as gc
import pandas as pd
from datetime import datetime, timezone

# (age, ward, top3_problems, description, rating, solution)
survey_rows = [
    (30, "Airport", "Water supply, Drainage, Garbage collection", "We only get water once a month", 5, "connect more water pipes to every house"),
    (24, "Mtopanga", "Water supply, security, Unemployment", "We only get water once a week or sometimes once a month. Many youths are also unemployed and they are all learned!", 5, "Provide job opportunities and ensure at least thrice a week water supply"),
    (20, "Bamburi", "Security, Water supply, Drainage", "We get water once a per month", 4, "Water to come 3 per week"),
    (27, "Kisauni", "Security, Water supply, Drug abuse", "We only get water 2 days a week", 5, "Drill borehole; Employ the youths"),
    (19, "Mtopanga", "Water supply, Unemployment, Drug abuse", "Shortages of water", 3, "Assure us specific days that we can get and see how we can manage water in a week"),
    (21, "Junda", "Security, Healthcare, Unemployment", "", 5, ""),
    (29, "Junda", "Unemployment", "Many people loitering", 3, "Business/Employment creation"),
    (35, "Mjambere", "Security, Unemployment, Drug abuse", "We don't get water, drugs everywhere", 5, "Government should work"),
    (30, "Mwakirunge", "security", "Poor security", 5, "Proper lighting"),
    (38, "Mikindani", "Water supply, Unemployment, Drug abuse", "", 3, ""),
]

def rating_to_urgency(rating):
    if rating >= 4:
        return "High"
    if rating == 3:
        return "Medium"
    return "Low"

rows = []
for age, ward, top3, description, rating, solution in survey_rows:
    raw_text = f"Top concerns: {top3}. {description}".strip()
    if solution:
        raw_text += f" Suggested fix: {solution}"

    result = gc.classify_complaint(raw_text)
    result["ward"] = ward  # trust the respondent's own stated ward
    result["urgency"] = rating_to_urgency(rating)  # trust their own severity rating
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    rows.append(result)

df = pd.DataFrame(rows)[["category", "urgency", "ward", "english_summary", "raw_text", "timestamp"]]
df.to_csv("data/real_ground_data.csv", index=False)
print(df[["category", "urgency", "ward", "english_summary"]].to_string())
print(f"\nSaved {len(df)} real ground-truth complaints to data/real_ground_data.csv")