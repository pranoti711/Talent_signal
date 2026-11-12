"""Terminal helper for hand-labelling skills. Resumable; saves after each posting."""
import pandas as pd
from extract_skills import SKILLS

PATH = "data/processed/label_sample.csv"
df = pd.read_csv(PATH).fillna("")
names = {n.lower(): n for n in SKILLS}

print("Type the skills you see, separated by commas (e.g. sql, python, power bi).")
print("Commands: Enter on a blank line = none found | ? = list valid names | q = save and quit\n")

for i, row in df.iterrows():
    if row["true_skills"] != "":
        continue
    print("=" * 80)
    print(f"[{i + 1}/{len(df)}]  job_id {row['job_id']}")
    print(row["description"][:2500])
    while True:
        raw = input("\nskills> ").strip()
        if raw.lower() == "q":
            df.to_csv(PATH, index=False)
            raise SystemExit("Saved. Run again to resume.")
        if raw == "?":
            print(", ".join(sorted(names.values())))
            continue
        items = [x.strip().lower() for x in raw.split(",") if x.strip()]
        bad = [x for x in items if x not in names]
        if bad:
            print("Unknown:", bad, "(type ? to list valid names)")
            continue
        df.at[i, "true_skills"] = "; ".join(names[x] for x in items) or "NONE"
        df.to_csv(PATH, index=False)
        break

print("All done.")
