---

pr_body_template: |

## Handoff pointer

* Workstream: CON-READY / Of Conks end-to-end dogfood
* Flow: CON-READY
* Direction: STEWARDSHIP → DOGFOOD / MINING
* Handoff: `Docs/Plans/HANDOFF-CON-READY-of-conks-end-to-end-dogfood.md`
* Branch: `dogfood/of-conks-end-to-end`
* PR title: `CON-READY: dogfood Of Conks end to end`

## Important disposition

* This is an exploratory vertical-slice / mining PR.
* It is NOT a wholesale merge candidate.
* Durable capabilities proven here must be extracted into focused successor PRs.
* Dogfood findings live in the checked-in report named by the handoff.

## Base / collision pointer

* Design base: `main` `24f7c25b49fdab8271b0d84d36e4a609b9832d69`
* Base includes merged BF3B / PR #673.
* PR #674 `AGENT-INTERACTION: enable truthful Play Ask` is active at handoff creation.
* Do not edit #674's lease before it merges; rebase and consume it afterward if available.

The checked-in handoff, cumulative exploratory diff, dogfood report, screenshots,
exact browser journeys, and extraction/disposition ledger are the evidence contract.
This PR is not accepted by making its cumulative diff merge-ready.
------------------------------------------------------------------

# HANDOFF — Of Conks & Cons end-to-end dogfood and capability mining

**Created:** 2026-08-31
**Status:** ACTIVE DOGFOOD / MINING — **DO NOT MERGE WHOLESALE**
**Canonical handoff:** `Docs/Plans/HANDOFF-CON-READY-of-conks-end-to-end-dogfood.md`
**Workstream:** `CON-READY / Of Conks end-to-end`
**Owner:** `CON-READY`
**Branch:** `dogfood/of-conks-end-to-end`
**PR title:** `CON-READY: dogfood Of Conks end to end`
**Design base:** `main` `24f7c25b49fdab8271b0d84d36e4a609b9832d69`
**Dogfood report:** `Docs/Reports/REPORT-of-conks-end-to-end-dogfood.md`

> This branch is an intentional exception to the normal rule that one implementation PR delivers one independently useful mergeable capability.
>
> The exception is safe only because **this PR is not a merge unit**.
>
> Its job is to assemble one real vertical product journey, expose where DungeonBuddy works and where it breaks, and produce enough evidence to extract the smallest durable successor capabilities afterward.
>
> Do not “clean up” this branch into a mega-PR and merge it. Do not promote an Of-Conks-specific mechanism into architecture merely because it makes the demo work.

Parent authorities:

* `AGENTS.md`
* `Docs/Roadmaps/ROADMAP-con-ready.md`
* `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
* `Docs/Design/ARCHITECTURE-application-state-layer.md`
* `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
* `Docs/Design/DESIGN-play-current-moment-cockpit.md`
* `Docs/Design/DESIGN-playable-authoring-and-adoption.md`
* `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
* `Docs/Reports/REPORT-pr578-play-dogfood-mining.md`
* `Docs/Plans/HANDOFF-CON-READY-build-lossless-markdown-import.md`
* `Docs/Plans/HANDOFF-BUILD-graph-object-source-navigation.md`

Accepted starting state:

```text
SOURCE / BUILD
  lossless Markdown source ingress exists
  rich Markdown reader exists
  graph evidence → source navigation exists
  local/source-relative asset display does not yet exist

WORLD
  DungeonMind owns World Graph authority
  production reads are DungeonMind-native
  Buddy no longer owns graph architecture/runtime

PLAN
  durable Plan WorkObjects + immutable WorkRevisions exist
  blank Plan authoring exists
  graph/reference interaction exists

PLAYABLE
  durable Runbook WorkObjects + historical WorkRevisions exist
  Beat-first v2 grammar exists
  Beat → Scene / Decision → Option structure exists
  Runbook can be edited through native Plan authoring

PLAY
  durable Run + manifest + Runtime state exist
  active Run continuity exists
  Scene-centered Current Moment exists
  BF3B Scene-owned Decision interaction is merged

