import argparse
import hashlib
import html
import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, TZPATH
from . import __version__
from .core import schedule


def tz_fingerprint(zone):
    ZoneInfo(zone)  # Reject traversal even when called as a library helper.
    # Hash the exact source file when system tzdb is accessible. Never guess a version.
    for base in TZPATH:
        p = Path(base) / zone
        if p.is_file():
            return hashlib.sha256(p.read_bytes()).hexdigest()
    try:
        import importlib.resources as resources
        resource = resources.files('tzdata.zoneinfo').joinpath(*zone.split('/'))
        return hashlib.sha256(resource.read_bytes()).hexdigest()
    except (ImportError, FileNotFoundError, ModuleNotFoundError):
        return None


def report(data):
    e = lambda x: html.escape(str(x), quote=True)
    rows = ''.join('<tr>' + ''.join('<td>'+e(row.get(k, ''))+'</td>' for k in
                   ('requested','kind','status','calendar_adjusted','adjustment')) + '<td>'+e(', '.join(row.get('wall', [])))+'</td><td>'+e(', '.join(row['utc']))+'</td></tr>' for row in data['rows'])
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><title>TimeEdge boundary lab</title><style>body{font:16px system-ui;background:#0b1524;color:#edf4ff;margin:4vw;line-height:1.6}h1{font-size:3rem;margin-bottom:0;color:#73e7ca}table{border-collapse:collapse;width:100%;min-width:1000px;font-size:.9rem}td,th{padding:12px;border-bottom:1px solid #34465b;text-align:left}td{white-space:nowrap}section{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#a8c8e9}.tag{color:#73e7ca}footer{margin-top:40px}</style><p class="tag">WALKER512 / TIMEEDGE 0.1</p><h1>Wall time is not an instant.</h1><p>Inspect calendar and timezone boundaries before they become production bugs. Every adjustment is explicit.</p><pre>'''+e(json.dumps(data['contract'], indent=2))+'''</pre><p>On narrow screens, scroll the table horizontally to inspect all columns.</p><section tabindex="0" aria-label="Schedule results, scroll horizontally"><table><thead><tr><th>Requested local time</th><th>Boundary</th><th>Outcome</th><th>Calendar clamped</th><th>DST shift</th><th>Resolved local time(s)</th><th>UTC instant(s)</th></tr></thead><tbody>'''+rows+'''</tbody></table></section><footer>Offline report. No uploads, telemetry, scripts or remote assets. Rejected rows are not scheduled. “Both” produces two instants. A gap shift preserves position within the gap, not the first valid minute.</footer></html>'''


class ContractParser(argparse.ArgumentParser):
    def error(self, message):
        # Exit 2 is reserved for a valid report containing rejected slots.
        self.print_usage(sys.stderr)
        self.exit(1, f'{self.prog}: error: {message}\n')


def main():
    p = ContractParser(description='Explicit wall-clock recurrence boundary lab. JSON goes to stdout; --html creates a standalone report.')
    p.add_argument('--start', required=True, help='Naive local ISO datetime, e.g. 2026-03-07T02:30:00')
    p.add_argument('--zone', required=True)
    p.add_argument('--count', type=int, default=5)
    p.add_argument('--recurrence', choices=['daily','monthly','yearly'], default='daily')
    p.add_argument('--month-end', choices=['reject','skip','clamp'], default='reject')
    p.add_argument('--ambiguous', choices=['reject','earlier','later','both'], default='reject')
    p.add_argument('--nonexistent', choices=['reject','skip','shift-forward'], default='reject')
    p.add_argument('--html', type=Path, help='Create NEW HTML file (will not overwrite)')
    args = p.parse_args()
    try:
        ZoneInfo(args.zone)  # validates zone before filesystem access
        start = datetime.fromisoformat(args.start)
        rows = schedule(start, args.count, args.zone, args.recurrence, args.month_end, args.ambiguous, args.nonexistent)
        data = {'contract': {'tool_version': __version__, 'python': platform.python_version(),
                'zone':args.zone, 'tzfile_sha256':tz_fingerprint(args.zone), 'start':args.start,
                'count':args.count, 'recurrence':args.recurrence, 'month_end':args.month_end,
                'ambiguous':args.ambiguous, 'nonexistent':args.nonexistent}, 'summary': {'requested_slots': len(rows),
                    'utc_instants': sum(len(row['utc']) for row in rows),
                    'rejected_slots': sum(row['status'] == 'rejected' for row in rows),
                    'skipped_slots': sum(row['status'] == 'skipped' for row in rows)}, 'rows':rows}
        if args.html:
            with args.html.open('x', encoding='utf-8') as f: f.write(report(data))
        print(json.dumps(data, indent=2))
        return 2 if any(r['status']=='rejected' for r in rows) else 0
    except (ValueError, OverflowError, ZoneInfoNotFoundError, OSError) as exc:
        print(f'TimeEdge: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__': sys.exit(main())
