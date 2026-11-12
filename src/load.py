
import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

RAW = Path("data/raw/linkedin_postings")
SCHEMA = Path("sql/schema.sql")
engine = create_engine(os.environ["DATABASE_URL"])

# ---------------------------------------------------------------------------
# Role classification (first match wins, so order matters)
# ---------------------------------------------------------------------------
ROLE_PATTERNS = [
    ("Data Scientist", r"data scien"),
    ("Data Engineer", r"data engineer"),
    ("BI Analyst", r"\bbi\b.*(analy|develop|engineer)|business intelligence|power ?bi|tableau"),
    ("Reporting Analyst", r"reporting analy"),
    ("Data Analyst", r"data analy|analytics analy|insights? analy"),
    ("Business Analyst", r"business analy"),
    ("Operations Analyst", r"operations? analy"),
    ("Supply Chain Analyst", r"(supply chain|logistics|procurement|inventory|demand planning).*analy|analy.*(supply chain|logistics)"),
    ("Financial Analyst", r"financ\w* analy"),
    ("Other Analyst", r"analyst"),
]
ROLE_REGEX = [(name, re.compile(pat)) for name, pat in ROLE_PATTERNS]


def role_family(title) -> str:
    t = str(title or "").lower()
    for name, rx in ROLE_REGEX:
        if rx.search(t):
            return name
    return "Other"


def split_location(loc):
    """'Chicago, IL' -> ('Chicago', 'IL', 'US'); 'United States' -> country only."""
    if not isinstance(loc, str) or not loc.strip():
        return (None, None, None)
    parts = [p.strip() for p in loc.split(",")]
    if len(parts) >= 2:
        last = parts[-1]
        return (parts[0], last, "US" if len(last) == 2 else last)
    return (None, None, parts[0])  # e.g. "United States"


def load(df: pd.DataFrame, table: str) -> None:
    df.to_sql(table, engine, if_exists="append", index=False,
              method="multi", chunksize=2000)
    print(f"  {table}: {len(df):,} rows")


def main() -> None:
    # 1. Create schema ------------------------------------------------------
    with engine.begin() as conn:
        conn.exec_driver_sql(SCHEMA.read_text())
    print("Schema created.")

    # 2. Read raw files -----------------------------------------------------
    postings = pd.read_csv(RAW / "postings.csv")
    companies = pd.read_csv(RAW / "companies" / "companies.csv")
    industries = pd.read_csv(RAW / "mappings" / "industries.csv")
    skills_map = pd.read_csv(RAW / "mappings" / "skills.csv")
    job_ind = pd.read_csv(RAW / "jobs" / "job_industries.csv")
    job_cat = pd.read_csv(RAW / "jobs" / "job_skills.csv")
    print(f"Read {len(postings):,} postings.")

    # 3. Clean postings -----------------------------------------------------
    postings = postings.drop_duplicates("job_id").copy()
    postings["listed_date"] = pd.to_datetime(
        postings["listed_time"], unit="ms", errors="coerce").dt.date
    postings["role_family"] = postings["title"].map(role_family)
    postings["remote_allowed"] = postings["remote_allowed"].fillna(0).astype(bool)
    postings["company_id"] = pd.to_numeric(
        postings["company_id"], errors="coerce").astype("Int64")

    # normalized_salary is annualised by the dataset; drop implausible values
    sal = postings["normalized_salary"]
    postings["salary_annual"] = sal.where(sal.between(15_000, 1_000_000))

    # 4. Dimensions ---------------------------------------------------------
    dim_company = (companies[["company_id", "name", "company_size",
                              "city", "state", "country"]]
                   .drop_duplicates("company_id").copy())
    dim_company["company_size"] = pd.to_numeric(
        dim_company["company_size"], errors="coerce").astype("Int64")

    locs = postings["location"].dropna().unique()
    dim_location = pd.DataFrame(
        [(loc, *split_location(loc)) for loc in locs],
        columns=["location_raw", "city", "state_code", "country"])

    dates = pd.date_range(postings["listed_date"].min(),
                          postings["listed_date"].max())
    dim_date = pd.DataFrame({
        "date_id": dates.date,
        "year": dates.year,
        "month": dates.month,
        "month_name": dates.strftime("%B"),
        "week": dates.isocalendar().week.values,
        "day_of_week": dates.dayofweek,
    })

    dim_industry = industries.drop_duplicates("industry_id")
    dim_category = skills_map.rename(columns={"skill_name": "category_name"})

    print("Loading dimensions ...")
    load(dim_date, "dim_date")
    load(dim_company, "dim_company")
    load(dim_location, "dim_location")
    load(dim_industry, "dim_industry")
    load(dim_category, "dim_category")

    # 5. Fact table ---------------------------------------------------------
    loc_ids = pd.read_sql(
        "SELECT location_id, location_raw FROM dim_location", engine)
    fact = postings.merge(loc_ids, left_on="location",
                          right_on="location_raw", how="left")

    # keep company_id only when it exists in dim_company (avoids FK errors)
    valid_companies = set(dim_company["company_id"].dropna().astype(int))
    fact["company_id"] = fact["company_id"].where(
        fact["company_id"].isin(valid_companies))

    fact = fact.rename(columns={"formatted_work_type": "work_type",
                                "formatted_experience_level": "experience_level"})
    # postings.csv also has a raw 'work_type' code column; the rename above
    # would create a duplicate, so keep only one:
    fact = fact.loc[:, ~fact.columns.duplicated(keep="last")]

    fact = fact[["job_id", "company_id", "location_id", "listed_date", "title",
                 "role_family", "work_type", "experience_level", "remote_allowed",
                 "salary_annual", "views", "applies", "description"]]

    print("Loading fact table ...")
    load(fact, "fact_postings")

    # 6. Bridge tables ------------------------------------------------------
    valid_jobs = set(fact["job_id"])
    print("Loading bridges ...")
    load(job_ind[job_ind["job_id"].isin(valid_jobs)
                 & job_ind["industry_id"].isin(dim_industry["industry_id"])]
         .drop_duplicates(), "bridge_posting_industry")
    load(job_cat[job_cat["job_id"].isin(valid_jobs)
                 & job_cat["skill_abr"].isin(dim_category["skill_abr"])]
         .drop_duplicates(), "bridge_posting_category")

    # 7. Summary ------------------------------------------------------------
    summary = pd.read_sql("""
        SELECT COUNT(*)              AS postings,
               MIN(listed_date)      AS first_date,
               MAX(listed_date)      AS last_date,
               COUNT(salary_annual)  AS with_salary
        FROM fact_postings""", engine)
    print("\nLoad summary:")
    print(summary.to_string(index=False))

    roles = pd.read_sql("""
        SELECT role_family, COUNT(*) AS n, ROUND(AVG(salary_annual)) AS avg_salary
        FROM fact_postings GROUP BY role_family ORDER BY n DESC""", engine)
    print("\nPostings by role family:")
    print(roles.to_string(index=False))


if __name__ == "__main__":
    main()
