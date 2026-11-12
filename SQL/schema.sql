DROP TABLE IF EXISTS bridge_posting_skill, bridge_posting_category,
    bridge_posting_industry, fact_postings, dim_skill, dim_category,
    dim_industry, dim_location, dim_company, dim_date CASCADE;

CREATE TABLE dim_date (
    date_id      DATE PRIMARY KEY,
    year         INT, month INT, month_name TEXT,
    week         INT, day_of_week INT
);

CREATE TABLE dim_company (
    company_id   BIGINT PRIMARY KEY,
    name         TEXT, company_size INT,
    city TEXT, state TEXT, country TEXT
);

CREATE TABLE dim_location (
    location_id  SERIAL PRIMARY KEY,
    location_raw TEXT UNIQUE,
    city TEXT, state_code TEXT, country TEXT
);

CREATE TABLE dim_industry (
    industry_id  BIGINT PRIMARY KEY,
    industry_name TEXT
);

CREATE TABLE dim_category (            -- LinkedIn's coarse skill categories
    skill_abr    TEXT PRIMARY KEY,
    category_name TEXT
);

CREATE TABLE dim_skill (               -- YOUR extracted skills (filled in next step)
    skill_id     SERIAL PRIMARY KEY,
    skill_name   TEXT UNIQUE NOT NULL,
    skill_group  TEXT                  -- e.g. Programming, BI Tool, Cloud, Soft Skill
);

CREATE TABLE fact_postings (
    job_id            BIGINT PRIMARY KEY,
    company_id        BIGINT REFERENCES dim_company(company_id),
    location_id       INT REFERENCES dim_location(location_id),
    listed_date       DATE REFERENCES dim_date(date_id),
    title             TEXT,
    role_family       TEXT,
    work_type         TEXT,
    experience_level  TEXT,
    remote_allowed    BOOLEAN,
    salary_annual     NUMERIC,         -- from normalized_salary, outliers removed
    views             INT,
    applies           INT,
    description       TEXT
);

CREATE TABLE bridge_posting_skill (
    job_id   BIGINT REFERENCES fact_postings(job_id),
    skill_id INT    REFERENCES dim_skill(skill_id),
    PRIMARY KEY (job_id, skill_id)
);

CREATE TABLE bridge_posting_category (
    job_id    BIGINT REFERENCES fact_postings(job_id),
    skill_abr TEXT   REFERENCES dim_category(skill_abr),
    PRIMARY KEY (job_id, skill_abr)
);

CREATE TABLE bridge_posting_industry (
    job_id      BIGINT REFERENCES fact_postings(job_id),
    industry_id BIGINT REFERENCES dim_industry(industry_id),
    PRIMARY KEY (job_id, industry_id)
);

CREATE INDEX idx_fact_role   ON fact_postings(role_family);
CREATE INDEX idx_fact_date   ON fact_postings(listed_date);
CREATE INDEX idx_fact_loc    ON fact_postings(location_id);
CREATE INDEX idx_fact_exp    ON fact_postings(experience_level);