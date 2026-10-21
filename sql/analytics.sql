-- Grid is an official regional aggregate and must never be added to its dams.
CREATE VIEW daily_changes AS
WITH previous AS (
 SELECT o.*, LAG(date) OVER(PARTITION BY site_id ORDER BY date) AS prior_date,
 LAG(storage_pct) OVER(PARTITION BY site_id ORDER BY date) AS prior_pct,
 LAG(volume_ml) OVER(PARTITION BY site_id ORDER BY date) AS prior_ml
 FROM observations o
)
SELECT *,CASE WHEN julianday(date)-julianday(prior_date)=1 THEN storage_pct-prior_pct END AS day_change_pp,
 CASE WHEN julianday(date)-julianday(prior_date)=1 THEN volume_ml-prior_ml END AS day_change_ml
FROM previous;
CREATE VIEW latest_storage AS
WITH ranked AS (SELECT o.*,ROW_NUMBER() OVER(PARTITION BY site_id ORDER BY date DESC) AS rn FROM observations o)
SELECT s.name,s.kind,r.site_id,r.date,r.storage_pct,r.volume_ml FROM ranked r JOIN sites s USING(site_id) WHERE rn=1;

-- Q01: parameterised analysis windows, anchored to the dataset's latest date.
CREATE VIEW analysis_observations AS
WITH windows(window_days) AS (VALUES(30),(90),(366)),
bounds AS (SELECT MAX(date) AS end_date FROM observations)
SELECT w.window_days,o.* FROM observations o CROSS JOIN windows w CROSS JOIN bounds b
WHERE julianday(o.date)>julianday(b.end_date)-w.window_days;

-- Q02: calendar-based rolling means, not an arbitrary count of available rows.
CREATE VIEW rolling_storage AS
SELECT o.*,
 AVG(storage_pct) OVER(PARTITION BY site_id ORDER BY julianday(date) RANGE BETWEEN 6 PRECEDING AND CURRENT ROW) AS mean_7d,
 COUNT(*) OVER(PARTITION BY site_id ORDER BY julianday(date) RANGE BETWEEN 6 PRECEDING AND CURRENT ROW) AS count_7d,
 AVG(storage_pct) OVER(PARTITION BY site_id ORDER BY julianday(date) RANGE BETWEEN 29 PRECEDING AND CURRENT ROW) AS mean_30d,
 COUNT(*) OVER(PARTITION BY site_id ORDER BY julianday(date) RANGE BETWEEN 29 PRECEDING AND CURRENT ROW) AS count_30d
FROM observations o;

CREATE VIEW window_changes AS
WITH previous AS (
 SELECT a.*,LAG(date) OVER w AS prior_date,LAG(storage_pct) OVER w AS prior_pct,
 LAG(volume_ml) OVER w AS prior_ml FROM analysis_observations a
 WINDOW w AS (PARTITION BY window_days,site_id ORDER BY date)
)
SELECT *,CASE WHEN julianday(date)-julianday(prior_date)=1 THEN ROUND(storage_pct-prior_pct,6) END AS day_change_pp
FROM previous;

-- Q03: ranked endpoints separate net change from within-period variation.
CREATE VIEW window_summary AS
WITH ranked AS (
 SELECT a.*,ROW_NUMBER() OVER(PARTITION BY window_days,site_id ORDER BY date) AS first_rank,
 ROW_NUMBER() OVER(PARTITION BY window_days,site_id ORDER BY date DESC) AS last_rank
 FROM analysis_observations a
), aggregates AS (
 SELECT window_days,site_id,COUNT(*) AS observations,MIN(date) AS start_date,MAX(date) AS end_date,
 AVG(storage_pct) AS mean_pct,MIN(storage_pct) AS minimum_pct,MAX(storage_pct) AS maximum_pct,
 MAX(CASE WHEN first_rank=1 THEN storage_pct END) AS start_pct,
 MAX(CASE WHEN last_rank=1 THEN storage_pct END) AS end_pct,
 MAX(CASE WHEN first_rank=1 THEN volume_ml END) AS start_ml,
 MAX(CASE WHEN last_rank=1 THEN volume_ml END) AS end_ml
 FROM ranked GROUP BY window_days,site_id
)
SELECT *,ROUND(end_pct-start_pct,6) AS net_change_pp,end_ml-start_ml AS net_change_ml,
 maximum_pct-minimum_pct AS range_pp FROM aggregates;

