# BUDDY: adopt validated prospective command transfer

Status: COMPLETE — accepted Buddy #4029. Owner: Elderwyld pre-cutover optimization lane.
Authority: operator goal with implementation/review/merge authorization.
Base: 84b9bc9ab104cf2b7a54d74af53f6e6ae72c8f98, current fetched main.
Branch: codex/native-validated-command-adoption. Serial successor to #4024.
Dependency: accepted Core #228 merge4b6516e2c0dfd81acaa4410b9b9bb9da18894c90,
reviewed8c5b291, all CI44432180173 passed and independent review approved.

## Outcome, scope and ownership

Adopt Core's removal of one duplicate command restoration in ordinary publication
and governed source extension. Both retain binding validation before persistence;
ordinary post-publication verification restores an independent sealed expectation.
Public copy-on-read behavior, deterministic identity, receipts and recovery remain.

Four paths only: pyproject.toml; uv.lock; this handoff;
Docs/Plans/HANDOFF-BUDDY-native-read-artifact-adoption.md (accepted #4024 seal).
No Buddy runtime, tests, route/DTO/auth, WorldKeeper, migration, selector, provider,
ingestion, deployment or cutover changes. Preserve unrelated lock metadata and
shared environment. Both planner callers and adversarial command-mutation cases
are covered at Core's owning boundary; Buddy must qualify its consumer pin.

Forty open Buddy PR file lists inspected. Older hosted branches3936/3873/3872/
3871/3869/3868/3866/3865/3823/3822/3821/3820 show inherited dependency diffs;
their fetched heads pin older a672/a9 or current e8, not the new4b target. Their
transport/runbook work is not a competing Core upgrade. Preserve their ownership;
this lane owns only the new exact dependency pin and its own handoff settlement.

## Validation and acceptance boundaries

- Confirm both project declarations and locked Git source select exact4b6516;
  run uv lock --check without syncing the shared Python environment.
- Run affected native inspection/source/recap-preparation tests against exact
  accepted Core source, plus auth-app in explicit local configuration and existing
  disposable database isolation.
- Qualify final full SHA using the unmodified repo-owned hosted verifier and
  canonical evidence validator, pinned Node/npm and normal global resource lock.
- Require independent cumulative review and current automatic CI before merge.
  Preserve failed attempts separately; never claim a queued/refused run passed.

Core candidate diagnostic proves2restorations per commit/replay, exact replay,
one counted head event and relationship endpoints; six module hashes match Git.
Profiled prepare/commit/replay1.93/11.83/10.14s are not unprofiled latency acceptance.
The retained classic baseline is not rerun. Broader V8 route/write/memory/scale
and canonical joint evidence remain open; only accepted V8 permits V9 preparation.

Migration0022 remains required before artifact-capable database reads. Only the
isolated candidate clone has been migrated/backfilled by this lane. Recent V8
serving refresh found5202 unavailable and a separate local API8000 with unqualified
loaded-source identity. Neither process/deployment is changed by this adoption.
Do not treat checkout metadata as proof of loaded code or activate a cutover.

## Resources and cleanup

Reuse existing Projects task Core/Buddy checkouts, owning Python environment,
cache/source-proof-adoption and pinned Node22.23.0/npm10.9.8. All scratch, logs,
receipts and caches stay under /home/drakosfire/Projects/.codex/v7-elderwyld-scope,
verified filesystem48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8. No new worktree/env.
Retain unique refs/evidence for optimization-lane review/integration. Cleanup
requires explicit scope and active process/connection/mount, dirty checkout and
unique-data/commit checks. No standing deletion permission or manual removal.
Settle this slice's merge only after it occurs through the next dependent consumer.

## Accepted settlement

Exact reviewed head0c2717cd43c1443afecb5d79776085900654b3a9 merged as
0a746752da32324256d83b018e884aa7cb8ad692. Independent review approved;
263 native/recap tests and253 auth tests passed, four opt-in PostgreSQL cases
passed separately, and exact-head hosted frontend qualification passed1410 tests
plus build/canonical validation. All normal automatic checks were green. V8 was
subsequently accepted through Core #229 atf770098; V9.A now owns restore/canary
qualification. This adoption did not itself perform a serving switch.
