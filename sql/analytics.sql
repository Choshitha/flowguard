-- Hourly flow_kl is volume pumped during that hour; sum gives period throughput.
CREATE VIEW site_daily AS
SELECT s.site_id,s.name,s.region,DATE(r.timestamp) AS day,
 COUNT(*) AS accepted_hours,AVG(level_pct) AS mean_level,
 SUM(flow_kl) AS throughput_kl,SUM(energy_kwh) AS energy_kwh,
 SUM(energy_kwh)/NULLIF(SUM(flow_kl),0) AS kwh_per_kl
FROM readings r JOIN sites s ON s.site_id=r.site_id
GROUP BY s.site_id,DATE(r.timestamp);
-- A window function selects the latest accepted observation for each site.
CREATE VIEW latest_site_status AS
WITH ranked AS (SELECT r.*, ROW_NUMBER() OVER(PARTITION BY site_id ORDER BY timestamp DESC) AS rn FROM readings r)
SELECT s.name,r.*,
 CASE WHEN level_pct<20 THEN 'Critical' WHEN energy_kwh/NULLIF(flow_kl,0)>0.85 THEN 'High' WHEN level_pct<30 THEN 'Watch' ELSE 'Normal' END AS status
FROM ranked r JOIN sites s ON s.site_id=r.site_id WHERE rn=1;
