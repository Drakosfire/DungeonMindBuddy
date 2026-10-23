# COMBAT — scene templates and session encounter ownership

## Authority and serial topology

**ACTIVE design lease**, adopted for exact-head Bugbot review under the operator's
scene→encounter→manual revision→explicit adoption→Play→resume objective. PRIME
owns design, implementation, review coordination, merge and local delivery.
Base `0cea62670164ded25646d0686693022b851ad220` (#1621), existing
buddy-context-loop checkout, branch `codex/combat-scene-template-contract`.
One design PR, then serial C1 and C2 implementation PRs. No new worktree or runtime.
This design PR edits only this contract, the predecessor scene/revision and adoption
handoffs, ROADMAP-demo.md and the steward handoff's current-pickup section.
Runtime writes remain **BLOCKED** until this contract passes independent review;
its adoption does not itself claim implementation or activate overlapping leases.
Fresh remote/open-PR census found no competing scene-template runtime work. Older
#1367 is C0 rendered-adoption design, not this scene ownership implementation.

Architecture assessment `01a16645-01a1-7911-a423-55ad615ceb2e` in authorized chat
`01a086f2-c457-7b10-b753-df6063cab1ce` is adopted: Plan template first, then Run
instance; stable scene IDs; exact pins; fresh session actor IDs; one encounter per
scene; no global-selection fallback. The closures below define the remaining
version-history, capture, race and recovery boundaries before implementation.

## Settled predecessor; remaining outcome

#1621 reviewed head `6bd4641aae344f670d7ae0d335eb19f9b21f2c85`, one Bugbot
cycle, merged/live `0cea62670164ded25646d0686693022b851ad220`, APP0050.
The ordinary synthetic retained encounter adopted the saved AC16/HP28 successor
for one actor, preserving current HP10/temp7/Prone/note; its sibling stayed unchanged.
Normal turns then saved first HP12 and second HP11/current. Reload after protected
API restart reopened that exact revision4. Other encounters, associations, revision
proofs and agent turns stayed unchanged. This proves B's bounded adoption/recovery,
not Conks/Sheep, scene ownership or full journey acceptance.

C must make the scene the entry into its encounter while preserving Plan drafts,
scene position, exact mechanics and session isolation. No AI is needed to create,
edit, save, select or materialize a prepared encounter. Existing shared Combat
editing, source verification, adoption and recovery remain the owning mechanisms.

## Product and identity contract

1. A saved World Plan scene has **zero or one encounter template**. Its identity
   is `(World, Plan WorkObject UUID, stable scene marker ID)`, never title, deck
   index, the currently selected World encounter or a browser storage key.
2. Preparing a template creates a distinct editable combat workspace bound to that
   scene. Display its encounter/enemy names and an explicit “Prepare encounter” /
   “Open encounter” action beside the scene. The shared Combat Surface opens it
   directly; no unrelated encounter chooser is inserted into this scoped mode.
   Standalone Combat retains its ordinary World encounter controls.
3. An encounter template is preparation, not a running fight. Its mutable workspace
   retains existing encounter CAS, actor editing, exact mechanics and local draft
   recovery. Each successful persisted revision also has an immutable, digest-checked
   template snapshot. Saving mechanics remains separate from adopting it into actors.
4. Template history stores the full self-contained encounter record at each exact
   encounter revision, including ruleset, exact mechanics and actor/group identity.
   A unique `(template encounter ID, revision)` and canonical payload digest prevent
   substitution. Snapshots are inserted in the same APP transaction as creation or
   CAS/adoption; failure rolls back both. All existing encounter writers converge
   on repository insert/CAS, the integration boundary to verify. No history-only
   background job, latest-resource fetch or producer call is needed to reopen one.
5. The Plan link records its admitted committed Plan WorkRevision/revision/SHA at
   creation. This is origin evidence, not a claim that future Plan revisions contain
   identical prose. Later template versions retain that origin and their own digest.
   Plan prose and template editing stay separate writers; neither rewrites the other.
6. Scene prose can change while retaining its marker. Renamed/deleted scene markers
   leave the old binding/history intact but orphaned; never title-match or silently
   rebind. Ordinary entry checks the current manifest and explains missing scenes.
   C1 supplies no reassignment/deletion command. Plan Trash retains the template.
7. Multiple encounter slots and one live encounter reused by multiple scenes are
   deferred. Existing standalone fights are not silently converted into templates.
   Cloning/linking an existing standalone fight needs a separately explicit command.

## C1 — Plan template preparation

The independently useful first implementation creates, opens, edits, revises and
reopens the scene's prepared encounter through shared Combat, before starting Play.

- Add APP-owned scene-template binding and immutable version tables in a new additive
  migration. Bindings are unique by World/document/scene and template encounter ID;
  database foreign keys and service checks prevent cross-World/document substitution.
  Existing fights remain untouched; no historical-row migration or fallback.
- Creation admits the exact **current, clean, active World Plan** through existing
  content admission and canonical v2 manifest derivation. Reject wrong kind/World,
  stale revision/work-revision/SHA, dirty source, missing/ambiguous scene or invalid
  marker. Create the binding, empty combat record and first immutable snapshot in
  one APP unit of work. Serialize on the admitted WorkObject and binding identity.
- The caller supplies a retained creation intent containing exact source pin, scene,
  title/ruleset and operation UUID. Repeated identical intent returns the same
  binding; changed body under the same key conflicts. Concurrent different keys
  targeting one scene conflict instead of returning an unrelated actor workspace.
  Persist a metadata receipt atomically with creation; uncertain responses inspect
  that exact receipt before repost. Receipt replay precedes current-source checks.
- Scoped GET returns the binding, current template record and immutable-version
  metadata after World/document/scene checks; history/exact-version reads verify
  canonical digests and stay independent of producer/Graph availability. Read
  identity never falls back to localStorage, another World or the newest fight.
- Save and explicit mechanics adoption continue using existing validated combat
  commands. Extend their shared repository boundary to append template snapshots
  only for bound templates; ordinary fights do not acquire duplicate histories.
  An open template can retain/save encounter work if its scene later disappears;
  its history remains recoverable, but it cannot be newly materialized from an
  absent scene. Saving never changes the link or another source document.
- Plan scene entry uses current navigation identity and saved basis. Disable Create
  while Plan edits/save/recovery are pending; explain Save is needed. Opening an
  existing template does not discard those drafts. Mount through the existing
  Surface projection host with scoped context and generation fences. Keep the Plan
  editor mounted, scene position intact and Combat's recovery ownership unchanged.
- Scoped Combat hides World chooser/create controls and opens the supplied bound
  encounter. Changing World/document/scene cannot apply a late response to the new
  scope. Recoverable drafts and unknown operations remain attached to their original
  encounter and browser writer; no automatic discard or duplicate creation.

C1's implementation lease will be activated on a fresh exact base after design
review. Expected paths: new APP combat scene-template types/service/repository and
additive migration; combat encounter repository snapshot integration; new server
scene-template routes/service with existing router registration; UI combat API/types,
new scene-encounter entry/controller and tests, shared CombatRosterModule scoped
host props, combatProjection, PlanSurfacePage; owning HTTP/APP/concurrency/migration
and mounted UI tests. Existing recovery schema/generator may change only if a DTO
actually changes. No DMS/Core, World publication, Run creation or rebase edits in C1.
Amend the activated allowlist before any newly required path is edited.

## C2 — exact Run capture and session materialization

C2 stays BLOCKED on reviewed/merged C1 and a fresh activated runtime lease. C1 alone
does not close the requested connected workflow. C2 must deliver all of these:

- Explicit Start Play shows the prepared encounters being taken into the session.
  Its versioned request carries the exact Plan pin and selected template revision /
  digest per stable scene. Under a shared APP transaction, admit the Plan, validate
  each selected scene and immutable template revision, require its current saved
  head to match the confirmed selection, and seal those selections with the Run.
  A concurrent template or Plan save conflicts; never silently choose latest.
- Run creation captures the selected template revisions even if combat is not opened
  yet. Later Plan/template edits cannot change what that Run can materialize. Store
  Run selections as immutable APP-owned pins, not mutable Plan links or client state.
- Explicit “Start encounter” creates one fresh Run-owned combat encounter for the
  selected scene from its sealed snapshot. Assign fresh encounter and actor IDs;
  remap groups, turn/round references and every internal actor reference consistently.
  Retain exact mechanics and source/template provenance. Reset combat progress through
  an explicit prepared-to-live initialization contract; do not inherit accidental
  rehearsal damage/turn state silently. Pin that contract in C2 before activation.
- Unique `(World, Run, scene ID)` plus operation-key/body receipt makes same-key retry
  return the same instance; conflicting intent cannot duplicate or rebind it. Commit
  binding, encounter and receipt together. Unknown response recovery uses the exact
  intent. Reopen uses the durable binding directly through the same scoped component.
- Older Runs with no sealed template selection offer an explicit separately scoped
  preparation path or honest absence. Never infer a template from current Plan or
  global selection. No backwards-compatibility execution branch.
- Run edition prose with retained marker IDs keeps the binding. Initially refuse
  rebase when sealed selections or scene encounters exist, pending a separately
  designed explicit reconciliation. Trash retains bindings/fights; restore reopens.
- Session encounter edits stay Run-owned and cannot mutate template revisions,
  other Runs, World associations or accepted mechanics. Navigation, reload and
  service restart preserve the exact encounter, actor identities and tracker state.

## Required evidence and failure critique

C1: real HTTP→APP tests for exact admission/World authorization, foreign IDs,
missing/deleted scene, stale/dirty Plan, same/different-key contention, transaction
rollback and unknown-response replay after source advances. Save/adoption must
append exactly one immutable snapshot transactionally; stale/replay must append
none. Historical snapshots and original mechanics remain byte-identical after
later edits, and read without producer/Graph. Test populated migration downgrade
refusal and failure before commit. UI tests prove direct scoped opening, no chooser
fallback, pending creation recovery/remount, foreign/late responses, Plan and combat
draft retention, Document/Cards scene position and tool close/reopen continuity.

C2: run-start Plan/template-save races and explicit selection, no mutable-latest
resolution, exact capture before first combat open, one instance under concurrency,
fresh actor ID remapping, source/other Run isolation, rebase hold, Trash/restore,
unknown operation recovery, meaningful turns and retained reload/restart state.

Each implementation gets exact cumulative Bugbot review, owner-boundary tests,
typecheck/build where affected, PRIME merge and guarded 8000/5202 rollout. Preserve
APP/native data, artifact files, drafts and frozen components. Then perform Conks
first and Sheep generality through ordinary UI, without console/SQL/manual-ID repair.
Do not use the synthetic #1621 witness to award the real adventure journey.
Full J1–J6 twice, original roughly10-second grounding→image benchmark, external
recap/supplemental evidence loop, 8GB/proxy measurement and operator acceptance
remain open. Hosted, rules graph and richer automation stay separately scoped.
