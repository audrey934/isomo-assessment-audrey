
import pandas as pd

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from db import get_connection

conn = get_connection()
cur = conn.cursor()

# --- Create schema ---
cur.execute("CREATE SCHEMA IF NOT EXISTS isomo;")

# --- Load mapping tables ---
learner_map = pd.read_csv("data/learner_id_mapping.csv")[["learner_id", "canonical_name", "combinations"]]
school_map = pd.read_csv("data/school_id_mapping.csv")[["school_id", "canonical_name"]]

# --- master_school ---
school = pd.read_csv("raw/reference/master_school.csv")
school.columns = [c.lower().strip().replace(" ", "_") for c in school.columns]

# Drop the empty school_id column and replace with mapping
school = school.drop(columns=["school_id"])
school = school.merge(school_map, on="canonical_name", how="left")
school = school[["school_id", "canonical_name", "active"]]  # reorder
school.to_csv("data/master_school_clean.csv", index=False)

cur.execute("DROP TABLE IF EXISTS isomo.master_school;")
cur.execute("""
    CREATE TABLE isomo.master_school (
        school_id TEXT,
        canonical_name TEXT,
        active BOOLEAN
    );
""")
for _, row in school.iterrows():
    cur.execute(
        "INSERT INTO isomo.master_school VALUES (%s, %s, %s)",
        (row.school_id, row.canonical_name, row.active)
    )

# --- master_student ---
student = pd.read_csv("raw/reference/master_student.csv")
student.columns = [c.lower().strip().replace(" ", "_") for c in student.columns]

# Drop empty ID columns and replace with mapping
student = student.drop(columns=["learner_id", "school_id"])
student = student.merge(learner_map, on=["canonical_name", "combinations"], how="left")
student = student.merge(school_map, on="canonical_name", how="left")

# Flag 3 null combinations
student["combinations_flag"] = student["combinations"].isna()

# Reorder columns cleanly
student = student[["learner_id", "school_id", "canonical_name", "gender", "combinations", "is_admitted", "combinations_flag"]]
student.to_csv("data/master_student_clean.csv", index=False)

cur.execute("DROP TABLE IF EXISTS isomo.master_student;")
cur.execute("""
    CREATE TABLE isomo.master_student (
        learner_id TEXT,
        school_id TEXT,
        canonical_name TEXT,
        gender TEXT,
        combinations TEXT,
        is_admitted TEXT,
        combinations_flag BOOLEAN
    );
""")
for _, row in student.iterrows():
    cur.execute(
        "INSERT INTO isomo.master_student VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (row.learner_id, row.school_id, row.canonical_name,
         row.gender, row.combinations, row.is_admitted, row.combinations_flag)
    )

conn.commit()
cur.close()
conn.close()
print("Done: master_school and master_student cleaned and loaded.")
