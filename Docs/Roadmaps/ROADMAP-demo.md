# Buddy roadmap — author, plan, play, remember

**Status:** current product roadmap; reconciled 2026-10-21; implementation paused for operator planning.
**Evidence anchor:** remote main `71db547cbb3eab3c5037d0b8446ce4014ecfa9f9` (through PR #1565 and #1546).
**Owner:** DungeonMindBuddy; [steward mandate](../Plans/STEWARDS-HANDOFF-demo.md).
**Purpose:** distinguish delivered capabilities, remaining acceptance and choices for the next goal.

This is the sole product execution ledger. Detailed history remains in Git, PRs
and bounded contracts. The operator paused implementation to choose the next goal.
No candidate below activates implementation. Draft #1566 remains unmerged and
undeployed. Historical “next” instructions in settled slices do not reactivate work.

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

1. **Root Plan inventory:** `/plan?documentId=…` still enters the old campaign
   inventory and omits native Session 29 Plans. The Plans exist under the native
   Elderwyld route. Draft [#1566](https://github.com/Drakosfire/DungeonMindBuddy/pull/1566)
   replaces the root fallback with shared World selection. Source review found
   no actionable product issue; rendered delivery remains pending. Its inherited
   Plan test cohort is not wholly green. Do not mark this fixed on 5202.
2. **Fresh reply completion:** an actual native Plan grounding request completed
   durably and rendered named evidence, but the composer stayed locked. Fresh Jev
   responses retain a replay-only null content basis; the UI rejects their fresh
   response contract. Fix and verify at the response/UI boundary, preserving true
   replay semantics. History/pending client-versus-durable turn correlation also
   needs examination for recovery. No fix has been implemented yet.
3. **Grounding latency:** the exact swamp/Edge question achieved one isolated
   9.841-second pass; the fresh browser request took 12.046 seconds. The requested
   roughly 10-second experience is not a reliable accepted target yet. Measure
   actual decision/read/writer times and quality; do not report a single pass as SLA.
4. **Fresh image continuation:** the fresh browser flow stopped at the locked
   composer before follow-up/image generation. A prior Build image witness cannot
   close this gap or establish a one-click image action in Plan.

The API backing 5202 is at the evidence-anchor revision; the UI serves
`a65de0de8ffa428efbfa00631b54eec1d2608ea7` (#1561). These are the observed
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

## Proposed next goals — operator choice pending

| Candidate | First useful outcome | Completion boundary |
|---|---|---|
| **Recommended: dependable Plan/Buddy/image journey** | Find Session 29 normally, ground a multi-turn discussion, inspect named evidence/exact Debug prompts and generate/reopen the chosen image | Root entry and fresh response fixed; ordinary 5202 workflow twice with no manual repair, retained drafts/scene position, honest measured latency and operator review |
| Session-to-memory continuation | Use the real external recap with matching played evidence in next-session planning | Review selected supplements, publish explicitly, retrieve/cite the accepted result on a fresh turn and after restart |
| Connected table tools | Use Rules and generated mechanics during Play | Select one bounded Rules coverage or Combat continuation slice; prove actual use and retained session state |
| 8 GB performance acceptance | Know current client cost and eliminate the largest measured waste | Current-build load/read/memory measurements, one prioritized repair and before/after evidence |
| Hosted v1 | Authenticated laptop use at buddy.dungeonmind.net | Separate SERVER/platform contract, access controls, repeatable deployment and backup/restart proof |

Choose one goal and sequence independently reviewable slices inside it. Do not
turn the candidate table into parallel implementation authority. Rules graph
experiments remain deferred until broader objectives are accepted or the operator
explicitly activates a bounded experiment; delivered Rules lookup remains useful
without that experiment. Semantic maps, linked speculative ideas, economics and
identity through time remain later evidence-driven candidates.

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
