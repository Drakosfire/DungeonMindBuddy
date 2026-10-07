# SERVER: exact recap session action correction V2

**Status:** ACTIVE, PRIME source execution authorized 2026-10-06 after ARCHITECTURE's versioned extension ruling.
**Base:** Buddy `origin/main@81dd3cd7744b953d083a5afec2bddef583835f47` (after #976 and #974).
**Branch:** `codex/recap-semantic-actions-v2`, isolated `/tmp/dmb-recap-semantic-actions-v2`.
**Topology:** serial, one independent source PR against main; no merge or runtime authority.
**Predecessor:** #976 merged `4599888d3cbcf7c28170d10ba03b6497837e1502`; V1 candidate correction and V1/V2 whole-child bases are established.

## Question and bounded contract

Can the existing recap semantic-candidate correction route accept an explicitly versioned request and manifest that replaces at most one exact `session_actions` entry, by node ID, tuple index, expected old text and replacement text, preserving order and all other entries? It must target the same node as any description replacement. The operation remains immutable, source/span/parent/child/manifest SHA bound, and held by default. Whole-child APP-STATE CAS and prepare/confirm sealing remain mandatory.

Version the new request and manifest distinctly from V1. Preserve the old route/request/manifest/basis behavior without reinterpretation. Use a distinct derivation and basis version that explicitly binds operation identity and manifest version; no generic patch format. A valid V2 request may have the session-action replacement alone or alongside at most one same-node description replacement and at most one edge omission. Every target is exact and stale values fail closed. No re-extraction, partial acceptance, migration, UI, provider, runtime, real S27 POST, semantic decision, or native publication.

## Exclusive write lease

- `apps/live_control_server/services/recap_semantic_candidate_correction.py` and focused tests.
- `apps/live_control_server/models/extract_promote.py`, `apps/live_control_server/routes/extract_promote.py`.
- `apps/live_control_server/services/recap_semantic_disposition.py`, `apps/live_control_server/services/extract_promote.py` only for V3 basis/confirm binding.
- `src/application_state/ingest/service.py`, repository only if genuinely needed; focused real PostgreSQL tests.
- This handoff, and backward-looking status settlement in `HANDOFF-SERVER-recap-semantic-candidate-correction.md`.

No shared runtime, ports, active databases, source artifacts, ignored S27 files, or external state. Disposable PostgreSQL test databases are permitted. Current open PR census #972/#970/#939/#927/#922/#917 and others shows no lease on these owner paths; #974 and #976 are merged.

## Stop conditions and evidence

Stop if this requires an arbitrary candidate patch, a second independent correction capability, changing the old V1/V2 meaning, a new table/migration, or writing outside the lease. Reject malformed schema, extra actions, missing/duplicate/stale target, wrong tuple index or expected text, cross-node replacement, no-op, parent/source/span/manifest drift, changed child bytes, lifecycle/scope drift, stale CAS and stale proposal/World head. The old literal and V1 candidate paths must still pass unchanged.

Prove deterministic replay, exact tuple-index edit and order preservation, immutable parent, default held, route/auth/body contract, real PostgreSQL V3 CAS plus V1/V2 parity, held/rejected prepare/confirm refusal and accepted exact binding, focused full-app HTTP tests with the repository-pinned Hermes preparation and `uv sync --locked`. Inspect cumulative exact base→head diff and update this handoff with source head/evidence. Source PR requires PRIME and APP-STATE independent review before merge.

**Acceptance token:** `SERVER_RECAP_SEMANTIC_ACTIONS_V2_SOURCE_READY`, pending exact-head reviews. No real S27 operation is implied.
