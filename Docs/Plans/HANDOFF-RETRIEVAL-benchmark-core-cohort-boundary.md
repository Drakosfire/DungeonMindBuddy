# Verify the shared Core snapshot at cohort boundaries

**ACTIVE.** The operator requested the harness update after the retained
six-worker Q/D/F run. Base `fe485787411d6cdc9b2ce8ed06a4b050584c3e7e`;
serial branch `codex/benchmark-core-cohort-boundary` in the existing
`jev-build-dialogue-warmup/DungeonMindBuddy` Projects checkout. Runtime and
hosted deployment are outside this slice. No open harness overlap was found.

Write set is this handoff, `evals/README.md`, the benchmark workflow,
cohort coordinator and shared artifacts routine, and their existing workflow
test module. The coordinator verifies one immutable Core inventory before
the cohort and one after it. Every worker still verifies exact loopback
database identities and requires Core access via a dedicated non-writing
login. Distinct App fixture databases prevent concurrent pointer races. Pin
each input manifest, run workers in fresh processes and retain every member
result. Standalone capture keeps its existing independent integrity checks.

Verify the two snapshot calls, early refusal for writable Core, drift
rejection, and unchanged row fingerprints without paid calls. Obtain
independent review of the exact head before delivery. No schema or port
changes and no writes to the serving system.
