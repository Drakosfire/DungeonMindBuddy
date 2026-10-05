# HANDOFF — APP-STATE: typed World Agent turn provenance

- **Status:** SETTLED — PR #862 merged at `cfec63c6df9bd14aa7a1b5963266f926c729f8ab`; the implementation lease is released.
- **Owner:** APP-STATE task `01a0f569-ab17-7411-8473-00544e7842dc`.
- **Repository:** `Drakosfire/DungeonMindBuddy`.
- **Pinned base:** Buddy `main@ce03018d8da85a57be1bf4e4ecccf2b2bc7e8fff`.
- **Branch:** `codex/app-state-world-agent-provenance`.
- **Topology:** serial — this APP-STATE contract repair, then AGENT-INTERACTION
  runtime adoption, then DEMO's Plan action-dialogue projection and Plan
  consumer cutover under their separate handoffs.
- **PR title:** `APP-STATE: preserve typed Agent turn provenance`.
- **Verification:** isolated disposable APP-STATE PostgreSQL only. No shared
  database, provider, live product server, or runtime. APP-STATE does not
  reserve or manage the dedicated test port described below.
- **Design authority:** APP-STATE World conversation contract;
  `ARCHITECTURE-application-state-layer.md`; `DECISION-agent-context-compilation.md`;
  PRIME's 2026-10-02 provenance ruling.

The allowlist and verification requirements below are historical records of the completed #862 implementation, not an active write lease. The later #865 test-file overlap was separately authorized and released at merge `1c0320d18c53037308cd7412719fb3e2f0610d99`. No APP-STATE runtime or operator-database migration authority remains. Preserve the suspended agent-world-conversation-backend checkout. Any new Graph receipt work requires its own explicit bounded handoff.

## Mission

Extend APP-STATE's typed historical provenance so Agent turn receipts and
composer drafts can preserve the exact resolved surface instance and Content
revision basis without overloading the legacy `revision` string.

Add `surface_instance_id` to `TurnProvenance`. Add separate optional
`object_revision`, `work_revision_id` (UUID), and `revision_n` fields to
`HistoricalReference`. If any Content revision field is present, all three
must be present and valid and the existing `content_sha256` must contain the
full digest. The existing generic `revision` field and digest-only historical
references retain their current meanings. Absent surface/reference identities
cannot carry the new identity fields.

The type is shared by turn and draft provenance. Persist and round-trip the
new fields for primary, supporting, and selected references on both records.
The runtime consumer must supply exact values from its server-side resolvers;
APP-STATE never resolves client locators or current Content state itself.

## Current evidence and boundaries

- The current APP-STATE contract landed through Buddy #822/#827. Its
  `TurnProvenance.surface_id` cannot separately retain an instance, and its
  `HistoricalReference.revision` cannot separately retain Content's object
  revision, WorkRevision UUID, and revision number.
- The existing Plan resolver already returns the exact World, document,
  `object_revision`, `work_revision_id`, `revision_n`, and SHA-256. The #833
  Agent route consumes that resolver. `get_committed_playable_revision()`
  also projects `WorldOwnedCommittedRevisionV2`. This slice adds no Content
  capability and changes no consumer route.
- Re-anchored `origin/main` is
  `ce03018d8da85a57be1bf4e4ecccf2b2bc7e8fff`. The open-PR census found no
  APP-STATE provenance path overlap: #844/#843 are DEMO handoff-only; #826 is
  World-space binding; the other open PRs are unrelated. DEMO's #859/#860
  settled design-only Plan action-dialogue authority; its successor handoffs
  remain blocked behind the runtime and separate Plan projection.
- The runtime adoption lane is paused at its pinned activation commit `ee213e0a`.
  Do not edit its branch, runtime allowlist, or the preserved suspended
  `agent-world-conversation-backend` checkout.

## Exclusive write lease

Only these paths may change in this APP-STATE slice:

