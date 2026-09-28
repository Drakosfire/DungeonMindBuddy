# DEMO — one prepared adventure, one connected session

**Status:** ACTIVE — sole Buddy DEMO execution roadmap, adopted 2026-09-26  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Steward:** [STEWARDS-HANDOFF-demo.md](../Plans/STEWARDS-HANDOFF-demo.md)  
**Transfer mapping and source evidence:** [reconciliation report](../Reports/REPORT-DEMO-roadmap-reconciliation-2026-09-26.md)

## Product contract

A new GM creates/selects a World through the existing fixed-URL World primitive,
opens a usable blank World-scoped Plan, and authors or imports material. Neither
a campaign, recap, corpus import nor a published graph head is a prerequisite
for that blank document. The GM then prepares and explicitly confirms knowledge,
retrieves and cites it through the ordinary Agent path, develops a statblock and
image, and runs/resumes the session using readable, quickly reachable components.

The developer can design a representative component in the existing lightweight
workshop and mount it through Buddy's accepted surface/controller contracts.
Adding a presentation variant must not require reimplementing graph authority.

Scope is one bounded real adventure corpus, one demo World/space, and one session
with representative NPC, Threat/statblock, choice, encounter and roll table.
The final journey includes image selection and editable generated statblocks.
PDF parsing itself is outside scope; parsed Markdown is the agreed input.

## Adopted decisions — 2026-09-26

- Prove the durable local journey first; SERVER's hosted acceptance proceeds in
  parallel. A local PASS does not certify hosted readiness.
- Use a bounded Of Conks corpus for early rehearsal; retain C1/C2 regressions
  and final human acceptance. This replaces the old prerequisite that Of Conks
  cannot enter until the C1/C2 demo gate passes.
- DEMO owns Buddy demo-facing sequencing listed in the reconciliation. External
  domain ownership and active implementation leases remain intact.
- The adoption-time in-scope DEMO merge rule is superseded by the operator's
  2026-09-27 merge-control assignment, relayed by PRIME: **PRIME owns ecosystem
  merge coordination**. DEMO retains roadmap, product design, implementation
  and rehearsal ownership, and sends merge-ready PRs with the exact reviewed
  head, checks/live evidence, blockers and merge order to PRIME. DEMO does not
  merge autonomously or request another operator "Merge" for ordinary work.
  Existing review, live-witness and owner/lease holds remain prerequisites;
  this assignment does not approve #785 or any other pending PR.

## Current execution checkpoint

The end-to-end demo remains unaccepted. Several integration and rehearsal steps
are now proven; J1–J6 have not passed as a connected journey.

**Current operator direction (2026-09-27, relayed by PRIME):** the knowledge
entry point is the first-customer path:

```text
New World (no campaign or recap)
→ blank, usable World-scoped Plan
→ author/import material
→ prepare + explicit confirmation of knowledge
→ ordinary Agent retrieval/citation of the accepted knowledge
→ restart and reopen
```

Use a **new native Of Conks World identity**, allocated through the existing
World primitive in designated isolated state. The original small one-shot
corpus/files are available, so retaining previous DEMO graph IDs or history is
not a prerequisite. Existing demo state is disposable in product intent, not
authorization to delete it, mutate an immutable revision, bypass source
admission or seed a synthetic graph. Leave old Worlds/artifacts available as
historical evidence. Keep the DB URLs fixed; do not allocate a database per World.
Use a new rehearsal display name so normal name-idempotency does not select the
previous World; the server, not the operator or a script, allocates its identity.

Document creation/editing/save and knowledge prepare/confirm retain their
separate accepted contracts. Import must not become the gate for making a Plan
usable, and document edits must not silently publish knowledge. Native genesis,
authentic source/evidence admission and ordinary read-after-write require a
bounded return contract from **MIND** before J3 is designed/activated. PRIME
is routing that prerequisite; no bridge migration, broad framework rewrite,
fake campaign or J3 implementation is authorized by this direction.

**Active implementation remains J4 / draft #785**, frozen repair head
`07ec031ab5b62b8dbcd34f51ed4b6eaf0fa25262`, incorporating accepted main
`11d7b5801b51f664e7a6eeafcb2aa2b0f5922b71`. Author exact-head evidence:
169/169 UI tests (zero exclusions), 140/140 backend tests (11 warnings,
23.31 seconds), scoped Ruff and cumulative/local diff checks pass. Typecheck
retains only the independently hashed inherited JSX error. Backend verification
uses the new private lane environment and accepted DungeonMind pin, not the
operator runtime's preserved Python environment. A minimal control reproduced
a sandbox-only TestClient stall; incomplete sandbox jobs are not green evidence.

