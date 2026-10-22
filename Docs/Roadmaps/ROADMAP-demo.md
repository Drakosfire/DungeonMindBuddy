# Buddy roadmap — author, plan, play, remember

**Status:** current product roadmap; reconciled 2026-10-21; goal activated by the operator on 2026-10-21.
**Evidence anchor:** remote main `339ddc3f724ed6dfc39fe96fa7c7528ecfd291ff` (through PR #1568).
**Owner:** DungeonMindBuddy; [steward mandate](../Plans/STEWARDS-HANDOFF-demo.md).
**Purpose:** distinguish delivered capabilities, remaining acceptance and choices for the next goal.

This is the sole product execution ledger. Detailed history remains in Git, PRs
and bounded contracts. The operator selected a sustained local preparation/play goal: dependable
Plan/Buddy/image use → usable connected Combat → both adventure rehearsals, with
foundation refinement throughout. PR #1566 is now merged and running on 5202; the shared image-prompt handoff
is the next bounded slice. Historical “next”
instructions do not reactivate old leases; new implementation slices still require
bounded ownership and review.

## Product decisions that remain in force

- Build, Plan and Play share Markdown, semantic blocks, tables and the existing
  media object, using shared Surface components and each surface's owning writer.
- Connected scene cards, scene lenses, choices and map/location navigation remain
  adopted direction; presentation does not create storage/runtime authority.
- Plan replaces Prep. Play edits the session copy; preserve the Plan, accepted
  Run basis, scene notes, progress and history.
- Human and Agent edits share mutation boundaries. Drafts, played recollections,
  generated candidates and accepted World facts retain distinct authority.
- **Recaps are external documents.** Closing a session asks for optional final
  recollections. Notes/reflections supplement planning and external recap ingestion;
  closing does not manufacture a recap or publish World facts.
- Ingestion belongs inherently in Build: one saved document/editor, frozen run
  configuration, review and explicit acceptance. Existing exact run links must
  remain recoverable; do not add a backwards-compatibility runtime pathway.
- Source citations should name the source. Technical revision/receipt information
  belongs in Debug or inspection, with exact provenance retained behind it.
- Target an older laptop with 8 GB RAM. Do not impose new character/token caps to
  substitute for efficient retrieval, deduplication and code loading.
- A merge, component test or isolated witness does not award connected journey,
  hosted readiness or operator acceptance. Keep unproven transitions visible.

## Delivered baseline — capabilities and their limits

| Capability | Evidence | Practical limit |
|---|---|---|
| Shared writing, autosave, semantic blocks, tables and media | #1415–#1429, #1442–#1444 | Representative cross-surface round-trip and recovery still require connected acceptance |
| Plan Cards and Document continuity, vertical deck, manual focused-card editing | #1458–#1465 | Structural create/reorder/remove and dense-scene acceptance remain separate |
| Shared Contents/book collapse, reference inspection, paper layout and navbar width | #1471–#1478, #1507 | Shared presentation retains surface-specific state/save ownership |
| Legacy card paths and unused surface forwarding removed | #1479–#1481 | Finite cleanup, not proof that every unused path is gone |
| Session-copy editing, notes, close/reopen and final recollections | #1420–#1437, #1453/#1454 | Real table use occurred; not full J5/J6 acceptance |
| Saved session evidence for cited planning and explicit recap supplements | #1438–#1441, #1455 | Saved content only; real external recap with matching supplements through publication/retrieval remains open |
| Recoverable Trash and actionable draft recovery | #1445–#1451 | Not a universal source/artifact purge contract |
| Demand loading and bounded/deduplicated history, evidence and graph reads | #1482–#1499, #1511, #1515–#1524, #1558, #1564/#1565 | No actual 8 GB hardware acceptance or complete latency/memory distribution yet |
| User/Agent Rules lookup in governed Plan and Play | #1500–#1506, #1526, #1543–#1545 | Admitted public SRD 5.2.1 occupancy corpus; not all 2024 rules, travel-rule coverage or a rules graph |
| Build ingestion in the existing document: Worldbuilding/Recap configuration, review and recovery | #1525, #1535–#1539, #1547–#1549, #1551 | Editing accepted World facts remains separate; full source-quality/chronology acceptance is open |
| Native publication and exact source reopen | #1552, #1560–#1563; isolated real Worldbuilding and public Recap review→selected identity publication→cold source reopen | Selected publication, not every proposed attribute/relationship; private external Session 29 extraction was reviewable but not published and had no supplements selected |
| Native Combat C0 Surface module, artifact lookup, roster state save/reopen and responsive layout | #1550, #1556/#1557; isolated rendered persistence witness | Not connected Play continuity, C1–C4, graph roster selection or live generated-statblock acceptance |
| Ordinary Build Jev retrieval (#1325–#1369), plus Plan retrieval decisions, host-owned reads and one writer; actual per-call usage | #1527–#1534, #1540–#1546 | Fresh rendered response has a contract defect below; latency target not reliably met |
| Named source citations and exact lazy Debug prompt inspection, including failures | #1553–#1555, #1559, #1563 | Component and selected live evidence do not prove every fresh multi-turn/image path |
| Real image generation from an authored/prepared prompt | #1443/#1444 and actual Build image acceptance | Build prompt→generated asset proved; fresh Plan conversation→prompt→image completion has not |

The operator's played session established useful improvisation and note-taking.
It also exposed navigation and media weaknesses. Preserve that evidence without
calling the full local demo accepted.

## Current dogfood failures — next-goal inputs

1. **Root Plan inventory — resolved:** #1566 merged `955064067` and runs on5202.
   The exact formerly failing root URL now shows World selection. Ordinary
   Elderwyld selection exposes both Session29 Plans, and Campaign2Session29 opens
   through the normal selector. The guarded UI rollout retained all1458 APP rows
   with the API unchanged. The broad Plan fixture cohort still has documented
   inherited failures; do not call that entire suite green.
2. **Fresh reply completion — resolved:** #1568 merged `339ddc3f7` and runs on
   API8000/UI5202. Fresh replies carry their exact committed basis; true replay
   remains distinct. Exact completed-history correlation releases only its
   unchanged pending envelope. Bugbot independently passed8backend/228UI/typecheck.
   Rendered fresh grounding and a follow-up both unlocked the composer; named
   citation and exact Debug writer request opened. Live rehearsal changed only
   intended agent rows; Plans/sessions and other non-agent APP tables stayed unchanged.
3. **Grounding latency:** the exact swamp/Edge question achieved one isolated
   9.841-second pass; fresh browser requests took 12.046 and 12.016 seconds. The requested
   roughly 10-second experience is not a reliable accepted target yet. Measure
   actual decision/read/writer times and quality; do not report a single pass as SLA.
4. **Fresh image continuation:** the repaired fresh browser flow now writes an image prompt, but has no
   action handing that prompt into Plan Image Studio. A prior Build image witness cannot
   close this gap or establish a one-click image action in Plan. The next bounded
   [shared Studio handoff](../Plans/HANDOFF-PLAN-image-prompt-handoff.md) prepares
   an editable seed with explicit user Generate/Save/placement; it is not delivered yet.
5. **Trace presentation:** the live trace shows duplicate response_received
   observations for the same model call, one without usage and one with reported
   usage. Aggregate/per-call reported counts are available; presentation still
   needs reconciliation and must not imply an extra paid call.

The API backing 5202 is at the evidence-anchor revision; the UI serves
`339ddc3f724ed6dfc39fe96fa7c7528ecfd291ff` (#1568). These are the observed
planning checkpoint, not a requirement to keep those revisions after delivery.

## Remaining acceptance

- **Authoring and continuity:** representative prose/blocks/tables/media through
  Build, Plan and Play; human/Agent edits, Document/Cards position, drafts, autosave,
  reload/restart and conflict recovery. Direct focused Plan editing has delivered;
  structural card operations and dense-content acceptance have not.
- **Connected knowledge:** ordinary retrieval of published recap/authored sources,
  callbacks and relationships with exact named citations. Source availability in
  an isolated publication witness is not ordinary next-turn retrieval acceptance.
  The previously reported Build Find `authority_receipt_missing` failure has no
  recorded fresh acceptance here and must not be silently considered resolved.
- **Session-to-memory:** real external recap plus explicitly matching scene notes
  and closing recollections → discrepancy review → selected publication → ordinary
  cited next-session planning. Keep chronology and separate evidence authority.
- **Rules/assets/table tools:** cited 2024 travel rules, real async statblock
  generation/retrieval/editing, selected image association, connected Combat and
  recorded roll results. Current Rules corpus and Combat C0 do not close this.
- **Performance:** fresh/current-build measurements on the 8 GB target or an
  explicitly stated proxy; cold/warm load, repeated reads, latency and retained
  memory. Historical frontend assessment numbers are not current measurements.
- **Full local acceptance:** J1–J6 below, twice in a resettable environment without
  console/SQL/manual-ID repair, including fresh World and restart. No local demo
  acceptance is awarded. Hosted v1 has separate identity/deploy/backup gates.

## Selected goal and later candidates

| Candidate | First useful outcome | Completion boundary |
|---|---|---|
| **Recommended: dependable Plan/Buddy/image journey** | Find Session 29 normally, ground a multi-turn discussion, inspect named evidence/exact Debug prompts and generate/reopen the chosen image | Root entry and fresh response fixed; ordinary 5202 workflow twice with no manual repair, retained drafts/scene position, honest measured latency and operator review |
| Session-to-memory continuation | Use the real external recap with matching played evidence in next-session planning | Review selected supplements, publish explicitly, retrieve/cite the accepted result on a fresh turn and after restart |
| Connected table tools | Use Rules and generated mechanics during Play | Select one bounded Rules coverage or Combat continuation slice; prove actual use and retained session state |
| 8 GB performance acceptance | Know current client cost and eliminate the largest measured waste | Current-build load/read/memory measurements, one prioritized repair and before/after evidence |
| Hosted v1 | Authenticated laptop use at buddy.dungeonmind.net | Separate SERVER/platform contract, access controls, repeatable deployment and backup/restart proof |

The operator selected dependable planning, connected Combat and the two adventure
rehearsals as one sustained goal, sequenced in independently reviewable slices.
Foundation refinement runs throughout: shared Surface components, demand loading,
bounded/deduplicated reads and current-build 8 GB performance evidence. The
session-to-memory evidence boundary applies to the rehearsals; hosted v1 remains
a separately selected candidate. This table does not grant parallel write leases. Rules graph
experiments remain deferred until broader objectives are accepted or the operator
explicitly activates a bounded experiment; delivered Rules lookup remains useful
without that experiment. Semantic maps, linked speculative ideas, economics and
identity through time remain later evidence-driven candidates.

## Selected continuation after dependable planning

The operator identified the mechanical, unfilled Combat landing and nominated
**Of Conks and Cons** and **A Wild Sheep Chase** as full adventure witnesses.
The operator included these priorities in the active goal. This does not reactivate
old prototype/handoff leases.

### 1. Make Combat a usable table instrument

Start with an evidence-based design comparison of the played Session 22/23/26
trackers, Session 24 dogfood feedback and current native Combat. The existing
[generic command-board contract](../Plans/HANDOFF-COMBAT-generic-command-board-experience.md)
and [played tracker feedback](../Plans/HANDOFF-c2s24-live-combat-tracker-design.md)
are design inputs; their old ACTIVE/base/runtime statements do not grant a new
lease. Inspect current code before adopting any historical implementation claim.

Prioritize the actual GM flow:

- A useful empty/returning landing explains how to assemble an encounter and resume
  a saved fight. Show real saved work; do not fill it with invented sample encounters.
- Select creatures or exact statblock versions from available World/assets, adjust
  the encounter, then open that same encounter from the relevant Plan/Play scene.
- Keep current/next actor, initiative/round, HP/temp HP, damage/healing, conditions,
  notes and one-step statblock inspection usable during a fight. Carry forward
  proven initiative/grouping interactions after checking their current gaps.
- Navigate away, reload and restart, then resume the exact fight and scene without
  silently replacing the roster, Plan, mechanics versions or player notes.
- Keep Combat an embeddable Surface module with durable encounter ownership.
  Rules lookup uses the admitted Rules tool; a rules graph is not a prerequisite.
  Summon placement, timed conditions and richer automation are separately bounded
  follow-ons informed by the played feedback, not implicitly delivered by C0.

**Acceptance:** use a source-grounded adventure encounter through normal controls:
assemble → enter from Play → run several turns and state changes → leave/reopen →
restart/resume. Compare the experience against the played prototypes. Preserve
original historical saves; do not import prototype adapters or campaign mappings
into the runtime to make the demonstration work.

### 2. Adventure ingestion through a winding story and combat

Use both named adventures to exercise the same general Build→Plan→Play→Combat
workflow. Begin by locating and verifying the permitted local source editions,
existing imports/runs, source digests and retained Worlds. Current main contains
historical Of Conks evidence and derived-candidate correction (#778), but that
record explicitly did not confirm publication or close J1. It is not proof of a
current accepted import. A current Wild Sheep Chase source/run has not yet been
verified in this reconciliation. Preserve useful existing work before deciding
whether any extraction must be repeated. Keep licensed text out of Git fixtures.

The target is an adventure usable at the table:

1. Build retains the exact saved source, extracts/reviews candidates and publishes
   selected supported knowledge with named citations. Distinguish authored options,
   conditional encounters and GM secrets from events that have actually happened.
2. Buddy can answer representative questions about people, places, motives,
   alternative routes and encounter triggers from that accepted source. Review
   omissions and unsupported connections against the adventure, not candidate counts.
3. Plan supports meaningful scene choices and linked NPCs, locations, tables and
   mechanics. Preserve branches, callbacks and conditional progression; do not
   flatten the adventure into an asserted chronological history.
4. Play can follow different routes and reach a real encounter. Open its creatures/
   statblocks in Combat, record turn/HP/notes and any table results, then resume the
   same story position after reload/restart. Return combat outcomes to the session
   record without silently publishing them as World facts.
5. Complete the connected J1–J6 acceptance applicable to this rehearsal, including
   real generation where required. A prepared packet, fixture roster or API-only
   publication cannot stand in for the whole journey. Use the second adventure
   to check generality without adventure-specific runtime branches.

**Selected sequencing:** finish the fresh Plan/Buddy/image failures, then design
and deliver the Combat entry/encounter/Play connection in bounded reviewed slices.
Use one adventure as the first connected rehearsal and the other as the generality
check; choose their order after inspecting current source/run readiness. Repair
missing ingestion or knowledge contracts at the owning boundary as the rehearsal
exposes them. The session-to-memory loop remains another useful bounded goal,
with external recaps and explicit note supplements rather than generated history.

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
