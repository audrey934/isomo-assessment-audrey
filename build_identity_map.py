import pandas as pd

# -----------------------------
# LOAD MASTER (TRUTH LAYER)
# -----------------------------
master = pd.read_csv("data/master_student_clean.csv")

identity_rows = []

for _, row in master.iterrows():
    identity_rows.append({
        "internal_learner_id": row["learner_id"],
        "source_system": "master",
        "source_id": row["learner_id"],
        "email": None,
        "name": row["canonical_name"],
        "confidence": 1.0
    })

identity_map = pd.DataFrame(identity_rows)

# Normalize email safely
identity_map["email"] = identity_map["email"].fillna("").str.lower().str.strip()


# -----------------------------
# LOAD EFSET (RAW)
# -----------------------------
efset = pd.read_csv("raw/assessments/efset_results_long.csv")

if "email" in efset.columns:
    efset["email"] = efset["email"].fillna("").str.lower().str.strip()

    efset_matched = efset.merge(identity_map, on="email", how="left")

    efset_links = efset_matched.dropna(subset=["internal_learner_id"])[
        ["internal_learner_id", "email"]
    ].drop_duplicates()

    efset_links = efset_links.assign(
        source_system="efset",
        source_id=efset_links["email"],
        name=None,
        confidence=1.0
    )
else:
    efset_links = pd.DataFrame(columns=[
        "internal_learner_id", "email", "source_system", "source_id", "name", "confidence"
    ])


# -----------------------------
# LOAD DET (RAW)
# -----------------------------
det = pd.read_csv("raw/assessments/det_scores_long.csv")

if "email" in det.columns:
    det["email"] = det["email"].fillna("").str.lower().str.strip()

    det_matched = det.merge(identity_map, on="email", how="left")

    det_links = det_matched.dropna(subset=["internal_learner_id"])[
        ["internal_learner_id", "email"]
    ].drop_duplicates()

    det_links = det_links.assign(
        source_system="det",
        source_id=det_links["email"],
        name=None,
        confidence=1.0
    )
else:
    det_links = pd.DataFrame(columns=[
        "internal_learner_id", "email", "source_system", "source_id", "name", "confidence"
    ])


# -----------------------------
# COMBINE ALL
# -----------------------------
final_map = pd.concat(
    [identity_map, efset_links, det_links],
    ignore_index=True
)

final_map.to_csv("data/learner_identity_map.csv", index=False)

print("Identity map updated with EFSET + DET")
print("Total rows:", len(final_map))