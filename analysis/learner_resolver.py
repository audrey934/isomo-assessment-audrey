"""
learner_resolver.py
-------------------
Resolves a raw username or email to an internal learner_id from learner_id_mapping.csv.

Match tiers (stored in match_route):
  matched_exact   — single structural candidate (initial+lastname or token-concat)
  matched_fuzzy   — single fuzzy candidate at cutoff 0.75; less certain
  ambiguous       — multiple structural candidates; cannot safely pick one
  unresolvable    — MD5 hash username; structurally unmatchable
  unmatched       — no candidate found by any strategy

Usage:
    from learner_resolver import LearnerResolver
    resolver = LearnerResolver()
    result   = resolver.resolve("cmutabaruka@icircles.rw")
    # result["learner_id"], result["match_route"], result["note"]
"""

import re
import csv
import difflib
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parent.parent
ID_MAPPING  = REPO_ROOT / "data" / "learner_id_mapping.csv"


def _norm(s: str) -> str:
    """Strip all non-alphanumeric chars and lowercase."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _norm_sorted(s: str) -> str:
    """Lowercase, alpha-only tokens, sorted — order-invariant name comparison."""
    tokens = re.sub(r"[^a-z ]", "", s.lower()).split()
    return " ".join(sorted(tokens))


class LearnerResolver:
    def __init__(self):
        self.students: list[str] = []
        self.id_map:   dict[str, str] = {}

        with open(ID_MAPPING, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.students.append(row["canonical_name"])
                self.id_map[row["canonical_name"]] = row["learner_id"]

        self._norm_names        = [_norm(s) for s in self.students]
        self._norm_sorted_names = [_norm_sorted(s) for s in self.students]

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def resolve(self, username_raw: str) -> dict:
        """
        Resolve a raw username (email, plain name, or SSO token) to a learner_id.

        Returns dict with keys:
            learner_id   — our ID_LRN_XXXXXX, or None
            match_route  — one of the tier labels above
            note         — extra detail (candidate list, fuzzy score, etc.)
        """
        if not username_raw or not str(username_raw).strip():
            return self._result(None, "unmatched", "empty username")

        u = str(username_raw).strip()

        if re.match(r"^[a-f0-9]{32}$", u):
            return self._result(None, "unresolvable", "MD5 hash — structurally unmatchable")

        prefix = u.split("@")[0] if "@" in u else u

        # --- Strategy 1 & 2: structural (initial+lastname, token-concat) ---
        cands = self._structural_candidates(_norm(prefix))

        if len(cands) == 1:
            return self._result(self.id_map[cands[0]], "matched_exact", cands[0])

        if len(cands) > 1:
            return self._result(
                None, "ambiguous",
                "multiple candidates: " + "; ".join(cands)
            )

        # --- Strategy 3: full-name match (for Quill/Northstar plain names) ---
        # Try direct sorted-token match first (exact order-invariant)
        ns = _norm_sorted(prefix)
        if ns in self._norm_sorted_names:
            idx   = self._norm_sorted_names.index(ns)
            canon = self.students[idx]
            return self._result(self.id_map[canon], "matched_exact", canon)

        # --- Strategy 4: fuzzy ---
        close = difflib.get_close_matches(_norm(prefix), self._norm_names, n=1, cutoff=0.75)
        if close:
            idx   = self._norm_names.index(close[0])
            canon = self.students[idx]
            score = difflib.SequenceMatcher(None, _norm(prefix), close[0]).ratio()
            return self._result(
                self.id_map[canon], "matched_fuzzy",
                f"{canon} (score={score:.2f})"
            )

        return self._result(None, "unmatched", "no candidate found")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _structural_candidates(self, prefix_norm: str) -> list[str]:
        """
        Strategy 1 — initial + lastname:
          'cmutabaruka' matches 'Chania Ikirezi Mutabaruka'
          (c = first char of 'Chania', mutabaruka = token)

        Strategy 2 — concatenated tokens (any order):
          'agasaroorion' matches 'Orion Agasaro'
        """
        cands = []

        for s in self.students:
            parts = s.lower().split()
            found = False
            for i, part in enumerate(parts):
                for j, other in enumerate(parts):
                    if i != j and other and prefix_norm == _norm(other[0] + part):
                        cands.append(s)
                        found = True
                        break
                if found:
                    break

        if not cands:
            for s in self.students:
                parts = s.lower().split()
                if len(parts) >= 2:
                    if (_norm(parts[0] + parts[1]) == prefix_norm or
                            _norm(parts[1] + parts[0]) == prefix_norm):
                        cands.append(s)

        return list(dict.fromkeys(cands))

    def _result(self, learner_id, match_route, note) -> dict:
        return {
            "learner_id":   learner_id,
            "match_route":  match_route,
            "note":         note,
        }
