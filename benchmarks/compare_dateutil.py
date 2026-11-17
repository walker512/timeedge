"""Reproducible capability check, not a performance benchmark. Run from repository root."""
import json
import subprocess
import sys
from datetime import datetime, timezone
import dateutil
from dateutil import tz

CASES = [
    ('spring-gap', '2026-03-08T02:30:00', 'America/New_York'),
    ('autumn-fold', '2026-11-01T01:30:00', 'America/New_York'),
    ('half-hour-gap', '2026-10-04T02:15:00', 'Australia/Lord_Howe'),
    ('skipped-day', '2011-12-30T12:00:00', 'Pacific/Apia'),
    ('normal', '2026-07-01T12:00:00', 'Europe/Berlin'),
    ('utc', '2026-01-01T00:00:00', 'UTC'),
]
results = []
for name, wall, zone in CASES:
    dt = datetime.fromisoformat(wall).replace(tzinfo=tz.gettz(zone))
    if not tz.datetime_exists(dt):
        kind = 'nonexistent'
        expected = [tz.resolve_imaginary(dt).astimezone(timezone.utc).isoformat()]
    elif tz.datetime_ambiguous(dt):
        kind = 'ambiguous'
        expected = sorted({tz.enfold(dt, fold=f).astimezone(timezone.utc).isoformat() for f in (0, 1)})
    else:
        kind = 'normal'
        expected = [dt.astimezone(timezone.utc).isoformat()]
    run = subprocess.run([sys.executable, '-m', 'timeedge', '--start', wall, '--zone', zone,
                          '--count', '1', '--ambiguous', 'both', '--nonexistent', 'shift-forward'],
                         check=True, capture_output=True, text=True)
    row = json.loads(run.stdout)['rows'][0]
    results.append(dict(case=name, expected=expected, observed=row['utc'],
                        agrees=row['utc'] == expected and row['kind'] == kind))
print(json.dumps({'dateutil_version':dateutil.__version__, 'cases':results}, indent=2))
raise SystemExit(0 if all(x['agrees'] for x in results) else 1)
