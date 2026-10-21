import csv,importlib.util,io,json,sqlite3,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pipeline',ROOT/'pipeline/build.py');pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)
class PipelineTests(unittest.TestCase):
 def setUp(self):self.db=sqlite3.connect(ROOT/'pipeline/flowguard.sqlite')
 def tearDown(self):self.db.close()
 def test_exact_source_round_trip(self):
  source,*_=pipeline.parse_export(ROOT/'pipeline/raw/seqwater-history.zip')
  actual=self.db.execute('SELECT name,date,storage_pct,volume_ml FROM observations JOIN sites USING(site_id) ORDER BY date,name').fetchall()
  self.assertEqual(actual,source);self.assertEqual(len(actual),2561)
 def test_latest_real_measurements(self):
  pct,ml=self.db.execute("SELECT storage_pct,volume_ml FROM latest_storage WHERE name='Hinze'").fetchone()
  self.assertEqual(pct,94.5);self.assertAlmostEqual(ml,293690.34089225)
  self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sites WHERE kind='dam'").fetchone()[0],6)
 def test_missing_day_is_not_fabricated(self):
  self.assertEqual(self.db.execute("SELECT COUNT(*) FROM observations JOIN sites USING(site_id) WHERE kind='grid'").fetchone()[0],365)
  gaps=self.db.execute('SELECT COUNT(*) FROM daily_changes WHERE prior_date IS NOT NULL AND julianday(date)-julianday(prior_date)>1 AND day_change_pp IS NULL').fetchone()[0]
  self.assertEqual(gaps,1)
 def test_daily_change_formula(self):
  for date,prior,pct,previous,delta in self.db.execute('SELECT date,prior_date,storage_pct,prior_pct,day_change_pp FROM daily_changes WHERE day_change_pp IS NOT NULL'):
   self.assertAlmostEqual(delta,pct-previous)
 def test_validator_handles_spilling_and_bad_rows(self):
  text='Name,Date,Last Observation (%),Last Observation (ML)\nHinze,01-01-2026,105,100\nHinze,01-01-2026,105,100\nHinze,02-01-2026,nan,100\nHinze,bad,50,100\nHinze,03-01-2026,50,-1\n'
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('Hinze.csv',text)
   rows,raw,duplicates,rejected,_=pipeline.parse_export(p)
   self.assertEqual(rows,[('Hinze','2026-01-01',105.,100.)]);self.assertEqual(raw,5);self.assertEqual(duplicates,1);self.assertEqual(len(rejected),3)
 def test_calendar_rolling_means_preserve_missing_day(self):
  latest=self.db.execute("SELECT mean_7d,count_7d,count_30d FROM rolling_storage WHERE site_id='D07' AND date='2026-10-21'").fetchone()
  independent=self.db.execute("SELECT AVG(storage_pct) FROM observations WHERE site_id='D07' AND date BETWEEN '2026-10-15' AND '2026-10-21'").fetchone()[0]
  self.assertAlmostEqual(latest[0],independent);self.assertEqual(latest[1:],(6,29))
 def test_drawdown_preserves_temporal_order(self):
  import itertools
  for days in [30,90,366]:
   for site, in self.db.execute('SELECT site_id FROM sites'):
    values=self.db.execute('SELECT date,storage_pct FROM analysis_observations WHERE window_days=? AND site_id=? ORDER BY date',(days,site)).fetchall()
    maximum=max(a[1]-b[1] for i,a in enumerate(values) for b in values[i:])
    result=self.db.execute('SELECT drawdown_pp,peak_date,trough_date FROM maximum_drawdown WHERE window_days=? AND site_id=?',(days,site)).fetchone()
    self.assertAlmostEqual(result[0],maximum);self.assertLessEqual(result[1],result[2])
  self.assertAlmostEqual(self.db.execute("SELECT drawdown_pp FROM maximum_drawdown WHERE window_days=366 AND site_id='D07'").fetchone()[0],6.7)
 def test_monthly_completeness_and_annual_path(self):
  month=self.db.execute("SELECT net_change_pp,complete_month FROM monthly_storage WHERE window_days=366 AND site_id='D07' AND month='2026-03'").fetchone()
  self.assertEqual(month,(7.8,1))
  self.assertEqual(self.db.execute("SELECT complete_month FROM monthly_storage WHERE window_days=366 AND site_id='D07' AND month='2026-10'").fetchone()[0],0)
  self.assertEqual(self.db.execute("SELECT net_change_pp FROM window_summary WHERE window_days=366 AND site_id='D07'").fetchone()[0],-1.4)
 def test_decline_runs_against_source_sequence(self):
  from datetime import date
  for days in [30,90,366]:
   for site, in self.db.execute('SELECT site_id FROM sites'):
    rows=self.db.execute('SELECT date,storage_pct FROM analysis_observations WHERE window_days=? AND site_id=? ORDER BY date',(days,site)).fetchall()
    longest=streak=0
    for prior,current in zip(rows,rows[1:]):
     consecutive=(date.fromisoformat(current[0])-date.fromisoformat(prior[0])).days==1
     streak=streak+1 if consecutive and round(current[1]-prior[1],6)<0 else 0
     longest=max(longest,streak)
    sql=self.db.execute('SELECT MAX(decline_days) FROM decline_runs WHERE window_days=? AND site_id=?',(days,site)).fetchone()[0] or 0
    self.assertEqual(longest,sql)
 def test_sql_correlation_statistics_match_python(self):
  import math,statistics
  for days,a,b,n,numerator,denominator in self.db.execute('SELECT window_days,site_a,site_b,n,numerator,denominator_squared FROM change_correlations'):
   pairs=self.db.execute('SELECT x,y FROM paired_changes WHERE window_days=? AND site_a=? AND site_b=?',(days,a,b)).fetchall()
   self.assertEqual(n,len(pairs));self.assertNotIn('D07',(a,b))
   if denominator>0:self.assertAlmostEqual(numerator/math.sqrt(denominator),statistics.correlation([v[0] for v in pairs],[v[1] for v in pairs]),places=10)
if __name__=='__main__':unittest.main()
