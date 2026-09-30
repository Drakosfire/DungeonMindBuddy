# HANDOFF — DEMO: World-owned Play Runs

**Status:** BLOCKED — bounded contract is designed; no implementation lease
**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Pinned base:** Buddy `main@f23d43d714b7aba68d940bbcb4cceb027f3c63e1`, including the merge of #805
**Topology:** Serial DEMO successor to #805; this owner contract precedes generic Agent Run resolution and Play Agent UI adoption
**Architecture ruling:** ARCHITECTURE task `01a086f2-c457-7b10-b753-df6063cab1ce`, 2026-09-30, after the current PlayRun consumer audit

This document records a concrete Buddy-owned product contract and its unresolved
activation gate. It grants no code write lease. Do not begin implementation
until PRIME accepts the boundary and activates a new `ACTIVE` handoff with the
exact path allowlist, base, verification commands, and PR topology.

## User transition and capability

A GM should be able to prepare a Runbook for a selected World, start a Play Run
from that Runbook, and list, open, and resume the Run in the same World. The
Run's owner must remain correct through its exact pinned Runbook artifact,
revision, and content digest. This is a prerequisite to truthful Play Agent
context on the fresh-World journey; it does not itself implement a generic
Agent Run turn or a Play conversation UI.

The current Play model is campaign-shaped. Reusing a World ID as a campaign ID,
inventing a Campaign, or trusting matching strings would create false owner
authority. The World owner must be explicit on the World-owned Runbook and
resolved from the Run's exact pinned Runbook revision.

## Accepted owner contract

ARCHITECTURE's ruling after the consumer audit establishes these decisions:

1. A World-owned Runbook has an explicit canonical `world_id` on its
   `WorkObject` and committed revision. Do not infer it from `campaign_id`.
2. A Play Run pins one exact Runbook artifact, committed revision, and content
   SHA. The server derives the Run's World from that exact pinned revision; do
   not add a separately mutable Run owner or trust browser pointers.
3. A PlayRun list/detail response exposes a typed, server-derived
   `world_id: string | null`. A new response schema version may be needed to
   preserve strict V1 consumers. The proposed World-owned response reports no
   `campaign_id`; the internal locator is not exposed as a Campaign. A
   campaign-backed Run retains its current Campaign value, and an unbound
   legacy Run resolves to `world_id=null`.
4. The persisted V1 `campaign_id` column may use a reserved locator such as
   `world:<world_id>` only as opaque compatibility storage after every reader
   has been migrated. It is never owner evidence, a Campaign lookup key, or a
   substitute for the typed resolved `world_id`. Campaign list queries must
   never surface a World-only Run just because a real Campaign ID matches the
   locator. Do not expose the locator as a Campaign label.
5. A legacy Run becomes World-bound only when its exact pinned Runbook revision
   already has an explicit World binding. Never backfill ownership from
   `campaign_id == world_id`, even when the values match.
6. The separate generic Agent Run resolver and Play Agent UI require a later
   handoff. That resolver must validate the requested World, exact Run, pinned
   Runbook revision/SHA, sealed manifest, `run_revision`, and current Beat or
   Scene before a model call.

## Current boundary and why activation is blocked

The current code on the pinned base does not implement that contract:

- `WorkObject.validate_scope` currently permits `world_id` only for Plan.
- Runbook creation is campaign-only, and the committed playable-revision path
  has World ownership handling only for Plan.
- PlayRun V1 requires nonblank `campaign_id`; its row has no World field.
- Run creation copies the Runbook's `campaign_id`; rebase checks equality with
  that field.
- `GET /play-runs` filters by `campaign_id`, and the UI uses the selected World
  ID as that Campaign value.
- Play UI and context code compare or publish `campaign_id` as if it named the
  World: `PlaySurfacePage`, `StartRunPanel`, `playSurfaceAgentContext`, and
  `RunbookTableDeck`. `nativeRunbookProjection` copies the committed
  `campaign_id`; the separate `agent_play_surface_context` also requires a
  Campaign match.
- Generic `routes/agent.py::_work_resolver` still supports `kind="plan"` only;
  a Run turn fails with `work_kind_unresolved`. The A7 Play context resolver is
  separate and does not establish World ownership for generic Agent turns.