GRAPH OBJECT PROJECTION
  PlayGraphObjectSheet exists
  World + Source + Runbook occurrence + exact Threat mechanics composition exists
  native current-Play click/open wiring remains incomplete

AGENT
  A7 current Play SurfaceContext is merged
  A8 truthful Play Ask is active in PR #674 at handoff creation

COMBAT
  existing Combat product/runtime exists
  full CON-READY Combat durability/integration remains incomplete
  generic Play Threat → Add to Combat remains a separate capability

ROLL TABLES
  Markdown tables are readable
  no first-class generic Roll Table product contract is assumed by this handoff
```

---

## §0 Why this dogfood branch exists

The immediate forcing function is simple:

> **Can DungeonBuddy take one real published adventure from source material through preparation and into live play strongly enough that it tells the product story end to end?**

The material is **Of Conks & Cons v2.1**, focused on Hempholm.

This is especially useful because the repository already contains a manually curated source-module surrogate:

`evals/c1s4_preplanning_vertical_slice/support_knowledge/source_module_facts.of_conks_and_cons.json`

It already captures:

* Hempholm;
* the Jove Home;
* the Shacks;
* Morwin's Store;
* Saladin's Mobile Emporium;
* the Grotesque Tree;
* Hollow Root Corridors;
* the Marrow;
* Torbin and Mark Jove;
* Morwin;
* Saladin;
* Narfi;
* Bill the Belly;
* Lord Fiddlestick;
* the Grotesque Tree creature;
* Caretakers;
* the Guardian;
* the Child in the Helix;
* the adventure progression from arrival through the Marrow and later guild consequences.

Its authority is intentionally correct:

```text
SOURCE MODULE
  planning support
  not campaign canon merely because it exists

WORLD
  accepted campaign truth from DungeonMind

PLAYABLE
  the GM's intended adaptation

RUNTIME
  what is happening in this Run
