import pandas as pd
from learner_resolver import LearnerResolver

resolver = LearnerResolver("data/master_student_clean.csv")


def resolve_quill(df, name_col, id_col):
    resolved_ids = []
    match_routes = []
    confidences = []

    for _, row in df.iterrows():
        result = resolver.resolve(
            external_id=row.get(id_col),
            name=row.get(name_col),
            source_system="quill"
        )

        resolved_ids.append(result["internal_learner_id"])
        match_routes.append(result["match_route"])
        confidences.append(result["confidence"])

    df["internal_learner_id"] = resolved_ids
    df["match_route"] = match_routes
    df["confidence"] = confidences

    return df


# -------------------------
# 1. QUILL ACTIVITY
# -------------------------
activity = pd.read_csv("raw/platform/quill_activity_long.csv")
activity.columns = [c.strip().lower().replace(" ", "_") for c in activity.columns]

activity = resolve_quill(
    activity,
    name_col="student_name_raw",
    id_col="learner_id"
)

activity["date"] = pd.to_datetime(activity["date"], errors="coerce")

activity.to_csv("data/quill_activity_clean.csv", index=False)


# -------------------------
# 2. QUILL SESSIONS
# -------------------------
sessions = pd.read_csv("raw/platform/quill_connect_sessions.csv")
sessions.columns = [c.strip().lower().replace(" ", "_") for c in sessions.columns]

sessions = resolve_quill(
    sessions,
    name_col="student_name_raw",
    id_col="learner_id"
)

sessions["date"] = pd.to_datetime(sessions["date"], errors="coerce")

sessions.to_csv("data/quill_connect_sessions_clean.csv", index=False)


# -------------------------
# SUMMARY
# -------------------------
print("DONE: All Quill cleaned")

print("Activity rows:", len(activity))
print("Activity match rate:", activity["internal_learner_id"].notna().mean())

print("Session rows:", len(sessions))
print("Session match rate:", sessions["internal_learner_id"].notna().mean())