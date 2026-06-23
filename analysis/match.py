"""
Reusable school-name matching, implementing your suggested strategy

  1. Exact match against master_school.csv canonical names
  2. Exact match against a crosswalk raw_school_name (approved rows only)
  3. Normalized match (lowercase, strip punctuation, collapse spaces) against both of the above
  4. Fuzzy match — NEVER auto-accepted. Logged as "needs_manual_review" with the best
     candidate + similarity score, for a human to confirm.
  5. Blank / "NA" raw names are flagged as "no_school_info", never guessed at.

Usage from another cleaning script:
    from match_school import SchoolMatcher
    matcher = SchoolMatcher()
    result = matcher.match("GS Mubuga II")
    # result.school_id, result.canonical_name, result.tier, result.note
"""

import csv
import re
import difflib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER_SCHOOL = REPO_ROOT / "raw" / "reference" / "master_school.csv"
CROSSWALK = REPO_ROOT / "raw" / "reference" / "school_name_crosswalk.csv"
SCHOOL_ID_MAPPING = REPO_ROOT / "data" / "school_id_mapping.csv"

BLANK_VALUES = {"", "na", "n/a", "none", "null"}


def normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)  # punctuation/hyphens become spaces, not deleted
    text = re.sub(r"\s+", " ", text).strip()  # THEN collapse whitespace
    return text


@dataclass
class MatchResult:
    school_id: str | None
    canonical_name: str | None
    tier: str          # "exact_canonical" | "exact_crosswalk" | "normalized" | "needs_manual_review" | "no_school_info"
    note: str = ""      # extra detail, e.g. fuzzy candidate + score


class SchoolMatcher:
    def __init__(self):
        # canonical_name -> school_id
        self.canonical_to_id = {}
        with open(SCHOOL_ID_MAPPING, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.canonical_to_id[row["canonical_name"]] = row["school_id"]

        # exact raw_school_name (as written) -> canonical_name, approved rows only
        self.exact_crosswalk = {}
        # normalized name -> canonical_name, built from canonical names + all approved crosswalk variants
        self.normalized_lookup = {}

        for canon in self.canonical_to_id:
            self.normalized_lookup[normalize(canon)] = canon

        with open(CROSSWALK, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["match_status"] != "approved":
                    continue
                raw = row["raw_school_name"]
                canon = row["canonical_name"]
                self.exact_crosswalk[raw] = canon
                norm = normalize(raw)
                # Sanity check: flag if two DIFFERENT schools normalize to the same string —
                # exactly the Mubuga-style risk. Fail loudly rather than silently picking one.
                if norm in self.normalized_lookup and self.normalized_lookup[norm] != canon:
                    raise ValueError(
                        f"Normalization collision: '{norm}' matches both "
                        f"'{self.normalized_lookup[norm]}' and '{canon}'"
                    )
                self.normalized_lookup[norm] = canon

        self._all_normalized_names = list(self.normalized_lookup.keys())

    def match(self, raw_name: str) -> MatchResult:
        if raw_name is None or raw_name.strip().lower() in BLANK_VALUES:
            return MatchResult(None, None, "no_school_info")

        # Tier 1: exact against canonical
        if raw_name in self.canonical_to_id:
            return MatchResult(self.canonical_to_id[raw_name], raw_name, "exact_canonical")

        # Tier 2: exact against crosswalk raw spelling
        if raw_name in self.exact_crosswalk:
            canon = self.exact_crosswalk[raw_name]
            return MatchResult(self.canonical_to_id[canon], canon, "exact_crosswalk")

        # Tier 3: normalized match against either set
        norm = normalize(raw_name)
        if norm in self.normalized_lookup:
            canon = self.normalized_lookup[norm]
            return MatchResult(self.canonical_to_id[canon], canon, "normalized")

        # Tier 4: fuzzy — find the closest candidate, but DO NOT auto-accept it.
        close = difflib.get_close_matches(norm, self._all_normalized_names, n=1, cutoff=0.6)
        if close:
            candidate_canon = self.normalized_lookup[close[0]]
            score = difflib.SequenceMatcher(None, norm, close[0]).ratio()
            return MatchResult(
                None, None, "needs_manual_review",
                note=f"closest candidate: '{candidate_canon}' (similarity {score:.2f}) — confirm before using",
            )

        return MatchResult(None, None, "needs_manual_review", note="no candidate found at all")


if __name__ == "__main__":
    # Quick self-test against real cases we found while designing this
    matcher = SchoolMatcher()
    test_cases = ["ASYV", "Fawe Girls School - Gahini", "GS Mubuga II", "NA", "Some Totally Unknown School"]
    for name in test_cases:
        r = matcher.match(name)
        print(f"{name!r:35s} -> school_id={r.school_id}, canonical={r.canonical_name}, tier={r.tier}  {r.note}")