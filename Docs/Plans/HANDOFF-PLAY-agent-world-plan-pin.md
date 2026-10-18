# PLAY: Agent resolves the admitted World Plan pin

Status: ACTIVE — PRIME stewardship under the Build → Plan → Play dogfood goal; ARCHITECTURE critiqued this invariant and failure cases on 2026-10-17.

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
