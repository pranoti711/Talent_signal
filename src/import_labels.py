"""Read labels back from Excel, validate names, save to label_sample.csv."""
import pandas as pd
from extract_skills import SKILLS

SHEET = "data/processed/label_sheet.xlsx"
CSV = "data/processed/label_sample.csv"

names = {n.lower(): n for n in SKILLS}
sheet = pd.read_excel(SHEET).fillna("")
base = pd.read_csv(CSV).fillna("")

clean, problems = {}, []
for _, r in sheet.iterrows():
    raw = str(r["true_skills"]).strip()
    if not raw:
        continue
    if raw.upper() == "NONE":
        clean[r["job_id"]] = "NONE"
        continue
    items = [x.strip().lower() for x in raw.replace(";", ",").split(",") if x.strip()]
    bad = [x for x in items if x not in names]
    if bad:
        problems.append((r["job_id"], bad))
    else:
        clean[r["job_id"]] = "; ".join(sorted({names[x] for x in items}))

base["true_skills"] = base["job_id"].map(clean).fillna("")
base.to_csv(CSV, index=False)

print(f"{len(clean)} postings labelled and saved.")
if problems:
    print("\nFix these in the sheet (unknown skill names), then re-run:")
    for job_id, bad in problems:
        print(f"  job_id {job_id}: {bad}")
