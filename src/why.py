"""Show where a skill matched in a posting.  Usage: python src/why.py <job_id> "<skill>" """
import os, sys
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from extract_skills import COMPILED, normalise

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])
job_id, skill = int(sys.argv[1]), sys.argv[2]

text = pd.read_sql(f"SELECT description FROM fact_postings WHERE job_id = {job_id}", engine).iloc[0, 0]
text = normalise(text)
rx = COMPILED[skill][1]
hits = list(rx.finditer(text))
print(f"{len(hits)} match(es) for '{skill}'")
for m in hits[:5]:
    s, e = max(0, m.start() - 60), min(len(text), m.end() + 60)
    print("...", text[s:e].replace("\n", " "), "...")s