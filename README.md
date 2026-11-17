# TimeEdge

**Turn a wall-clock scheduling policy into an inspectable boundary report.**

At `02:30` in New York on 8 March 2026 there is no instant to schedule.
At `01:30` on 1 November there are two. TimeEdge makes this a deliberate
contract rather than an accidental library default.

A local CLI for developers reviewing recurring calendar behavior. It produces
JSON for CI and a self-contained, script-free HTML report for review. It is
not a scheduler, calendar service, timezone database or replacement for dateutil.

## Install and run

Requires Python 3.11+. From a source checkout:

```sh
python -m pip install .
timeedge --start 2026-03-07T02:30 --zone America/New_York --count 3 --html report.html
```

Open `report.html` locally. The command exits **2** because the default rejects
the missing hour. JSON is still printed and the HTML is still created.
Select a deliberate policy to resolve it:

```sh
timeedge --start 2026-03-07T02:30 --zone America/New_York --count 3 --nonexistent shift-forward
```

This produces 03:30 on the missing-hour day, **not 03:00**. New report files
must have a new filename: existing files are never overwritten.

On a Linux system without timezone data, install `tzdata` with pip. Windows
installs it as a dependency. Runtime needs no network. Installation may.

## Explicit policy choices

| Boundary | Choices | Default |
|---|---|---|
| Repeated wall time | `reject`, `earlier`, `later`, `both` | reject |
| Missing wall time | `reject`, `skip`, `shift-forward` | reject |
| Invalid month/year day | `reject`, `skip`, `clamp` | reject |

`--recurrence` is `daily`, `monthly` or `yearly`.
`--count` means **requested calendar slots**, between 1 and 366, including
rejected and skipped ones, not a count of successful executions. “Both” can
produce two instants in one slot. There is no automatic retry of skipped slots.

Monthly and yearly rules retain the original day anchor. January 31 with
`--month-end clamp` yields February 28 then March 31, not March 28.
Daily means the same local wall time on consecutive dates, not 24 elapsed hours.
Inputs must be local ISO datetimes without a UTC offset, in an IANA zone.
Leap seconds and leap-second scheduling are unsupported.

```sh
timeedge --start 2026-01-31T09:00 --zone Europe/Berlin --count 3 --recurrence monthly --month-end clamp
timeedge --start 2026-11-01T01:30 --zone America/New_York --count 1 --ambiguous both
timeedge --start 2024-02-29T09:00 --zone UTC --count 5 --recurrence yearly --month-end skip
```

## Evidence, not scheduling promises

The JSON records requested time, classification, policy outcome, resolved wall
time, UTC instant(s), tool/Python versions and available timezone-file SHA-256.
The hash identifies the locally available source file; it is not a signed
attestation, a timezone version label or protection from local tampering.
Timezone law and data change. Rerun your tests after updating timezone data.

Exit codes: `0` completed with no rejected slots (may include skips), `2`
completed with rejected slots, `1` invalid input or file/environment error.
HTML contains the schedule; inspect it before sharing confidential timings.

## Why this rather than a date library?

Use **dateutil** for general calendar rules, parsing and mature integration.
Use **ZoneInfo** for IANA timezone conversion. TimeEdge uses ZoneInfo rather
than pretending to implement better timezone arithmetic.

TimeEdge's narrower value is a ready-made **review workflow**: explicit choices,
one report containing rejected slots as well as successful ones, portable
JSON and a CI exit status. It saves writing that wrapper. Our six-case comparison
agrees with dateutil on every tested resolution. It does **not** prove improved
accuracy, faster computation or general superiority. See [COMPARISON.md](COMPARISON.md).

## Development

```sh
python -m unittest discover -s tests -v
python -m pip install python-dateutil==4.0.0
python benchmarks/compare_dateutil.py
```

See [VALIDATION.md](VALIDATION.md) for actually completed checks and gaps.
MIT licensed. Maintainer: **walker512**.

## Optional real Python / JavaScript experiments (0.2.0)

[Language boundary comparisons](docs/LANGUAGE_BOUNDARIES.md) execute explicitly trusted local Python and Node adapters on seven original date/DST cases, record UTC/wall/offset/fold differences and compare each side with its own declared expectation. The original TimeEdge policy appears as a separate recorded reference, not a universal answer for unlike arithmetic methods. Native “24 hours” is deliberately labeled non-equivalent across the demonstrated operations.

Use `python -m timeedge.compare run examples/compare/suite.json --python-adapter examples/compare/python_adapter.py --node-adapter examples/compare/node_adapter.js --out boundary-run --allow-execute --require-expected`, then `python -m timeedge.compare verify boundary-run --require-expected`. **Trusted code only, not a sandbox.** The installed command is `timeedge-compare`. Offline verification does not execute scripts or recompute reference timezone behavior. There is no animation/new GUI acceptance, language ranking, shared-tzdb assumption or external API call. The original core/CLI/tests and core version 0.1.0 remain unchanged; the distribution/new mode are 0.2.0.

Comparison increment validation: **55 local tests passed, zero skips** (28 original unchanged + 27 new), plus an offline wheel install and actual seven-case run/verify outside the source checkout. These are original local Python/Node examples only; original UI/hosted evidence does not cover this new CLI mode.
