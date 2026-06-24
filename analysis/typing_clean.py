"""
typing_clean.py
---------------
Cleans typing_lesson_activity.csv and typing_test_attempts.csv.

Steps per file:
  1. Standardise column names (lowercase, underscores)
  2. Rename platform school_id -> source_school_id
  3. Parse dates to ISO YYYY-MM-DD
  4. Replace bare "NA" strings with proper nulls
  5. Compute sso_available boolean
  6. Resolve school via SchoolMatcher -> resolved_school_id + school_match_tier
  7. Resolve learner via LearnerResolver -> learner_id + match_route + match_note

Run from repo root:
    python3 analysis/typing_clean.py
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from learner_resolver import LearnerResolver
from school_match import SchoolMatcher


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
resolver = LearnerResolver()
school_matcher = SchoolMatcher()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def standardise_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    return df


def resolve_school(df: pd.DataFrame, school_col: str) -> pd.DataFrame:
    results = df[school_col].apply(
        lambda x: school_matcher.match(str(x)) if pd.notna(x) else school_matcher.match("")
    )
    df["school_match_tier"]    = results.apply(lambda r: r.tier)
    df["canonical_school_name"] = results.apply(lambda r: r.canonical_name)
    df["resolved_school_id"]   = results.apply(lambda r: r.school_id)
    return df


def resolve_learners(df: pd.DataFrame) -> pd.DataFrame:
    results = df["username_raw"].apply(resolver.resolve)
    df["internal_learner_id"] = results.apply(lambda r: r["learner_id"])
    df["match_route"]         = results.apply(lambda r: r["match_route"])
    df["match_note"]          = results.apply(lambda r: r["note"])
    return df


def print_summary(name: str, df: pd.DataFrame):
    unique_users = df["username_raw"].nunique()
    per_user = (
        df.drop_duplicates("username_raw")["match_route"]
        .value_counts()
    )
    print(f"\n{name}  ({len(df):,} rows, {unique_users} unique usernames)")
    for flag, count in per_user.items():
        print(f"  {flag:20s}: {count:4d} users ({count/unique_users*100:.1f}%)")


# ---------------------------------------------------------------------------
# Clean lesson activity
# ---------------------------------------------------------------------------

lesson = pd.read_csv("raw/platform/typing_lesson_activity.csv")
lesson = standardise_cols(lesson)
lesson = lesson.rename(columns={"school_id": "source_school_id"})

lesson["date"] = pd.to_datetime(lesson["date"], utc=True).dt.date
lesson = lesson.replace("NA", pd.NA)
lesson["sso_available"] = (
    lesson["sso_school_id"].notna() &
    (lesson["sso_school_id"].astype(str) != "NA")
)

lesson = resolve_school(lesson, "school_name")
lesson = resolve_learners(lesson)
lesson.to_csv("data/typing_lesson_activity_clean.csv", index=False)


# ---------------------------------------------------------------------------
# Clean test attempts
# ---------------------------------------------------------------------------

attempts = pd.read_csv("raw/platform/typing_test_attempts.csv")
attempts = standardise_cols(attempts)
attempts = attempts.rename(columns={"school_id": "source_school_id"})

# test_attempts uses dayfirst date format (DD/MM/YYYY)
attempts["date"] = pd.to_datetime(attempts["date"], dayfirst=True, utc=True).dt.date
attempts = attempts.replace("NA", pd.NA)
attempts["sso_available"] = (
    attempts["sso_school_id"].notna() &
    (attempts["sso_school_id"].astype(str) != "NA")
)

attempts = resolve_school(attempts, "school_name")
attempts = resolve_learners(attempts)
attempts.to_csv("data/typing_test_attempts_clean.csv", index=False)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print_summary("typing_lesson_activity", lesson)
print_summary("typing_test_attempts", attempts)
print("\nDone — files written to data/")