PRIME's formal **Cycle 1 HOLD** on prior head
`2e33b57737164ac0393975ab31d42a1c91a43d34` is
[review 5333492877](https://github.com/Drakosfire/DungeonMindBuddy/pull/785#pullrequestreview-5333492877).
Independent evidence on that earlier head was 164 UI / 140 backend tests.
The blocker was a delayed old completion overwriting a newer settled same-World
recovery pointer, so reload opened the old candidate. The repair and mounted
two-generation/unmount/remount/reload regression are committed; both reviewer
failures reproduced before the fix. Settlement now requires the exact current
draft/request/source-version attempt, including after settlement. Cycle 2 is
requested, not passed; a fix commit is not another review cycle.

PRIME merged Buddy #780 after independent Cycle 2 PASS (review 5333525840;
98 tests, zero skips) as `11d7b5801b51f664e7a6eeafcb2aa2b0f5922b71`.
Buddy now pins accepted DungeonMind `b83baf82c381b1929c2c7989326d667200ff544c`;
WorldKeeper remains `49a8620f066ce7ef8972a699020c012f50af9158`. This inherited
source-anchor preservation proof does not prove source-body opening, native
admission or J3, and does not expand the asset slice.

The required real generation/navigation/reload witness is still false.
Necessary bounded API calls are authorized; the persistent demo targets
`54330`/`54331` still have their separate exact-target gate. Read-only inspection
of the handoff's development PostgreSQL at `54329` found that its two named
demo databases do not yet exist; no alternative database was created or used.
Keep this PR's scope, lease, review/live gates and serial topology intact.
No J3/image work, #785 merge or full DEMO acceptance is claimed.

The earlier integrated/rehearsal facts below are preserved evidence, not an
instruction to preserve the legacy Of Conks head as this rehearsal's destination.

**Latest re-anchor (2026-09-27):** #775–#778 are integrated. #776
proves ordinary named-World switching across Build, Plan, Ingest and Play on
one runtime and DB pair. A fresh Of Conks World then received the exact parsed
adventure Markdown through Buddy's local source-import API and produced one
reviewable extraction candidate. #777 made all 48 assertions inspectable,
including 3 nonliteral evidence quotes. #778 enabled explicit literal quote
correction as a distinct immutable child run; its 48 assertions have zero
invalid quotes. The first inert prepare identified three selected relationships
whose endpoint kinds the current DungeonMind predicate contract does not admit;
those were explicitly rejected in review. A governed confirmation through the
normal Buddy product flow published 21 objects and 5 `contains` relationships
as `rev:22ef509825ee1048efc73a1a1aa4a60c`, with no model call, SQL repair or
manual ID assignment. This is a reviewed initial World, not a claim that every
candidate is good or that the extraction profile captures all adventure
content. The source was imported through the local source-import path; the
long-file browser import witness remains outstanding. The older ghost run
remains untouched.

Buddy #782 now supplies exact world-scope consumption by Plan object View,
Agent graph retrieval, grounding, and source-citation requests. PRIME passed
the exact `5762cf335593e9836ec07a40a7ba1632741f7231` head in one formal
review cycle; it merged at `9d31fef89e74a4e8b1f6fd9a5d4f9ed98f283437`.
The saved Of Conks Plan opened Hempholm and a real model Ask answered its
relationship to The Shacks and The Greenfields under the pinned World revision.
The published evidence anchors are still unreadable; Buddy #783 owns that
separate provenance defect. This was a bounded Plan-read PASS, not full J1 or
source-verified grounding. The first J2 rehearsal exposed Agent replies that
stayed in chat instead of editing the selected Plan. Buddy #784 now closes
that bounded transition: reviewed proposals apply to the exact mounted draft,
can be revised in a later turn, and survive ordinary Save/reload as registered
prose, Read Aloud and Decision/Consequence nodes. PRIME accepted exact head
`57c1e632f30e43702e640e301ab26aba14016bf2` in Review Cycle 2
(`5332645721`); merge is `b6c63a56f784be5cc2fc7de5bb6d167e32520bb8`.
The review repaired asynchronous target drift and stale Agent-thread races;
independent evidence is 154 focused UI tests, 10 Python tests and six additional
reviewer race witnesses. The unchanged ThreatPublicationPanel JSX typecheck
failure remains inherited. Real model proposals, ordinary Ask, Apply, Save and
reload were exercised on a separate disposable Plan without overwriting the
operator's draft. This is bounded J2 editing evidence, not the connected J1–J6
or human acceptance. Next: rehearse the repaired Plan transition and J3's
source-to-governed-knowledge doorway under one read/write authority. J3 is not
implemented or activated merely because #784 merged. Buddy #779 previously merged at
`2ccc96ff2a7d76328578609d5289fd3babcf6442`; its isolated PostgreSQL
proof is accepted and its test/report lease is released. The original basic-presentation
design STOP resolves to `RESUME_NON_UI` for this observed functional blocker;
no UI redesign successor is authorized by that decision.

