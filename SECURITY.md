# Security and privacy

The original policy/schedule CLI does not fetch remote content, run user scripts,
execute schedules or send telemetry. The optional 0.2.0 comparison mode explicitly
runs trusted Python/JavaScript adapters only with --allow-execute. It is NOT a
sandbox: those scripts retain user privileges and can independently access files,
credentials or networks. See docs/LANGUAGE_BOUNDARIES.md before running any adapter.
The harness and bundled original examples make no network calls or deployments. Its HTML output escapes data and uses no JavaScript or remote
assets. Output includes requested times and zone names; review before sharing.
Only use trusted timezone databases and Python packages. Local package or timezone
file tampering is outside this tool's threat model. Do not place output in sensitive
paths. Existing HTML paths are refused, including symbolic links to existing files.
There is no server and no authentication surface. Report a suspected issue privately
to the repository maintainer before publishing exploitable details.
