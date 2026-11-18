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

## Separate 0.2.0 execution-comparison increment

The new `timeedge.compare` mode has **55 local tests passed, zero skips** (28 original unchanged + 27 new), Linux/Python 3.12.14 with actual Node v24.22.1/ICU78.3/tz2026e reports. The new tests execute trusted original adapters; they do not establish language superiority or a shared timezone dataset. An offline-built wheel was installed into a new virtual environment and invoked from outside the checkout: the seven-case comparison, source-hash offline verification and original policy CLI all ran. [Detailed scope and execution warnings](docs/LANGUAGE_BOUNDARIES.md) distinguish runner probes, adapter self-report and recorded-but-not-reexecuted policy references. No new browser/animation/Windows/macOS/hosted-CI result is claimed for this mode.

## Additive boundary-player candidate

The historical results above apply to their original modes. The new playback
candidate was tested on Linux/Python 3.12 with **69 tests, 0 skipped**, including
real Node execution for the controller. Builder Chromium exercised gap, fold,
monthly and leap-year examples, policy changes, Play/end/restart and keyboard
slider navigation. This does not retroactively validate comparison adapters in
a browser or claim mobile/cross-browser accessibility coverage. Offline wheel
installation and generation outside the source checkout were also run. Hosted
CI is not claimed. See README's boundary-player limits; no publication is implied.
