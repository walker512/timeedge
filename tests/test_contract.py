import json
import subprocess
import sys
import unittest
from datetime import datetime
from timeedge.core import resolve, schedule
from timeedge.__main__ import tz_fingerprint

class Contracts(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'timeedge', *args], capture_output=True, text=True)

    def test_summary_counts_slots_and_instants(self):
        r = self.run_cli('--start', '2026-11-01T01:30', '--zone', 'America/New_York', '--count', '1', '--ambiguous', 'both')
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)['summary'], dict(requested_slots=1, utc_instants=2, rejected_slots=0, skipped_slots=0))

    def test_skip_is_not_successful_instant(self):
        r = self.run_cli('--start', '2026-03-08T02:30', '--zone', 'America/New_York', '--count', '1', '--nonexistent', 'skip')
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)['summary']['utc_instants'], 0)
        self.assertEqual(json.loads(r.stdout)['summary']['skipped_slots'], 1)

    def test_invalid_iso(self):
        for start in ('not-a-date', '2026-02-30T01:00', '2026-01-01T00:00+08:00', '2016-12-31T23:59:60'):
            r = self.run_cli('--start', start, '--zone', 'UTC')
            self.assertEqual(r.returncode, 1)
            self.assertNotIn('Traceback', r.stderr)

    def test_overflow_clean_error(self):
        for recurrence in ('daily', 'monthly', 'yearly'):
            r = self.run_cli('--start', '9999-12-31T12:00', '--zone', 'UTC', '--recurrence', recurrence)
            self.assertEqual(r.returncode, 1)
            self.assertNotIn('Traceback', r.stderr)

    def test_argument_errors_have_no_boundary_exit(self):
        for args in ((), ('--start', '2026-01-01', '--zone', 'UTC', '--count', 'nope'),
                     ('--start', '2026-01-01', '--zone', 'UTC', '--ambiguous', 'guess')):
            r = self.run_cli(*args)
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, '')
            self.assertNotIn('Traceback', r.stderr)

    def test_html_displays_resolved_wall(self):
        from timeedge.__main__ import report
        row = resolve(datetime(2026, 3, 8, 2, 30), 'America/New_York', nonexistent='shift-forward')
        page = report({'contract': {}, 'rows': [row]})
        self.assertIn('2026-03-08T03:30:00-04:00', page)
        self.assertIn('Resolved local time(s)', page)

    def test_count_type(self):
        for count in (True, 1.5, '1'):
            with self.assertRaises(ValueError): schedule(datetime(2026,1,1), count, 'UTC')

    def test_invalid_policy(self):
        for kwargs in ({'ambiguous':'guess'}, {'nonexistent':'guess'}):
            with self.assertRaises(ValueError): resolve(datetime(2026,1,1), 'UTC', **kwargs)

    def test_fingerprint_path_rejected(self):
        with self.assertRaises(ValueError): tz_fingerprint('../etc/passwd')

    def test_half_hour_fold(self):
        row = resolve(datetime(2026,4,5,1,45), 'Australia/Lord_Howe', ambiguous='both')
        a,b = map(datetime.fromisoformat, row['utc'])
        self.assertEqual((b-a).total_seconds(), 1800)

    def test_daily_is_wall_clock_not_elapsed(self):
        rows = schedule(datetime(2026,3,7,12), 3, 'America/New_York')
        instants = [datetime.fromisoformat(r['utc'][0]) for r in rows]
        self.assertEqual((instants[1]-instants[0]).total_seconds(), 23*3600)

    def test_no_monthly_anchor_drift(self):
        rows = schedule(datetime(2024,1,31), 3, 'UTC', 'monthly', 'clamp')
        self.assertEqual([r['wall'][0][:10] for r in rows], ['2024-01-31','2024-02-29','2024-03-31'])

if __name__ == '__main__': unittest.main()
