"""Extract skills from job descriptions into dim_skill + bridge_posting_skill.

Run from the project root:  python src/extract_skills.py
Safe to re-run: it rebuilds dim_skill and bridge_posting_skill each time,
and never overwrites data/processed/label_sample.csv once it exists.
"""
import os
import re

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

I = re.I  # case-insensitive; flags=0 means case-sensitive (for ambiguous words)

# name: (group, regex, flags)
SKILLS = {
    # Programming
    "Python": ("Programming", r"\bpython\b", I),
    "R": ("Programming", r"(?<![&\w])R\b(?=\s*(?:programming|language|studio|shiny|,|/|\)|and Python|or Python|or other))|(?:Python|SAS|SQL|MATLAB|Stata|SPSS)\s*(?:,|/|and|or)\s*R\b", 0),
    "SQL": ("Programming", r"\b[Ss][Qq][Ll]\b|(?<=[A-Z]{2})SQL\b", 0),
    "SAS": ("Programming", r"\bSAS\b", 0),
    "VBA": ("Programming", r"\bvba\b|visual basic for applications", I),
    "Java": ("Programming", r"\bjava\b", I),
    "Scala": ("Programming", r"\bscala\b", I),
    "JavaScript": ("Programming", r"\bjavascript\b", I),
    # Databases / warehouses
    "PostgreSQL": ("Database", r"\bpostgres(?:ql)?\b", I),
    "MySQL": ("Database", r"\bmysql\b", I),
    "SQL Server": ("Database", r"\bsql server\b|\bt-sql\b|\bmssql\b", I),
    "Oracle": ("Database", r"\boracle\b", I),
    "MongoDB": ("Database", r"\bmongo ?db\b", I),
    "Snowflake": ("Database", r"\bsnowflake\b", I),
    "BigQuery": ("Database", r"\bbig ?query\b", I),
    "Redshift": ("Database", r"\bredshift\b", I),
    "Databricks": ("Database", r"\bdatabricks\b", I),
    # BI / reporting tools
    "Power BI": ("BI Tool", r"\bpower ?-?bi\b", I),
    "Tableau": ("BI Tool", r"\btableau\b", I),
    "Looker": ("BI Tool", r"\blooker\b", I),
    "Qlik": ("BI Tool", r"\bqlik(?:view|sense)?\b", I),
    "Excel": ("BI Tool", r"\b(?:Microsoft Excel|MS Excel|Excel)\b(?!\s+(?:in|at|as|under|when|by|with a)\b)", 0),
    "Google Sheets": ("BI Tool", r"\bgoogle sheets\b", I),
    "DAX": ("BI Tool", r"\bDAX\b", 0),
    "Power Query": ("BI Tool", r"\bpower query\b", I),
    "SSRS/SSIS": ("BI Tool", r"\bssrs\b|\bssis\b|\bssas\b", I),
    "Alteryx": ("BI Tool", r"\balteryx\b", I),
    # Cloud
    "AWS": ("Cloud", r"\baws\b|amazon web services", I),
    "Azure": ("Cloud", r"\bazure\b", I),
    "GCP": ("Cloud", r"\bgcp\b|google cloud", I),
    # Data engineering
    "Spark": ("Data Engineering", r"\b(?:apache )?spark\b|\bpyspark\b", I),
    "Airflow": ("Data Engineering", r"\bairflow\b", I),
    "dbt": ("Data Engineering", r"\bdbt\b", I),
    "Kafka": ("Data Engineering", r"\bkafka\b", I),
    "Hadoop": ("Data Engineering", r"\bhadoop\b", I),
    "ETL": ("Data Engineering", r"\betl\b|\belt\b|data pipelines?", I),
    "Data Warehousing": ("Data Engineering", r"data warehous\w*", I),
    # Libraries / ML
    "pandas": ("Python Library", r"\bpandas\b", I),
    "NumPy": ("Python Library", r"\bnumpy\b", I),
    "scikit-learn": ("Python Library", r"\bscikit-?learn\b|\bsklearn\b", I),
    "TensorFlow": ("Python Library", r"\btensorflow\b", I),
    "PyTorch": ("Python Library", r"\bpytorch\b", I),
    "Machine Learning": ("Analytics", r"machine learning|\bml\b", I),
    # Analytics methods
    "Statistics": ("Analytics", r"\bstatistic\w*", I),
    "A/B Testing": ("Analytics", r"\ba/b test\w*|\bexperimentation\b", I),
    "Forecasting": ("Analytics", r"\bforecast\w*", I),
    "Regression": ("Analytics", r"\bregression\b", I),
    "Data Visualization": ("Analytics", r"data visuali[sz]ation|data visuals|\bdashboard\w*", I),
    "Data Modeling": ("Analytics", r"data model(?:l)?ing", I),
    "KPI/Metrics": ("Analytics", r"\bkpis?\b|key performance indicators?", I),
    "Data Cleaning": ("Analytics", r"data cleaning|data cleansing|data wrangling", I),
    # Business tools
    "SAP": ("Business Tool", r"\bSAP\b", 0),
    "Salesforce": ("Business Tool", r"\bsalesforce\b", I),
    "Jira": ("Business Tool", r"\bjira\b", I),
    "Git": ("Business Tool", r"\bgit(?:hub)?\b", I),
    # Soft skills
    "Communication": ("Soft Skill", r"\bcommunicat\w+", I),
    "Stakeholder Management": ("Soft Skill", r"\bstakeholder\w*", I),
    "Problem Solving": ("Soft Skill", r"problem[- ]solving", I),
    "Project Management": ("Soft Skill", r"project management", I),
    "Agile": ("Soft Skill", r"\bagile\b|\bscrum\b", I),
    "Leadership": ("Soft Skill", r"\bleadership\b", I),
}

