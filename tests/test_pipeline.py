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
if __name__=='__main__':unittest.main()
