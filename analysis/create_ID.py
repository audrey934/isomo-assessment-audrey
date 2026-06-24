"""
Generates stable, unique learner_id and school_id values
and produce mapping tables linking each new ID back to the source fields.

Run from the repo root:
    python3 analysis/generate_ids.py

Inputs:
    data/reference/master_student.csv
    data/reference/master_school.csv

Outputs:
    data/learner_id_mapping.csv
    data/school_id_mapping.csv
"""

import csv
import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER_STUDENT = REPO_ROOT / "raw" / "reference" / "master_student.csv"
MASTER_SCHOOL = REPO_ROOT / "raw" / "reference" / "master_school.csv"
OUT_LEARNER = REPO_ROOT / "data" / "learner_id_mapping.csv"
OUT_SCHOOL = REPO_ROOT / "data" / "school_id_mapping.csv"


def normalize(text: str) -> str:
    """Lowercase, turn punctuation into spaces, then collapse whitespace. Same input -> same output, always."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_id(prefix: str, *fields: str, digits: int = 6) -> str:
    """Build a deterministic numeric ID from one or more fields. Same fields -> same ID, every time."""
    key = "|".join(normalize(f) for f in fields)
    full_hash = hashlib.sha256(key.encode()).hexdigest()
    num = int(full_hash, 16)
    code = str(num % (10 ** digits)).zfill(digits)
    return f"{prefix}_{code}"


def generate_learner_ids():
    rows_out = []
    seen_ids = {}

    with open(MASTER_STUDENT, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["canonical_name"]
            combo = row["combinations"]
            learner_id = make_id("ID_LRN", name, combo)

            # Safety net: if this somehow collides with someone else, fail loudly
            # rather than silently overwriting a learner's identity.
            if learner_id in seen_ids and seen_ids[learner_id] != (name, combo):
                raise ValueError(
                    f"ID collision: {learner_id} generated for both "
                    f"{seen_ids[learner_id]} and {(name, combo)}"
                )
            seen_ids[learner_id] = (name, combo)

            rows_out.append({
                "learner_id": learner_id,
                "canonical_name": name,
                "combinations": combo,
                "gender": row["gender"],
                "is_admitted": row["is_admitted"],
            })

    with open(OUT_LEARNER, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows_out[0].keys())
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Learners processed: {len(rows_out)}")
    print(f"Unique learner_ids: {len(seen_ids)}")
    print(f"Wrote {OUT_LEARNER}")


def generate_school_ids():
    rows_out = []
    seen_ids = {}

    with open(MASTER_SCHOOL, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["canonical_name"]
            school_id = make_id("ID_SCH", name)

            if school_id in seen_ids and seen_ids[school_id] != name:
                raise ValueError(
                    f"ID collision: {school_id} generated for both "
                    f"{seen_ids[school_id]} and {name}"
                )
            seen_ids[school_id] = name

            rows_out.append({
                "school_id": school_id,
                "canonical_name": name,
                "active": row["active"],
            })

    with open(OUT_SCHOOL, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows_out[0].keys())
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Schools processed: {len(rows_out)}")
    print(f"Unique school_ids: {len(seen_ids)}")
    print(f"Wrote {OUT_SCHOOL}")


if __name__ == "__main__":
    generate_learner_ids()
    print()
    generate_school_ids()