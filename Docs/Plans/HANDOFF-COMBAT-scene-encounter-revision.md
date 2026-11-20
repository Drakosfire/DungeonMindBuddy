# COMBAT — scene encounter and durable enemy revision

## Authority, topology and current state

The operator explicitly selected this next segment on2026-10-22 under PRIME's
active local Buddy goal. **ADOPTED DESIGN** in #1618, merge
`05a6fe0c95d68e337ce589677012bdb0e32da08c`, after Bugbot approved
`e24fdb038eea32f52b3a8dc2125ef055a2e90449` in cycle2. The design lease is released.
Slice A shipped #1619/#1620 with real manual armor/HP revisions and protected restart.
B shipped #1621, reviewed and running on5202 with selected-actor adoption, normal
tracker changes and protected restart/reopen. C is split into Plan templates then
Run-owned encounters under [the scene ownership contract](HANDOFF-COMBAT-scene-template.md).
C implementation and the full connected milestone remain unproven.
Base `df98f6a5a554ac7ef234b1196b4f8dd3377d178a` (#1617), existing
buddy-context-loop checkout, branch `codex/combat-connected-revision-design`.
Topology **serial**: this bounded design/reconciliation PR, then independently
useful implementation slices with exact activation/write leases. No new worktree,
environment, provider, external corpus publication or legacy runtime route.
Current remote/open-PR census has no competing implementation of this workflow.

Design write lease: this handoff, `../Roadmaps/ROADMAP-demo.md`,
`STEWARDS-HANDOFF-demo.md` current-pickup section and
`HANDOFF-AGENT-authored-excerpt-selection.md` predecessor settlement. No runtime
source edits in this design slice. Architecture critique from authorized chat `01a086f2-c457-7b10-b753-df6063cab1ce`,
turn `01a165f0-74e5-7b00-8e3e-ddff70c748d3`, is adopted below. Exact-head Bugbot
review precedes design adoption.

Live lease remains owned8000/5202, APP54331/native54330, persistent artifact root,
Core617635c and DMS7860 unchanged. #1617/APP0048 is deployed and healthy with
retained-data fingerprints. Its original-query and post-answer restart acceptance
remain pending; deployment alone is not a successful grounding witness.

## User outcome

Open a Plan scene containing a source-grounded encounter; open that encounter;
edit an enemy manually and save a new mechanics version; explicitly select that
version for this encounter; run it in Play; navigate/reload/restart and resume
the same scene, encounter, mechanics and recorded combat state.

First witness: Of Conks and Cons. Generality witness: A Wild Sheep Chase. Both
use ordinary product controls and the same implementation. No console/SQL/manual-ID
repair, hardcoded adventure paths or invented source mechanics. Difficulty is a
GM decision supported by visible mechanics; no automatic balance certification.

## Inspected gaps and preserved foundations

- Shared CombatRosterModule already mounts in Plan/Play; shared hosting and local
  recovery are not a durable scene↔encounter link.
- StatblockWorkbenchModule uses the shared StatblockDefinitionEditor, validation
  and first acceptance. MechanicsSavedAppendBoundary explicitly says subsequent
  edits remain working-copy only; saving another mechanics revision is unavailable.
- APP combat service rejects changing a saved actor's mechanics snapshot. Existing
  exact snapshot/reopen behavior is valuable; an explicit governed adoption command
  must replace the current remove/re-add workaround without mutating old revisions.
- Existing Combat stores independent tracker fields and exact resource snapshots;
  World associations and accepted assets have different proven ownership. Reuse
  them rather than conflating a World node, candidate, accepted revision and actor.
- Conks source publication and cited retrieval are retained, but its current minimal
  Plan/Run are not an already linked, encounter-ready adventure. Prepare real scene,
  enemy and branch content through ordinary authoring rather than count fixtures.

## Adopted lifecycle vocabulary

- **Editable copy:** recoverable user changes based on an exact saved revision;
  not accepted mechanics and not an encounter mutation.
- **Saved immutable revision:** producer-owned validated resource with exact base,
  identity, lineage and digest. Saving creates a successor; never edits the old bytes.
- **Buddy accepted mechanics reference:** explicit durable selection of a proven
  saved resource for this World-scoped product draft. Validation/Save may present
  one coherent user action while preserving separate durable outcomes/recovery.
  It is not World Graph publication or a World-node mechanics association.
- **Encounter adoption:** a separate explicit command selecting that exact version
  for specific actor IDs. Saving/accepting a revision does not update any fight.
- **World association:** existing optional, separately governed node→exact mechanics
  linkage. No automatic association replacement is included in this milestone.

Architecture recommends A first, followed by independent B and C. Before activating
A, pin exact producer append API, product accepted-reference history/selection and
stale-base/recovery contracts. Before B, resolve tracker reconciliation; before C,
resolve scene cardinality/template/session ownership. These are steward design
gates, not requests for another routine operator permission.

## Contract to resolve and adopt

1. **Manual revision.** Open the exact selected accepted resource in the shared
   Surface editor. Retain base identity/digest and a recoverable working copy;
   validate and save an immutable successor with explicit lineage. Cancellation
   and failed validation preserve the prior accepted version. Manual changes do
   not require AI generation/revision. Preserve unknown/protected mechanics fields.
2. **Producer ownership.** DMS owns generic immutable statblock resources/revisions;
   Buddy owns editing orchestration, durable draft/acceptance/recovery and encounter
   adoption. Inspect the current producer API before activation. If generic append
   behavior is missing, name and obtain that bounded owning contract. Never build
   a competing Buddy-only accepted mechanics store or import control-plane config.
3. **Explicit encounter adoption.** Select an exact saved successor; preview the
   change and affected actor(s)/copies; adopt only after explicit user action.
   Keep actor IDs, groups, active/next turn, initiative, conditions and notes.
   Do not silently reset or recalculate tracker HP/temp HP/AC from source values.
   Define deliberate reconciliation, including a lower new maximum, before coding.
   One edited enemy does not implicitly change every copy or another encounter.
4. **Scene identity.** Link under APP-owned document/scene/encounter boundaries.
   Resolve whether Plan prepares a template or selects a live fight, and which
   explicit action creates a session instance. Do not silently clone, resolve
   latest or rebind an existing Run after Plan edits. Run entry pins its accepted
   Plan/scene relationship and exact selected fight/mechanics identity. Session
   changes stay session-owned; source plans and other Runs remain intact.
5. **Same Surface interaction.** Entry, inspection, editing/review, Save/version
   selection and Combat use shared components/controllers across Plan and Play.
   The scene shows understandable encounter/enemy names and the chosen version;
   opaque IDs/digests/ledger details belong in inspection/Debug. Preserve scene
   position and pending drafts when opening/closing tools or switching views.
6. **Recovery and concurrency.** Use expected base versions, existing idempotent
   acceptance/replay and encounter CAS. Distinguish rejected, committed, unknown
   and conflicting outcomes; inspect/recover the original operation before resend.
   No duplicate version on retry, silent stale overwrite or automatic refresh.
   Late responses cannot target another World/scene/actor; recover across restart.
7. **Historical safety.** Prior immutable mechanics and saved fights reopen with
   their exact versions even when producer/Graph services are unavailable. New
   commands version their wire/storage contracts where necessary; preserve old
   readers without current-execution compatibility fallback or old-row rewriting.

## Proposed serial implementation boundaries

A. Durable manual accepted-mechanics successor and shared version history/editor.
B. Explicit exact-version adoption into an existing encounter actor with safe
   tracker reconciliation and unaffected siblings/other encounters.
C. Durable scene entry and Plan→Play ownership/continuity using the shared module.
D. Ordinary Conks rehearsal and Sheep generality; fix exposed transition defects
   at their owners in bounded slices, then perform protected restart acceptance.

These are sequencing proposals, not simultaneous dispatched leases. Architecture
critique may reorder them to establish a useful vertical slice earlier. Each
activation names exact base, files, tests, producer dependency, runtime/state lease,
review gates and settlement; no broad shared-schema write authority is implied.

## Acceptance of the next segment

- Ordinary Conks Plan: find the actual encounter from scene content, with named
  enemies/source support. No unrelated World encounter chooser as the sole entry.
- Edit one saved enemy's relevant abilities/actions/AC/HP through the shared editor;
  validate/save a new exact version; reload and reopen both old and new versions.
- Choose that version explicitly for the intended actor(s). Prove another copy,
  another encounter and the old version unchanged; reconcile tracker fields only
  through the stated user choice. Invalid/stale/foreign changes fail atomically.
- Enter Play from the saved Plan; open the intended encounter; run several turns,
  change HP/temp HP/conditions/notes, switch scenes/tools and return. Same actor,
  encounter and mechanics identities; no regeneration or implicit new fight.
- Reload and restart owned services; reopen the exact scene/fight/state/versions,
  including draft/unknown-outcome recovery and a conflict witness. Retain sources,
  World heads, original Plans, other Runs and accepted mechanics files.
- Repeat the connected flow with Sheep through the general implementation. This
  milestone advances J4–J6; full J1–J6 twice, original grounding/image consistency,
  external-recap memory,8GB measurements and operator acceptance remain open.

## Goal-state handling

The existing conversation goal remains active and incomplete. This contract
refines its next milestone under explicit operator steering; it does not mark
unmet objectives achieved or replace the goal with an easier acceptance boundary.
