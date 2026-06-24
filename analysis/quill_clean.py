"""
quill_clean.py
--------------
Cleans quill_activity_long.csv and quill_connect_sessions.csv.

Quill has real full names in student_name_raw and IS_CIR IDs in learner_id.
IS_CIR IDs are the typing platform's internal IDs — they are NOT our learner IDs
and master_student has no IS_CIR column to join against, so matching goes through
the name field using LearnerResolver's sorted-token + fuzzy strategies.

Steps:
  1. Standardise column names
  2. Parse dates to ISO YYYY-MM-DD
  3. Replace bare "NA" strings with nulls
  4. Resolve school via SchoolMatcher using folder_name
  5. Resolve learner via LearnerResolver using student_name_raw

Run from repo root:
    python3 analysis/quill_clean.py
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from learner_resolver import LearnerResolver
from school_match import SchoolMatcher


resolver       = LearnerResolver()
school_matcher = SchoolMatcher()


def standardise_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    return df


def resolve_school(df: pd.DataFrame, school_col: str) -> pd.DataFrame:
    results = df[school_col].apply(
        lambda x: school_matcher.match(str(x)) if pd.notna(x) else school_matcher.match("")
    )
    df["school_match_tier"]     = results.apply(lambda r: r.tier)
    df["canonical_school_name"] = results.apply(lambda r: r.canonical_name)
    df["resolved_school_id"]    = results.apply(lambda r: r.school_id)
    return df


def resolve_learners(df: pd.DataFrame, name_col: str) -> pd.DataFrame:
    results = df[name_col].apply(resolver.resolve)
    df["internal_learner_id"] = results.apply(lambda r: r["learner_id"])
    df["match_route"]         = results.apply(lambda r: r["match_route"])
    df["match_note"]          = results.apply(lambda r: r["note"])
    return df


def print_summary(name: str, df: pd.DataFrame, name_col: str):
    unique_users = df[name_col].nunique()
    per_user = (
        df.drop_duplicates(name_col)["match_route"]
        .value_counts()
    )
    print(f"\n{name}  ({len(df):,} rows, {unique_users} unique learner names)")
    for flag, count in per_user.items():
        print(f"  {flag:20s}: {count:4d} users ({count/unique_users*100:.1f}%)")


# ---------------------------------------------------------------------------
# Quill activity
# ---------------------------------------------------------------------------

activity = pd.read_csv("raw/platform/quill_activity_long.csv")
activity = standardise_cols(activity)
activity = activity.replace("NA", pd.NA)
activity["date"] = pd.to_datetime(activity["date"], errors="coerce").dt.date

activity = resolve_school(activity, "folder_name")
activity = resolve_learners(activity, "student_name_raw")
activity.to_csv("data/quill_activity_clean.csv", index=False)


# ---------------------------------------------------------------------------
# Quill connect sessions
# ---------------------------------------------------------------------------

sessions = pd.read_csv("raw/platform/quill_connect_sessions.csv")
sessions = standardise_cols(sessions)
sessions = sessions.replace("NA", pd.NA)
sessions["date"] = pd.to_datetime(sessions["date"], errors="coerce").dt.date

sessions = resolve_school(sessions, "folder_name")
sessions = resolve_learners(sessions, "student_name_raw")
sessions.to_csv("data/quill_connect_sessions_clean.csv", index=False)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print_summary("quill_activity", activity, "student_name_raw")
print_summary("quill_connect_sessions", sessions, "student_name_raw")
print("\nDone — files written to data/")
