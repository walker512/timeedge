# Validation status

Candidate validation, 2026-11-17. No public release or hosted CI result claimed.

## Completed locally

- Python 3.12.14 on Linux: `python -m unittest discover -s tests -v`, **26 tests passed**.
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
- Windows/macOS and Python 3.11/3.13 not run locally. CI matrix is configured but
  has not run in a remote repository.
- Not exhaustively tested against all historical or future timezone transitions.
- No user adoption or star-growth validation. Independent code-review outcome is recorded below; visual and platform gates remain open.

Release gate: run cross-platform CI on the exact candidate before claiming a
finished public release. Independent code and responsive-layout reviews are below.

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
checks. The code-review stage passes for this narrow diagnostic scope; release
remains on hold pending those independent execution/visual gates. The comparison
supports a packaged review-workflow benefit only, not superior time arithmetic.

### Browser layout verification

Chromium desktop and a 390px-wide iframe viewport were visually inspected.
Timestamp cells initially wrapped across several lines on the narrow viewport;
the table now preserves timestamps and provides an explicitly labelled,
keyboard-focusable horizontal scrolling region. Left and right columns were
visually checked after scrolling. This is responsive-layout QA, not a real
phone/device test. Headless browser launch remains restricted in this executor;
these checks used the available cloud browser and a local static preview.
