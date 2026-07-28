import sys
sys.path.insert(0, "src")
import data_store as ds
import gemma_client as gc

# Reseed fresh (since we deleted complaints.csv)
n = ds.seed_from_csv("data/synthetic_complaints.csv")
print(f"Seeded {n} complaints.")

df = ds.load_complaints()
print(f"Store has {len(df)} rows. All statuses should be 'Open':")
print(df["status"].value_counts())

# Pick one complaint to resolve
target = df.iloc[0]
print(f"\nResolving complaint {target['id']} ({target['category']} in {target['ward']})...")
ds.mark_resolved(target["id"], note="Road graded and potholes filled by county crew.", photo_path="")

df2 = ds.load_complaints()
resolved_row = df2[df2["id"] == target["id"]].iloc[0]
print(f"Status now: {resolved_row['status']}")
print(f"Evidence note: {resolved_row['resolution_note']}")

# Now dispute it twice (threshold is 2)
print(f"\nDisputing complaint {target['id']}...")
ds.dispute_resolution(target["id"])
ds.dispute_resolution(target["id"])

df3 = ds.load_complaints()
disputed_row = df3[df3["id"] == target["id"]].iloc[0]
print(f"Status after 2 disputes: {disputed_row['status']}")
print(f"Dispute count: {disputed_row['dispute_count']}")

print("\nALL CHECKS DONE — verify status went Open -> Resolved -> Disputed above.")