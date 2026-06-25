import pandas as pd


# =========================
# LOAD FILES
# =========================
MASTER_PATH = "data/master_student_clean.csv"
MAP_PATH = "data/student_school_map.csv"
OUTPUT_PATH = "data/master_student_enriched.csv"


master = pd.read_csv(MASTER_PATH)
school_map = pd.read_csv(MAP_PATH)


# =========================
# STANDARDISE COLUMN NAMES
# =========================

# Master uses learner_id → must align to internal_learner_id
if "learner_id" in master.columns:
    master = master.rename(columns={"learner_id": "internal_learner_id"})

# Ensure required columns exist
required_master_cols = ["internal_learner_id"]
for col in required_master_cols:
    if col not in master.columns:
        raise ValueError(f"Missing required column in master: {col}")

required_map_cols = ["internal_learner_id", "resolved_school_id"]
for col in required_map_cols:
    if col not in school_map.columns:
        raise ValueError(f"Missing required column in map: {col}")


# =========================
# CLEAN DATA (important for joins)
# =========================
master["internal_learner_id"] = master["internal_learner_id"].astype(str).str.strip()
school_map["internal_learner_id"] = school_map["internal_learner_id"].astype(str).str.strip()


# =========================
# REMOVE DUPLICATES IN MAP
# =========================
school_map = (
    school_map.dropna(subset=["resolved_school_id"])
    .groupby("internal_learner_id")["resolved_school_id"]
    .agg(lambda x: x.value_counts().index[0])
    .reset_index()
)


# =========================
# DEBUG STATS BEFORE MERGE
# =========================
print("\n========================")
print("ENRICHMENT PIPELINE START")
print("========================")

print("Master rows:", len(master))
print("Map rows:", len(school_map))
print("Unique mapped learners:", school_map["internal_learner_id"].nunique())


# =========================
# MERGE
# =========================
enriched = master.merge(
    school_map,
    on="internal_learner_id",
    how="left"
)


# =========================
# COVERAGE CHECK
# =========================
coverage = enriched["resolved_school_id"].notna().mean()

print("\n========================")
print("ENRICHMENT COMPLETE")
print("========================")
print("Rows:", len(enriched))
print("School coverage:", round(coverage * 100, 2), "%")


# =========================
# SAVE OUTPUT
# =========================
enriched.to_csv(OUTPUT_PATH, index=False)

print("\nSaved to:", OUTPUT_PATH)
print("========================\n")
enriched = master.merge(
    school_map,
    on="internal_learner_id",
    how="left"
)

# =========================
# MISSING SCHOOL ANALYSIS
# =========================

missing = enriched[enriched["resolved_school_id"].isna()].copy()

print("\n========================")
print("MISSING SCHOOL SUMMARY")
print("========================")

print("Total rows:", len(enriched))
print("Missing school:", len(missing))
print("Coverage:", round(enriched["resolved_school_id"].notna().mean(), 4))


# --- breakdown by activity presence ---
quill = pd.read_csv("data/quill_activity_clean.csv")
typing = pd.read_csv("data/typing_test_attempts_clean.csv")

quill_ids = set(quill["internal_learner_id"].dropna().unique())
typing_ids = set(typing["internal_learner_id"].dropna().unique())


def classify(lid):
    in_q = lid in quill_ids
    in_t = lid in typing_ids

    if in_q and in_t:
        return "IN_BOTH"
    elif in_q:
        return "ONLY_QUILL"
    elif in_t:
        return "ONLY_TYPING"
    return "NO_ACTIVITY"


missing["activity_bucket"] = missing["internal_learner_id"].apply(classify)

print("\n--- Breakdown ---")
print(missing["activity_bucket"].value_counts())

print("\n--- Sample missing learners ---")
print(missing[["internal_learner_id", "canonical_name"]].head(15))