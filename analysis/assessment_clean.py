"""
assessment_clean.py
-------------------
Cleans the three assessment files: DET, EFSet, Northstar.

DET and EFSet both carry email addresses — learner matching goes through
LearnerResolver using the email prefix (same initial+lastname pattern as typing).

Northstar has no email and no learner name column:
  - PDF rows (record_source='pdf_text_extract'): name + IS_SCH/IS_CIR IDs are
    embedded in the source_file filename. Extracted via regex, then fuzzy-matched.
  - CSV rows (record_source='csv'): no learner identifier at all. Matched at
    school level only via school_folder. Learner match flagged as
    'unresolvable_csv_source' — these rows cannot be linked to individuals.

DET-specific issues documented:
  - Surname(s) column is corrupted: contains IS_CIR IDs, raw numbers, and one
    literal typo (IS_CIR_0(six)35). Renamed to surname_raw and kept as-is for
    audit; not used for matching.
  - 14 rows are repeat attempts (attempt_number > 1). Kept with flag.

EFSet-specific issues:
  - 10 emails have typos (e.g. @icicles.rw, @circles.rw). Flagged as
    email_typo; matching proceeds on the prefix anyway and may still succeed.
  - 10 rows are endline repeat attempts (attempt_n > 1). Kept with flag.

Northstar-specific issues:
  - assessment_date is null for all 835 PDF rows — date was not in the PDF.
  - score_pct has 228 nulls across both record types — treated as incomplete
    submissions and retained with null score.

Run from repo root:
    python3 analysis/assessment_clean.py
"""

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from learner_resolver import LearnerResolver
from school_match import SchoolMatcher


resolver       = LearnerResolver()
school_matcher = SchoolMatcher()

TYPO_DOMAINS = {"icicles.rw", "circles.rw", "ciecles.rw", "icircle.rw",
                "icirles.rw", "icirclees.rw", "gmail.com"}


def standardise_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    return df


def resolve_learner_from_email(email) -> dict:
    """Pass the email prefix to LearnerResolver (same pattern as typing)."""
    if email is None or isinstance(email, float):
        return resolver.resolve("")
    return resolver.resolve(str(email).strip())


def print_summary(name: str, df: pd.DataFrame):
    total = len(df)
    matched = df["internal_learner_id"].notna().sum()
    routes  = df["match_route"].value_counts().to_dict()
    print(f"\n{name}  ({total:,} rows)")
    print(f"  Learner resolved: {matched}/{total} ({matched/total*100:.1f}%)")
    for route, count in routes.items():
        print(f"  {route:30s}: {count}")


# ===========================================================================
# 1. DET
# ===========================================================================

det = pd.read_csv("raw/assessments/det_scores_long.csv").reset_index(drop=True)
# DET has original Title Case columns (cols 0-20) AND their pre-processed equivalents.
# Drop the raw ones to prevent duplicate column names after standardise_cols.
det = det.drop(columns=[c for c in det.columns if c[0].isupper() or c in ["DOB","Scale","Score"]], errors="ignore")
det = standardise_cols(det)

# Surname(s) is corrupted — rename so it's clear we're not using it for matching
det = det.rename(columns={"surname(s)": "surname_raw"})

# Parse timestamps
for col in ["test_taken_datetime", "score_sent_datetime"]:
    if col in det.columns:
        det[col] = pd.to_datetime(det[col], errors="coerce", utc=True)

det = det.replace("NA", pd.NA)

# Resolve learner via email
results = det["email"].apply(resolve_learner_from_email).tolist()
det["internal_learner_id"] = [r["learner_id"] for r in results]
det["match_route"]         = [r["match_route"] for r in results]
det["match_note"]          = [r["note"] for r in results]

det.to_csv("data/det_scores_clean.csv", index=False)
print_summary("DET", det)


# ===========================================================================
# 2. EFSet
# ===========================================================================

