# BUILD: canonical local Elderwyld

Status: ACTIVE. Operator explicitly authorized execution on 2026-10-28.

## Authority and invariant

PRIME owns this serial slice on `codex/elderwyld-consolidation`, based on
`da6fe2551e3af0b11b3d45cd75d9dc960c68bbe6`. Preserve original source bytes and
all unique dogfood writing (including drafts); use one live managed/native
identity `elderwyld` and one canonical source root. Derived Graph/import state
may be reset. Do not claim an empty Graph is completed reingestion.

Independent preimplementation critique accepted the supported Core empty adoption
experiment: truthful reset provenance, pristine canonical target, exact replay,
ordinary validated Buddy binding, separate vNext source admission proof.

## Exclusive write lease

- This handoff.
- `scripts/consolidate_elderwyld.py` and `tests/test_consolidate_elderwyld.py`.
- Established private evidence directory `~/.local/state/dungeonmindbuddy/runtime-evidence/elderwyld-consolidation-20261028`.
- Primary Buddy source/registry root and APP/native authority databases, only
  Elderwyld-selected state, after restored-clone proof and independent review.
- PRIME-owned restored rehearsal databases and extracted source/registry root.
- Owned API8000/UI5202 only as needed for protected delivery; no other service.

Other open ingestion and hosting lanes do not own these new script/test paths.
No Core contract changes; consume pinned Core adoption/initialization APIs.

## Execution and failure boundaries

Verify backups by actual restoration, source hashes, and current saved documents.
Refuse unexpected canonical authority, nonidentical file collisions, symlinks,
writer drift, and cross-World deletion. Preserve immutable history in the backup,
not by rewriting its identities. Keep exact operation inputs and a resumable
journal; a failure must not be described as success. Freeze live writers before
final inventory/apply and verify retained state after restarting.

## Gates

Provider-free collision/drift/replay tests; clone execution against actual
Postgres/Core authority; no changes outside selected namespace; same document
IDs and authored byte hashes; ordinary saved-page reopen; honest fresh Graph
and source-ingestion state. Inspect cumulative diff, independent exact-head
review and required CI, commit/push/open one PR. PRIME may merge under standing
operator authority. Live application follows reviewed script and clone evidence.