```

That separation is part of the dogfood, not metadata hidden behind it.

### 0.1 Mining law

Carry forward the strongest lesson from PR #578:

> **Preserve the interaction that works. Remove the adventure-specific mechanism that made it work.**

An Of-Conks-specific bridge is acceptable as **temporary dogfood evidence** only when:

1. the generic product seam genuinely does not yet exist;
2. the workaround is isolated and named as temporary;
3. it does not become durable authority;
4. it is entered immediately into the dogfood report;
5. its final disposition is `MINE`, `DISCARD`, or `KEEP AS TEST MATERIAL`.

No `ofConks*` dictionary becomes architecture by inertia.

---

# §1 Dogfood mission and branch invariant

## 1.1 Mission

> **A GM can take Of Conks & Cons from readable source material through a durable adaptation Plan and structured Runbook into a real Play Run, then use source, World Graph context, exact mechanics, authored branching, a useful roll table, and prepared encounter material at the table without reconstructing the adventure from memory.**

The mission is intentionally larger than a mergeable implementation slice.

The branch exists to answer whether the **product journey** works.

## 1.2 Branch invariant

> **Every successful demo interaction must use the real existing DungeonBuddy authority where one exists; every temporary capability must remain visibly dogfood-scoped and non-authoritative; no step may fabricate World truth, Playable identity, Run state, mechanics identity, Agent context, or persistence merely to make the demo appear complete.**

This invariant governs the whole branch.

The acceptable compromise is:

```text
thin / ugly / boutique
```

The unacceptable compromise is:

```text
fake authority / hidden hardcoding / false durability / false provenance
```

## 1.3 Success is not “the demo runs”

Success means we know, with evidence:

```text
what already composes cleanly
what required only content
what required thin product wiring
what required adventure-specific scaffolding
what deserves extraction into a durable capability
what should be thrown away
```

---

# §2 Base, concurrency, and active-lane rules

## 2.1 Base

Current design base:

```text
main
24f7c25b49fdab8271b0d84d36e4a609b9832d69
Merge PR #673
PLAY-SURFACE: make Scene Decisions table-usable
```

Re-fetch immediately before creating the dogfood branch.

If `main` advances, record the exact branch base in this handoff and the PR body.

## 2.2 Active A8 collision

At handoff creation, PR #674 is active:

```text
AGENT-INTERACTION: enable truthful Play Ask
```

Its lease includes, among other paths:

```text
apps/live-control-ui/src/agentInteraction/**
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx
apps/live-control-ui/src/playSurface/PlayAgentInteractionPlugin.tsx
apps/live_control_server/main.py
apps/live_control_server/routes/agent.py
apps/live_control_server/services/agent_*
apps/live_control_server/services/hermes_graph_query.py
apps/live_control_server/services/live_agent_loop.py
```

Until #674 merges:

* do not edit those paths;
* do not duplicate Play Ask;
* do not create a dogfood Agent transport;
* work on disjoint source/content/reference/roll/encounter seams;
* after #674 merges, rebase before consuming it.

If #674 is still open when the demo is otherwise ready, Agent is allowed to remain a truthful omitted station rather than being reimplemented here.

---

# §3 Required end-to-end journey

The branch should optimize for one repeatable golden path.

## Station 1 — Original Source

Open a real Of Conks source document inside DungeonBuddy.

Required:

* normal readable headings and prose;
* at least one table;
* at least one source image displayed through a controlled product path;
* source authority remains visibly distinct from World/Playable truth;
* source-relative media does not expose arbitrary filesystem access.

Preferred source presentation includes representative material for:

* Hempholm;
* the Grotesque Tree;
* the root network / Marrow;
* one useful table or other structured source element.

### Important copyright/storage rule

The repository's existing source surrogate contains hand-authored summaries rather than reproduced module text.

Do not commit copyrighted source PDF/image bytes into the repository merely to make this dogfood portable.

Use an operator-owned lawful local source bundle or existing source ingress/storage capability.

The dogfood report may record filenames, digests, dimensions, and semantic role without copying protected source content into Git.

---

## Station 2 — Adaptation Plan

Create a real durable Plan:

```text
Of Conks & Cons — Hempholm Adaptation
```

The Plan should make the authority boundary useful rather than academic.

Representative sections:

```text
Source premise
What already exists in this campaign/world
Adaptation decisions
Important people and places
Threats / mechanics
Runbook shape
Open questions / changes from source
```

Required:

* real `kind=plan` WorkObject;
* ordinary Plan Save;
* immutable WorkRevision;
* hard reload;
* World references use real graph identity where available;
* Source facts not accepted into World remain labeled/source-grounded rather than silently canonized.

At minimum, exercise graph-backed context around:

* Hempholm;
* the Grotesque Tree;
* one important NPC;
* one deeper/root-network object if available in the current graph.

---

## Station 3 — Real Runbook

Create a real v2 `kind=runbook` WorkObject representing the version intended to run.

Use the source adventure shape as the starting spine rather than recreating PR #578's hardcoded scene deck.

Target structure should be approximately:

```text
Runbook — Of Conks & Cons: Hempholm

Beat — Arrival / The Visible Problem
  Scene — Hempholm / Jove Home
  Scene — The Grotesque Tree
  Decision where useful

Beat — False Victory
  Scene — The Shacks / Premature Celebration

Beat — Retaliation
  Scene — Caretaker Rampage
  Decision where useful

Beat — Descent
  Scene — Hollow Root Corridors
  Scene — Guardian / approach to the Marrow

Beat — The Marrow
  Scene — The Marrow
  Decision — disposition of the strange child / helix problem

Optional / continuation
  Mages' Guild cleanup or another future consequence
```

Exact prose and authored Options belong to the GM adaptation and need not reproduce the original module wording.

Required:

* stable Beat/Scene/Decision/Option IDs;
* ordinary native Runbook Save;
* immutable WorkRevision;
* hard reopen;
* graph references point at real graph identities where one exists;
* source-only adaptation remains Playable rather than becoming World truth.

---

## Station 4 — Start and Run Play

Start a **real Run** from the exact committed Runbook revision.

Required:

```text
Runbook WorkRevision N
→ Start Run
→ sealed manifest
→ READY
→ current Beat
→ current Scene
→ Scene-centered cockpit
```

Exercise:

* current Scene framing;
* one authored Decision;
* select Option;
* change Option;
* clear/reselect if useful;
* `activates` / `suppresses` relevance;
* inspect another Scene without moving current position;
* explicit Make Current;
* hard reload and resume exact current moment.

No demo-local Runtime state may substitute for the real Run.

---

## Station 5 — World / Source / Mechanics inspection

From Plan or Play, open at least one important object through the normal projection architecture.

Preferred witness:

```text
Grotesque Tree
```

The useful interaction is:

```text
Runbook / current Scene reference
→ exact World Graph resolution
→ PlayGraphObjectSheet
→ World identity
→ relationships
→ Source evidence
→ Runbook occurrence
→ exact mechanics when a valid mechanics binding exists
```

Required:

* exact graph scope/revision remains authoritative;
* relationship navigation stays revision/campaign safe;
* source evidence uses the existing source-navigation contract;
* no `ofConksPlayObjectBridge`;
* no fabricated local graph projection;
* no copied World object body stored in the Runbook.

If native reference → object-sheet opening is missing, implement the smallest dogfood wiring necessary and mark it `MINE CANDIDATE` immediately.

---

## Station 6 — Roll Table

The demo needs one table action that feels useful at the table.

This branch does **not** need to solve generic Roll Table architecture.

Minimum acceptable interaction:

```text
recognized/adopted table
→ readable table
→ Roll
→ one result selected/highlighted
```

Rules:

* table rows remain authored/source/Playable material;
* the random result is ephemeral unless a real persistence requirement emerges;
* do not invent a universal RollTable database model;
* do not publish rolled outcomes to World;
* use actual Of Conks material when the lawful source bundle supplies an appropriate table;
* if the module does not provide a suitable random table, use an explicitly GM-authored adaptation table and label it Playable rather than Source.

Any reusable Roll interaction discovered here should be mined as its own successor.

---

## Station 7 — Prepared encounter / Combat

The demo should show that known fights are runnable.

Do **not** make generic Combat completion a prerequisite.

Prepare boutique, bounded encounter projections for representative Of Conks fights, preferably:

```text
Grotesque Tree
Caretaker Rampage
Guardian / Marrow
```

Acceptable for this dogfood:

* static prepared encounter page;
* exact known mechanics projected where available;
* combatants / quantities / encounter notes;
* links back to relevant World/Source/Runbook objects;
* clearly local/boutique presentation.

Not acceptable:

* claiming CR-U13/CR-U14/CR-U17 are complete;
* inventing fake persistent Combat;
* silently copying authoritative statblocks into adventure-local JSON;
* generalizing P4 Add-to-Combat inside this branch without separately earning it.

If the existing Combat runtime can be composed cheaply and truthfully, use it.

If not, a prepared encounter sheet is better than fake generic integration.

---

## Station 8 — Agent, if A8 lands

If PR #674 is merged and the dogfood branch has rebased onto it, exercise truthful Play Ask.

Representative question:

```text
What matters about the Grotesque Tree right now?
```

or:

```text
What do I know about the tree, and what matters in this Scene?
```

Required:

* current Play context comes from real Run APP-STATE;
* World retrieval remains governed;
* Source follow-through retains authority distinctions;
* advanced trace shows the real model calls/tokens/cost/timing;
* no dogfood Agent prompt/runtime fork.

If A8 does not land in time, record `NOT EXERCISED — active predecessor` in the report.

---

# §4 Demo material and authority map

Use this authority model explicitly while building content:

| Material                                        | Authority                       | Dogfood use                                        |
| ----------------------------------------------- | ------------------------------- | -------------------------------------------------- |
| Original Of Conks source prose/images/tables    | SOURCE                          | Read/reference; never automatically campaign canon |
| `source_module_facts.of_conks_and_cons.json`    | SOURCE SUPPORT / eval surrogate | Bootstrap planning and fixture understanding       |
| Existing Eldyrwild/Hempholm DungeonMind objects | WORLD                           | Durable accepted campaign identity/facts           |
| Of Conks adaptation Plan                        | BUDDY PLAN                      | GM reasoning and adaptation                        |
| Of Conks Runbook                                | PLAYABLE                        | Intended table material                            |
| Current Beat/Scene/Decision selection           | PLAY RUNTIME                    | What is current in this Run                        |
| Accepted statblock revision                     | MECHANICS                       | Exact mechanics authority                          |
| Prepared encounter sheet                        | PLAYABLE / projection           | Prep unless actual Combat runtime owns live state  |
| Rolled table result                             | EPHEMERAL PLAY interaction      | Do not persist unless separately justified         |

A source fact and a World fact may disagree.

That is not a demo failure.

The product must make the difference understandable.

---

# §5 Source images / asset experiment

Image display is a first-class dogfood target because the current Markdown reader intentionally refuses local/relative media as renderable web content.

The branch may prototype the smallest safe source-relative asset seam.

## Required safety properties

```text
SourceArtifact / workspace source
+ safe relative media reference
+ source-owned asset root
→ controlled HTTP asset resolution
→ Markdown reader image
```

Must remain false:

```text
relative path → arbitrary repo path
relative path → file:// URL
browser supplies trusted filesystem path
../ path traversal
absolute host filesystem access
image bytes become World Graph state
Play owns source media
```

The experiment should answer:

1. What should identify an attached source asset?
2. Can relative Markdown refs survive import without rewrite?
3. Where should the browser resolve them?
4. What is the smallest safe server authority?
5. Does this need full Asset-domain identity now, or can a source-relative attachment remain a narrower first capability?
6. What migration path exists toward the Asset service / DungeonMindServer byte-storage architecture?

Do not solve those questions by silently declaring a permanent contract on this branch.

A useful reusable seam should be extracted after dogfood.

---

# §6 Explicitly acceptable dogfood shortcuts

These are allowed when isolated and recorded.

### Acceptable

* manually preparing the Of Conks Plan content;
* manually preparing the Runbook from the source surrogate;
* local operator-owned source asset bundle;
* adventure-specific CSS/presentation under a clearly dogfood-only module;
* a small hardcoded list saying which three prepared encounter sheets exist;
* a boutique Roll projection over known table rows;
* temporary wiring from a known Runbook reference into an already-real generic object sheet;
* fixture/setup scripts whose only purpose is reproducible dogfood state.

### Not acceptable

* fake graph nodes;
* fake DungeonMind revision IDs;
* fake accepted statblock bindings;
* browser-local replacement for Run Runtime;
* copying Runbook state into a dogfood JSON authority;
* fake SourceArtifact provenance;
* hidden `ofConks*` registries pretending to be generic APIs;
* new permanent storage formats merely because the demo needs persistence;
* bypassing APP-STATE because setup is inconvenient;
* arbitrary filesystem/image serving;
* silently modifying World truth to make source material match;
* implementing around an active write lease.

---

# §7 Write lease and bounded discovery

Because this is a mining PR rather than a merge candidate, the lease is deliberately broader than an ordinary implementation slice, but it is **not unlimited**.

## 7.1 Always allowed

| Action          | Path                                                                                                 | Purpose                                                                                                                                                                         |
| --------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Modify          | `Docs/Plans/HANDOFF-CON-READY-of-conks-end-to-end-dogfood.md`                                        | Record base changes and final dogfood disposition only; do not rewrite original constraints.                                                                                    |
| Create / Modify | `Docs/Reports/REPORT-of-conks-end-to-end-dogfood.md`                                                 | Living evidence and learning ledger.                                                                                                                                            |
| Read only       | `evals/c1s4_preplanning_vertical_slice/support_knowledge/source_module_facts.of_conks_and_cons.json` | Existing source-module seed.                                                                                                                                                    |
| Create / Modify | `evals/of_conks_end_to_end_dogfood/`                                                                 | Dogfood-only metadata, setup fixtures, derived summaries, screenshots/manifests where licensing permits. No copyrighted source bytes without explicit redistribution authority. |

## 7.2 Expected source/media seam

Likely paths include:

```text
apps/live-control-ui/src/markdownReader/MarkdownDocumentReader.tsx
apps/live-control-ui/src/markdownReader/markdownReaderUrlPolicy.ts
owning markdown-reader tests / CSS

apps/live_control_server/routes/workspace_documents.py
or a new narrowly owned source-asset route/service
owning source-asset tests
```

Do not force these exact implementation details if current code offers a cleaner seam.

## 7.3 Expected Play/reference seam

Likely paths include:

```text
apps/live-control-ui/src/playSurface/reference/**
apps/live-control-ui/src/playSurface/currentMoment/**
native Runbook/reference projection tests
```

Use the existing Projection host.

Do not create a second projection host/provider.

## 7.4 Dogfood-only presentation seam

New dogfood-only components may live under one clearly named root such as:

```text
apps/live-control-ui/src/dogfood/ofConks/**
```

or the nearest existing surface-owned equivalent discovered from current code.

Keep temporary adventure-specific behavior physically easy to delete.

## 7.5 Bounded discovery exception

Before editing any path not already named above:

```text
1. record the path in REPORT-of-conks-end-to-end-dogfood.md;
2. record which demo station requires it;
3. record current owner / active-PR collision status;
4. state whether the change is:
   EXISTING-SEAM WIRING
   DOGFOOD-ONLY
   or CANDIDATE DURABLE CAPABILITY;
5. only then edit.
```

Maximum unplanned production paths before steward re-evaluation: **20**.

Crossing that threshold means the dogfood has stopped being a thin vertical assembly and should be re-decomposed before continuing.

## 7.6 Active #674 paths

Until PR #674 merges, its changed paths are read-only to this branch.

After merge:

* rebase;
* consume A8;
* avoid modifying Agent internals unless an actual dogfood defect requires a separately recorded successor;
* `PlaySurfacePage.tsx` may be touched only if composition genuinely requires it and no narrower seam exists.

---

# §8 Required dogfood evidence

This PR does not have a normal merge gate.

It has an **evidence-completeness gate**.

## 8.1 Reproducible browser journey

Record one exact journey:

```text
1. start clean local product
2. open Of Conks Source
3. show image + table
4. open adaptation Plan
5. inspect real World reference / source
6. open/edit Runbook
7. Start exact Run
8. reach current Scene
9. select authored Decision Option
10. inspect Grotesque Tree or another real graph object
11. open exact mechanics where available
12. roll one table
13. open prepared encounter
14. Ask Agent if A8 is available
15. hard reload
16. resume exact Run/current moment
```

Record:

* exact branch head;
* APP-STATE database/setup used;
* World/campaign/revision;
* Plan object/revision;
* Runbook object/revision;
* Run ID;
* screenshots;
* failures/workarounds;
* whether the step was generic product behavior or dogfood-only behavior.

## 8.2 Truthfulness adversaries

At minimum test these manually or automatically:

| Adversary                                                         | Required result                                                                     |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Source module contains geography not accepted into campaign World | Source remains readable without becoming World truth                                |
| World object has richer Source evidence                           | Source opens through governed navigation                                            |
| Runbook references object                                         | Reference opens existing generic projection; Runbook does not own copied graph body |
| Hard reload during Run                                            | Same Run/current moment resumes                                                     |
| Change Decision Option                                            | returned authoritative Runtime drives presentation                                  |
| Inspect ≠ Make Current                                            | inspection never silently moves Runtime                                             |
| Source image has `../` traversal                                  | refuse                                                                              |
| Source image missing                                              | visible broken/unresolved media state; no guessed filesystem fallback               |
| Exact mechanics absent                                            | say unavailable; do not fabricate statblock                                         |
| Combat is boutique                                                | UI/report labels it as such; do not claim generic Combat completion                 |
| A8 unavailable                                                    | omit Agent station truthfully                                                       |

## 8.3 Automated evidence

Run focused existing suites for every permanent seam modified.

At minimum:

```bash
# relevant frontend focused tests
npm run typecheck
npm run build

# relevant backend focused tests
uv run pytest <owning dogfood/source/reference tests>

git diff --check
git diff --name-only <base>...HEAD
```

Do not require the cumulative branch to satisfy ordinary merge-ready scope rules.

Do require no unexplained failures in a reusable seam the branch intends to mark `MINE`.

---

# §9 Living dogfood report

The **first dogfood-branch commit** should create:

`Docs/Reports/REPORT-of-conks-end-to-end-dogfood.md`

The report is evidence, not architecture authority.

Use this structure.

```text
# Of Conks & Cons end-to-end dogfood report

Status:
Branch:
Current head:
Dogfood date:
Operator:
World / campaign:
Plan:
Runbook:
Run:

## 1. Golden-path status

| Station | Status | Generic / dogfood-only | Evidence |
| Source |
| Plan |
| Runbook |
| Play |
| World/object |
| Mechanics |
| Roll |
| Encounter/Combat |
| Agent |
| Reload |

## 2. Learning ledger

| ID | Observation | Type | Severity | Evidence | Candidate disposition |
| OC-001 | ... | MAGIC / FRICTION / DEFECT / ARCHITECTURE SIGNAL / CONTENT | ... | ... | MINE / DISCARD / KEEP TEST |

## 3. Dogfood-only mechanisms

| Mechanism | Why it exists | Generic seam missing | Safe to delete? | Disposition |
| ... |

## 4. Product magic moments

What felt materially faster, clearer, or safer than ordinary notes/PDF/manual memory?

## 5. Friction

Where did the GM have to understand internal product architecture or reconstruct context?

## 6. Authority/truth problems

Any point where Source / World / Playable / Runtime / Mechanics boundaries were confusing or false.

## 7. Performance / table-speed observations

Load times, clicks, interruption cost, visual hierarchy, Agent latency where relevant.

## 8. Extraction candidates

| Priority | Candidate capability | Owning flow | Why independently useful | Suggested handoff |
| ... |

## 9. Things to discard

Dogfood glue or ideas that should not survive.

## 10. Final disposition

DO NOT MERGE WHOLESALE.

List:
- commits/files worth mining;
- successor PRs required;
- fixture/content worth retaining;
- branch portions to discard.
```

### 9.1 Learning rule

Record a finding when it occurs.

Do not wait until the end and reconstruct the experience from memory.

The report is part of the experiment.

---

# §10 Capability extraction taxonomy

Every non-content change must leave the dogfood with one of four dispositions.

## KEEP AS TEST MATERIAL

Examples:

* Of Conks source surrogate;
* Runbook fixture;
* representative encounter fixture;
* screenshot/eval fixture;
* repeatable setup script.

This material may survive because it is useful regression/dogfood material, not because Of Conks is product ontology.

## MINE

The interaction proved generically useful and should receive a normal focused handoff.

Likely candidates before dogfood include:

```text
source-relative asset resolution / rendering
native Runbook/Play reference → graph object sheet open
first-class lightweight Roll Table interaction
prepared encounter projection / Combat composition
generic current-moment contextual object inventory
```

Dogfood evidence decides whether these are actually warranted.

## DISCARD

The interaction was useful but the mechanism was adventure-specific or structurally wrong.

Delete it after extracting the lesson.

## ALREADY PRODUCT

No new capability was needed; Of Conks simply exercised existing architecture successfully.

This is a positive result.

Do not create unnecessary successor work merely because the dogfood touched the feature.

---

# §11 Expected post-dogfood successor decomposition

Do not pre-commit to this sequence, but use it as the initial hypothesis.

### Candidate A — Source-relative assets

Possible owner:

```text
SOURCE / BUILD / CON-READY
```

Outcome:

```text
imported/readable SourceArtifact can safely resolve its own attached media
```

### Candidate B — Native Play graph-reference opening

Possible owner:

```text
PLAY-SURFACE
```

Outcome:

```text
current Runbook reference
→ exact generic graph object sheet
→ return to same current moment
```

### Candidate C — Lightweight Roll interaction

Possible owner:

```text
PLAY-SURFACE or shared Playable projection
```

Outcome:

```text
authored table
→ table-facing roll
→ highlighted ephemeral result
```

### Candidate D — Prepared encounter composition

Possible owner:

```text
COMBAT / PLAY-SURFACE
```

The dogfood must determine whether the useful capability is:

```text
prepared encounter sheet
```

or:

```text
real Play → Combat handoff
```

Do not assume they are the same slice.

### Candidate E — Contextual At-a-Glance inventory

Only create if Of Conks proves repeatedly that current Scene needs direct NPC/Location/Threat/Table presence beyond existing Scenes.

Do not build BF3C merely because the roadmap predicts it.

---

# §12 Stop conditions

Stop the relevant experiment rather than hiding the problem if:

* the demo requires creating fake World graph identity;
* a source asset requires arbitrary filesystem serving;
* source-relative image support requires committing copyrighted module bytes to a public repository;
* Runbook reference opening requires a second Projection host;
* exact mechanics cannot be reached without copying accepted statblocks into dogfood data;
* a Roll experiment starts creating a permanent persisted RollTable schema;
* Combat requires pretending ephemeral state is durable;
* Agent work collides with active #674;
* the dogfood begins mutating DungeonMind merely to make source and campaign state agree;
* an adventure-specific dictionary starts being consumed by generic production code as if it were authority;
* more than 20 unplanned production paths are required;
* the branch begins looking like a plausible wholesale merge.

For each stop:

```text
Dogfood station:
Observed blocker:
Why truthful completion is blocked:
Existing authority involved:
Temporary workaround considered:
Why accepted / rejected:
Candidate durable successor:
Can the remaining golden path continue without it?
```

---

# §13 Final handback

The final dogfood handback must include:

1. exact branch/head;
2. final golden-path status for every station;
3. screenshots of the important journey;
4. exact Plan ID/revision used;
5. exact Runbook ID/revision used;
6. exact Run ID/current Beat/current Scene witness;
7. exact World/campaign/revision witness;
8. image/asset mechanism used;
9. graph-object opening mechanism used;
10. Roll mechanism used;
11. encounter/Combat mechanism used;
12. Agent status and #674 relationship;
13. hard-reload result;
14. complete learning ledger;
15. every dogfood-only mechanism;
16. every candidate capability to mine;
17. every mechanism to discard;
18. files/fixtures worth retaining;
19. a proposed successor order based on observed friction rather than prior roadmap expectation;
20. explicit statement:

```text
WHOLESALE MERGE: PROHIBITED
```

The steward then chooses extraction successors one at a time under normal `AGENTS.md` law.

---

# §14 Dogfood acceptance rubric

This experiment is complete when:

* [ ] Of Conks source is readable inside DungeonBuddy.
* [ ] At least one source image displays through a controlled product path.
* [ ] At least one table is useful in the source/Playable journey.
* [ ] A real durable Of Conks adaptation Plan exists and survives reload.
* [ ] A real durable v2 Of Conks Runbook exists and survives reload.
* [ ] A real Run starts from an exact Runbook WorkRevision.
* [ ] Scene-centered Play is usable on the Of Conks material.
* [ ] At least one authored Decision is exercised through Runtime.
* [ ] At least one real World object is opened from the journey.
* [ ] Source evidence is reachable without manual file hunting.
* [ ] Exact mechanics are shown where accepted mechanics actually exist.
* [ ] A useful roll interaction is demonstrated.
* [ ] Prepared encounter material is reachable and truthfully scoped.
* [ ] Play Ask is exercised if merged A8 is available; otherwise the omission is recorded truthfully.
* [ ] Hard reload returns to the same Run/current moment.
* [ ] Every dogfood-only mechanism is named.
* [ ] Every meaningful finding is in the living report.
* [ ] Every candidate durable capability has an owning flow and bounded proposed outcome.
* [ ] No source/World/Playable/Runtime/Mechanics authority was faked.
* [ ] No copyrighted source asset was committed without redistribution authority.
* [ ] The branch is explicitly handed back as mining evidence, not a mega-PR.

The product question at the end is not:

> Did every box work?

It is:

> **After using DungeonBuddy this way, which pieces made running the adventure materially better, and what is the smallest durable product work required to make those pieces ordinary rather than dogfood?**