Inherited work: PLAY-1 / Buddy #773 merged at
`7fe771e86df2e796484b058aa2e6a8e7c94c9fb9` after two review cycles;
it proves only the in-memory Buddy→WorldKeeper consumer mapping. Buddy #779
now proves isolated persistent composition; browser interaction, source
admission, and next-turn retrieval remain open. Basic presentation
design/dogfood has an existing merged handoff independent of Canvas F5/F6.
Foundation evidence and exact snapshot PRs are in the reconciliation; refresh at
activation rather than copying those snapshots into another permanent tracker.

Initial actions at roadmap adoption (historical sequence):

1. Establish one reproducible demo checkout/version combination, corpus and
   isolated durable state. Inventory actual codepaths for ingestion, graph reads,
   graph writes, document persistence, generation and Run persistence.
2. Rehearse the journey, recording the first broken transition and any explicitly
   prepared downstream checkpoints. Do not skip to implementing every proposed lane.
3. Continue the already-available basic-presentation pass on disjoint scope while
   knowledge integration progresses. It remains design/dogfood until its successor
   direction is accepted.
4. Keep the dependency-file order explicit: #773 is merged first; Rules #763
   must re-anchor/review against that main before its own merge; E5Q remains
   blocked behind #763. Route minimal external gaps to their existing owners.

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

**Current route / activation gate:** first-customer native initialization and
source admission in a fresh Of Conks World, not migration of the previous demo
head. MIND must return accepted versions/public entry points, the exact empty
World/genesis and source/evidence/parent semantics, governing profile/scope
policy, and the ordinary read/citation authority for the same published child.
DEMO then verifies the return, re-anchors and designs one bounded Buddy handoff.
Do not activate J3 or create a second implementation PR while the serial #785
lane remains open. If a new topology is needed, it must be explicitly designed.

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

## Execution ledger — sole mutable work state

Maintain one concise record per selected slice or delegated blocker here. Do not
prematurely create six implementation PRs from the six journey milestones.

Each record contains:

```text
Journey milestone / concrete user transition
State: unverified | ready | active | blocked | integrated | human-accepted
Observed failure and acceptance witness
Owner task / active handoff / PR / exact accepted version
Write and runtime lease / predecessor / shared-file merge order
Latest integrated evidence and date
Next action or delegated dependency + return contract
```

The initial state of J1–J6 is **unverified as a connected journey**, not an assertion
that their foundations are absent. Historical slices retain their IDs.

### 2026-09-26 — PLAY-1 integration and DEMO preflight

- **DEMO-J3, in-memory consumer boundary:** integrated, not human-accepted.
  Buddy #773 accepted head `5a1736c55988e4b852bbcc2f0ada36d493fa5668`,
  merge `7fe771e86df2e796484b058aa2e6a8e7c94c9fb9`, final review
  `5327172769` (2 cycles). Independent exact-head evidence: 68 focused/V6
  tests, locked sync, Ruff, runtime import and diff check pass; default suite
  retains eight inherited collection errors. No product write route or
  persistent authority changed. No PLAY-2/3 dispatch follows automatically.
