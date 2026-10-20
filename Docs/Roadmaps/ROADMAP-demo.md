# Buddy roadmap — author, plan, play, remember

**Status:** current product roadmap; reconciled 2026-10-19.
**Evidence anchor:** remote main `74a604ce3542fbb0501ac0baf2ff9a32cdfa42a5` (PR #1458).
**Owner:** DungeonMindBuddy; [steward mandate](../Plans/STEWARDS-HANDOFF-demo.md).
**Purpose:** distinguish delivered capabilities, remaining acceptance and choices for the next goal.

This checkpoint replaces the accumulated “next”, “immediate” and historical
execution instructions previously embedded here. No implementation is activated
by this audit. The operator has selected the cards/navigation design examination
described below. Detailed execution history
is retained in Git, merged PRs and existing bounded contracts; do not copy it
back into the active roadmap. The pre-pruning document is available at the
[evidence anchor](https://github.com/Drakosfire/DungeonMindBuddy/blob/fcaab28ab1db7ce2c024152d15ca844e4c3bb3ef/Docs/Roadmaps/ROADMAP-demo.md).

## Product decisions that remain in force

- **Build, Plan and Play share one writing system:** Markdown, semantic blocks,
  tables and the existing media object. Keep that media boundary under scrutiny
  as needs grow; no replacement is presumed.
- **Plan replaces Prep. Play is the table-use mode.** A coherent shared Plan/Play
  workspace is still a design/continuity objective; shared components and separate
  routes alone do not establish that complete experience.
- **Play edits save to the session copy.** Preserve the Plan, original accepted
  Run basis, history, scene notes and progress. Existing scenes first; structural
  editing follows separately.
- Human and optional Agent authoring use the same owning mutation boundaries.
  Agent proposals, document saves, played recollections and published World facts
  remain distinct.
- **Recaps are external documents.** Ending a session asks for optional final
  thoughts/recollections. Scene notes and reflections supplement planning and
  external recap extraction; Buddy does not manufacture a recap on close.
- Real user journeys, reopen/restart retention, narrow-screen use and operator
  feedback matter. A merge or isolated test does not prove overall acceptance.

## Delivered baseline — keep and build on it

| Capability | Evidence | Practical limit |
|---|---|---|
| Build/Plan autosave; Plan Markdown entry/help and tables/callouts | #1415–#1419; later #1442 import-fidelity reuse | Does not prove every content shape across every view |
| Saved media projection and editing in Play | #1421, #1422, #1425–#1429; normal 5202 edit/save/reopen/history witnesses | Existing scenes; session edits preserve Plan |
| Prominent movable/collapsible scene notes; compact Play navigation and chat below navbar | #1420, #1431–#1437; desktop/narrow and retained-state evidence | Cards still need their own coherent design |
| Buddy reads saved session content and notes; reviewed scene edits | #1438–#1441; real and disposable acceptance | Saved context, not unsaved keystrokes; existing scene targets |
| Image authoring in Plan and Play | #1443/#1444; generation/selection/insertion delivered | Media availability, navigation and consistent use remain dogfood concerns |
| Recoverable Trash across Build, Plan and Play | #1445–#1447 | Reversible document/session lifecycle; not a universal source-artifact purge contract |
| Shared compact navbar actions and actionable draft recovery | #1448–#1451; root Plan route included | Further layout issues require concrete reproduction |
| Plan Cards navigation and Document continuity | #1458 merged `74a604ce`; Architecture Cycle 1 PASS on `d6936b0e`; PRIME desktop/narrow and 12 protected-response preservation checks passed | Existing-scene browsing; direct card editing and dense-scene facets remain open |
| Useful root Play landing | #1452 | Old #1190 welcome proposal is not the current delivery plan |
| End/reopen sessions and retain final recollections separately | #1453 corrected by #1454 | External recap remains separate |
| Next-session planning from notes/reflections with active exact-revision citations | #1455; actual saved-session planning answer and pinned citation navigation on 5202 | Recent ended active sessions, bounded context; not automatic Graph truth |
| Explicit session-evidence supplements for external recap ingestion | #1455; same-World/ref/digest checks, sealed lineage and unchanged recap bytes | Production adapter verified synthetically; real external-recap use remains open |
| Ingest exact candidate/source navigation and correction safeguards | #1315, #1375, #1391, #1395/#1396, #1399–#1407 | Extraction quality and complete chronology still need source-based evaluation |
| Ordinary Build Jev retrieval and one evidence-bound writer | #1325 and subsequent accounting/coverage fixes through #1369 | Generality, coverage, latency and cost are separate from one successful answer |
| Agent service regression baseline | `tests/test_agent_turn_service.py`: 164 passed on 2026-10-19 after repairing seven inherited fixture failures; [bounded handoff](../Plans/HANDOFF-TEST-agent-baseline.md) | Specific suite baseline; not repository-wide test or J1–J6 acceptance |
| Shared document-reference inspection across Build, Plan and Play | #1471 plus core-shell correction #1472; Architecture review and actual desktop/narrow open/Back/Close, exact Plan revision, draft/scene/Notes retention and protected-state checks on 5202; [settled contract](../Plans/HANDOFF-SURFACE-reference-peek-slot.md) | Build/Plan document targets; unavailable historical Build revisions stay unavailable, no silent current fallback |

The operator ran a real session: Play helped improvisation and scene note-taking.
They identified media access and navigation as major weaknesses. This is useful
real-use evidence; it is not blanket acceptance of J1–J6, all views, all sources
or hosted readiness. The latest real planning witness used separately attributed saved notes/reflections
with source links and no Plan or Graph mutation. Its campaign content remains private.

## Remaining acceptance — do not erase these gaps

1. **Authoring/view continuity:** prove representative Markdown, blocks, tables
   and media through Build, Plan and Play, Document/Cards switching, manual and
   Agent edits, autosave/reopen, navigation and conflict recovery. Preserve each
   document/session authority. Cross-surface availability is not arbitrary
   bidirectional synchronization.
2. **Cards:** the reviewed design distinguishes scene navigation from bounded card
   presentation; Plan navigation/view continuity has delivered. Direct focused-scene
   editing, dense-content acceptance, visible boundaries, reorder/create/remove and
   the full content-first workflow remain open. The navigation slice does not prove
   Plan Cards' entire workflow.
3. **Connected knowledge:** ordinary Plan access to the published Session 29 recap,
   historical authored-source availability and the song callback remain specific open
   witnesses unless demonstrated. The delivered shared read-only document interaction is bounded by
   the [surface reference contract](../Plans/HANDOFF-SURFACE-document-references.md):
   Build/Plan links share one peek interaction across Build, Plan and Play. Exact
   historical Build reads without an admitted owner API remain unavailable; the
   former Edge revision-8 href is absent from the current saved Plan. #1455 proves session-note use, not these recap
   and authored-source journeys.
4. **Session-to-memory loop:** exercise a real externally authored recap with
   explicit notes/reflections attached; review discrepancies and publish through
   the existing governed path. Retain source attribution and chronology.
5. **Semantic richness:** maps, roster/table collections, people, economics,
   refugee/survivor identity through time and linked speculative GM ideas need
   evidenced relationships and useful retrieval. A heading or media wrapper alone
   does not establish those graph semantics.
6. **Rules and table tools:** cited 2024 travel-rule retrieval and the connected
   statblock/combat/recorded-roll journeys remain acceptance work; the prepared
   rules text and a standalone statblock do not prove those tools.
7. **Full local acceptance:** first-World preparation and J1–J6 twice without
   console repair remain unaccepted. Existing selected-World use is not full
   corpus or fresh-World proof. The Agent service suite baseline is now green;
   keep failures in other suites and repository-wide coverage limits explicit.

## Current chosen design focus

The operator selected cards/navigation on 2026-10-19. Architecture's
[Plan/Play cards proposal](../Design/DESIGN-plan-play-cards-navigation.md) examines
card purpose, capacity, editing and context-preserving navigation against the
current code. It recommends Plan scene-navigation/view continuity first, then
focused existing-scene editing through each surface's owning writer. The design
was independently reviewed and merged as #1457. The first bounded navigation/
continuity slice is now [settled](../Plans/HANDOFF-CARDS-plan-navigation-continuity.md)
after #1458 review, merge and PRIME's final delivery/preservation checks. Its source
leases are released. The follow-up
[thumbnail deck](../Plans/HANDOFF-CARDS-plan-thumbnail-deck.md) is also settled:
#1460 merged `4a6d758b` after Architecture Cycle 2 PASS and PRIME's desktop/narrow,
14-scene draft/media continuity and protected-state acceptance. Cards uses the
vertical deck; Plan selection remains in the navbar. One scene is one deck entry;
this does not deliver direct editing or dense-scene facets. Its leases are released.
The follow-up [shared Contents/top-alignment slice](../Plans/HANDOFF-CARDS-shared-contents.md)
is settled as #1461 (`6f4092d0`), Architecture Cycle 1 PASS. PRIME verified Plan
alignment and shared Play thumbnails at desktop/narrow widths, preserved inspection
versus current-scene/Notes targeting, and all 12 protected responses. Contents
shares presentation; each surface retains its existing state/save owners. Leases
are released; this adds no editing or structural capability.
Direct focused-card editing in Plan is the next proposed
capability, followed by the Play adapter; neither is authorized by this settlement.

## Other candidates for a later operator decision

These remain options, not a newly activated implementation sequence.

| Candidate | User value / first useful outcome |
|---|---|
| Real session-to-memory continuation | Attach the next external recap, compare with saved notes, review/publish and use it in ordinary next-session planning |
| Graph-aware authoring and continuity | Preserve authored table/map meaning; connect song/people/refugees and resurface ideas without turning proposals into facts |
| Rules/statblock/combat integration | Retrieve cited 2024 rules and use the prepared mechanics through actual table controls |
| Hosted v1 | Authenticated laptop use of the retained World at buddy.dungeonmind.net, repeatable deploy/update, backup/restore and restart proof |

Next discussion: bound direct focused-card editing and its representative
shared-authoring acceptance journey before expanding that UI;
use the next external recap as the memory-loop witness when it exists. Hosted v1
can be chosen independently, but needs its own bounded SERVER/platform contract.
No provider-parity program or platform-wide rewrite is an automatic prerequisite.

## Card adoption direction — operator decision, 2026-10-03

Connected scene cards, scene lenses, choices and map/location navigation remain
adopted product direction. The document/card/Play projections and shared authoring
now provide a substantial implementation baseline. The operator's later explicit
request for a serious card-design pass governs the next design examination:
purpose, capacity, overflow/splitting, editing and accessible detail. Prototype
appearance is evidence, not accepted storage or runtime authority. Preserve J2/J5
acceptance and the same document/Run controller seams.

## Scope and ownership

Buddy owns the product, source UX, writing system, Plan/session state and Agent
orchestration. DungeonMind owns admitted knowledge and evidence; GenerationEngine
owns inference execution. SERVER/platform owns hosted identity/access/deployment.
Cross-repository decisions stay in DungeonOverMind. Fresh source admission,
semantic interpretation, map authoring and hosting use explicit owner contracts;
no product work may infer a missing contract from a fixture or legacy fallback.

The Mirathorn source → reviewed publication → ordinary cited answer → restart
journey remains useful acceptance material, not an instruction to rerun old
migration/adoption work. The Stacey continuity catch remains a separate isolated
synthetic acceptance scenario; do not modify canonical campaign identities to
make it pass. The campaign and game notes remain private.

## Durable journey acceptance

The original J1–J6 criteria below remain the broader local product bar. Their
presence does not reactivate their historical dispatches or mark them complete.

## DEMO-J1 — start a World and prepare

**Acceptance:** Create/select a new World and open a coherent editable blank
World-scoped Plan through ordinary controls before importing a corpus. Author
material or import the bounded parsed Markdown using the normal source/document
flow; preserve exact document/source identity and round-trip. No campaign,
recap, initialized graph or special Of Conks import path is a prerequisite for
the blank Plan. Inspect accepted objects/source relationships when knowledge
has been explicitly confirmed under J3; an editable document alone is not
published knowledge.

**Inherited evidence:** CON-READY CR-U1–U5/U11; source ingress and durable
application-state foundations. Their presence is not proof that arbitrary
adventure Markdown becomes usable preparation without intervention.

**Likely owner:** DEMO Document/Agent plus Knowledge consumer.

**Verify before dispatch:** lossless Markdown/component round-trip; document and
source identity; supported ingestion authority; required source admission and
new-space initialization. If the chosen vNext demo cannot admit this corpus,
delegate the missing contract rather than borrowing an incompatible legacy read path.
The World-container create contract allocates identity/source root, not a graph
head; no source-admission or native-initialization capability is inferred from it.

## DEMO-J2 — collaborate on the surface

**Acceptance:** Across multiple turns, the agent authors and revises prose and
registered Markdown components in the selected Plan. The GM edits too. Save,
reload and route changes preserve the document; concurrent edits do not silently
overwrite each other. The agent retains the agreed planning context.

**Inherited evidence:** MarkdownCanvasSession, AgentRuntime, A5/A6/A7, CR-U12,
AUTHORING-ARTIFACT. Preserve current authoring and command arbitration rather than
building another editor or treating chat text as a completed document edit.

**Likely owner:** DEMO Document/Agent.

**Boundary:** ordinary reversible document edits can be immediate/undoable under
accepted policy; graph publication is a separate governed action. Unknown
component payloads cannot become executable code or silently vanish on save.

## DEMO-J3 — create knowledge and use it next turn

**Acceptance:** Highlight source content, create a node and an edge through the
accepted preparation/confirmation path, inspect their exact durable identities,
then ask the agent a factual question requiring the new node. Normal retrieval
must find it under the same scope/authority; a creation-payload echo is insufficient.
Reopen after restart.

**Current evidence boundary:** selected-World ingestion, review, publication and
ordinary source-backed conversation have advanced substantially beyond the old
#787/#790 bootstrap. Do not revive that historical implementation sequence.
The exact highlight → create node/edge → confirm → ordinary next-turn retrieval
journey, fresh-World admission and the full corpus gate still need their own
current end-to-end evidence before J3 is accepted. Existing-source publication
and revision-pinned session-note context are distinct capabilities. Session
reflections are not automatically published World facts.

**Inherited evidence:** PLAY-1 #773 and accepted isolated persistent PLAY-2
#779; PLAY-3 is not dispatched; V6.2 adapter; WorldKeeper #7/#8; CR-U4–U7.
These proofs do not close the connected DEMO-J3 journey.

**Likely owner:** DEMO Knowledge consumer; external repairs to MIND/WORLDKEEPER.

**Boundary:** profile pin, evidence admission, source identity and immutable child
read-back remain exact. Do not infer occurrence/mention binding from evidence
support. If text highlighting requires an unsupported binding capability, record
and delegate that gap; do not mask it with UI-only state. No silent V2→V3 migration.

## DEMO-J4 — design and generate a usable asset

**Acceptance:** Discuss/debate a creature across turns, settle a brief, launch
real async generation, keep working and navigate away, then find the completed
statblock. Review it, unlock/edit through its proper working-copy lifecycle,
save it, and reference the selected version from Plan. Generate image candidates,
select one, and reopen the association. The resulting object is available through
the agreed graph/product lookup path.

**Inherited evidence:** SBW foundations, Threat publication/hydration/projection,
REVISE-UX, HERMES-LIVENESS and cross-surface demo requirements. Rehearse existing
behavior before activating a large revision or media program.

**Likely owner:** DEMO Assets/Generation; producer/assets dependencies to SERVER;
generic execution gaps to ARCHITECTURE.

**Boundary:** generated candidate ≠ accepted mechanics ≠ editable working copy.
Editing accepted mechanics yields the governed successor behavior required by the
domain; never modify an immutable revision in place. Keep ongoing Run references
stable unless explicitly adopted. Reuse existing jobs/assets contracts; missing
durability is an explicit gap. Prepared assets may support a presentation only
when labeled prepared and do not count as real-generation acceptance.

## DEMO-J5 — turn preparation into a playable instrument

**Acceptance:** Start a Run from the prepared document/version. Quickly move among
the plan, choices, readable NPC/statblock projections, combat and roll tables.
Return from inspection without losing the current scene or current work. The
same component family can be exercised in the UI workshop and in the real surface
through accepted controllers.

**Inherited evidence:** BF/Playable foundations, exact mechanics projection,
current-moment context, CR-U8/U10/U13/U15/U16 and compact Combat Tracker interaction.

**Likely owner:** DEMO Run/Tools; presentation variants may proceed in isolation
once the view-model/action contract is agreed.

**Boundary:** document content/identity survives Plan→Play. Runtime choices,
initiative and HP belong to the Run. A full PC character-builder, universal rules
evaluator, pagination convergence or spatial workspace is not a prerequisite.

For the assigned Plan-to-Run transition, start only from a clean, saved World
Plan bound to its exact committed WorkRevision ID, `revision_n`, and digest.
Dirty or stale Plan state blocks Start. Reopening an existing Run after its Plan
is edited or discarded must load the originally pinned historical revision
without rebasing the Run or copying the Plan.

## DEMO-J6 — act, record and resume

**Acceptance:** Record a choice, modify combat HP, enter a physical roll, resolve
the selected table entry and record the outcome. Navigate, reload, restart and
resume the same Run with the same outcomes and selected content. No implicit
reroll when reopening a table.

**Inherited evidence:** APP-STATE durability, current Run identity and relevant
roll/combat code. Table parsing alone does not prove durable recorded results.

**Likely owner:** DEMO Run/Tools.

**Boundary:** preserve table identity/version, submitted roll and resolved result;
define unsupported/out-of-range input visibly. No need for Rules/Jev reasoning
to resolve an explicit table. Do not mutate canonical mechanics to record HP.

## Final acceptance

Perform J1→J6 twice from a resettable environment without console/SQL/manual-ID
repair, including real generation, graph read-after-write and restart/resume.
Each journey begins with the first-customer World/blank-Plan path above; fresh
World identities may provide isolated rehearsal state under the existing fixed
DB URLs, without deleting old Worlds or requiring a corpus before Plan is usable.
Use production code and declared exact dependency versions. Record meaningful
limitations and failures. The operator then accepts legibility, coherence and
usefulness; technical test success does not self-award that judgment.

The evidence bundle contains corpus identity, repository/dependency pins, minimal
setup/reset instructions, durable-data location, recovery instructions, recorded
journey results and owner-routed residuals. Prefer existing scripts and reports;
avoid creating a new platform to run one rehearsal.

Label the first accepted outcome **LOCAL DEMO ACCEPTED**. SERVER's
hosted gate additionally proves login, world authorization, remote storage,
logout/login and deployed-service restart. Hosting consumes the same product
journey, rather than redefining or reimplementing it.