-- Q04: monthly boundaries, completeness and ranked start/end observations.
CREATE VIEW monthly_storage AS
WITH ranked AS (
 SELECT a.*,SUBSTR(date,1,7) AS month,
 ROW_NUMBER() OVER(PARTITION BY window_days,site_id,SUBSTR(date,1,7) ORDER BY date) AS first_rank,
 ROW_NUMBER() OVER(PARTITION BY window_days,site_id,SUBSTR(date,1,7) ORDER BY date DESC) AS last_rank
 FROM analysis_observations a
), grouped AS (
 SELECT window_days,site_id,month,COUNT(*) AS observations,
 CAST(strftime('%d',date(month||'-01','+1 month','-1 day')) AS INTEGER) AS calendar_days,
 AVG(storage_pct) AS mean_pct,MIN(storage_pct) AS minimum_pct,MAX(storage_pct) AS maximum_pct,
 MAX(CASE WHEN first_rank=1 THEN storage_pct END) AS start_pct,
 MAX(CASE WHEN last_rank=1 THEN storage_pct END) AS end_pct,
 MIN(date) AS first_date,MAX(date) AS last_date
 FROM ranked GROUP BY window_days,site_id,month
)
SELECT *,ROUND(end_pct-start_pct,6) AS net_change_pp,
 CASE WHEN observations=calendar_days THEN 1 ELSE 0 END AS complete_month FROM grouped;

-- Q05: peak-to-subsequent-trough drawdown; order matters, unlike MAX - MIN.
CREATE VIEW drawdown_path AS
WITH peaks AS (
 SELECT a.*,MAX(storage_pct) OVER(PARTITION BY window_days,site_id ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_peak_pct
 FROM analysis_observations a
)
SELECT *,ROUND(running_peak_pct-storage_pct,6) AS drawdown_pp FROM peaks;
CREATE VIEW maximum_drawdown AS
WITH ranked AS (
 SELECT d.*,ROW_NUMBER() OVER(PARTITION BY window_days,site_id ORDER BY drawdown_pp DESC,date) AS rn FROM drawdown_path d
)
SELECT r.window_days,r.site_id,r.date AS trough_date,r.storage_pct AS trough_pct,r.running_peak_pct AS peak_pct,r.drawdown_pp,
 (SELECT MAX(a.date) FROM analysis_observations a WHERE a.window_days=r.window_days AND a.site_id=r.site_id AND a.date<=r.date AND a.storage_pct=r.running_peak_pct) AS peak_date
FROM ranked r WHERE rn=1;

-- Q06: gaps-and-islands identifies uninterrupted, strictly declining days.
-- A missing day, flat value or increase breaks the run.
CREATE VIEW decline_groups AS
SELECT c.*,SUM(CASE WHEN day_change_pp IS NULL OR day_change_pp>=0 THEN 1 ELSE 0 END)
 OVER(PARTITION BY window_days,site_id ORDER BY date ROWS UNBOUNDED PRECEDING) AS run_id
FROM window_changes c;
CREATE VIEW decline_runs AS
WITH runs AS (
 SELECT window_days,site_id,run_id,MIN(prior_date) AS start_date,MAX(date) AS end_date,
 COUNT(*) AS decline_days,MAX(prior_pct) AS start_pct,MIN(storage_pct) AS end_pct,
 ROUND(SUM(-day_change_pp),6) AS decline_pp
 FROM decline_groups WHERE day_change_pp<0 GROUP BY window_days,site_id,run_id
)
SELECT *,ROW_NUMBER() OVER(PARTITION BY window_days,site_id ORDER BY decline_days DESC,start_date) AS duration_rank FROM runs;

-- Q07: pairwise daily-change correlation; only individual dams, on matched dates.
-- The grid is excluded because it overlaps the dams. Gaps are not interpolated.
CREATE VIEW paired_changes AS
SELECT a.window_days,a.site_id AS site_a,b.site_id AS site_b,a.date,
 a.day_change_pp AS x,b.day_change_pp AS y
FROM window_changes a JOIN window_changes b
 ON a.window_days=b.window_days AND a.date=b.date AND a.site_id<b.site_id
JOIN sites sa ON sa.site_id=a.site_id AND sa.kind='dam'
JOIN sites sb ON sb.site_id=b.site_id AND sb.kind='dam'
WHERE a.day_change_pp IS NOT NULL AND b.day_change_pp IS NOT NULL;
CREATE VIEW change_correlations AS
WITH sums AS (
 SELECT window_days,site_a,site_b,COUNT(*) AS n,SUM(x) AS sx,SUM(y) AS sy,
 SUM(x*x) AS sxx,SUM(y*y) AS syy,SUM(x*y) AS sxy FROM paired_changes
 GROUP BY window_days,site_a,site_b
)
SELECT *,n*sxy-sx*sy AS numerator,
 (n*sxx-sx*sx)*(n*syy-sy*sy) AS denominator_squared FROM sums;
