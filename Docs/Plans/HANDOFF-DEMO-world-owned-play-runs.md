# HANDOFF — DEMO: World-owned Play Runs

**Status:** DESIGN ACCEPTED — Phase A merged; Phase B ACTIVE; Phase C BLOCKED
**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Design base:** Buddy `main@f23d43d714b7aba68d940bbcb4cceb027f3c63e1`, including the merge of #805
**Topology:** Serial gates A → B → C, each with its own ACTIVE handoff and PR; A is merged, B is active, C is blocked. Generic Agent Run resolution and Play Agent UI follow as a separate successor.
**Architecture ruling:** ARCHITECTURE task `01a086f2-c457-7b10-b753-df6063cab1ce`, 2026-09-30, after the current PlayRun consumer audit

This design document records the Buddy-owned contract and three-gate serial
sequence. It is not an implementation allowlist. The active Phase B write
lease, base, branch, and verification commands are in the separate
[`HANDOFF-DEMO-world-play-run-v2-backend.md`](HANDOFF-DEMO-world-play-run-v2-backend.md).

## Design-review checkpoint

PRIME held initial PR #806 head `12821bc55dd7e2e2b2406665cdc59334f7c1021b`
for a revision, then passed the revised design at
`2656d90807fc8331943cd75faccda1e0ddc0fc23`. PRIME accepted the explicit
versioned response plan that preserves strict campaign V1 clients and the
three separately reviewable serial gates. Final reviewed head
`16974eee5f4904f907cdb4d57b170affa1107a15` merged as
`36deec27e8a963cdb75bdb67609e15547786b446`. Phase A Buddy PR #808 then merged
at `6c6a8ab48d568c2827fca4ce019d701beb473166`; its final evidence head
`ed09199b56206a0d3b7a6262380a1352ea567849` passed the five-suite PostgreSQL
owning-boundary witness (53 passed, 11 Pydantic `schema`-field shadow warnings,
35.18 seconds) on a separate PostgreSQL 16 tmpfs target. Phase A establishes
explicit World ownership on the exact World-owned Runbook revision; it does
not create Play Runs or change their storage.

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
3. Preserve the current strict campaign PlayRun V1 contract unchanged. It has
   the fixed `dmb_play_run_record_v1` discriminator and requires nonblank
   `campaign_id`; do not emit a World-owned V1 record or leak a tagged locator
   to a V1 client.
4. World-owned Runs use a separate, explicitly versioned V2 API family. Its
   record/list discriminators are V2, the response requires server-derived
   `world_id`, and it carries no Campaign identity. List, detail, create/replay,
   progress, rebase, and World Run reference-manifest operations use that same
   World-scoped family. The request's World scope is an expectation to verify
   against the exact pinned Runbook revision, not an authority source.
5. Phase B's reviewed storage strategy adds nullable `play.run.world_id`, makes
   `campaign_id` nullable, and enforces exactly one owner with a database check;
   a World index supports scoped list queries. Existing rows keep
   `world_id = NULL`, including rows where `campaign_id` happens to equal a
   World ID. No tagged locator, synthetic Campaign, or inferred backfill is
   allowed. The exact pinned Runbook revision remains canonical; stored
   `world_id` is only a checked list hint. Campaign V1 and default product
   continuity inventory remain campaign-only, and downgrade refuses while
   World-owned Run rows exist.
6. Existing campaign V1 endpoints and records retain their exact behavior.
   Campaign list queries must never surface a World-only Run because a real
   Campaign ID matches an internal locator. An unbound legacy Run has no World
   owner and remains on the campaign V1 path only where its existing campaign
   contract is valid.
7. A legacy Run becomes World-bound only when its exact pinned Runbook revision
   already has an explicit World binding. Never backfill ownership from
   `campaign_id == world_id`, even when the values match.
8. The separate generic Agent Run resolver and Play Agent UI require a later
   handoff. That resolver must validate the requested World, exact Run, pinned
   Runbook revision/SHA, sealed manifest, `run_revision`, and current Beat or
   Scene before a model call.

## Required serial implementation gates

These are three separately reviewable capabilities. This design handoff grants
no lease across them; PRIME activates each phase with its own `ACTIVE` handoff
and exact path allowlist. Merge and verify each predecessor before dispatching
the next.

### A — World-owned Runbook foundation

