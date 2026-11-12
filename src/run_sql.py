"""Run a .sql file against the Talent Signal database."""
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()
path = Path(sys.argv[1] if len(sys.argv) > 1 else "sql/analytics.sql")

# DATABASE_URL looks like postgresql+psycopg2://user:pass@host:5432/db
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")

conn = psycopg2.connect(url)
try:
    with conn, conn.cursor() as cur:       # commits on success, rolls back on error
        cur.execute(path.read_text(encoding="utf-8"))
    print("Ran", path)
finally:
    conn.close()