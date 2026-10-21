PRAGMA foreign_keys = ON;
DROP VIEW IF EXISTS site_daily;
DROP VIEW IF EXISTS latest_site_status;
DROP TABLE IF EXISTS readings;
DROP TABLE IF EXISTS sites;
CREATE TABLE sites(site_id TEXT PRIMARY KEY, name TEXT NOT NULL, region TEXT NOT NULL, capacity_kl REAL NOT NULL);
CREATE TABLE readings(
 site_id TEXT REFERENCES sites(site_id), timestamp TEXT NOT NULL,
 level_pct REAL NOT NULL CHECK(level_pct BETWEEN 0 AND 100),
 flow_kl REAL NOT NULL CHECK(flow_kl>=0), energy_kwh REAL NOT NULL CHECK(energy_kwh>=0),
 PRIMARY KEY(site_id,timestamp));
