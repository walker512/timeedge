# Scope and comparison

Evidence date: 2026-11-17. Actual installed comparator: python-dateutil 4.0.0.
Reproduce with `python benchmarks/compare_dateutil.py`. This invokes the real
TimeEdge CLI and dateutil's public timezone functions. All six cases agree:
New York gap/fold, Lord Howe half-hour gap, Apia's skipped date, Berlin normal
and UTC normal. `benchmarks/observed.json` records the observed outputs.
This is a small, deliberately chosen boundary suite, not comprehensive accuracy
or performance evidence.

| Task | TimeEdge | dateutil / ZoneInfo |
|---|---|---|
| IANA conversion | Uses ZoneInfo | Native, established capability |
| Detect gaps/folds | Round-trip validation | dateutil provides explicit detection |
| Shift imaginary time | Explicit CLI policy | dateutil `resolve_imaginary` already does this |
| Rich recurrence rules | Only daily/monthly/yearly | dateutil rrule is substantially broader |
| General parsing | ISO local input only | dateutil provides broader parsing |
| Review rejected calendar slots | Built-in JSON and HTML | Can be implemented in a wrapper |
| CLI failure status + report | Built in | Custom integration required |

Do not call dateutil's invalid-date skipping a bug. RFC recurrence sets intentionally
ignore such dates. Its count means returned occurrences; TimeEdge's means attempted
slots. Comparing those counts without explaining this would be misleading.

Sources read:
- https://dateutil.readthedocs.io/en/stable/tz.html
- https://dateutil.readthedocs.io/en/stable/rrule.html
- https://docs.python.org/3/library/zoneinfo.html

This project is a diagnostic presentation layer, not a competitor that replaces
these libraries. There is no evidence it is universally superior or will gain stars.
