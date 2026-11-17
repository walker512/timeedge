# Validation status

Validation record, 2026-11-17. Hosted CI evidence is recorded below.

## Completed locally

- Python 3.12.14 on Linux: `python -m unittest discover -s tests -v`, **28 tests passed** in the current reviewed suite (initial baseline: 26).
- Covers one-hour and half-hour gaps/folds, Apia skipped date, UTC false-fold
  avoidance, leap years, preserved month-end anchor, wall-day vs elapsed-day,
  invalid policies/input/ranges, summary semantics, output escaping and refusal
  to overwrite an existing report.
- CLI invoked by subprocess, including exit 2 for rejected slots and exit 0
  with explicitly skipped slots. Summary distinguishes those from resolved instants.
- Six real CLI cases agree with installed dateutil 4.0.0. See comparison and
  machine-readable observations. This is not a claim of superior resolution accuracy.
- Wheel built with and without build isolation. Installed wheel into a separate
  directory and invoked outside the source checkout. Lord Howe gap adjustment
  returned 02:45 +11:00, matching expected behavior.
- Example JSON and HTML generated from the CLI, not hand-written outputs.

## Not passed / not run

- Initial headless screenshot attempts were blocked by the executor socket restriction.
  Desktop and narrow-layout checks subsequently passed in the cloud browser (below).
  Real mobile-device and observed offline browser-network tests are not claimed.
- Windows/macOS and Python 3.11/3.13 were not run locally; the remote matrix
  has now passed (see exact run below).
- Not exhaustively tested against all historical or future timezone transitions.
- No user adoption or star-growth validation. Completed independent code-review, visual and platform results are recorded below.

Code, responsive-layout and cross-platform test gates passed for the narrow
diagnostic scope. Real phone-device and exhaustive timezone testing are not claimed.

## Independent code review

A separate review reproduced the original 26 tests and the six-case CLI/dateutil
comparison, inspected recurrence and timezone resolution and output safety, then
fixed two report-contract issues:

- Argument-parser failures previously returned 2, colliding with the documented
  valid-report-with-rejected-slots status. They now return 1 and no JSON.
- HTML omitted the resolved local wall time, requiring reviewers to calculate it
  from UTC. It now includes the resolved local timestamp and offset(s).

The resulting 28 tests pass on Linux, including new regressions for both issues.
The wheel was rebuilt successfully. The bundled HTML was regenerated from the
example JSON. No browser, Windows/macOS or hosted CI result is implied by these
checks. The code-review stage passes for this narrow diagnostic scope; subsequent
execution and visual results are recorded below. The comparison
supports a packaged review-workflow benefit only, not superior time arithmetic.

### Browser layout verification

Chromium desktop and a 390px-wide iframe viewport were visually inspected.
Timestamp cells initially wrapped across several lines on the narrow viewport;
the table now preserves timestamps and provides an explicitly labelled,
keyboard-focusable horizontal scrolling region. Left and right columns were
visually checked after scrolling. This is responsive-layout QA, not a real
phone/device test. Headless browser launch remains restricted in this executor;
these checks used the available cloud browser and a local static preview.

## Hosted cross-platform verification

[CI run 44008115591](https://github.com/walker512/timeedge/actions/runs/44008115591)
passed on commit `930da6272068aef0e84b4167f22f37d239640fad`: Linux, Windows and
macOS, each with Python 3.11, 3.12 and 3.13 (nine successful jobs). The Windows
3.11 log was inspected and confirms 28 tests executed, not an empty discovery.
The downloaded repository ZIP contained exactly the 17 reviewed source files,
with every SHA-256 matching the local candidate.

The run emitted GitHub Actions Node 20 deprecation warnings for checkout v4
and setup-python v5; the platform executed them using Node 24. These warnings
were not test failures. Runner-image/capacity notices are not application defects.
No public package registry upload, real-device testing or adoption claim is made.
