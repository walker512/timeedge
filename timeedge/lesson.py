"""Script-free lessons from verified comparison records; never executes adapters."""
import argparse
import html
import json
import os
from pathlib import Path
import sys

from . import compare

LIMIT = 16 * 1024 * 1024


def escaped(value):
    return html.escape(str(value), quote=True)


def block(label, value):
    text = json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2)
    return '<h3>' + escaped(label) + '</h3><pre>' + escaped(text) + '</pre>'


def render(report):
    """Internal renderer. Public build always supplies compare.verify output."""
    parts = ["""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>TimeEdge · Recorded boundary lessons</title><style>
body{font:17px system-ui;background:#111a25;color:#edf4fa;margin:auto;max-width:1100px;padding:24px}p{line-height:1.6}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:16px;background:#1b2a3b;border-radius:8px}details{margin:24px 0;border:1px solid #60768e;padding:16px;border-radius:12px}summary{cursor:pointer;font-weight:bold}summary:focus-visible{outline:3px solid #8ee5d0}.pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:16px}.warning{border-left:4px solid #efc476;padding:12px}h2{margin-top:32px}section{min-width:0}
</style></head><body><main><h1>Recorded boundary lessons</h1>
<p class="warning">Offline display of a comparison bundle that passed internal consistency verification when this page was built. No code runs here. This does not authenticate execution, sources, timezone databases, or correctness. A coherently rewritten bundle can still verify. Recheck this page against the original bundle before relying on it.</p>
<p>Open each numbered case, read the request and intent, compare recorded fields, then inspect the separate TimeEdge policy reference. Failure, missing expectations and domain errors are not successful assertions. This page never changes policy or recomputes a timezone result.</p>"""]
    parts.append(block('Bundle binding and expectation gate', {
        'receipt_sha256': report['receipt_sha256'],
        'all_declared_expectations_match': report['all_declared_expectations_match'],
        'reference_reexecuted_by_verify': False,
        'execution_authenticated': False,
        'same_timezone_database_assumed': False,
    }))
    for number, case in enumerate(report['cases'], 1):
        parts.append('<details><summary>Case ' + str(number) + ' / ' +
                     str(len(report['cases'])) + ' · ' + escaped(case['case_id']) + '</summary>')
        parts.append(block('1. Requested operation', case['request']))
        parts.append(block('2. Declared semantics, not inferred equivalence', case['semantics']))
        parts.append('<h2>3. Recorded execution outcomes</h2><div class="pair">')
        for side in ('python', 'node'):
            result = case['sides'][side]
            label = ('Recorded response; not re-executed' if result['execution_status'] == 'complete'
                     else 'No successful response recorded; not re-executed')
            parts.append('<section>' + block(side + ' · ' + label, result) + '</section>')
        parts.append('</div>')
        parts.append(block('4. Field differences (null means comparison unavailable)', case['field_differences']))
        parts.append('<p class="warning">Different fields do not establish a language defect. Identical fields do not establish equal intent or timezone database versions.</p>')
        parts.append(block('5. Separate recorded TimeEdge policy reference', case['recorded_timeedge_reference']))
        parts.append('<p>This reference was archived by the original run, not recomputed by verification or this lesson. It is not an oracle for a different adapter operation.</p></details>')
    parts.append('<footer>walker512 · TimeEdge · Full recorded inputs and outputs may be private. No links, external resources, scripts or copied adapter code are included.</footer></main></body></html>')
    data = ''.join(parts).encode('utf-8')
    if len(data) > LIMIT:
        raise compare.Invalid('Lesson exceeds output bound.')
    return data


def expected(bundle):
    # Render the returned in-memory report, never reread unchecked report.json.
    return render(compare.verify(bundle))


def build(bundle, output):
    data = expected(bundle)
    destination = Path(output)
    # Trusted stable parents required. Do not follow or overwrite an existing leaf.
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(fd, 'wb') as target:
        target.write(data)
    return {'bytes': len(data), 'sha256': compare.sha(data)}


def verify(bundle, output):
    data = expected(bundle)
    if compare.read(output, LIMIT) != data:
        raise compare.Invalid('Lesson differs from verified comparison.')
    return {'bytes': len(data), 'sha256': compare.sha(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build', 'verify'))
    parser.add_argument('bundle')
    parser.add_argument('html')
    args = parser.parse_args()
    try:
        operation = build if args.command == 'build' else verify
        print(json.dumps(operation(args.bundle, args.html), sort_keys=True))
        return 0
    except (ValueError, OSError, TypeError, KeyError, OverflowError, RecursionError):
        print('Lesson failed: verify the supported comparison bundle, resource bounds and new output path. No input or paths echoed.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
