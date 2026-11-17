# Real Python / JavaScript time boundaries · 0.2.0

This optional CLI executes **reviewed, trusted local Python and JavaScript adapters** against explicitly declared time-boundary cases. It records actual results field by field, single-side expected assertions, and the original TimeEdge policy's separately recorded reference. It is not a scheduler, language correctness ranking, shared timezone database, sandbox or complete animated debugging interface.

The original `timeedge.core`, `timeedge.__main__`, core version 0.1.0 and 28 original tests remain unchanged. The distribution and new comparison mode are 0.2.0. A recorded core version is deliberately different from the new mode version.

## Real seven-case example

Python 3.11+, trusted local Node, and POSIX execution are required. No additional package, external agent/API, model call or network is used by the harness or original examples. From the source checkout:

```sh
python -m timeedge.compare run examples/compare/suite.json \
  --python-adapter examples/compare/python_adapter.py \
  --node-adapter examples/compare/node_adapter.js \
  --out boundary-run --allow-execute --require-expected
python -m timeedge.compare verify boundary-run --require-expected
```

The two original editable adapters actually use Python `datetime`/`zoneinfo` and Node's built-in `Date`. They do not simulate language answers, call another agent, use Temporal or import third-party packages. The tested Node runtime does not provide Temporal. The bundled independently specified expectations describe these particular methods and policies, not universal answers every implementation should give.

| Case | Actual methods and useful distinction |
| --- | --- |
| Spring missing hour | Python attaches ZoneInfo with default fold 0 and retains an imaginary 02:30 wall value; Date normalizes it to 03:30. They can produce **the same UTC instant but different wall/offset fields**. UTC-only comparison would hide the distinction. |
| Autumn repeated hour | Both native constructors choose the earlier occurrence in this case. Python exposes fold 0; Date has no fold field. The declared TimeEdge `both` reference keeps two distinct instants. |
| January 31 → February | Python `replace(month=2)` rejects an invalid date. `Date.setMonth(1)` overflows into March. The separate TimeEdge monthly `clamp` reference is a third deliberate policy, not a judge. |
| Leap day → following year | Python `replace(year=...)` rejects February 29 in a non-leap year; Date's `setFullYear` normalizes into March. Reference `skip` records an invalid calendar slot. |
| One local calendar day | Python aware datetime + one day and Date `setDate` retain noon across spring DST, taking only 23 elapsed hours. |
| Native “24 hours” | Python aware datetime + `timedelta(hours=24)` uses wall arithmetic with that same ZoneInfo, while Date epoch + 86,400,000 milliseconds is elapsed arithmetic. **These are explicitly unequal semantics**, not a fair universal language score. |
| Explicit elapsed 24 hours | Python converts to UTC, adds 24 hours, then converts back; Date adds epoch milliseconds. Both reach 13:00 in this example, unlike the calendar-day reference. |

