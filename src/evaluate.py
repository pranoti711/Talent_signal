"""Precision/recall of the skill extractor against hand labels."""
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from extract_skills import extract, SKILLS

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

lab = pd.read_csv("data/processed/label_sample.csv").fillna("")
lab = lab[lab["true_skills"] != ""]
if lab.empty:
    raise SystemExit("No labels yet. Run label_helper.py first.")
print(f"{len(lab)} labelled postings")

# full, untruncated descriptions for the same job_ids
ids = ",".join(str(i) for i in lab["job_id"])
desc = pd.read_sql(f"SELECT job_id, description FROM fact_postings WHERE job_id IN ({ids})", engine)
lab["description"] = lab["description"].str.slice(0, 2500)

lab["pred"] = lab["description"].map(extract)
lab["true"] = lab["true_skills"].map(
    lambda s: set() if s == "NONE" else {x.strip() for x in s.split(";") if x.strip()})

rows = {}
for pred, true in zip(lab["pred"], lab["true"]):
    for s in pred | true:
        r = rows.setdefault(s, {"tp": 0, "fp": 0, "fn": 0})
        r["tp"] += s in pred and s in true
        r["fp"] += s in pred and s not in true
        r["fn"] += s in true and s not in pred

res = pd.DataFrame(rows).T.astype(int)
res["precision"] = (res.tp / (res.tp + res.fp).replace(0, float("nan"))).round(2)
res["recall"] = (res.tp / (res.tp + res.fn).replace(0, float("nan"))).round(2)
res["group"] = [SKILLS[s][0] if s in SKILLS else "?" for s in res.index]
res = res.sort_values(["fp", "fn"], ascending=False)
print(res.to_string())


def overall(sub, label):
    tp, fp, fn = sub.tp.sum(), sub.fp.sum(), sub.fn.sum()
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    print(f"{label:<12} precision {p:.3f}   recall {r:.3f}   (tp={tp}, fp={fp}, fn={fn})")


print()
overall(res, "All skills")
overall(res[res.group != "Soft Skill"], "Technical")
res.to_csv("data/processed/extractor_eval.csv")