Add explicit `world_id` to a World-owned Runbook `WorkObject` and its committed
revision, and resolve that owner through the exact revision. Keep campaign
Runbooks unchanged. This phase does not create a Play Run, change the PlayRun
V1 record/storage, or migrate Play UI consumers.

The owning-boundary witness creates and commits a World-owned Runbook, reloads
its exact revision and verifies its World; rejects a foreign World or malformed
scope; and proves existing campaign Runbook create/read/commit behavior remains
unchanged. No Run may be started from the new World-owned Runbook in Phase A.

### B — World PlayRun backend V2

Add a separate explicit World-scoped route family, proposed as
`/api/live/world-play-runs/v2`. Do not change existing campaign
`/api/live/play-runs` V1 routes or responses. The V2 family covers list, detail,
create/replay, progress, rebase, and reference-manifest read/seal operations.
Proposed operations are `GET /api/live/world-play-runs/v2?world_id=W`,
`GET|PUT /api/live/world-play-runs/v2/{run_id}?world_id=W`,
`PUT /api/live/world-play-runs/v2/{run_id}/progress?world_id=W`,
`PUT /api/live/world-play-runs/v2/{run_id}/rebase?world_id=W`, and
`GET|PUT /api/live/world-play-runs/v2/{run_id}/reference-manifest?world_id=W`.
The World value is a requested scope to verify, never the owner proof.
Every PlayRun record/list response uses its own V2 discriminator and returns
the World resolved from the exact pinned Runbook revision. Define separate
literals such as `dmb_world_play_run_record_v2` and
`dmb_world_play_runs_list_v2`; the World record requires `world_id` and has no
`campaign_id`. Preserve the Run ID, artifact ID, playable revision, immutable
WorkRevision ID/SHA, independent `run_revision`, timestamps, and progress in
V2. A new Run requires a current, clean exact revision; same-ID/same-pin replay
of an existing Run verifies and returns that retained pin even if the source is
later discarded or advances. Reusing its ID with a different pin conflicts.
The reference
manifest retains its own schema and is read/sealed only through the World V2
family with exact Run/artifact/revision/SHA checks. Create verifies the
requested World against the exact Runbook revision; operations on an existing
Run verify its World against that Run's pin before they read or mutate state.
V1 endpoints remain campaign-only and cannot create or return World-owned Runs.

The V2 API shape does not prescribe PlayRun storage. Before enabling its
World-owned create path, the implementation must separately inspect every
storage reader and select a safe persistence/index strategy. A tagged internal
locator is usable only if the full storage consumer audit proves it is opaque;
otherwise use an explicitly reviewed storage migration. Neither option may
create a competing World authority or backfill by Campaign equality. Existing
campaign V1 behavior must be proven unchanged. The V2 route has no UI caller in
this phase; World Run creation remains unavailable through all unmigrated V1
consumers.

### C — Play surface migration and enablement

Migrate the audited Play surface, Start Run, resume/active selection, Runbook
label/projection, and Agent-context readers to the typed V2 `world_id`. Treat
the existing global active-Run pointer as a selection hint only and verify it
through the World-scoped V2 detail route before resume. Remove all World-owner
checks and labels that depend on `campaign_id`. Only after every World-scoped
reader uses the V2 owner may the Play UI create, list, open, and resume
World-owned Runs.

The owning witness runs the mounted Play flow from a managed World: create a
World-owned Runbook, start a Run, list/select it in that World, reload and
resume it, update progress, and rebase only to a same-World exact revision.
Repeat the campaign-backed path as a compatibility control. Cross-World
selection, a matching Campaign string, an unbound legacy Run, and a damaged pin
must fail closed. This phase does not add the generic Agent Run resolver or
Play conversation UI.

After C is merged and accepted at the owning boundary, create a separate serial
handoff for generic Agent Run resolution and Play Agent UI adoption. Its real
`POST /api/live/agent/turn` witness must resolve World A from the exact Runbook
pin, reject World B before the model call, reject unbound legacy Runs, and
report exact Run/run revision, artifact/playable revision, and current
Beat/Scene. It must never use the browser's published pointer or `campaign_id`
as authority.

## Current boundary and phase status