The tagged-locator condition is therefore false today. All listed consumers
must migrate to the typed resolved owner in the same owner-capability lane, or
World-owned Run creation must stay unavailable to any consumer that cannot
resolve it safely. The schema versioning and exact code write set still need
PRIME's activation review; this BLOCKED handoff is not an implementation path
allowlist.

## Invariants and failure cases

- A Runbook committed under World A starts a Run whose response reports
  `world_id=A`, derived from the Run's exact artifact/revision/SHA pin.
- A World B list or detail request cannot admit the World A Run, even if a
  legacy Campaign ID, locator, URL, or browser context happens to match.
- Rebase may advance to a new committed revision only when that exact revision
  remains owned by the same explicit World and its manifest/digest bindings
  verify. A mismatched artifact, revision, SHA, or manifest fails closed.
- Runbook listing, Start Run admission, Play surface filtering/resume, labels,
  rebase, and Play context publication use the server-resolved typed owner.
  No UI guard treats `campaign_id` equality as authorization.
- Existing campaign Runs continue to list, open, resume, and rebase under their
  current campaign contract. World-only Runs do not appear as a Campaign.
- Legacy Runs without an explicitly World-owned pinned Runbook remain unbound;
  a matching campaign string does not repair or authorize them.
- A failed owner or pin check returns a typed failure before any dependent
  mutation. No migration edits existing ownership, and no live database or
  product runtime is part of this capability's test lane.

## Owning-boundary evidence required after activation

The activated implementation must prove the real Buddy WorkObject/committed
revision → Run create/list/detail/rebase path, not only a helper projection:

1. Create and commit a World-owned Runbook; start a Run; reload list and detail.
   The response reports the World derived from the exact pinned revision and
   preserves artifact ID, playable revision/SHA, and independent `run_revision`.
2. Attempt list/detail under World B and with a Campaign whose ID resembles the
   legacy locator; neither admits World A's Run. The successful World A path
   does not depend on a Campaign record.
3. Exercise every audited consumer: World filtering and selected-Run admission,
   resume, Start Run, context publication, Runbook labeling, native projection,
   rebase, and `agent_play_surface_context`. None exposes or treats the locator
   as authority.
4. Preserve campaign-backed Run behavior. A legacy Run with no explicit World
   binding has `world_id=null`; an exact pinned Runbook revision with a real
   World binding resolves only to that World. Corrupt pins and manifests fail
   closed.
5. Run focused backend/API and mounted Play tests, the relevant compatibility
   suites, UI typecheck, and cumulative base-to-head diff review. Record
   inherited failures without expanding the slice.

Generic `POST /api/live/agent/turn` Run-resolution tests with a model/runtime
spy belong to the later Agent Run resolver handoff, not this owner-capability
slice. The later test must show World A success, World B rejection before the
model even when compatibility campaign strings match, unbound legacy Run
rejection, corrupted pin rejection, and a typed summary with exact World, Run,
`run_revision`, artifact, playable revision, and current Beat/Scene.

## Candidate areas to recheck at activation — not a write lease

The contract likely touches World-scoped content types and committed revision
resolution, Runbook creation, PlayRun service/registry/routes, API response and
query types, Play surface/runbook/context consumers, migrations, and their
owning tests. PRIME must pin the exact expected paths after inspecting current
main and open PRs. The shared surface publisher contract is not included by
default. If typed World context cannot reach a consumer without changing that
contract, activation must add the exact Buddy-owned path to the write lease or
keep that consumer unavailable for World-owned Runs until a later authorized
slice. Generic Agent route/resolver, providers, graph publication, J3, external
repositories, dependencies, and runtime state remain out of scope.

## Activation gate and handback

Before implementation, PRIME must explicitly accept or revise this proposed
capability, settle whether its strict response compatibility requires a V2
PlayRun response, and activate an `ACTIVE` handoff with one exact serial path
lease. Re-anchor Buddy main and all open PRs at activation; the 2026-09-30
inventory (#798, #781, #760–#761, #763–#765) is only a snapshot. Confirm the
World-owned Runbook contract remains Buddy-owned and does not require a new
DungeonMind or WorldKeeper authority. Do not start a database, server, provider,
or corpus for this slice.

After merge and owner-boundary verification, create a separate serial handoff
for generic Agent Run resolution and Play Agent UI adoption. That later slice
must prove a real `POST /api/live/agent/turn` response is derived from the
validated owner chain. Neither slice closes J1–J6, the rejected visual
acceptance gate, the governed J3 read-after-write path, or operator acceptance.
