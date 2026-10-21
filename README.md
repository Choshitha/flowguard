# South East Queensland Water Storage Analytics

**FlowGuard — regional storage trends, drawdown analysis and comparative dam performance.**

[Open the dashboard](https://choshitha.github.io/flowguard/#overview)

Published dam observations → Python validation → SQLite analytics → interactive GitHub Pages dashboard.

## Original source data

Official Seqwater historical CSV export downloaded on **21 October 2026**, covering **21 October 2025–21 October 2026** inclusive. Six individual dams (Baroon Pocket, Hinze, Little Nerang, North Pine, Somerset and Wivenhoe) plus the official SEQ Water Grid regional aggregate. The archive contains **2,561 actual observations** from 2,562 expected series-day slots; one regional grid day is missing. No observations are simulated, imputed or interpolated.

Publisher: **Seqwater**

Publisher page: https://www.seqwater.com.au/historic-dam-levels

[Download the original publisher export](https://choshitha.github.io/flowguard/source/seqwater-historical-storage.zip)

The downloadable ZIP is byte-for-byte identical to `pipeline/raw/seqwater-history.zip`. Original CSV field names are `Name`, `Date`, `Last Observation (%)`, and `Last Observation (ML)`. Displayed summaries are derived separately and do not replace the original files.

The publisher describes these as automated, unverified daily observations. Each record is the last observation on its calendar day and may omit intraday peaks. The download includes dates, not precise observation times. This is a historical snapshot, not a live feed.

## Analytical methods

The research workspace displays query results produced in SQLite, rather than presenting example SQL alongside unrelated charts. Research panels follow the selected 30-day, 90-day or full-year window. The overview defaults to the full observed year.

- Calendar rolling means (7/30 days), with accepted-observation counts and explicit axis controls.
- Ranked endpoints and monthly aggregates with incomplete months flagged.
- Ordered peak-to-trough maximum drawdown using cumulative maxima, ranking and a correlated peak-date lookup.
- Gaps-and-islands analysis of consecutive strictly declining calendar days.
- Same-date self-joins for cross-dam daily-change Pearson correlation. SQL computes sufficient statistics; Python normalises them and guards zero variance. The overlapping grid is excluded.
- A query notebook showing the executed SQL view definitions, dependent views and materialised result previews. It is not an arbitrary browser SQL executor.

The source page retains the publisher’s automated/unverified caveat and the snapshot date. The main interface uses a concise provenance strip. No change implies publisher verification, live data, causal inference or recurring seasonal behaviour.

## Working features

- Regional and individual dam views with 30-day, 90-day and full-year filters.
- Published storage percentage, stored volume (ML), and window change in percentage points.
- Daily storage chart that leaves missing-day gaps unconnected.
- Largest daily movement per series, with before/after evidence and interpretation limits.
- Data-quality reconciliation, missing-day details and source SHA-256 checksums.
- Filtered CSV exports containing source precision; values shown on screen are rounded.

The regional overview chart uses the **official grid series**. The grid overlaps individual dams and is never added to their volumes. There is no attempt to reconstruct the full regional grid from the six selected dams. No pump energy, throughput, rainfall, demand, AI or forecasting data is claimed.

## Run locally

Open `docs/index.html` in a modern browser, or:

```sh
python -m http.server 8000 --directory docs
```

Visit http://localhost:8000. The frontend has no third-party dependencies.

## Rebuild and validate

Requires Python 3.10+ and Node 18+:

```sh
python pipeline/build.py
python -m unittest discover -s tests -p 'test_*.py'
node tests/analytics.test.cjs
```

The importer reads the retained original ZIP, validates known series, dates and finite nonnegative measurements, deduplicates site + date, loads SQLite, creates analytical views and exports `docs/data.js`. Storage above 100% is valid and is **not clipped** in the data. Rejected source rows are reported in `pipeline/rejections.json`. The database and exported snapshot are rebuilt reproducibly from the raw input.

## Refresh with a new official export

1. Open the source page and choose the desired date window.
2. Select the six dams above plus SEQ Water Grid; download the official ZIP.
3. Replace `pipeline/raw/seqwater-history.zip` with the new original archive.
4. Run `python pipeline/build.py --retrieved YYYY-MM-DD` with the actual download date. Retain this date when rebuilding the same archive.
5. Run the importer and checks. Update fixed snapshot assertions when intentionally changing the date window.
6. Commit changes; the existing GitHub Actions workflow validates and deploys `docs/`.

This workflow deliberately imports official user-downloadable exports. It does not rely on scraping, undocumented endpoints, or claim an automatic refresh. Some publisher pages restrict programmatic downloads.

## SQL definitions

- `sql/schema.sql`: relational keys, foreign keys, value constraints and separate `dam`/`grid` series types.
- `sql/analytics.sql`: CTEs, conditional aggregation, `LAG`, ranked endpoints, calendar `RANGE` frames, running maxima, correlated subqueries, gaps-and-islands grouping and matched-date self-joins.
- `pipeline/flowguard.sqlite`: generated local database with actual accepted observations.

The browser uses the exported accepted rows and calculates filtered metrics in JavaScript. Python tests compare SQLite values exactly against the original CSV; Node checks verify browser calculations.

## Metric definitions

| Metric | Calculation |
|---|---|
| Latest storage | Latest accepted percentage for charted series |
| Stored volume | Published ML for that same latest observation |
| Change over window | Last observed percentage minus first observed percentage, in percentage points |
| Largest daily movement | Largest absolute change between consecutive dates in selected window; earliest pair wins ties |
| Coverage | Accepted unique series-days ÷ (calendar dates × imported series) |

A stored-volume change is not demand or pumped volume. An observed change does not identify a leak, flood event, equipment fault or cybersecurity incident. Capacity changes and reduced operating levels affect interpretation. Follow the publisher's notes for North Pine, Somerset and Wivenhoe. No safety or drought classification is inferred from a percentage alone.

## Source rights and attribution

Source data: **Seqwater**, downloaded using its historical CSV export. Publisher rights are retained; this dashboard does not apply a new licence to source data or claim that an open-data licence was verified. The retained archive and member checksums document provenance. Source caveats and attribution appear in the dashboard. FlowGuard is a separate analytical presentation and is not a Seqwater product or endorsement.

## Findings from the full observed year

The official regional grid moved from 80.7% to 79.3% (−1.4 percentage points). Its maximum ordered drawdown was 6.7 pp, from an observed peak on 19 March 2026 to a subsequent trough on 18 October 2026. March 2026 had the largest complete-month first-to-last rise (+7.8 pp). Among the six selected dams, Little Nerang had the largest maximum drawdown (26.2 pp). These are descriptive findings within this dataset and time window, not risk ratings or causal diagnoses.

One annual cycle does not establish seasonality. Correlations are exploratory, depend on matched observations and have not been adjusted for multiple comparisons; they are not forecasts. Day-to-day changes use rounded publisher percentages and may be quantised. Monthly first-to-last changes omit transitions between months and should not be summed into annual change. The earliest longest decline run wins ties; maximum drawdown uses the earliest trough among equal drawdowns and the most recent equal preceding peak. Rolling means include available history before the selected analysis window and expose their observation counts.
