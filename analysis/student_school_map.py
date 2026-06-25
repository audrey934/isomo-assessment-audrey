import pandas as pd

quill = pd.read_csv("data/quill_activity_clean.csv")
typing = pd.read_csv("data/typing_test_attempts_clean.csv")

quill_map = quill[["internal_learner_id", "resolved_school_id"]].copy()
typing_map = typing[["internal_learner_id", "resolved_school_id"]].copy()

all_maps = pd.concat([quill_map, typing_map])
all_maps = all_maps.dropna(subset=["resolved_school_id"])

final_map = (
    all_maps
    .groupby("internal_learner_id")["resolved_school_id"]
    .agg(lambda x: x.value_counts().index[0])
    .reset_index()
)
final_map.to_csv("data/student_school_map.csv", index=False)

print("\n==============================")
print("PIPELINE STATUS CHECK")
print("==============================")

print("Quill rows:", len(quill))
print("Typing rows:", len(typing))

print("\nQuill school matches:",
      quill["resolved_school_id"].notna().sum())

print("Typing school matches:",
      typing["resolved_school_id"].notna().sum())

print("\nCombined rows:", len(all_maps))
print("After dropping NaNs:", len(all_maps.dropna(subset=['resolved_school_id'])))

print("\nFinal map rows:", len(final_map))

print("\nDONE → student_school_map pipeline executed")
print("==============================\n")