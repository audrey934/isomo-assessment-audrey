import glob
import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)

query_files = sorted(glob.glob("queries/*.sql"))

for path in query_files:
    with open(path, "r") as f:
        sql = f.read()

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)

    print("\n==============================")
    print(path)
    print(f"Rows returned: {len(df)}")
    print(df.head(5))