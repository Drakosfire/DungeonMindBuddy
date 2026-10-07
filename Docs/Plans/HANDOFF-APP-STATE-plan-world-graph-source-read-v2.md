# HANDOFF — APP-STATE: validated Plan Graph source-read receipts v2

**Status:** ACTIVE — PRIME confirmed this bounded APP-STATE implementation lease on 2026-10-07.
**Branch:** `codex/app-state-graph-source-read-v2`.
**Base:** Buddy `main@b06040f16e95da8411d0a93d19710285a84e6236` (#1001).
**Topology:** one APP-STATE PR; SERVER source-read adapter follows after RAKE's separate turn-stage-timing lease settles.
**Predecessor:** APP-STATE Graph execution V1 merged in #929; retain its stored rows and V1 serialization semantics. Do not repair the superseded V1 handoff in this slice.

## Mission and owner boundary

Add a strict V2 saved-Plan Graph execution contract for admitted source reads. Keep V1 metadata-only execution, context receipts, completions, fingerprints, and replay behavior compatible. A source-opened indication is derived only from a validated successful source-read receipt. Model-produced JSON cannot assert that a source was opened.

APP-STATE validates and persists typed receipts, policy budgets, operation ordering, and citation-to-receipt membership. It does not open sources, resolve Graph/source authority, make provider calls, or write live database data. Reuse the existing `ReadGraphSourceRequest` boundary: active retrieval session, 1–8 admitted anchor IDs, `maxChars` 1–12,000.

A V2 receipt binds the frozen context-receipt digest and immutable execution-policy digest; retrieval session; world and nullable campaign; exact Graph revision; admitted anchor/evidence identity; resolved source artifact and source revision; read ID; outcome; returned-content SHA-256; line bounds; returned character count; truncation; and evidence sufficiency separately from read completeness. Do not persist source text, excerpts, filesystem paths, or caller-supplied artifact authority.

V2 policy carries explicit total source-read call, anchor, and character budgets. Reserve budget under the existing turn claim/fence before a source read; append the validated result receipt afterward. An unresolved reservation consumes budget and cannot yield a citation or source-opened state. Reject wrong session/world/campaign/revision, unadmitted IDs, duplicate IDs, forged source-opened values, failed/no-content receipts with content fields, malformed successful receipts, and cumulative budget overflow. Partial/truncated reads remain distinct from evidence sufficiency.

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

V1 remains its existing strict discriminator and canonical JSON representation. V2 is separately discriminated; only V1 and V2 parse, and unknown future versions fail closed. V2 adds the source-read scope, explicit budgets, pre-read reservation, validated source-read receipt, and citation binding needed to derive `source_opened`. Keep V1 policies/events/citations/completions unchanged. Same-key frozen-policy comparison, claim fencing, append-only event sequencing, and atomic completion rules continue to apply.

Migration 0018 only widens the existing execution/completion JSONB checks enough to admit strict V2 while retaining V1 constraints, receipt/completion digest linkage, event and serialized-size ceilings. Downgrade refuses if any V2 execution or completion row exists; otherwise it restores the V1-only checks without dropping columns or rewriting V1 rows.

## Required verification

- Golden V1 serialization, digests, strict parsing, and persisted round-trip remain byte-for-byte unchanged.
- V2 fresh-service and PostgreSQL round-trips preserve execution policy, ordered reservations/results, and citation links.
- Wrong scope/revision/unadmitted anchors, forged source-opened claims, malformed outcome/content/line data, duplicate/read-after-unknown IDs, and each total budget overflow fail closed.
- Successful validated content derives source-opened; failed/no-content receipts derive false; partial/truncated status is not conflated with support sufficiency; raw source body never persists.
- Migration upgrade preserves existing V1 rows; downgrade is safe with only V1 data and refuses before changing schema when V2 data exists.
- Exact cumulative base-to-head diff and owning tests pass. No live source reads, provider calls, or live database writes.

## Acceptance

PR title: `APP-STATE: persist validated Plan Graph source-read receipts`. PRIME owns exact-head review and merge. The later SERVER adapter must consume this contract under a separate lease after RAKE settles.
