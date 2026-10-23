# COMBAT — exact session capture and scene-owned live encounters

## ADOPTED bounded design authority

PRIME adopts this C2 design under the operator's connected preparation→Play→resume
objective. Base/live `5cdc29f77e87f16d03735a5d286944e96a65768e` (#1623), existing
buddy-context-loop checkout, branch `codex/combat-run-encounter-contract`.
Topology serial: one reviewed design PR, then one C2 implementation PR on a fresh
base and activated exact path lease. No new worktree, environment, producer or AI.
This design lease edits only this contract, the predecessor scene-template handoff,
ROADMAP-demo.md and the steward handoff's current pickup. The design shipped #1624, reviewed head08cd10bd7dcfd264e865a4575c97c72332180a59
in Bugbot cycle2, mergea894be2fb255c5fae5e89d6c9a31bd0f278ad901. Its design lease
is released. Runtime authority is the explicit activation below.
Fresh remote/open-PR census shows no competing C2 runtime lane.

Architecture assessment `01a1666f-fbde-7892-8034-2c42256bdf7e` in authorized chat
`01a086f2-c457-7b10-b753-df6063cab1ce` is adopted. It requires exact HP/reset
semantics, complete replayable Run intent including entry scene, and server-side
Run ownership rather than a UI-only link. The closures below resolve those gates.

## SETTLED C2 implementation lease

PRIME activates one serial implementation PR on
`a894be2fb255c5fae5e89d6c9a31bd0f278ad901`, branch
`codex/combat-run-scene-encounters`, existing buddy-context-loop checkout. Fresh
remote/open-PR census is clear of competing C2 work; reviewed design gates are
satisfied. Owned delivery: API8000/UI5202, APP54331/native54330; persistent source/
artifact root, Core617635c and DMSf95e retained. Additive APP0052 only. No new service,
provider, worktree or per-slice environment.

Exclusive expected write set: this handoff and ROADMAP-demo.md settlement;
new APP play/session_encounters.py and session_encounter_types.py, new
combat_encounters/access.py; play/service.py; combat_encounters/service.py,
repository.py,adoption.py,scene_templates.py; new migration20261022_0052;
server routes/play_runs.py,combat_scene_templates.py, new combat_run_encounters.py,
main.py; services/play_run_registry.py,play_run_reference_manifest.py,combat_encounters.py,combat_mechanics.py;
UI api/liveApi.ts, existing liveApi.test.ts, new liveApi.sessionEncounters.test.ts;
playSurface/startRunAttempt.ts and test,StartRunPanel.tsx and test,
PlaySurfacePage.tsx and test; planSurface/PlanSurfacePage.tsx and test;
combat/combatApi.ts,combatProjection.tsx and test,CombatMechanicsAdoption.tsx and test,
combatRecovery.ts and test, new runEncountersApi.ts,RunSceneEncounter.tsx and test,
WorldSessionPreparation.tsx and test, exactIntent.ts and test,
SceneEncounterLauncher.tsx; shared surface/modules/CombatRosterModule.tsx and test.
New owning HTTP/APP/concurrency tests/test_run_scene_encounters.py and
application_state/test_run_scene_encounters_postgres.py; current World creation
fixture helper tests/application_state/session_encounter_helpers.py and affected
existing test_world_play_runs_v2.py,test_rules_only_parent.py,test_agent_turn_route.py,test_agent_play_surface_context.py,application_state/
{test_play_active_run_postgres.py,test_play_runtime_world_runs_postgres.py,
test_native_play_graph_postgres.py,test_play_run_editions_postgres.py,
test_agent_conversation_postgres.py}, product_continuity/test_inventory_postgres.py.
Amend before any additional path edit. No historical migration, runtime source
outside this lease or standalone status PR.

## SETTLED rendered confirmation correction

C2 shipped #1625 after three Bugbot cycles, reviewed head
`7e0ec136d851a986aa034ae616f209e87c100eb2`, merge
`56b6ddd80378604fd4dd3cff7187597d7c312cd6`. API8000/UI5202 now serve that
merge on APP0052. Protected APP/native rows,79 mechanics files and17 frozen
components were preserved. Its implementation lease is released.

Ordinary UI rehearsal found the Plan session confirmation right-aligned to a
left-edge trigger, placing its Start button outside the viewport. PRIME activates
one serial correction PR on that merge, branch
`codex/combat-session-confirmation-placement`, existing checkout and runtime lease.
Exclusive write set: this handoff, ROADMAP-demo.md, shared
surfaceInteraction/contextHost/{SurfaceContextPrimitives.tsx,surfaceContext.css,
SurfaceContextPrimitives.test.tsx}. Fix viewport-aware below/beside alignment in
the shared component, independently review, merge, deploy and resume the ordinary
Plan→Play encounter/reload/restart witness. No session/data contract change.
Full adventure acceptance remains open. Amend before additional paths.

Correction #1626 shipped after one Bugbot cycle, reviewed
b0dca04f719493e13b7ae0b53d5f633febb925dd, merge
15b31ebc55038b664ae622ef5125b3230848aae6. UI5202 serves that merge; API remains
56b6ddd8/APP0052. Ordinary synthetic Plan confirmation became visible/clickable;
Run captured version4, created a distinct scene fight, saved HP/tempHP/condition/
note/active actor, navigated scenes and resumed the exact revision after reload
and protected API restart. Original Plan version4 stayed unchanged.1774 APP rows,
native rows,79 mechanics files and17 frozen components survived restart. Obsolete
runtime source/dist artifacts were pruned after consumer checks; active shared
Vite dependencies retained. Correction lease released. Real adventures/fullgoal
remain unproven; Conks revealed an independent discovery/answer-gap defect.

## C1 settlement and outcome

#1623 final reviewed head `baaf0163d1c383eed414e49c29b7789951753c4a`, two Bugbot
cycles, merged/live `5cdc29f77e87f16d03735a5d286944e96a65768e`, APP0051/native0017.
The C1 runtime lease is released. Ordinary synthetic retained Plan UI proved direct
scene creation, two independent actors, Document/Cards draft recovery, transactional
Save and exact mechanics adoption for one actor, four immutable versions and exact
revision4 reopen after protected API restart. Five prior fights,16 protected
content/agent/association tables,79 product files and17 frozen components stayed
unchanged. All1769 post-witness APP rows and native rows survived restart. The broad
Plan suite retains the same50 failures independently reproduced on base/current;
new C1 entry,55 transport/mounted UI and51 author backend tests passed.

C2 must now take the exact prepared choices into a new session and create a separate
live encounter only when the GM explicitly starts it. Merely hosting Combat in Play,
or resolving the current Plan template when a fight is first opened, is insufficient.
Conks first/Sheep generality and full goal acceptance remain open.

## 1. Complete session-start intent

- Replace the current World Run creation wire body with a closed versioned contract,
  `dmb_world_session_create_v1`. Require the source artifact UUID, committed revision,
  WorkRevision UUID and SHA; selected entry scene ID or explicit null; and one entry
  for **every** scene in the canonical v2 manifest. Each entry explicitly selects
  no template, or its exact bound template encounter UUID/revision/digest. Reject
  duplicate, omitted, extra, foreign or stale selections. Historical Run readers
  remain; the old World creation body is rejected, not inferred or upgraded.
- Source can be a current clean active World Plan or Runbook. Templates belong only
  to Plans; Runbook scene entries explicitly select none. Fresh World execution uses
  canonical v2 structure. Preserve historical v1 readers without a new v1 creation
  fallback. Update affected current creation tests/fixtures to this contract.
- A read-only preparation preview admits the exact source and returns scene names,
  encounter/enemy names, saved versions/digests and explicit absence. Orphaned Plan
  template links are identified as excluded; never matched by title or position.
  Capturing an available encounter does not start combat or mark a branch played.
- The GM confirms the displayed choices and entry scene. Extend the existing World
  Start Run controller/attempt rather than create a second retry writer. Plan can
  mount that shared confirmation in its existing Surface host, retaining its editor,
  drafts and scene cursor; after successful creation navigate by returned Run UUID.
  No selection map in a URL. Recheck the mounted Plan's clean/current state at entry
  and confirmation; source changes invalidate confirmation without losing its work.
- The selected scene must be in the pinned manifest. Initialize current_scene_id to
  that scene and current_beat_id to its actual parent Beat, even if it is not the
  opening Beat. If scenes exist, null is rejected; the GM must confirm a valid
  scene. When the source has no scenes, explicit null seeds only the authored
  opening Beat. Entry selection does not create played facts or completed scenes.
- Persist the exact complete request and canonical scope/body digest with the Run,
  manifest and immutable per-scene choices in **one APP transaction**. A separate
  immutable preparation/creation receipt can retain the existing Run record schema.
  Return a versioned outcome containing its receipt and current Run/manifest. Expose
  the same saved preparation through a dedicated read contract after reload.
- Serialize by global Run UUID before replay and source admission. Lock the source
  WorkObject as existing admission/C1 creation does, then existing template encounter
  heads in deterministic order using locks that conflict with Save/adoption. Confirm
  all selected heads and exact snapshots before committing. C1 creation after a
  confirmed no-template selection must serialize on that same source lock.
  A winning later template save cannot alter a captured Run; a winning earlier save
  makes stale confirmation conflict. No external IO inside the transaction.
- Same Run UUID and full body replays the captured receipt before current source
  checks, even after Plan/template advancement. Changed scene/selection/body/World
  conflicts. Return current Run state explicitly; never restore initial progress.
  Retain the exact pending body/key before the first mutation across tool close,
  reload and restart. Unknown response recovery inspects the creation receipt, not
  only an existing Run with a matching Plan pin. Never rebuild from a new preview.
- Cancellation shares the Run-operation lock and exact digest: return applied if
  creation committed, otherwise persist a cancellation fence before releasing UI
  intent. Late requests cannot commit afterward. Missing GET never unlocks intent.
  Since current APP creation seals the manifest atomically, remove the obsolete
  World create→separate seal write/retry pathway; Campaign behavior is a distinct
  owner contract. This also removes a redundant request from the current World flow.

## 2. Explicit live encounter initialization

Play shows the current scene's sealed preparation and an explicit Start encounter
preview. After materialization it shows Open encounter and the bound fight's name.
Older Runs without captured preparation show honest absence and a route back to
Plan/new-session preparation; never select a current/latest/global template.

Initialization policy `dmb_fresh_scene_encounter_v1` is explicit and versioned:

| Field | New session value |
|---|---|
| Encounter and actor IDs | Fresh UUIDs; never reuse a template or another Run's actor IDs |
| Name, team, order, initiative, AC, maximum HP, tags, statblock/source identity, exact mechanics | Preserve exact prepared values |
| Current HP with typed integer maximum >=0 | Set to that maximum; show the before/after per actor, including healing |
| Current HP with string or null maximum | Preserve current HP exactly; strings remain descriptive even if they look numeric; explain no typed maximum was available |
| Negative typed integer maximum | Refuse materialization; require an explicit preparation revision, never clamp silently |
| Temp HP, conditions, defeated | Set0, empty list, false, with those resets shown explicitly |
| Round/current actor/round-start actor | Round1, null, null |
| Actor notes | Preserve preparation notes; they are not played facts |
| Groups | Preserve grouping/labels/configuration and remap every member to its new actor ID |
| Encounter event provenance | Do not copy old encounter-event claims into a new fight; preserve them in the immutable template origin instead |

Only actual integers count as typed maxima (not booleans or coerced strings).
Zero is accepted and shown as HP0 with defeated=false; GM controls remain explicit.
Retain source/template version and a complete old→new actor map in the materialization
receipt, so no dangling source actor references are carried into the live encounter.
Actor-level source evidence remains intact; original event history is not rewritten.
Do not copy old turn pointers. Validate the complete resulting draft against existing
limits before committing; refusal rolls back the binding/receipt/encounter together.
No new limits, resource generation, balancing claim or World association update.

- Materialization request binds an operation UUID, exact World/Run/scene, sealed
  preparation digest, template pin, initialization policy and preview digest. It
  carries no caller-supplied actor resource. Derive from the verified immutable
  template snapshot, not mutable Plan state, Graph head or producer latest.
- One live encounter per `(World, Run, scene)` and unique encounter ownership.
  Same-key retry returns that same instance/current state; changed intent conflicts.
  Different-key concurrent starts cannot bind duplicates. Binding, fresh fight and
  metadata receipt commit atomically. Cancellation is a terminal same-lock fence,
  with applied meaning committed rather than rolled back. Retain exact intent before
  dispatch, validate receipts, and fence late responses by scope/generation.
- Preview and historical reopening need no producer/Graph request for mechanics.
  Reuse returned bound records when mounting shared Combat; avoid an immediate
  duplicate encounter GET. A dirty/recoverable draft cannot be silently replaced by
  a refresh or another scene. Original encounter recovery remains World/encounter
  scoped; globally fresh IDs make the Run binding unambiguous. Scoped Plan/Play
  recovery must not overwrite the standalone World chooser selection key. The
  current recovery open helper writes that key unconditionally; separate selection
  remembrance from draft ownership as part of the shared scoped-host integration.

## 3. Server ownership, lifecycle and shared Surface

- Add APP-owned immutable Run-preparation and creation/cancellation records plus
  Run/scene encounter bindings/materialization receipts in additive migration(s).
  Foreign keys/uniqueness and service validation bind World/Run/scene/encounter and
  exact source pins. No historical-row rewrite or default new selection for old Runs.
- Generic World encounter lists exclude session-owned instances. Generic World GET,
  Save, generated-add, adoption, adoption cancellation and receipt inspection reject
  Run-owned encounters, including replay responses. Do not guard only the UI or
  only new actor insertion. Read-only World mechanics catalogs/previews stay reusable.
- Run-scoped commands verify the complete World/Run/scene/encounter binding at APP
  authority before reading or mutating the fight. Extend the existing Save/adoption
  orchestration with an explicit typed Run scope; reuse existing exact-source proof,
  CAS, snapshot-preservation and recovery logic. No copied alternative combat writer.
- Scoped mutations lock Run before operation/encounter; generic World routes reject
  a Run binding without acquiring that Run's lock, preventing inverse lock order.
  Preserve scene progress/notes while saving a fight; do not rewrite Run progress
  merely because combat advances. Another Run, template and World association stay
  unchanged. No implicit fight reuse across scenes or sessions.
- Require active, non-trashed and playing Run state for new materialization and fight
  mutations. Latest session review status ended requires explicit Reopen session.
  Reuse the Run lock shared by review/Trash so closing or trashing serializes with
  mutations. Read/recovery inspection and cancellation may verify retained bindings
  in ended/trashed state, without resuming play or rolling back applied commands.
- Rebase refuses whenever the immutable preparation/creation receipt exists, even
  a zero-scene capture with an empty selection set, or scene encounters exist. It
  also refuses explicit no-template selections, until an explicit reconciliation
  design is selected. Trash retains all preparation/fight/history; restore/reopen recovers
  the same identities. Run editions with unchanged scene markers keep their binding.
- Plan and Play use the same scene-level encounter launcher, scoped projection host,
  CombatRosterModule, manual editor, version adoption and recovery. Keep authored
  content mounted; display meaningful names, hiding opaque receipt metadata in
  inspection/Debug. Preserve Document/Cards scene position and source/session drafts.

## Implementation activation and acceptance gates

C2 runtime is BLOCKED on exact-head design approval and a fresh lane activation.
The implementation lease must enumerate actual paths before edits: APP Play create/
rebase/review access boundaries and new Run encounter types/service/repository/
migration; shared Combat get/save/adoption/replay access gates; server Run creation
and scoped Combat routes/orchestration; authenticated transport classification;
World Start Run controller/panel/pending recovery and tests; Plan start/Play current
scene entry; shared projection/Combat API scope; affected current creation fixtures.
No DMS/Core, hosted, rules graph, unrelated publication or new automation.

Owning-boundary tests must prove: complete null/template selections; foreign/stale
source and template refusal; selected later scene/parent Beat; lock-order and both
Plan/template race orders; exact replay after source advances; changed-body conflict;
create/materialization cancellation wins/loses; rollback/unknown response; typed,
descriptive/zero/negative HP behavior and explicit resets; fresh/remapped IDs and
provenance; legacy World creation rejection with historical readers preserved;
all generic World encounter mutation/read bypasses refused; source/other Run state
unchanged; ended/trashed mutation holds, cancellation recovery and restore; rebase
hold; no duplicate seal/read request. Mounted tests cover explicit confirmations,
durable exact pending recovery, late/foreign response fences, draft/scene continuity.

Independent Bugbot review, owner tests and typecheck/build precede PRIME merge and
protected5202 delivery. Ordinary UI must take the retained prepared scene into Play,
start its exact separate encounter, change turns/HP/temp/conditions/notes, navigate,
reload/restart and resume; edit preparation afterward and prove the Run unchanged.
Then execute real source-grounded Conks first and Sheep generality, with no console/
SQL/manual-ID repair. Full J1–J6 twice, grounding→image latency/quality, external
recap/supplements,8GB/proxy measurement and operator acceptance remain open.
