-- Talent Signal: analytics views
-- Prerequisite: load.py and extract_skills.py have both run successfully.

-- 1. Skill demand by role (% of that role's postings mentioning the skill)
CREATE OR REPLACE VIEW v_skill_demand AS
WITH role_totals AS (
    SELECT role_family, COUNT(*) AS role_postings
    FROM fact_postings
    WHERE role_family <> 'Other'
    GROUP BY role_family
)
SELECT f.role_family,
       s.skill_name,
       s.skill_group,
       COUNT(*)                                          AS postings,
       rt.role_postings,
       ROUND(100.0 * COUNT(*) / rt.role_postings, 1)     AS pct_of_role
FROM bridge_posting_skill b
JOIN fact_postings f ON f.job_id   = b.job_id
JOIN dim_skill s     ON s.skill_id = b.skill_id
JOIN role_totals rt  ON rt.role_family = f.role_family
GROUP BY f.role_family, s.skill_name, s.skill_group, rt.role_postings;


-- 2. Skill demand by experience level
CREATE OR REPLACE VIEW v_skill_by_experience AS
SELECT COALESCE(f.experience_level, 'Not stated') AS experience_level,
       s.skill_name,
       s.skill_group,
       COUNT(*) AS postings
FROM bridge_posting_skill b
JOIN fact_postings f ON f.job_id   = b.job_id
JOIN dim_skill s     ON s.skill_id = b.skill_id
GROUP BY 1, 2, 3;


-- 3. Skill premium: median salary with vs. without each skill (analyst roles)
CREATE OR REPLACE VIEW v_skill_premium AS
WITH base AS (
    SELECT job_id, salary_annual
    FROM fact_postings
    WHERE role_family <> 'Other' AND salary_annual IS NOT NULL
),
with_skill AS (
    SELECT s.skill_id, s.skill_name, s.skill_group,
           COUNT(*) AS n_with,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY base.salary_annual) AS median_with
    FROM base
    JOIN bridge_posting_skill b ON b.job_id   = base.job_id
    JOIN dim_skill s            ON s.skill_id = b.skill_id
    GROUP BY s.skill_id, s.skill_name, s.skill_group
),
without_skill AS (
    SELECT w.skill_id,
           COUNT(*) AS n_without,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY base.salary_annual) AS median_without
    FROM with_skill w
    JOIN base ON NOT EXISTS (
        SELECT 1 FROM bridge_posting_skill b
        WHERE b.job_id = base.job_id AND b.skill_id = w.skill_id)
    GROUP BY w.skill_id
)
SELECT w.skill_name,
       w.skill_group,
       w.n_with,
       o.n_without,
       ROUND(w.median_with::numeric)                         AS median_with,
       ROUND(o.median_without::numeric)                      AS median_without,
       ROUND((w.median_with - o.median_without)::numeric)    AS premium
FROM with_skill w
JOIN without_skill o USING (skill_id)
WHERE w.n_with >= 30;


-- 4. Skill co-occurrence with lift (lift > 1: appear together more than chance)
CREATE OR REPLACE VIEW v_skill_pairs AS
WITH n AS (
    SELECT COUNT(DISTINCT job_id)::float AS total FROM bridge_posting_skill
),
sc AS (
    SELECT skill_id, COUNT(*)::float AS c
    FROM bridge_posting_skill GROUP BY skill_id
),
pairs AS (
    SELECT a.skill_id AS a_id, b.skill_id AS b_id, COUNT(*)::float AS c
    FROM bridge_posting_skill a
    JOIN bridge_posting_skill b
      ON a.job_id = b.job_id AND a.skill_id < b.skill_id
    GROUP BY 1, 2
)
SELECT sa.skill_name AS skill_a,
       sb.skill_name AS skill_b,
       p.c::int      AS together,
       ROUND(((p.c / n.total) / ((ca.c / n.total) * (cb.c / n.total)))::numeric, 2) AS lift
FROM pairs p
CROSS JOIN n
JOIN dim_skill sa ON sa.skill_id = p.a_id
JOIN dim_skill sb ON sb.skill_id = p.b_id
JOIN sc ca        ON ca.skill_id = p.a_id
JOIN sc cb        ON cb.skill_id = p.b_id
WHERE p.c >= 20;


-- 5. Demand and average salary by city and role
CREATE OR REPLACE VIEW v_location_demand AS
SELECT l.city,
       l.state_code,
       f.role_family,
       COUNT(*)                   AS postings,
       ROUND(AVG(f.salary_annual)) AS avg_salary
FROM fact_postings f
JOIN dim_location l ON l.location_id = f.location_id
WHERE f.role_family <> 'Other' AND l.city IS NOT NULL
GROUP BY l.city, l.state_code, f.role_family;

DROP VIEW IF EXISTS v_postings;
CREATE VIEW v_postings AS
SELECT job_id,
       role_family,
       COALESCE(experience_level, 'Not stated') AS experience_level,
       work_type,
       remote_allowed,
       listed_date,
       salary_annual
FROM fact_postings
WHERE role_family <> 'Other';