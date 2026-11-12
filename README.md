
# Talent Signal: Labour Market Intelligence Platform

An end-to-end data analytics project that turns **123,849 LinkedIn job postings** into evidence about the US analyst job market: which skills employers ask for, how demand differs by role and experience level, and what the salary data can and cannot support.

**Stack:** Python · PostgreSQL · SQL · Power BI · DAX

<p align="center">
  <img src="docs/screenshots/01_home.png" alt="Talent Signal dashboard home page" width="100%">
</p>

---

## Table of contents

1. [Business questions](#business-questions)
2. [Dashboard pages](#dashboard-pages)
3. [Key findings](#key-findings)
4. [Architecture](#architecture)
5. [Data](#data)
6. [Methodology](#methodology)
7. [Skill extractor validation](#skill-extractor-validation)
8. [Repository structure](#repository-structure)
9. [How to run it](#how-to-run-it)
10. [Limitations](#limitations)
11. [Future work](#future-work)
12. [Author](#author)

---

## Business questions

1. Which skills are most requested for each analyst role (Data Analyst, BI Analyst, Business Analyst and others)?
2. How does skill demand change with experience level?
3. Which skills travel together in the same posting?
4. Is there a salary premium for a skill, once role and seniority are accounted for?
5. Given the skills a candidate has, which roles fit best and what should they learn next?

---

## Dashboard pages

The report uses one layout on every page: a left rail for navigation and slicers, a KPI ribbon across the top, a large main visual on the left, and supporting visuals on the right.

| # | Page | What it answers |
|---|------|-----------------|
| 1 | **Home** | What the project is, the data behind it, and navigation to every page. |
| 2 | **Overview** | Headline KPIs, top skills, and postings by role. |
| 3 | **Skill demand** | Share of postings naming each skill, grouped by skill family. |
| 4 | **Experience and salary** | Skill demand by experience level, with median salary and sample size. |
| 5 | **Salary premium** | Raw salary gaps beside regression-adjusted effects with confidence intervals. |
| 6 | **Geography** | Top metros by posting count, with salary shown only where the sample allows. |
| 7 | **Skill gap simulator** | Pick your skills, see your match per role and the skills to learn next. |


### Home
![Home](docs/screenshots/01_home.png)

### Overview
![Overview](docs/screenshots/02_overview.png)

### Skill demand
![Skill demand](docs/screenshots/03_skill_demand.png)

### Experience and salary
![Experience and salary](docs/screenshots/04_experience_salary.png)

### Salary premium
![Salary premium](docs/screenshots/05_salary_premium.png)

### Geography
![Geography](docs/screenshots/06_geography.png)

### Skill gap simulator
![Skill gap simulator](docs/screenshots/07_skill_gap_simulator.png)


---

## Key findings

All figures come from a 28-day snapshot of US-weighted postings, so read them as patterns in this sample.

**Skill demand (745 Data Analyst postings)**

| Skill | Share of postings |
|-------|------------------|
| SQL | 54.1% |
| Python | 35.6% |
| Excel | 35.0% |
| Power BI | 19.1% |

**Skills requested with Power BI** (analyst-type roles): SQL appears in 58% of those postings, Excel in 48% and Python in 34%. Tableau appears in 42%, but this mostly reflects postings that list both tools as alternatives, not employers requiring both.

**Salary: raw gaps mostly disappear after adjustment** (536 analyst postings with a stated salary, R² = 0.41)

- Raw median salary gaps looked large. For example, postings naming Tableau had a median about $15.6K higher than those that did not.
- After controlling for role family and experience level with a log-salary regression, the Tableau effect fell to **+3.0%** with a confidence interval that includes zero. Most skills behave the same way.
- **ETL (+16.6%, 95% CI +5.5% to +29.0%)** and **Jira (+14.8%, +2.9% to +28.2%)** are the clearest positive associations.
- **Excel (-9.0%)** and **Power BI (-7.3%)** are negative. Read this as "postings naming these tools pay less than comparable postings", which is likely an employer or industry mix effect, not evidence that the skills reduce pay.

**Geography:** New York is the largest market in the sample (49 analyst postings, 20 with a stated salary). Most other metros have too few salaried postings to report an average, so the dashboard hides salary below 10 postings.

---

## Architecture

```
Kaggle dataset
     |
     v
ingest.py        download raw CSVs
     |
     v
load.py          clean, classify roles, load star schema into PostgreSQL
     |
     v
extract_skills.py   regex skill dictionary -> dim_skill + bridge_posting_skill
     |
     v
analytics.sql    reporting views (demand, premium, geography, postings)
     |
     +--> premium_model.py   adjusted salary regression -> CSV
     |
     v
Power BI         model, DAX measures, 9-page report
```

**Star schema**

- `fact_postings`: one row per job posting (role family, experience level, salary, dates, description)
- `dim_company`, `dim_location`, `dim_date`, `dim_industry`, `dim_skill`, `dim_category`
- `bridge_posting_skill`, `bridge_posting_industry`, `bridge_posting_category`

---

## Data

- **Source:** LinkedIn Job Postings (2023-2024) dataset on Kaggle, `arshkon/linkedin-job-postings`.
- **Size:** 123,849 postings, of which 6,744 are analyst-type roles.
- **Time window:** 28 days, so the project is a snapshot and does not measure trends over time.
- **Geography:** mostly US locations.
- **Licence:** check the dataset's licence on its Kaggle page before redistributing any raw data. This repository does not include the raw files; the pipeline downloads them.

---

## Methodology

**1. Cleaning and role classification.** Postings are deduplicated, timestamps converted, and salaries restricted to a plausible annual range. A rule-based classifier maps job titles to role families (Data Analyst, BI Analyst, Business Analyst, Reporting Analyst, Operations Analyst, Supply Chain Analyst, Financial Analyst, Data Scientist, Data Engineer). Roles outside these families are labelled "Other" and excluded from skill analysis.

**2. Skill extraction.** The LinkedIn skill field only holds broad categories, so skills are extracted from each description with a curated dictionary of about 60 skills and regex patterns. Patterns handle aliases (`PowerBI`, `Power BI`), ambiguous words (the language R versus the letter) and sentences the dataset glued together without spaces.

**3. Skill demand.** Demand is the share of postings in a role that mention a skill, which keeps roles with different posting counts comparable.

**4. Salary premium.** A raw with-versus-without median comparison is shown for transparency, then a log-salary OLS regression with robust standard errors estimates each skill's association after controlling for role family and experience level. Only skills with at least 25 salaried postings are included.

**5. Skill gap simulator.** For each posting, match is the share of its technical skills that the user has, averaged across postings in the chosen role.

---

## Skill extractor validation

The extractor was checked against postings read and labelled by hand. Labels follow these rules: a skill counts when the posting names it as a requirement or a tool used in the role, and the dictionary's wording is applied literally.

| Metric | Technical skills | All skills |
|--------|------------------|------------|
| Labelled postings | _to be completed_ | _to be completed_ |
| Precision | _to be completed_ | _to be completed_ |
| Recall | _to be completed_ | _to be completed_ |

Error analysis led to fixes for sentence-boundary glue in the raw text and for ambiguous patterns. The full per-skill table is written to `data/processed/extractor_eval.csv` by `src/evaluate.py`.

---

## Repository structure

```
talent-signal/
├── data/
│   ├── raw/                     downloaded by ingest.py (not committed)
│   └── processed/
│       ├── skill_premium_adjusted.csv
│       └── extractor_eval.csv
├── docs/                
│   └── screenshots/             one image per dashboard page
├── dashboard/
│   └── dashboard.pbix
├── sql/
│   ├── schema.sql               star schema
│   └── analytics.sql            reporting views
├── src/
│   ├── ingest.py                download the dataset
│   ├── load.py                  clean and load into PostgreSQL
│   ├── extract_skills.py        skill extraction
│   ├── run_sql.py               run a .sql file
│   ├── premium_model.py         adjusted salary regression
│   ├── export_labels.py         create the labelling sheet
│   ├── import_labels.py         read labels back
│   ├── label_helper.py          terminal labelling helper
│   ├── evaluate.py              precision and recall
│   └── why.py                   show where a skill matched
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## How to run it

**Requirements:** Python 3.10+, PostgreSQL, Power BI Desktop (Windows), and a free Kaggle account.

**1. Install**

```bash
git clone https://github.com/pranoti711/talent-signal.git
cd talent-signal
pip install -r requirements.txt
```

**2. Configure**

Create an empty PostgreSQL database named `talent_signal`, then copy `.env.example` to `.env` and fill it in:

```
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/talent_signal
KAGGLE_USERNAME=your_username
KAGGLE_KEY=your_api_key
```

**3. Build the pipeline**

```bash
python src/ingest.py            # download raw data
python src/load.py              # clean and load (drops and recreates all tables)
python src/extract_skills.py    # extract skills
python src/run_sql.py           # create the reporting views
python src/premium_model.py     # adjusted salary regression
```

`load.py` rebuilds every table, so run the last three commands again afterwards.

**4. Open the report**

Open `powerbi/talent_signal.pbix`, then **Transform data, Data source settings** and point the PostgreSQL connection at your local server.

**5. Optional: re-validate the extractor**

```bash
python src/export_labels.py      # creates the labelling sheet (run once)
# label postings in data/processed/label_sheet.xlsx, then:
python src/import_labels.py
python src/evaluate.py
```

---

## Limitations

- **Four-week snapshot.** The data cannot show trends over time, so there are no momentum or growth claims.
- **US-weighted sample.** Most locations are in the United States, so the results do not describe India or other markets.
- **Postings are not hires.** The data shows what employers ask for, not what they hire or pay.
- **Salary coverage is low.** Only 536 analyst postings state a salary, and many metros have too few to report an average.
- **Associations, not causes.** Regression results describe patterns in this sample and are not causal estimates. With about 20 skills tested, a few will look significant by chance.
- **Extractor scope.** Skills are matched with a fixed dictionary, so tools outside it (for example Cognos or ServiceNow) are not counted.

---

## Future work

- Add a second source with India-specific postings.
- Collect postings on a schedule to enable trend and momentum analysis.
- Replace regex matching with a model that learns skills from text, compared against the current baseline.
- Forecast demand for the top skills once enough history exists.
- Publish a short written report summarising the findings.

---

## Author

**Pranoti Munjankar**
GitHub: [pranoti711](https://github.com/pranoti711)

Linkedin:(www.linkedin.com/in/pranoti-munjankar-1760092b9)