- **DEMO-J3, isolated persistent composition:** integrated, not human-accepted.
  Buddy #779 accepted head `2d5ab6ade1d89ec608c941093819ea36404fd18e`,
  merged at `2ccc96ff2a7d76328578609d5289fd3babcf6442` after two formal
  review cycles (Cycle 1 HOLD `5331382343`, Cycle 2 PASS `5331441470`).
  Independent Cycle 2 evidence: four isolated PostgreSQL tests, zero skips;
  54 PLAY-1/V6.2 regressions; scoped Ruff and cumulative diff check pass;
  no disposable database residue. Token
  `CON_READY_PLAY_2_PERSISTENT_VNEXT_POSTGRES_ACCEPTED` records this bounded
  proof only. The ordinary product write route, source admission, next-turn
  retrieval, restartable browser journey and human J3 acceptance remain open.
- **DEMO-J1, isolated Of Conks rehearsal:** **blocked after successful source
  import and extraction, before connected Plan/World use.** At Buddy main
  `29fa749c094ab891d5041e6d5f7e09d54176b7bc`, an isolated local pair
  (`dungeonmind_demo_ofconks_v1` at DungeonMind schema 0010 and
  `dungeonbuddy_application_state_demo_ofconks_v1` at APP-STATE schema 0006)
  was established without touching C1/C2. Ordinary Build Import created the
  managed `of-conks-cons-demo` source and committed document
  `c03fbfcb-79fc-46ae-9124-3f1f7c384c1b` revision 2 from local purchased
  `specimens/01-cleaned-single-column.md`, SHA-256
  `7a379fc9025635b1862b6af7eb5a43dd1ee9387b51cf63ba505491fffe7e68f1`.
  One ordinary Build Extract produced reviewable run
  `07a33f99-7520-4c59-bee2-b38514cb61b8` under the current bounded
  worldbuilding profile, with 33 object candidates and 30 relationship
  candidates; Graph Review displayed the first-World review with 63 changes.
  This is candidate evidence, not a quality PASS or World publication. No
  candidate facts were confirmed. The default profile intentionally omits
  adventure beats/encounters; its suitability for the full demo is unproven.

  The first connected product failure is **Build/imported managed World → Plan**:
  Plan still opens a C2 Session 23 prep, `+ New prep` offers only a C2 session
  number/title, and Ask names Longmont C2. There is no ordinary selection of
  the newly imported World as the Plan destination. Build also disables
  `Find existing object` with `Unknown Build document scope:
  of-conks-cons-demo`, while shared World chrome tries Eldyrwild rather than
  the selected managed World. These are Buddy context/routing gaps, not
  presentation defects or evidence that the extraction failed. At this
  historical checkpoint J1 remained blocked; J2–J6 were not certified by the
  partial rehearsal. The selected-context repair that followed is recorded
  below. Do not spend on another extraction to fix routing.

  The licensed Of Conks package remains local-only and must not be committed.
  Its `specimens/02-prepared.md` matches its local manifest; the local
  `playable/hempholm-prep.md` SHA-256 is
  `c473329dd3a0425559e1d2fae60707a13036e0c473f1dd802e8a96804a2fd86f`,
  not the manifest's `1b350f...` pin. Resolve that input pin before claiming a
  fully reproducible final rehearsal. The new demo DBs and source root are
  disposable local rehearsal state, not production authority.
- **DEMO-J1 selected-context repair:** integrated, not full J1 acceptance.
  Buddy #775 accepted head `ad26172c099f1dd3f8aa983d5f950aa407bd610e`,
  merged at `029004be50057fa7f31d50e0b071633ed36f52f9` after two
  formal review cycles. Historical handoff:
  [`HANDOFF-DEMO-selected-world-context-v1.md`](../Plans/HANDOFF-DEMO-selected-world-context-v1.md).
  The original Of Conks run remains cataloged, but its file-backed components
  and World/source registry are unavailable; it was not replayed or confirmed.
  Under PRIME's pinned evidence amendment, a new explicitly synthetic World
  proved ordinary Build source → Plan create/save/reload, honest missing-head
  behavior, then a user-approved one-node reviewed initialization and exact
  Plan Ask request routing captured without forwarding to a model. This is
  selected-context evidence, not licensed adventure retrieval or DEMO-J1 PASS.
