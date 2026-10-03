# HANDOFF — APP-STATE: exact-basis Plan Ask projection

**Status:** BLOCKED — bounded implementation packet prepared; PRIME activation
and an exact write lease are required. No implementation, provider, database,
or runtime lease is active.

**Owner:** APP-STATE  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Preparation base:** `main@d5de2072f90c27b031f9f55157504915f98a189f`
(`#897` merged).  
**Topology:** one serial APP-STATE source-projection PR after the merged
AGENT-INTERACTION runtime code (#865) and Plan action projection (#897), before
the separate DEMO Plan conversation consumer. PRIME owns activation, path
transfer, review, and merge.

## Capability

Expose a read-only APP-STATE projection of the most recent completed, visible
Plan Ask user/assistant pairs for one verified World, the server-selected active
World conversation, one Plan document, and one exact committed-content basis.
This is an internal source projection for a later Plan boundary merge; it adds
no route or consumer wiring.

The exact basis is
`(world_id, document_id, object_revision, work_revision_id, revision_n,
content_sha256)`. The candidate caller must first verify the managed World and
resolve the current active World-owned Plan and committed Content revision at
their owning boundaries. APP-STATE accepts only a server-created typed basis;
it does not accept client-supplied basis fields or claim World/Content
authority. The APP service selects the active conversation through its own
World pointer. No active conversation returns an empty projection and does not
create one.

## Projection contract

- Select only `agent.turn` rows with `status = 'completed'`, nonempty visible
  `user_text` and `assistant_text`, resolved `surface_id = 'plan'`, and the
  active conversation for the verified World.
- Join the `primary` `agent.turn_reference`; require a resolved `kind = 'plan'`
  reference whose object ID, object revision, WorkRevision ID, revision number,
  and full content SHA match the complete basis. Require the turn World to
  match the basis World. Match every basis field; do not accept partial,
  unresolved, absent, supporting, selected, or stale references.
- Apply all eligibility predicates before the per-source cap. Select the most
  recent `1..6` eligible pairs, then return them oldest-to-newest. Preserve
  source-local metadata: `accepted_at`, turn `sequence`, and `turn_id` as the
  source record UUID. The future consumer merge orders by
  `(accepted_at, source rank [Ask=0, PlanAction=1], source sequence, source
  record UUID)` and applies its total-six cap after merging.
- Return a small typed projection containing only the visible user question,
  visible assistant answer, and the metadata above. Do not return complete
  `Turn` records, idempotency keys/fingerprints, failure data, provider state,
  graph/tool data, unrelated provenance, or hidden transcript fields. Preserve
  source surface metadata internally; do not treat `surface_instance_id` as a
  substitute for the Plan document or committed basis.
- Keep `AgentConversationService.list_turns` unchanged. It is chronological
  paging, not an exact-basis context read. Status/recovery rows, incomplete or
  failed turns, Compose/Revise actions, and browser history are not Ask pairs.

## Existing storage and schema decision

No new table or migration is currently needed. The landed conversation schema
already persists World/conversation identity, turn status/text/accepted time/
sequence/UUID, resolved surface identity, and typed primary references with
the complete Content basis. Implement the exact predicate as a dedicated
read-only repository query and return a purpose-built projection. Keep the
existing UoW and migration runner. Add an index only if an owning-boundary query
plan or measured fixture demonstrates a real need; return that requirement to
PRIME before expanding the lease.

## Candidate implementation allowlist — inactive until PRIME grants it

1. `src/application_state/agent_conversation/types.py` — validated basis and
   safe Ask-pair projection types.
2. `src/application_state/agent_conversation/repository.py` — dedicated query
   against existing turn/reference tables; eligibility filters before limit.
3. `src/application_state/agent_conversation/service.py` — read-only UoW
   boundary that validates the internal basis and resolves the active World
   conversation through APP-STATE.
4. `tests/application_state/test_agent_conversation_ask_projection_postgres.py`
   — new isolated owning-boundary test module, avoiding the preserved shared
   conversation test file.

No migration, schema, `unit_of_work.py`, migration environment/runner, Agent
route/runtime, Plan proposal route/service, UI, provider, Content/World
resolver, `list_turns`, or consumer context merger is in this packet's write
set. If implementation needs any additional path or changes the no-migration
decision, stop and return the exact need to PRIME before editing.

## Required owning-boundary evidence

Use only the repository's explicitly assigned disposable Application State
PostgreSQL fixture after activation; do not use shared runtime/database state.

- Prove exact completed Ask pairs are returned with all six basis fields
  matching. Seed more than six eligible pairs and confirm the newest six are
  returned in stable oldest-to-newest order with their original accepted time,
  sequence, and turn UUID.
- Seed newer completed Ask rows that differ one at a time by World, Plan
  document, object revision, WorkRevision ID, revision number, content digest,
  and surface; also seed accepted/running/failed rows. Confirm these are
  filtered before the eligible limit and cannot crowd older matching pairs out.
- Prove no active conversation yields an empty result without a write. Prove
  request/basis World mismatch fails closed. Confirm the projection contains
  only question, visible answer, accepted time, sequence, and source UUID.
- Prove equal accepted timestamps remain deterministic by source sequence and
  UUID. Leave source-rank tie handling and the merged six-pair cap to the
  future Plan boundary owning tests; do not implement or test that consumer
  here.
- Run this new PostgreSQL test module and relevant existing conversation
  service/type tests, plus Ruff and cumulative `git diff --check`. Report
  fixture limitations and inherited failures without broadening this slice.

## Re-anchor, collisions, and settlement

- Current remote `main` was compared through GitHub at exact commit
  `d5de2072f90c27b031f9f55157504915f98a189f`; it is the #897 merge. The
  existing cutover handoff
  `Docs/Plans/HANDOFF-DEMO-plan-world-conversation-cutover.md` still records
  the Plan action projection as design-only. PRIME/DEMO should truthfully
  reconcile that mutable predecessor state under the consuming handoff's
  authority; this packet does not edit the DEMO-owned handoff.
- The open-PR census found no APP-STATE conversation/projection PR. Open #886
  (Plan navigation shell), #887 (isolated prototype), #844 (Ingest handoff),
  #869, #826, #798, #781, #765, #764, #763, #761, and #760 have no path overlap
  with this candidate APP-STATE allowlist. Recheck PRs and active leases at
  activation.
- A preserved `codex/agent-world-conversation-backend` worktree has dirty Agent
  runtime/route files and `tests/application_state/test_agent_conversation_postgres.py`.
  Do not edit, transplant, clean, or remove that worktree. The dedicated new
  test path above avoids its dirty test file. Other historical APP conversation
  worktrees are clean; their existence is not an active lease.
- PR #897 is complete at merge `d5de2072f90c27b031f9f55157504915f98a189f`.
  Its Plan action source filters completed rows on the full same basis before
  its per-source cap and exposes stable `accepted_at`/`action_sequence`/action
  UUID metadata. This APP source must match that contract. The later DEMO
  consumer merges both sources and applies the total-six cap; this packet does
  not implement that consumer.

**Activation gate:** PRIME must confirm the exact base, open-PR/path census,
the current conversation/basis caller contract, the no-migration decision,
verification fixture ownership, and the four-path exclusive write lease. Until
then this handoff is design only.
