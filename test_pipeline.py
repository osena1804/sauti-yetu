import sys
sys.path.insert(0, "src")
import data_store as ds
import gemma_client as gc

n = ds.seed_from_csv("data/synthetic_complaints.csv")
print(f"Seeded {n} complaints into the store.")

df = ds.load_complaints()
print(f"\nStore now has {len(df)} rows, sorted by urgency/days_unresolved (public portal order):")
print(df[["category", "urgency", "ward", "days_unresolved"]].head(10).to_string())

# Test the CDF draft generator on one ward cluster
subset = df[df["ward"] == "Mwembe Tayari"]
print(f"\n--- Testing CDF draft generation for Mwembe Tayari ({len(subset)} complaints) ---")
draft = gc.generate_cdf_draft(subset)
print(draft)

print("\n--- Testing add_complaint() (simulating a new live submission) ---")
new = gc.classify_complaint("Kuna maji taka mengi Tudor, watoto wanaugua homa ya matumbo.")
ds.add_complaint(new)
df2 = ds.load_complaints()
print(f"Store now has {len(df2)} rows after live add.")