import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from timeedge.core import resolve, schedule
from timeedge.__main__ import report

class Boundaries(unittest.TestCase):
    def test_spring_reject(self):
        r=resolve(datetime(2026,3,8,2,30),'America/New_York')
        self.assertEqual((r['kind'],r['status'],r['utc']),('nonexistent','rejected',[]))
    def test_spring_shift(self):
        r=resolve(datetime(2026,3,8,2,30),'America/New_York',nonexistent='shift-forward')
        self.assertEqual(r['wall'],['2026-03-08T03:30:00-04:00'])
    def test_autumn_both(self):
        r=resolve(datetime(2026,11,1,1,30),'America/New_York',ambiguous='both')
        self.assertEqual(r['utc'],['2026-11-01T05:30:00+00:00','2026-11-01T06:30:00+00:00'])
    def test_autumn_later(self):
        self.assertEqual(resolve(datetime(2026,11,1,1,30),'America/New_York',ambiguous='later')['utc'],['2026-11-01T06:30:00+00:00'])
    def test_half_hour_gap(self):
        r=resolve(datetime(2026,10,4,2,15),'Australia/Lord_Howe',nonexistent='shift-forward')
        self.assertEqual(r['wall'],['2026-10-04T02:45:00+11:00'])
    def test_missing_day(self):
        r=resolve(datetime(2011,12,30,12),'Pacific/Apia',nonexistent='shift-forward')
        self.assertEqual(r['wall'],['2011-12-31T12:00:00+14:00'])
    def test_anchor_not_drift(self):
        r=schedule(datetime(2026,1,31,9),3,'UTC','monthly','clamp')
        self.assertEqual([x['wall'][0][:10] for x in r],['2026-01-31','2026-02-28','2026-03-31'])
    def test_leap_year(self):
        r=schedule(datetime(2024,2,29,9),5,'UTC','yearly','skip')
        self.assertEqual([x['status'] for x in r],['resolved','skipped','skipped','skipped','resolved'])
    def test_invalid_calendar(self):
        self.assertEqual(schedule(datetime(2026,1,31),2,'UTC','monthly')[1]['kind'],'invalid-calendar-date')
    def test_no_false_fold_utc(self):
        self.assertEqual(len(resolve(datetime(2026,1,1),'UTC',ambiguous='both')['utc']),1)
    def test_aware_rejected(self):
        with self.assertRaises(ValueError): schedule(datetime.fromisoformat('2026-01-01T00:00+00:00'),1,'UTC')
    def test_limits(self):
        for n in (0,367):
            with self.assertRaises(ValueError): schedule(datetime(2026,1,1),n,'UTC')
    def test_escape(self):
        out=report({'contract':{'x':'<script>alert(1)</script>'},'rows':[]})
        self.assertNotIn('<script>',out)
        self.assertIn('&lt;script&gt;',out)
    def test_reproducible(self):
        a=schedule(datetime(2026,1,31),12,'Europe/Berlin','monthly','clamp')
        self.assertEqual(a,schedule(datetime(2026,1,31),12,'Europe/Berlin','monthly','clamp'))
    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'report.html'
            cmd=[sys.executable,'-m','timeedge','--start','2026-03-08T02:30','--zone','America/New_York','--count','1','--html',str(target)]
            run=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(run.returncode,2)
            self.assertEqual(json.loads(run.stdout)['rows'][0]['status'],'rejected')
            self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,1)
    def test_bad_zone(self):
        r=subprocess.run([sys.executable,'-m','timeedge','--start','2026-01-01','--zone','../etc/passwd'],capture_output=True)
        self.assertEqual(r.returncode,1)

if __name__=='__main__': unittest.main()
