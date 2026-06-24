import pandas as pd
import difflib
import re


class LearnerResolver:
    def __init__(self, master_student_path):
        self.master = pd.read_csv(master_student_path)

        # Lookup tables
        self.email_to_id = {}
        self.external_id_to_id = {}
        self.name_to_id = {}

        for _, row in self.master.iterrows():
            learner_id = row["learner_id"]

            # NAME (normalized consistently)
            if "canonical_name" in row and pd.notna(row["canonical_name"]):
                name = self.normalize_name(row["canonical_name"])
                self.name_to_id[name] = learner_id

            # EXTERNAL ID (optional)
            if "external_learner_id" in row and pd.notna(row["external_learner_id"]):
                self.external_id_to_id[row["external_learner_id"]] = learner_id

            # EMAIL (optional)
            if "email" in row and pd.notna(row["email"]):
                self.email_to_id[row["email"].lower().strip()] = learner_id

    # ---------------------------
    # NAME NORMALIZATION (FIXED)
    # ---------------------------
    def normalize_name(self, name: str):
        if not name:
            return ""

        name = name.lower().strip()
        name = re.sub(r"[^a-z0-9 ]", " ", name)
        name = re.sub(r"\s+", " ", name).strip()

        parts = name.split()

        # sort tokens so "David Munyampeta" == "Munyampeta David"
        if len(parts) >= 2:
            return " ".join(sorted(parts))

        return name

    # ---------------------------
    # GENERAL NORMALIZATION
    # ---------------------------
    def normalize(self, text):
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9 ]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    # ---------------------------
    # MAIN RESOLVE FUNCTION
    # ---------------------------
    def resolve(self, email=None, external_id=None, name=None, source_system=None):

        # 1. EMAIL MATCH
        if email:
            email = email.lower().strip()
            if email in self.email_to_id:
                return self.build_result(
                    self.email_to_id[email],
                    "email_exact",
                    0.99,
                    source_system
                )

        # 2. EXTERNAL ID MATCH
        if external_id:
            if external_id in self.external_id_to_id:
                return self.build_result(
                    self.external_id_to_id[external_id],
                    "external_id_exact",
                    0.97,
                    source_system
                )

        # 3. NAME FUZZY MATCH (FIXED NORMALIZATION)
        if name:
            norm_name = self.normalize_name(name)

            matches = difflib.get_close_matches(
                norm_name,
                self.name_to_id.keys(),
                n=1,
                cutoff=0.8
            )

            if matches:
                matched_name = matches[0]
                return self.build_result(
                    self.name_to_id[matched_name],
                    "name_fuzzy",
                    0.75,
                    source_system
                )

        # 4. UNRESOLVED
        return {
            "internal_learner_id": None,
            "match_route": "unresolved",
            "confidence": 0.0,
            "source_system": source_system
        }

    # ---------------------------
    # OUTPUT FORMAT
    # ---------------------------
    def build_result(self, learner_id, route, confidence, source_system):
        return {
            "internal_learner_id": learner_id,
            "match_route": route,
            "confidence": confidence,
            "source_system": source_system
        }