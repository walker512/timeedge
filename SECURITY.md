# Security and privacy

TimeEdge does not fetch remote content, run user scripts, execute schedules or
send telemetry. Its HTML output escapes data and uses no JavaScript or remote
assets. Output includes requested times and zone names; review before sharing.
Only use trusted timezone databases and Python packages. Local package or timezone
file tampering is outside this tool's threat model. Do not place output in sensitive
paths. Existing HTML paths are refused, including symbolic links to existing files.
There is no server and no authentication surface. Report a suspected issue privately
to the repository maintainer before publishing exploitable details.
