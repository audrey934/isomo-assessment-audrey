import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)

files = {
    "quill_activity": "data/quill_activity_clean.csv",
    "quill_connect_sessions": "data/quill_connect_sessions_clean.csv",
    "typing_lesson_activity": "data/typing_lesson_activity_clean.csv",
    "typing_test_attempts": "data/typing_test_attempts_clean.csv",
    "det_scores": "data/det_scores_clean.csv",
    "efset_results": "data/efset_results_clean.csv",
    "northstar_results": "data/northstar_results_clean.csv",
    "master_student": "data/master_student_clean.csv",
    "master_school": "data/master_school_clean.csv",
}

for table, path in files.items():
    df = pd.read_csv(path)
    df.to_sql(table, engine, if_exists="replace", index=False)
    print(f"{table}: {len(df)} rows loaded")