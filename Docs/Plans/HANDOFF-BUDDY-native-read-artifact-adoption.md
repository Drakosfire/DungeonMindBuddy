# BUDDY: adopt accepted native read-artifact storage

Status: COMPLETE, accepted #4024 merge3ec5c8bf04a8889c052b54e685704a4ec4c63fbd.
Reviewed5dff4ec;78 native and253 auth tests,1410 exact-head frontend tests/build/
canonical receipt validation,3 automatic CI jobs and independent review passed.
Owner: Elderwyld pre-cutover optimization lane.
Current dependency updates belong to HANDOFF-BUDDY-native-validated-command-adoption.md.
Authority: operator goal with implementation, review and merge authorization.
Base: 044aaba4d29ac85c49d546dc20f572f0a7744d53, current fetched Buddy main.
Branch: codex/native-read-artifact-adoption. Serial successor to accepted #4013.
Dependency: Core #218 merge e8b05965bb43df370a1292149c8c809aec0e7fb9,
reviewed f392a3300bb591de53b094b519173f11596105b8, all CI44428259747 passed.

## Outcome and exclusive write lease

Pin Buddy to the accepted Core artifact implementation so its existing native
read adapters can consume source-verified derived PostgreSQL artifacts. Preserve
fresh source verification/provenance and the existing explicit proof-cache owner.

Four paths only: pyproject.toml; uv.lock; this handoff;
Docs/Plans/HANDOFF-BUDDY-native-source-proof-reuse.md (accepted predecessor seal).
No route, DTO, authorization, profile, WorldKeeper, runtime service, migration,
selector, ingestion/provider, deployment or cutover changes in this slice.
Preserve unrelated dependency graph, wheel/hash metadata and shared environment.

Re-anchor inspected thirty current open PRs, including combat4022, lore4021,
source/hosted branches3883/3888/3889 and retry3868. None owns a new change to
these paths. #3868's broad inherited file list includes them, but exact comparison
of its head with current main has no difference on the three existing lease paths.
No ownership transfer is inferred for its actual hosted transport changes.

## Safety and acceptance boundaries

Core migration0022 must exist before an artifact-capable read uses a database.
The current isolated Elderwyld clone is migrated and explicitly backfilled for
head and parent. This does not authorize migrating or deploying serving state.
Absent artifact rows fall back to ordinary parsing; malformed current artifacts
fail closed. Reads do not generate artifacts. Source withdrawal remains fresh.

The previous full-app 10k candidate measured first485–493ms and warm78–84ms,
with exact DTO/citation checks. Historical536–554ms includes one sample above
retained~540ms classic reference. The frozen baseline has not been rerun.
Repository adoption is not overall V8 acceptance or serving adoption.

A later Elderwyld restore probe completed18 mounted route parity/anonymous401
cases and6 citation openings at head2320336/parent643a896. It then failed its final
head assertion due to a scratch harness variable shadowing bug. Preserve its red
result. An independent read-only final check confirms the unchanged head and binds
that result's SHA256; do not present the original harness as entirely passing.
These are warm-DB/OS, local-operator, fixture-binding mounted routes, not full app,
current live head, hosted ownership or current deployment qualification.

## Verification and review gates

- Verify both project declarations and lock source resolve the exact accepted pin;
  run uv lock --check with the owning existing Python environment and task cache.
- Run affected native inspection/source owner tests and auth-app contract against
  accepted Core source, with isolated disposable database fixtures where needed.
- Qualify the final isolated full SHA with the repo-owned hosted frontend verifier,
  validate its canonical evidence.json, and retain clean-boundary/cleanup evidence.
- Review cumulative base-to-head dependency/doc changes independently. Require
  current automatic CI and review before merge. No fabricated hosted status.
- Record learned facts while active; settle merge identity with the next dependent
  slice. V8 remains open for broader correctness/performance/write/memory/scale
  evidence and canonical joint acceptance. Only accepted V8 permits V9 preparation.

## Resources and cleanup

Reuse existing Projects task Buddy/Core checkouts and owning shared Python env.
Do not sync that shared environment. Scratch/cache/receipts remain under
/home/drakosfire/Projects/.codex/v7-elderwyld-scope on verified filesystem
48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8. Reuse cache/source-proof-adoption and
cached Node22.23.0/npm10.9.8. Honor the existing global frontend resource lock;
never modify another holder or unlink its inode.

Retain evidence, unique refs and isolated candidate DB for optimization-lane review
and integration. Cleanup follows explicit scope and active process/connection,
mount, dirty checkout and unique evidence/commit checks. No standing deletion
permission. Report verifier-owned cleanup separately from any manual removal.