- **DEMO-J1 ordinary World selection:** integrated, not full J1 acceptance.
  Buddy #776 accepted head `59f71fe68bac981c275d7bbeb2e1ceab4764edf7`,
  merged at `4f341eb5ca5edc6c81d5dd956bcea70ff9d9be85` after two
  formal PRIME review cycles. Historical handoff:
  [`HANDOFF-DEMO-world-selection-primitive-v1.md`](../Plans/HANDOFF-DEMO-world-selection-primitive-v1.md),
  adopted from PRIME's pinned OverMind design `936c7c9`. One verified World
  now scopes ordinary Build/Plan/Ingest/Play navigation, inventories and exact
  admission while both DB URLs stay fixed. The accepted same-runtime A/B proof
  covered a Plan→Build stale `documentId`, foreign Run refusal, browser
  back/forward, an unsaved draft return, alternate source import, and native
  graph A-versus-B isolation. World B had no graph head and truthfully reported
  it unavailable. This is synthetic product routing evidence, not recovery of
  the licensed Of Conks artifacts or full DEMO acceptance.
- **DEMO-J1 first World publication:** completed through reviewed Buddy
  extraction correction and the ordinary governed publication flow after #778.
  The selected candidate contained 25 objects and 23 relationships; three
  relationships were rejected after DungeonMind returned an explicit
  endpoint-kind admission error. The reviewed retry published 21 objects and
  five location `contains` relationships at
  `rev:22ef509825ee1048efc73a1a1aa4a60c`. Plan's normal projection reads the
  same head with 21 objects and 5 relationships. This proves a durable World
  head, not broad extraction quality, all source coverage, or J1 completion.
- **DEMO-J1 managed-World Plan read:** Buddy #782 passed one exact-head PRIME
  review cycle and merged at `9d31fef89e74a4e8b1f6fd9a5d4f9ed98f283437`.
  The saved Of Conks Plan opened Hempholm and a real Agent turn retrieved the
  pinned World under explicit world scope with a blank campaign ID. Its answer
  remained `partial_coverage`: the current published source anchors have no
  readable typed locator. Buddy #783 tracks that source-authority gap. Neither
  source-verified grounding nor the editable multi-turn Plan or full J1 journey
  has passed.