Official semantic references: [Python datetime arithmetic](https://docs.python.org/3/library/datetime.html), [ECMAScript Date objects](https://tc39.es/ecma262/#sec-date-objects), and [Date.setMonth](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/setMonth). The examples use modern local ISO years 1900..2099, second precision, avoiding JavaScript's special numeric-constructor treatment of years 0..99. Leap seconds and arbitrary historical calendar systems are unsupported. Output wall fields allow 1899..2100 so bounded day arithmetic can cross an input-year edge; UTC/epoch bounds also allow the one-day offset margin. These are protocol bounds, not a claim of all Date/datetime ranges. Outputs outside them are a protocol error, not proof that a language calculated incorrectly.

## Customize code and declarations

Edit copies of the two standalone files, review them, and run again into a new directory with `--allow-execute`. Both initial source byte streams are read once and hashed, then copied to a fresh temporary directory for each case/side. Relative assets/dependencies are not copied. Preserving the same filename does not preserve the source hash. Your code may use different operations, but it must accept the documented request and return the exact protocol; describe its actual semantics honestly in the suite.

A suite contains `schema: 1` and 1..12 unique cases. Each has:

- `id`: a bounded safe label.
- `request`: `local` (second-precision local ISO without offset), IANA `zone`, one of `construct`, `replace_month`, `replace_year`, `calendar_day`, `native_24h`, `elapsed_24h`, and its bounded `argument` or null.
- `semantics`: descriptions for `python` and `node`, explicit boolean `equivalent_intent`, and an explanatory note. This equivalence flag is a human declaration, **not automatically established**.
- `expected`: independent complete observation for each side, or null if not asserted. The fixture's expected UTC/wall values are specified independently; epoch numbers are derived from those declared UTC strings, not harvested from adapter output.
- `reference`: explicit original TimeEdge calendar recurrence/count and month-end/ambiguous/nonexistent policies. It is a separate declaration, not an automatically inferred translation of the adapter operation.

Only `request` is supplied to adapter stdin. Expected answers are not sent, but this is not a blind benchmark: trusted code can read other accessible files or hard-code results. No assertion result can prove honesty or absence of side effects.

## Exact adapter observation

Stdout must be exactly one UTF-8 JSON object with `observation` and `adapter_runtime`, no logging prefix. Successful observations contain:

- `status: "ok"`, `error: null`;
- `utc` as `YYYY-MM-DDTHH:mm:ssZ`, integer `epoch_ms`;
- `wall` and `roundtrip_wall` as second-precision local ISO strings;
- integer `offset_seconds` and `roundtrip_offset_seconds`, with **UTC = wall − offset**;
- `fold` as integer 0/1 or null when the API does not expose it;
- `wall_fields` as `[year,month,day,hour,minute,second]` matching the raw wall string.

Epoch/UTC, wall/offset/UTC and field-list consistency are validated. The Node example derives second-resolution offset from its actual local fields and epoch, rather than claiming `getTimezoneOffset()` provides sub-minute precision. An imaginary Python wall value can differ from its UTC round-trip wall while both independently map to the same instant with different offsets. The requested local string remains separately visible, so Node's normalization is not mistaken for retaining the original input.

A domain error has `status: "domain_error"`, a fixed `error` label (`invalid_calendar_date`, `unsupported_operation`, `unknown_zone`), and null for all time fields. No exception message or arbitrary private text is used as a domain label. A valid domain error can match a side's declared expectation **only after exit 0 and successful protocol validation**. A crash, nonzero exit, timeout, excessive output or invalid JSON is an execution error, never a passing expected date exception.

All numeric protocol fields are integers, not booleans; floats/nonfinite values, duplicate JSON keys, malformed Unicode, excess nesting and unknown fields are rejected. Each case starts a new process on each side, so there is no persistent-session comparison. Object keys are normalized for matching; all declared observation fields, including API-specific fold/null, remain explicit.

## Report meaning and reference provenance

The report shows each side's actual observation and one of `match`, `mismatch`, `unasserted`, `execution_error`. It compares status/error, UTC, epoch, both wall values, both offsets, fold and wall fields separately. There is deliberately no “better language”, overall correctness or universal policy score. Differences may come from intentionally different methods, policies or timezone data. Even `equivalent_intent: true` does not authenticate semantic equivalence.

`run` really computes the TimeEdge reference using the unchanged core **before launching user adapters**. It records its policy, rows, core version, exact core-source hash, runner zone-file fingerprint where available, source category (system TZif / package resource / unknown), and installed tzdata package version if available. An installed package version does not prove that package was selected when system data exists. A zone-file hash is not a tzdb release label or signature.

The harness independently probes its Python version and selected Node's Node/V8/ICU/tz fields. These **runner observations are separate from adapter self-description**, which is untrusted returned JSON and not an authenticated measurement. Python adapter metadata reports system zone-file hash if accessible and installed package version; Node reports its own version, ICU/tz labels and resolved zone. Unknown fields stay null. Node's tz version cannot establish equality with a Python system zone file, and no shared database version is assumed.

The local tested environment is Python 3.12.14, Node v24.22.1, V8 13.6.233.17-node.58, ICU 78.3, Node-reported tz 2026e. Those are the tested runtime's reports, not requirements or a claim that Python uses tz2026e. No timezone data or Node binary is bundled or installed by this mode.

## Trusted execution, not containment

Every run requires exactly explicit consent (`--allow-execute`; API boolean True). Only execute code you have reviewed and are authorized to run. Python and Node run with your account's privileges. `python -I`, fresh directories, minimal environment, timeouts and pipe caps **are not a sandbox**: adapters can independently access files/network/credentials, spawn detached children or change other state. The harness and bundled adapters do none of those external actions, but cannot prevent custom scripts from doing so.

No shell is used. The environment passes only default PATH, LANG and the explicit case TZ; it does not inherit NODE_OPTIONS, PYTHONPATH or application credentials through environment variables. Other credential/filesystem access is still possible. The runner terminates ordinary same-process-group children on completion/error; deliberately detached processes are not controlled. There is no memory/disk/CPU security quota or rollback of side effects.

Inputs and new output destination are checked before user adapter execution. Python syntax can be compiled without executing it; JavaScript syntax/protocol errors become explicit runtime errors when Node runs. The new output directory is reserved before execution. Failure can leave an empty/partial directory; an incomplete bundle is not a successful comparison and is never overwritten on retry. Preserve originals and choose a new output path. No unknown directory is recursively deleted.

## Bounds, gate and offline verification

Up to 12 cases × 2 sides. `--timeout` is integer 1..5 seconds per adapter invocation (default 3): maximum nominal adapter budget 120 seconds. The independent Node probe has a 5-second budget; cleanup may add up to 50 seconds across 25 invocations. Process creation, kernel/filesystem blocking and cleanup are not hard real-time bounded. Combined stdout+stderr capture is limited to 64 KiB per process using incremental reads, not unlimited capture. Inputs/scripts are at most 1 MiB each; generated files at most 16 MiB each. All generated artifacts are serialized and size-checked before file writes, although code may already have made side effects. File leaves must be regular non-symlink files.

Exit 0 means command completion/internal consistency, even with mismatches or unasserted cases. `--require-expected` returns 3 unless **both sides of every case have supplied expectations, complete valid responses and exact matches**. A null expectation is always `unasserted`, never vacuous success. Invalid inputs/environment/output return 2. This is a supplied-contract gate, not scheduling/deployment authority or a claim that all language behavior was tested.

The exact bundle has `suite.json`, `receipt.json`, `report.json`, `review.html`. Scripts are **not included**. Preserve reviewed originals and dependencies if you want to execute again; a source hash alone is not runnable evidence. Optional source-byte checks do not execute code:

```sh
python -m timeedge.compare verify boundary-run \
  --python-adapter examples/compare/python_adapter.py \
  --node-adapter examples/compare/node_adapter.js --require-expected
```

`verify` reparses recorded successful stdout, checks status/order/types and byte binding, structurally checks the recorded reference, and recomputes field differences and single-side expected matches. It **does not run adapters or recompute the TimeEdge reference with today's timezone data**. No current runtime/tz match is implied. The reference is the record of the earlier run, not newly revalidated timezone truth. Failed stdout/all stderr are omitted except prefix lengths/hashes; nonempty omitted hashes cannot be independently reconstructed. A coordinated fabricated receipt and report can pass. Hashes are not signatures, execution attestations or proof of historical reference computation.

## Privacy and scope

Inputs, timing schedules, successful stdout, metadata and recorded policies may be private. No redaction, encryption or automatic upload is provided. Static HTML uses escaped content and restrictive CSP without scripts, widgets, animation or network resources. It is an inspectable report, not newly browser-accepted GUI functionality. The existing policy tool is retained; this increment only fills a narrow actual cross-language boundary experiment, not the entire time-debugging product theme.

## Actually executed checks

**55 tests passed on Linux/Python 3.12.14, zero skips**: all 28 original tests remain unchanged, plus 27 comparison tests. The latter execute actual local Python and Node processes for all seven cases, verify separate raw/round-trip wall fields, reference fold/gap records, month/leap domain exceptions, native versus elapsed arithmetic, output-year edges, unasserted/mismatched gates, environment omission, initial script-byte snapshots, subprocess timeouts/output limits/same-group child cleanup, strict protocol/status types, malformed/bound/tampered artifacts, source checks, static HTML escaping and actual CLI commands. Non-POSIX or missing-Node execution tests explicitly skip and are not counted as passes.

A wheel was built locally with package indexes/dependency fetching disabled, installed into a new virtual environment, and both installed entry points were invoked outside the checkout. The final seven-case `timeedge-compare run` launched 14 actual adapter processes; all independently supplied observations matched. Offline verification, including both original source hash checks, succeeded. The original installed `timeedge` policy command also ran successfully. Module bytes were checked against the reviewed source rather than relying on a checkout import.

This validates the supplied local examples and the stated protocols in that environment only. It does not validate real third-party services, arbitrary adapters, all IANA historical behavior, identical Python/Node timezone data, GUI/animation, browser rendering, Windows/macOS, hosted CI for this increment, language superiority or production scheduling. The original release's prior UI/CI/comparison evidence remains scoped to that original mode. No package-index fetch, external API call, publication or deployment was performed for this increment.
