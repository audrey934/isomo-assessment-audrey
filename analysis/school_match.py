"""
school_match.py
---------------
Reusable school-name matching.

Tiers:
  1. exact_canonical   — exact match against master_school canonical names
  2. exact_crosswalk   — exact match against approved crosswalk raw spellings
  3. normalized        — lowercase + strip punctuation match against both sets
  4. needs_manual_review — fuzzy candidate found but NOT auto-accepted
  5. no_school_info    — blank or NA input

Usage:
    from school_match import SchoolMatcher
    matcher = SchoolMatcher()
    result  = matcher.match("GS Mubuga II")
    # result.school_id, result.canonical_name, result.tier, result.note
"""

import csv
import re
import difflib
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

REPO_ROOT       = Path(__file__).resolve().parent.parent
MASTER_SCHOOL   = REPO_ROOT / "raw" / "reference" / "master_school.csv"
CROSSWALK       = REPO_ROOT / "raw" / "reference" / "school_name_crosswalk.csv"
SCHOOL_ID_MAP   = REPO_ROOT / "data" / "school_id_mapping.csv"

BLANK_VALUES = {"", "na", "n/a", "none", "null"}


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@dataclass
class MatchResult:
    school_id:      str | None
    canonical_name: str | None
    tier:           str
    note:           str = ""


class SchoolMatcher:
    def __init__(self):
        self.canonical_to_id: dict[str, str] = {}
        with open(SCHOOL_ID_MAP, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.canonical_to_id[row["canonical_name"]] = row["school_id"]

        self.exact_crosswalk:    dict[str, str] = {}
        self.normalized_lookup:  dict[str, str] = {}

        for canon in self.canonical_to_id:
            self.normalized_lookup[_normalize(canon)] = canon

        with open(CROSSWALK, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("match_status") != "approved":
                    continue
                raw   = row["raw_school_name"]
                canon = row["canonical_name"]
                self.exact_crosswalk[raw] = canon
                norm  = _normalize(raw)
                if norm in self.normalized_lookup and self.normalized_lookup[norm] != canon:
                    raise ValueError(
                        f"Normalization collision: '{norm}' maps to both "
                        f"'{self.normalized_lookup[norm]}' and '{canon}'"
                    )
                self.normalized_lookup[norm] = canon

        self._all_normalized = list(self.normalized_lookup.keys())

    def match(self, raw_name: str) -> MatchResult:
        if raw_name is None or (isinstance(raw_name, float) and pd.isna(raw_name)):
            return MatchResult(None, None, "no_school_info")

        raw_name = str(raw_name).strip()

        if raw_name.lower() in BLANK_VALUES:
            return MatchResult(None, None, "no_school_info")

        # Tier 1
        if raw_name in self.canonical_to_id:
            return MatchResult(self.canonical_to_id[raw_name], raw_name, "exact_canonical")

        # Tier 2
        if raw_name in self.exact_crosswalk:
            canon = self.exact_crosswalk[raw_name]
            return MatchResult(self.canonical_to_id[canon], canon, "exact_crosswalk")

        # Tier 3
        norm = _normalize(raw_name)
        if norm in self.normalized_lookup:
            canon = self.normalized_lookup[norm]
            return MatchResult(self.canonical_to_id[canon], canon, "normalized")

        # Tier 4 — fuzzy, never auto-accepted
        close = difflib.get_close_matches(norm, self._all_normalized, n=1, cutoff=0.6)
        if close:
            candidate = self.normalized_lookup[close[0]]
            score = difflib.SequenceMatcher(None, norm, close[0]).ratio()
            return MatchResult(
                None, None, "needs_manual_review",
                note=f"closest: '{candidate}' (score {score:.2f}) — needs manual confirmation",
            )

        return MatchResult(None, None, "no_school_info", note="no candidate found")


if __name__ == "__main__":
    matcher = SchoolMatcher()
    for name in ["ASYV", "Fawe Girls School - Gahini", "GS Mubuga II", "NA", "Unknown School"]:
        r = matcher.match(name)
        print(f"{name!r:35s} -> id={r.school_id}, tier={r.tier}  {r.note}")