- `Docs/Plans/HANDOFF-APP-STATE-world-agent-conversation-provenance-v1.md`
- `src/application_state/agent_conversation/types.py`
- `src/application_state/agent_conversation/repository.py`
- `src/application_state/migrations/versions/20261002_0012_agent_conversation_typed_provenance.py`
- `tests/application_state/test_agent_conversation_service.py`
- `tests/application_state/test_agent_conversation_postgres.py`
- `tests/application_state/test_agent_conversation_provenance_migration.py`

Do not edit `service.py`, existing migrations, Content, Agent runtime/routes,
Plan/Play UI, provider policy, shared runtime state, or other files. If a
required path or contract exceeds this lease, stop and return the exact need to
PRIME before editing.

## Migration and compatibility contract

Migration `20261002_0012` follows `20261001_0011` and is additive. Add nullable
`surface_instance_id` columns to `agent.turn` and `agent.composer_draft`. Add
nullable Content revision columns to `agent.turn_reference` and
`agent.draft_reference`, and to the primary/selected reference columns on
`agent.composer_draft`. Constrain the typed tuple to be all-null or complete;
when complete, require positive revisions, a UUID WorkRevision ID, and the
existing full digest. Keep the old generic `revision` columns unchanged.

Old rows receive no inferred provenance: existing `surface_id`, generic
revision, and digest remain unchanged; new columns remain null when their
historical values are unknown. Do not infer an instance from a route, or
promote old revision strings/digests into Content revision IDs or numbers.
Legacy imports remain caller-supplied typed history and gain no ownership
inference.

Downgrade refuses while any new typed provenance value is present so rollback
cannot silently discard surface-instance or Content revision identity.

Fingerprint serialization must preserve the pre-0012 serialized shape exactly
by omitting **only** the newly introduced fields when they are null. Do not
omit all null fields. Non-null instance and Content revision values participate
in request, turn-idempotency, draft-source, and import fingerprints. This keeps
existing retries valid while making changed provenance conflict.

## Required owning-boundary evidence

**PRIME-owned test-resource lease:** PRIME owns container
`prime-app-state-provenance-pg-20261002`, PostgreSQL 16.15 at
`127.0.0.1:55460`, admin database `postgres`, with tmpfs data and no persistent
volume. APP-STATE may connect to this target for the scoped suite by setting
`DMB_APPLICATION_STATE_TEST_DATABASE_URL` to the approved test-admin DSN. The
existing fixture creates and drops uniquely named
`dungeonbuddy_app_state_test_*` databases. APP-STATE must not reserve, start,
or stop the port/container, and must not use shared port 54329 or durable port
54331. PRIME owns container shutdown/removal after the test receipt and review.
This exception leases only disposable test-database access; it does not lease a
runtime or product server.

The migration test must exercise a database at `20261001_0011` with existing
rows before upgrading to `20261002_0012`. At minimum, verify:

1. Strict model validation accepts a complete Content tuple and rejects partial
   tuples, missing digest, invalid UUID, nonpositive/bool revisions, and new
   identity fields on absent references/surfaces.
2. Turn receipt creation, ordered listing, and a fresh service instance
   round-trip surface instance and exact primary/supporting/selected Content
   provenance without storing content bytes.
3. Composer draft save/read round-trips the same typed fields, including
   supporting references.
4. Same-key/same-provenance retries replay; changed surface instance or any
   Content tuple value conflicts. Legacy null extensions preserve prior
   fingerprint shape; only new non-null values change it.
5. The 0011→0012 migration preserves prior turn/draft text, surface IDs,
   generic revisions, digests, status, ordering, and stored fingerprints;
   newly added fields remain null. Assert the single migration head is
   `20261002_0012`.
6. Run the focused APP-STATE service, PostgreSQL receipt, and migration tests
   against disposable PostgreSQL. Report skips and inherited failures exactly.

No provider/runtime test is part of this owner boundary. The later
AGENT-INTERACTION PR must prove that production resolvers populate these typed
fields before dispatch and that the originating turn retains the exact basis.
