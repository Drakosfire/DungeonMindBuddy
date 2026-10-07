# HANDOFF — APP-STATE: validated Plan Graph source-read receipts v2

**Status:** ACTIVE — PRIME confirmed this bounded APP-STATE implementation lease on 2026-10-07.
**Branch:** `codex/app-state-graph-source-read-v2`.
**Base:** Buddy `main@b06040f16e95da8411d0a93d19710285a84e6236` (#1001).
**Topology:** one APP-STATE PR; the SERVER source-read adapter follows after RAKE's separate turn-stage-timing lease settles.
**Predecessor:** APP-STATE Graph execution V1 merged in #929; preserve its stored rows and V1 serialization. Do not repair the superseded V1 handoff in this slice.

## Mission and boundary

Add a strict V2 saved-Plan Graph execution contract for admitted source reads. Keep V1 metadata-only execution, context receipts, completions, fingerprints, and replay behavior compatible. A source-opened indication is derived only from a validated successful source-read receipt. Model-produced JSON cannot assert that a source was opened.

APP-STATE validates and persists typed receipts, policy budgets, operation ordering, and citation-to-receipt membership. It does not open sources, resolve Graph/source authority, make provider calls, or write live database data. Reuse the existing `ReadGraphSourceRequest` boundary: active retrieval session, 1–8 admitted anchor IDs, `maxChars` 1–12,000.

V2 freezes a `source_read_scope` with retrieval session, World, nullable campaign, exact Graph revision, and admitted anchor/evidence/source-artifact/source-revision tuples. The immutable execution-policy digest covers that scope and budget. Each V2 source-read authorization binds the context-receipt digest and execution-policy digest, pins, exact admitted tuples, per-call anchor IDs and requested max characters. A following validated receipt binds read IDs, outcomes, content SHA-256, line bounds, returned character count, truncation, and evidence sufficiency separately from read completeness. Do not persist source text, excerpts, filesystem paths, or caller-supplied artifact authority.

Budget policy is per turn: at most 8 read calls, 8 total anchors, and 96,000 requested characters, with `maxChars` at most 12,000 per call. Charge the requested maximum before a source read; unresolved authorizations consume budget and cannot produce citations or source-opened state. Reject wrong session/World/campaign/revision, unadmitted IDs, duplicate IDs, malformed or unsuccessful receipts that claim content, forged source-opened claims, and cumulative budget overflow. Partial/truncated outcomes remain distinct from evidence sufficiency.

V2 completion citations carry validated source-read receipt IDs; their serialized `source_opened` value is derived from those references and cross-validated against successful receipts in the producing envelope. V1 citations remain `Literal[False]` and V1 completion validation stays unchanged.

## Exact write lease

- `src/application_state/agent_conversation/types.py`
- `src/application_state/agent_conversation/service.py`
- `src/application_state/agent_conversation/repository.py`
- `src/application_state/migrations/versions/20261007_0018_agent_turn_graph_context_execution_v2.py` (`down_revision=20261005_0017`)
- `tests/application_state/test_agent_conversation_service.py`
- `tests/application_state/test_agent_conversation_postgres.py`
- This handoff only.

No SERVER route/service, worker, UI, source repository, live migration/data write, provider, or runtime path is included. If another path becomes necessary, stop and obtain an explicit lease amendment before editing it.

## Version and persistence contract

V1 remains its existing strict discriminator and canonical JSON representation. V2 is separately discriminated; only V1 and V2 parse, and unknown future versions fail closed. V2 adds immutable read scope/budgets, pre-read authorization, validated source-read receipts, and V2 citations/completion needed to derive `source_opened`. Keep V1 policies/events/citations/completions unchanged. Same-key frozen-policy comparison, claim fencing, append-only event sequencing, and atomic completion rules continue to apply.

Migration 0018 only widens the existing execution/completion JSONB checks enough to admit strict V2 while retaining V1 constraints, receipt/completion digest linkage, event and serialized-size ceilings. Downgrade refuses if any V2 execution or completion row exists; otherwise it restores the V1-only checks without dropping columns or rewriting V1 rows.

## Required verification

- Golden V1 serialization, digests, strict parsing, and persisted round-trip remain byte-for-byte unchanged.
- V2 fresh-service and PostgreSQL round-trips preserve policy, ordered authorizations/results, and citation links.
- Wrong scope/revision/unadmitted anchors, forged source-opened claims, malformed outcome/content/line data, duplicate/read-after-unknown IDs, and each total budget overflow fail closed.
- Successful validated content derives source-opened; failed/no-content receipts derive false; partial/truncated status is not conflated with support sufficiency; raw source body never persists.
- Migration upgrade preserves existing V1 rows; downgrade is safe with only V1 data and refuses before changing schema when V2 data exists.
- Exact cumulative base-to-head diff and owning tests pass. No live source reads, provider calls, or live database writes.

## Acceptance

PR title: `APP-STATE: persist validated Plan Graph source-read receipts`. PRIME owns exact-head review and merge. The later SERVER adapter must consume this contract under a separate lease after RAKE settles.
