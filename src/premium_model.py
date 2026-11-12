"""Skill premium adjusted for role family and experience level (OLS on log salary)."""
import os

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

ROLES = ("Data Analyst", "BI Analyst", "Business Analyst",
         "Reporting Analyst", "Operations Analyst")
MIN_N = 25  # a skill needs at least this many salaried postings

jobs = pd.read_sql("""
    SELECT job_id, role_family,
           COALESCE(experience_level, 'Not stated') AS exp_level,
           salary_annual
    FROM fact_postings
    WHERE role_family IN %(roles)s AND salary_annual IS NOT NULL
""", engine, params={"roles": ROLES})

sk = pd.read_sql("""
    SELECT b.job_id, s.skill_name, s.skill_group
    FROM bridge_posting_skill b JOIN dim_skill s ON s.skill_id = b.skill_id
""", engine)
sk = sk[sk["job_id"].isin(jobs["job_id"]) & (sk["skill_group"] != "Soft Skill")]

wide = pd.crosstab(sk["job_id"], sk["skill_name"]).clip(upper=1)
keep = wide.columns[wide.sum() >= MIN_N]
wide = wide[keep]

df = jobs.merge(wide, left_on="job_id", right_index=True, how="left")
df[list(keep)] = df[list(keep)].fillna(0)
df["log_salary"] = np.log(df["salary_annual"])
print(f"{len(df)} salaried postings, {len(keep)} skills with >= {MIN_N} postings")

terms = " + ".join(f"Q('{c}')" for c in keep)
model = smf.ols(f"log_salary ~ {terms} + C(role_family) + C(exp_level)",
                data=df).fit(cov_type="HC3")  # robust standard errors

ci = model.conf_int()
rows = []
for c in keep:
    key = f"Q('{c}')"
    rows.append({
        "skill": c,
        "n_with": int(df[c].sum()),
        "pct_effect": round((np.exp(model.params[key]) - 1) * 100, 1),
        "ci_low": round((np.exp(ci.loc[key, 0]) - 1) * 100, 1),
        "ci_high": round((np.exp(ci.loc[key, 1]) - 1) * 100, 1),
        "p_value": round(model.pvalues[key], 3),
    })
out = pd.DataFrame(rows).sort_values("pct_effect", ascending=False)
print(out.to_string(index=False))
print(f"\nR-squared: {model.rsquared:.2f}")
out.to_csv("data/processed/skill_premium_adjusted.csv", index=False)
