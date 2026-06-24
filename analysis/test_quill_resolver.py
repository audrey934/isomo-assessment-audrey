import pandas as pd
from analysis.learner_resolver import LearnerResolver

# path to your quill file
FILE_PATH = "raw/platform/quill_activity_long.csv"

resolver = LearnerResolver("data/master_student_clean.csv")

df = pd.read_csv(FILE_PATH)

matched = 0
unmatched = 0

results = []

unresolved_samples = []

for _, row in df.iterrows():

    result = resolver.resolve(
        email=row.get("email"),
        external_id=row.get("learner_id"),
        name=row.get("student_name_raw"),
        source_system="quill"
    )

    if result["internal_learner_id"]:
        matched += 1
    else:
        unmatched += 1

        # collect samples (first 30 only)
        if len(unresolved_samples) < 30:
            unresolved_samples.append({
                "name": row.get("student_name_raw"),
                "email": row.get("email"),
                "external_id": row.get("learner_id")
            })

# summary
total = len(df)

print("\n=== QUILL RESOLVER TEST ===")
print(f"Total rows: {total}")
print(f"Matched: {matched}")
print(f"Unmatched: {unmatched}")
print(f"Match rate: {matched / total:.2%}")

print("\n=== UNRESOLVED BREAKDOWN (sample) ===")
for x in unresolved_samples:
    print(x)