COMPILED = {n: (g, re.compile(p, f)) for n, (g, p, f) in SKILLS.items()}

# ---------------------------------------------------------------------------
# Text normalisation: the dataset often glues sentences together
# ("MatlabExperience", "ExperienceSQL"). We also scan a version of the text
# with those joins split, except for real CamelCase product names.
# ---------------------------------------------------------------------------
PROTECTED = {
    "JavaScript", "TypeScript", "TensorFlow", "PyTorch", "NumPy", "SciPy",
    "PostgreSQL", "MySQL", "NoSQL", "SQLite", "MongoDB", "BigQuery", "DataBricks",
    "GitHub", "GitLab", "PowerBI", "PowerShell", "PowerPoint", "SharePoint",
    "ServiceNow", "LinkedIn", "QlikView", "QlikSense", "PySpark", "DevOps",
    "MatLab", "RStudio", "OneDrive", "NetSuite", "WordPress",
}
_WORD = re.compile(r"[A-Za-z]+")
_SPLIT = re.compile(r"(?<=[a-z])(?=[A-Z])")


def normalise(text: str) -> str:

    def fix(m):
        w = m.group(0)
        return w if w in PROTECTED else _SPLIT.sub(" ", w)

    return _WORD.sub(fix, text)


def extract(text) -> set:
    """Return the set of skill names found in a description."""
    if not isinstance(text, str):
        return set()
    norm = normalise(text)
    return {name for name, (_, rx) in COMPILED.items()
            if rx.search(text) or rx.search(norm)}


# 'Other' roles are skipped: ~117K non-analytics postings
SCOPE_SQL = ("SELECT job_id, description FROM fact_postings "
             "WHERE role_family <> 'Other'")
LABEL_CSV = "data/processed/label_sample.csv"


def main() -> None:
    df = pd.read_sql(SCOPE_SQL, engine)
    print(f"Scanning {len(df):,} postings ...")
    df["skills"] = df["description"].map(extract)

    with engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE dim_skill RESTART IDENTITY CASCADE")

    dim = pd.DataFrame([(n, g) for n, (g, _) in COMPILED.items()],
                       columns=["skill_name", "skill_group"])
    dim.to_sql("dim_skill", engine, if_exists="append", index=False)
    ids = pd.read_sql("SELECT skill_id, skill_name FROM dim_skill", engine)
    id_of = dict(zip(ids["skill_name"], ids["skill_id"]))

    rows = [(j, id_of[s]) for j, ss in zip(df["job_id"], df["skills"]) for s in ss]
    bridge = pd.DataFrame(rows, columns=["job_id", "skill_id"])
    bridge.to_sql("bridge_posting_skill", engine, if_exists="append",
                  index=False, method="multi", chunksize=5000)
    print(f"Wrote {len(bridge):,} posting-skill links "
          f"({len(bridge) / len(df):.1f} skills per posting)")

    # Hand-labelling sample: created once, never overwritten
    if not os.path.exists(LABEL_CSV):
        sample = df.sample(100, random_state=42).copy()
        sample["true_skills"] = ""
        sample["description"] = sample["description"].str.slice(0, 3000)
        os.makedirs("data/processed", exist_ok=True)
        sample[["job_id", "true_skills", "description"]].to_csv(LABEL_CSV, index=False)
        print("Saved", LABEL_CSV)
    else:
        print(LABEL_CSV, "already exists, left untouched")


if __name__ == "__main__":
    main()