efset = pd.read_csv("raw/assessments/efset_results_long.csv").reset_index(drop=True)
efset = standardise_cols(efset)

# Flag email typos before matching — do not silently correct them
efset["email_domain_flag"] = efset["email"].apply(
    lambda e: "typo_domain" if pd.notna(e) and str(e).split("@")[-1].lower() in TYPO_DOMAINS
    else "ok"
)

efset["test_date"] = pd.to_datetime(efset["test_date"], dayfirst=True, errors="coerce").dt.date
efset = efset.replace("NA", pd.NA)

# Resolve learner via email
results = efset["email"].apply(resolve_learner_from_email).tolist()
efset["internal_learner_id"] = [r["learner_id"] for r in results]
efset["match_route"]         = [r["match_route"] for r in results]
efset["match_note"]          = [r["note"] for r in results]

efset.to_csv("data/efset_results_clean.csv", index=False)
print_summary("EFSet", efset)


# ===========================================================================
# 3. Northstar
# ===========================================================================

north = pd.read_csv("raw/assessments/northstar_results_long.csv").reset_index(drop=True)
north = standardise_cols(north)
north = north.replace("NA", pd.NA)


def extract_name_from_filename(fname: str) -> str | None:
    """
    Extract learner name from Northstar PDF filenames.
    Handles spacing variants: '- Name -', '- Name-', '-Name -', no-space dashes.
    Pattern: IS_SCH_NNN -[opt space] NAME [opt space]- IS_CIR_NNN
    """
    m = re.search(r"IS_SCH_\d+\s*-\s*(.+?)\s*-\s*IS_CIR_", str(fname))
    return m.group(1).strip() if m else None


def extract_school_id_from_filename(fname: str) -> str | None:
    m = re.search(r"(IS_SCH_\d+)", str(fname))
    return m.group(1) if m else None


north["extracted_name"]   = north["source_file"].apply(extract_name_from_filename)
north["extracted_school"] = north["source_file"].apply(extract_school_id_from_filename)

# Resolve school — PDF rows: use extracted IS_SCH ID via crosswalk
#                  CSV rows: use school_folder via SchoolMatcher

def resolve_northstar_school(row):
    if row["record_source"] == "pdf_text_extract" and pd.notna(row["extracted_school"]):
        # IS_SCH IDs are the typing platform's IDs; look them up via crosswalk
        result = school_matcher.match(row["extracted_school"])
        return result
    if row["record_source"] == "csv" and pd.notna(row["school_folder"]):
        return school_matcher.match(str(row["school_folder"]))
    return school_matcher.match("")

school_results = north.apply(resolve_northstar_school, axis=1)
north["school_match_tier"]     = school_results.apply(lambda r: r.tier)
north["canonical_school_name"] = school_results.apply(lambda r: r.canonical_name)
north["resolved_school_id"]    = school_results.apply(lambda r: r.school_id)

# Resolve learner
def resolve_northstar_learner(row):
    if row["record_source"] == "pdf_text_extract":
        if pd.notna(row["extracted_name"]):
            return resolver.resolve(str(row["extracted_name"]))
        return {"learner_id": None, "match_route": "unresolvable_no_name",
                "note": "filename did not match expected pattern"}
    # CSV rows: no learner identifier available
    return {"learner_id": None, "match_route": "unresolvable_csv_source",
            "note": "CSV rows carry no learner identifier — school-level only"}

learner_results = north.apply(resolve_northstar_learner, axis=1)
north["internal_learner_id"] = learner_results.apply(lambda r: r["learner_id"])
north["match_route"]         = learner_results.apply(lambda r: r["match_route"])
north["match_note"]          = learner_results.apply(lambda r: r["note"])

north["assessment_date"] = pd.to_datetime(north["assessment_date"], format="mixed", dayfirst=True, errors="coerce").dt.date

north.to_csv("data/northstar_results_clean.csv", index=False)
print_summary("Northstar", north)

print("\nDone — assessment files written to data/")