Phase A is merged. World-owned Runbooks now carry explicit `world_id` on their
WorkObject and committed revision, and the exact revision resolver verifies
that owner. Campaign Runbook behavior remains supported. This establishes the
Runbook owner contract only; PlayRun V1 still has campaign identity and its
storage has no World owner field on the Phase B base.

Phase B is ACTIVE under
[`HANDOFF-DEMO-world-play-run-v2-backend.md`](HANDOFF-DEMO-world-play-run-v2-backend.md),
from `main@6c6a8ab48d568c2827fca4ce019d701beb473166` on branch
`codex/demo-world-playruns-v2`. Its bounded capability is the V2 backend and
the reviewed nullable-owner migration described above. The campaign admission
path continues to reject World-owned Runbooks. The Play UI, global active-Run
selection, and Agent context remain campaign-bound until a later authorized
Phase C lease. Generic Agent Run resolution remains a separate successor.

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
  mutation. No migration assigns ownership to a legacy Run. Phase A may copy
  an already-explicit WorkObject owner onto that same object's committed
  revisions; it must never infer ownership from campaign_id. No live database
  or product runtime is part of this capability's test lane.

## Owning-boundary evidence

Each phase has its own owning-boundary witness above and a separate ACTIVE
implementation handoff. The tests for each gate must exercise that layer
directly; they are not one combined implementation PR or one helper-only proof.
Each ACTIVE handoff pins exact tests, inherited failures, and cumulative
base-to-head review.

Generic `POST /api/live/agent/turn` Run-resolution tests with a model/runtime
spy belong to the later Agent Run resolver handoff, not this owner-capability
slice. The later test must show World A success, World B rejection before the
model even when compatibility campaign strings match, unbound legacy Run
rejection, corrupted pin rejection, and a typed summary with exact World, Run,
`run_revision`, artifact, playable revision, and current Beat/Scene.

## Phase C and successor areas — not a write lease

Phase C must pin the exact Play surface, Runbook projection, and context
consumer paths after re-anchoring main and open PRs. The shared surface
publisher contract is not included by default. If typed World context cannot
reach a consumer without changing that contract, activation must add the exact
Buddy-owned path to its lease or keep that consumer unavailable until a later
authorized slice. Generic Agent route/resolver, providers, graph publication,
J3, external repositories, dependencies, and runtime state remain out of
scope for the current Phase B lease.

## Activation gate and handback

PRIME accepted the revised design at exact head
`16974eee5f4904f907cdb4d57b170affa1107a15`; #806 merged at
`36deec27e8a963cdb75bdb67609e15547786b446`. Phase A Buddy #808 merged at
`6c6a8ab48d568c2827fca4ce019d701beb473166` after its final evidence head
`ed09199b56206a0d3b7a6262380a1352ea567849` passed the PostgreSQL witness.

PRIME explicitly activated Phase B as one serial PR from that exact base on
`codex/demo-world-playruns-v2`. The ACTIVE handoff is
[`HANDOFF-DEMO-world-play-run-v2-backend.md`](HANDOFF-DEMO-world-play-run-v2-backend.md);
its 16 paths are the exclusive write lease. At activation PRIME refreshed the
open Buddy PR inventory (#798, #781, #760–#761, #763–#765) and found no overlap
with the lease; #763/#765 touch the shared route registry, so this lane adds
routes only to the already-registered `routes/play_runs.py`. The exact storage
consumer audit selected nullable `world_id` plus nullable `campaign_id`, an
exactly-one-owner check, a World index, no ownership backfill, campaign-only
default inventory, and downgrade refusal while World rows remain. The prior
Phase A PostgreSQL target was removed. PRIME designated a fresh disposable
PostgreSQL 16 tmpfs target for Phase B; the focused owner-boundary witness has
passed 75 tests there. Do not start a product database, server, provider, or
corpus for this slice.

The Phase B implementation and tests are committed at `40a8bbc9` on the
authorized branch. Phase C remains blocked until Phase B merges; its owning
witness now passes. Re-anchor main, open PRs, and active leases again before
each later phase.

After Phase C merges and passes its owner-boundary verification, create a
separate serial handoff for generic Agent Run resolution and Play Agent UI
adoption. That later slice
must prove a real `POST /api/live/agent/turn` response is derived from the
validated owner chain. Neither slice closes J1–J6, the rejected visual
acceptance gate, the governed J3 read-after-write path, or operator acceptance.