- **DEMO-J2 first broken transition (historical, repaired by #784):** two real Plan Agent turns asked for a
  brief Hempholm opening frame to be written into the selected Plan. The first
  reply stayed in chat and offered a later direct write; the second explicitly
  said the Agent cannot edit the document and suggested manual copy/paste.
  The TipTap canvas remained unchanged. At that checkpoint Agent received the selected
  Plan's metadata, not an authorized edit path into its mounted local draft.
  The resulting #784 design preserved the existing editor's dirty-draft/revision-safe
  save semantics and made every Agent edit reviewable before application.
- **DEMO-J2 reviewed Agent-to-Plan editing:** integrated, not full J2 or human
  acceptance. Buddy #784 accepted head
  `57c1e632f30e43702e640e301ab26aba14016bf2`, merged
  `b6c63a56f784be5cc2fc7de5bb6d167e32520bb8`, two formal PRIME
  cycles: Cycle 1 HOLD `5332599377`, Cycle 2 PASS `5332645721`.
  Historical handoff:
  [`HANDOFF-DEMO-plan-agent-reviewed-edit-v1.md`](../Plans/HANDOFF-DEMO-plan-agent-reviewed-edit-v1.md).
  Independent evidence: 154 focused UI tests, 10 Python tests, six additional
  reviewer boundary/race witnesses, scoped Ruff and cumulative diff check.
  No hosted checks were published; typecheck has only the unchanged inherited
  `ThreatPublicationPanel.tsx:553` JSX error. Cycle 1 exposed target/body drift
  during asynchronous hashing and stale Ask/Compose thread replacement; the
  accepted repair rechecks live bindings at mutation time and serializes requests
  with current-thread/scope/generation validation.
  Exact-head browser evidence used disposable Plan
  `37df6fd8-b37a-4806-adc3-e289f2c263fd` in the existing isolated Of Conks
  World. Read Aloud and Decision revisions applied as editable nodes; ordinary
  World Ask remained in the same thread; Save reached Committed and reload
  retained both revisions and eight conversation turns. Two proposal requests
  plus one ordinary Ask request exercised real generation; these HTTP counts
  are not a count of all provider calls in the Ask tool loop. Captured revised
  proposal: observed `gpt-5.3-codex`, 1178 input / 69 output tokens, 3300 ms
  model / 3358 ms request wall. The second proposal's detailed receipt was not
  transcribed before Apply, and provider dollar cost was not returned; no
  aggregate cost/token claim is made. No model-policy change or extraction rerun.
  The Plan edit lease is released. Next connected gate is J3: ordinary source
  highlighting → governed node/edge → later-turn durable retrieval and restart.
  Read-only reconnaissance finds the accepted WorldKeeper consumer has no
  production caller, and #779's native persistent test is not proof that the
  currently reviewed-initialized World uses the same read/write/source seam.
  A read-only contract clarification is routed to existing MIND; no answer,
  migration, source admission or J3 implementation is yet claimed. #783 remains
  independently owned and source-verified grounding remains unproven.
- **DEMO-J3 post-#784 product checkpoint:** read-only rehearsal on integrated
  `main@c19a6c2bf51ae01337b2ad8a3188d45ad6f0fd64`, same isolated World
  and disposable saved Plan. Unlocking and selecting Stacy in the mounted
  document exposes existing edit/insert/reference controls but no governed
  source-to-node/edge action. No document or graph mutation was performed.
  The existing WorldKeeper consumer has no production caller. Its native
  PostgreSQL proof uses a different repository composition from the ordinary
  reviewed-initialized World read path; compatibility is not established by
  sharing a World label or a “v3” name. WORLDKEEPER's read-only owner ruling
  confirms the accepted native runtime cannot consume this legacy parent:
  `bundle.world_graph` and `KnowledgeRevisionRepository` are distinct durable
  authorities, and native materialization rejects a legacy parent. A repin or
  shape wrapper is not a bridge. Preserving this selected World requires an
  explicitly accepted bridge-genesis, authentic source/evidence translation,
  and ordinary-read authority selection. A fresh isolated native World would
  still need a real product initialization/source-admission path, not fixture
  seeding. That minimum prerequisite is routed to existing MIND for an owner
  ruling/design; at that checkpoint no bridge, external merge or fresh genesis
  was authorized. The first-customer direction above now selects fresh native
  rehearsal, while its initialization/source-admission contract remains gated.
  Separately, WORLDKEEPER confirms Buddy's mandatory-campaign mapper is a
  consumer restriction: a bounded extension can use World-global `scope=()`
  without a fake campaign, but that does not solve parent/evidence/read authority.
  Accepted inspected pins: WorldKeeper
  `49a8620f066ce7ef8972a699020c012f50af9158`, DungeonMind
  `0f709d76fdc53bac9c9258d1751463ae2c76ca71`. No J3 implementation is active.
- **DEMO-J4 prepared-checkpoint scope defect:** opening Plan Tools → Statblock
  in Of Conks displays `eldyrwild · longmont-c2` creation defaults. Code
  inspection confirms `LIVE_CONTROL_CREATE_CONTEXT` drives projection
  bootstrap, exact-revision override and freestanding fallback, not just the
  label. The ThreatDraft create contract also requires a nonblank campaign;
  the accepted managed-World Plan context uses world scope / blank nested
  campaign. Generation was not submitted: no threat, model call or foreign
  World write occurred. This is an independent downstream diagnostic, not a
  bypass counted toward connected J3/J4 acceptance. DEMO owns the eventual
  bounded asset-context repair, which must define truthful world-only scope,
  preserve legacy campaign behavior and fail closed on context drift before
  executing. No C2 fallback or invented campaign may make the witness pass.
  PRIME's read-only critique confirmed generation needs no new SERVER argument,
  but found no accepted World-only ThreatDraft contract. The steward's explicit
  versioned scope decision is now durable in
  [`HANDOFF-DEMO-world-scoped-statblock-drafts-v1.md`](../Plans/HANDOFF-DEMO-world-scoped-statblock-drafts-v1.md):
  **ACTIVE after independent design ACCEPT at `de08711183e94065b12b3a4d24765b333a760a1e`**.
  Serial implementation lane: `codex/demo-world-scoped-statblock-drafts`,
  isolated `/tmp/dmb-world-statblocks-fp0eww`, API `8817` / UI `5198`;
  no implementation PR yet at activation. The old #742/#366 handoff ACTIVE
  headers were reconciled to their already-merged historical status to release
  stale preflight overlaps. The 101-test existing draft/generation baseline passes
  outside the sandbox; the sandbox-only in-process route harness stalled and
  was stopped, not reported as passing.
  It proposes one capability: create, generate and reopen a selected-World draft,
  preserving campaign V1 records and rejecting World-only graph publication.
  J3 integration, images and Plan placement remain separate.
  The first implementation checkpoint (historical) opened **draft Buddy #785** at
  `d0afb5c36a34350345a6213d9f7085580cfe6198`, from exact activation/dispatch
  base `d3e0797d64572ef981b9d0f5d03c67ae5261e348`. Its first nano-commit
  implements V2/store lifecycle, unchanged provider-body consumption and the
  owning World-only publication guard; 129 focused backend/authority-port
  regressions, scoped Ruff and diff check pass. Three historical identity-route
  fixtures fail identically on base/head because they reference retired
  `pub_svc.kernel`; not reported green. No new model call ran. API admission,
  mounted UI/attempt recovery, live generation and formal implementation review
  remained outstanding at that checkpoint. The current exact-head code/test
  evidence and unpassed live/review gates are recorded above; #785 is not
  merge-ready and does not close J4.
- **DEMO-J1 input-pin recheck:** the local purchased
  `/home/drakosfire/Downloads/of-conks-cons-v21-gold/specimens/01-cleaned-single-column.md`
  is still 48,778 bytes / 565 lines, SHA-256
  `7a379fc9025635b1862b6af7eb5a43dd1ee9387b51cf63ba505491fffe7e68f1`.
  It is human-normalized parsed Markdown, not proof of production PDF parsing.
  `specimens/02-prepared.md` matches its manufactured-target pin; the actual
  `playable/hempholm-prep.md` remains at the already recorded `c473329d…`
  rather than its stale local manifest pin. Do not use either manufactured
  target as real-generation evidence. Browser Import source currently exposes
  a Markdown paste field, not a file chooser. No new full-source import was
  submitted in this checkpoint, so the long-file browser witness remains open.
- **Shared lease:** #773 released `pyproject.toml`/`uv.lock` by merging first.
  Rules #763 still owns its open PR and must re-anchor against the new main;
  ARCHITECTURE confirmed E5Q is BLOCKED and has no active Buddy dependency-file
  lease. DEMO will not edit Rules or E5Q paths.

## External dependencies and independent programs

DEMO requests only the capability needed for an observed transition. MIND's kernel
program, WORLDKEEPER's lifecycle, ARCHITECTURE's E5 parity, SERVER's production
platform and Rules/Jev work remain separately owned. Shared leases still require
coordination even where acceptance paths are independent.

Do not wait for all of vNext, all provider parity, full hosting, or Canvas F5/F6 by
default. Equally, do not bypass an actually missing contract. A proposed isolated
demo must prove coherent read/write authority and source admission. The current
operator choice removes legacy bridge migration as a DEMO prerequisite, not
native genesis/source authority. If the fresh-native route requires an absent
contract, return that precise gap to MIND rather than reintroducing migration,
fixture seeding or a parallel authority as an implementation shortcut.

### First-customer native return gate — MIND

- **State:** BLOCKED / external contract return; no active Buddy J3 lease.
- **Owner:** existing MIND task `01a0a299-d6ee-7772-83c0-a3a79550479d`;
  PRIME is sending the bounded prerequisite request. Do not create a duplicate
  owner task or silently take over kernel/source policy.
- **Return required:** exact accepted pins and production entry points; how a
  new World with no campaign/recap obtains its native initial parent; how exact
  imported or authored document revisions become admitted source/evidence;
  whether initialization/admission/confirmation are separate durable steps and
  their retry/no-partial-publication behavior; exact profile/World-global scope
  binding; and how normal Buddy reads, Agent retrieval and citations resolve
  the accepted child on that same authority.
- **Owning evidence required:** real persistent empty/new-World plus authentic
  source admission and governed publication/read-back, including replay,
  rejection and restart. A fixture-only initialization proof cannot stand in
  for the normal source path; no future merge/version is invented.
- **DEMO witness after return:** ordinary New World → blank editable Plan before
  import → author/import bounded Of Conks material → inspect inert preparation
  → explicit confirm → later ordinary Agent retrieval/citation → restart.
  No console/SQL/manual-ID repair, forced campaign or synthetic source/graph.
- **Exclusions:** deleting previous demo state, importing legacy graph IDs,
  bridge migration, new DB per World, production C1/C2 changes, and expanding
  #785. The environment/identity/source pins must be recorded before execution.

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
