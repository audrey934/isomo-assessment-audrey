import os
from dotenv import load_dotenv
import psycopg2

# ALWAYS load .env from where you run the command (project root)
load_dotenv()

def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST")
    )