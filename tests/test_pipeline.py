import sqlite3, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PipelineTests(unittest.TestCase):
    def setUp(self): self.db=sqlite3.connect(ROOT/'pipeline/flowguard.sqlite')
    def tearDown(self): self.db.close()
    def test_quality_and_unique_keys(self):
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM readings').fetchone()[0],4302)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM (SELECT site_id,timestamp FROM readings GROUP BY 1,2 HAVING COUNT(*)>1)').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM readings WHERE level_pct<0 OR level_pct>100 OR flow_kl IS NULL').fetchone()[0],0)
    def test_known_faults_are_visible(self):
        statuses=dict(self.db.execute('SELECT site_id,status FROM latest_site_status'))
        self.assertEqual(statuses['S02'],'Critical')
        self.assertEqual(statuses['S05'],'High')
        self.assertEqual(sum(s!='Normal' for s in statuses.values()),2)
    def test_aggregation_preserves_totals(self):
        daily=self.db.execute('SELECT SUM(energy_kwh),SUM(throughput_kl) FROM site_daily').fetchone()
        raw=self.db.execute('SELECT SUM(energy_kwh),SUM(flow_kl) FROM readings').fetchone()
        for a,b in zip(daily,raw): self.assertAlmostEqual(a,b,places=6)
if __name__=='__main__': unittest.main()
