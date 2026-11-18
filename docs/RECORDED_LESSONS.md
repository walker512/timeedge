# Recorded comparison lessons

This opt-in bridge turns an existing `timeedge.compare` bundle into a script-free,
offline, numbered case view. Open each native HTML disclosure to inspect the
request, declared semantics, Python and Node outcomes, field differences and the
separate recorded TimeEdge calendar-policy reference. Nothing is executed or
rescheduled by this command or the page. This complements, but does not merge
with, the existing interactive policy playback: changing that player's policy
is not a rerun of a recorded comparison.

```sh
python -m timeedge.lesson build comparison-bundle lesson.html
python -m timeedge.lesson verify comparison-bundle lesson.html
```

Only bundles accepted by the installed `timeedge.compare.verify` are supported
(current comparison schema 1, version 0.2.0). The build renders the verifier's
returned in-memory report, not a later unchecked read of `report.json`.
Verification independently regenerates the page and compares exact UTF-8 bytes.
Changes to results, scripts inserted into HTML, external links or formatting
cause a mismatch. Unknown comparison versions fail closed. It does not modify
or add members to the original four-file comparison bundle.

Internal consistency is not authenticated execution or source authenticity.
Someone who rewrites all matching evidence can manufacture a consistent bundle;
this is not a signature. The original reference is archived, not rerun with the
current timezone database. Adapter runtime metadata is self-description. Missing
expected values remain unasserted, execution errors have no successful response,
and an adapter's domain error differs from a failed subprocess. Field agreement
is not a proof of equivalent intent, common tzdb versions or language correctness.

## Output and privacy

The destination is a new file, not a directory. Existing files, directories and
leaf symlinks are not overwritten. Parent directories must already exist and be
trusted and stable. POSIX creation requests mode 0600; Windows ACL privacy has
not been verified. Writes are exclusive, not transactional or power-loss durable.
A write failure can leave a partial file; it will fail verification. Preserve it
if needed and retry at a new path, rather than automatically deleting anything.
Concurrent builders for the same new path have at most one successful creator.
The same-user parent-directory race is not defended.

The page contains full recorded labels, notes, requests, observations and runtime
metadata. Treat it as private unless reviewed. No links, scripts, remote assets,
adapter source, or automatic refresh are inserted. Dynamic text is HTML-escaped;
a restrictive CSP denies resource loading. Other tools modifying or interpreting
this output differently are outside that guarantee. Output is bounded to 16 MiB;
the existing verifier's input and schema limits still apply. Unrelated files in
an output parent are not inspected or changed.

## Validation boundary

Public tests use actual trusted local Python and Node comparison execution,
then verify/build/check the page without launching adapters again. HTML parser
checks are static, not browser interaction or visual accessibility acceptance.
New lesson browser behavior, Windows and macOS are not verified. Prior CI and
playback browser results do not cover this increment. No old restricted CI logs
or workflows were accessed or changed.
