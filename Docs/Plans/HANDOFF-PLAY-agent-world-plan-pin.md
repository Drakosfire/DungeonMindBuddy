# PLAY: Agent resolves the admitted World Plan pin

Status: COMPLETE / HISTORICAL — PR #1392 merged at `70d36fec5c97377388d904ff1c1afe4f763d74cc` after ARCHITECTURE exact-head PASS on `a96fc46c1c6ee65ef38bb8666745a4d5b659171a` (one review cycle). The implementation/review lease ended; PRIME delivered the reviewed module and verified the ordinary Play flow.

Base: fetched `origin/main@eadef26d7951f3384042f0144085f9676c41be7e`.
Branch: `codex/play-agent-world-plan-pin`.
Checkout: existing `/home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy`.
Topology: serial, one Play implementation PR. PRIME implements and owns merge/delivery after independent ARCHITECTURE exact-head review. DOGFOOD's concurrent Ingestion diagnosis and settlement do not lease these paths. Current open PRs were inspected; none reserves this correction.

## Invariant and evidence

A World Run's Agent context resolves the exact admitted immutable playable pin, including a World Plan, despite later mutable aggregate edits. Only World-owned `plan` or `runbook` may enter this V2 path. Preserve exact World, Run ID/current revision, artifact ID, content revision number, WorkRevision UUID, SHA, sealed manifest binding/structure, and Beat/Scene membership. Legacy campaign Runbook resolution is unchanged.

The disposable live Run `9bbd98e1-ebaa-4a3f-92e9-f51db8268c73` displays its exact Plan version 2, but ordinary Agent submit returned 409 before any provider call. Direct read-only resolution identifies the `kind=plan` versus hardcoded `runbook` check as the mismatch; all immutable pin fields agree. Historical resolution also incorrectly compares today's mutable object revision to the frozen receipt's admission-time object revision.

Keep existing receipt `runbook_*` compatibility names and frozen object revision. Do not compare that metadata to today's aggregate revision or substitute new content into the historical receipt. Later title edits have no historical-title guarantee. No schema migration, latest-Plan fallback, automatic rebase, working-copy reads or relaxed pin validation.

## Exclusive write lease

- `Docs/Plans/HANDOFF-PLAY-agent-world-plan-pin.md`: bounded authority and verification/settlement.
- `apps/live_control_server/services/agent_play_surface_context.py`: World V2 current/historical type checks and mutable-revision correction only.
- `tests/test_agent_play_surface_context.py`: real disposable DB Plan → committed V2 structure → Run → context receipt → later Plan edits/progress → frozen historical context; failure cases.
- `tests/test_agent_turn_route.py`: accepted Plan reaches the post-context dispatch boundary; invalid pin never dispatches.

No other source, UI, registry, schema or dependency paths. Return any required expansion to PRIME before editing. First commit contains this handoff only.

## Verification

Use the current existing Python runtime and standard application_state_dsn disposable fixture, owned by PRIME on localhost54329; no retained database for tests, no new environment or source copy. Fixture container is removed after author and reviewer finish.

Prove current and historical resolution for World Plans and existing Runbooks, exact old content after title/body edits, frozen old moment after Run progression, stale current revision rejection, and wrong World/kind/artifact/revision/WorkRevision/SHA/manifest/membership rejection before provider. Run focused resolver/route suites and inspect the cumulative diff. Test data remains synthetic; no provider required for automated tests.

After independent review and merge, deliver the exact service module on the owned API with active-work preflight and retained-state checks. Resume the ordinary disposable Mirathorn Play question once, verify useful source/proposal separation and durable historical context. Preserve operator drafts, source/Run content, prior Ingestion runs and Graph state. Runtime restart is a delivery step under standing authority; no publication is included.

## Implementation verification

- World V2 current/historical lookup accepts only the existing `plan`/`runbook` types; legacy campaign code is unchanged. Historical comparison uses immutable content identity and leaves the frozen receipt object revision intact.
- 37 focused resolver/HTTP tests pass against disposable PostgreSQL, including real producers, sealed manifests, title/body edits, Run progress, historical context, unsupported kind, World/WorkRevision/revision/SHA mismatches, missing manifest and Scene-parent rejection. Valid Plan-backed HTTP reaches the fake runtime; stale revision dispatches zero additional calls. No real provider was called.
- Loading exact base production module in memory makes both new lifecycle cases and the new Plan HTTP acceptance fail: Plan kind rejection and historical mutable-object revision rejection. Working source files were not swapped.
- Broad route comparison with the same current test fixtures: candidate 42 passed / 18 failed; pinned base production loaded only in memory 40 passed / 20 failed. All 18 candidate failures also fail on base: stale auth-principal fixtures, old policy fixtures and digest/coverage expectations. The two additional base failures are the repaired Plan HTTP/replay cases. Logs remain in the owning checkout `.pytest_cache/prime-play-route-{base,candidate}.log`; this is not a green broad route suite.
- Ruff (`--no-cache`) and cumulative diff checks pass. Initial new-test dataclass assertion and two owning auth fixtures were corrected before the final run. Initial Ruff cache creation was denied by the filesystem sandbox; the read-only no-cache invocation passes.

## Delivered acceptance

The reviewed service module (SHA-256 `9a32a0fceef347cfc172671e332478d3c193b6c98f4dad3f32b1411caacef050`) is deployed on the existing API. Active-work preflight and retained media/source/Plan/Run checks passed; UI bytes and prior Ingestion artifacts were unchanged. Normal Play submission completed as durable turn `e6ca3694-f8a7-4c6b-924e-322815152061`, using the Run's Plan revision 2 / WorkRevision `73535c5a-0333-48b9-8171-ff0fc1c0dd3a`, even though the current Plan is newer. It named the expected Beat and Scene, separated supplied location facts from proposed sensory cues, and remained visible after ordinary reload/reopen without resubmission. Direct historical resolution and normal HTTP conversation history verified the retained receipt/context.

Private evidence remains under the established experiment root in `play-agent-pin-{rollout,live-turn,live-history,live-proof,live-traces}.json`. Trace `agent-trace-ad5dd8d24b4b` correlates the durable turn explicitly: 10,900 ms, two Luna calls, 23,856 input / 417 output / 24,273 total tokens. This deliberate acceptance is excluded from natural performance cohorts; no optimization or independently certified cost claim follows. Browser screenshot capture failed; rendered text was inspected, and no screenshot is claimed. Broader Ingestion semantic readiness remains open. No source/Run content or World Graph was changed by the acceptance.
