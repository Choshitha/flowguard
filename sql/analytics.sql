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
