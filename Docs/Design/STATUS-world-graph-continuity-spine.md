# Current State — World Graph Continuity Spine



**Status:** Current-state guide; not a replacement for architecture or sequencing authority

**Updated:** 2026-08-29 — D.3A mounted graph-engine excision is `COMPLETE` / MERGED Buddy #665 (accepted head `189ffd50157534d192b2af008c48a76d12ccbc4c`; merge `1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b`; 3 formal review cycles; Cycle 3 PASS-equivalent `5059851179`); D.3B physical legacy-package deletion is `DOING` / active lease (`cutover/delete-legacy-graph-engine`; dispatch base `d4a91d7b727c0eae7dd0e09ba068e250b4819b44`); D.3 is not `DONE`

**Active CUTOVER slice:** D.3B physical legacy-package deletion (`cutover/delete-legacy-graph-engine`). Predecessor D.3A / #665 is `COMPLETE` / MERGED. Dispatch base `d4a91d7b727c0eae7dd0e09ba068e250b4819b44`.

**Repository anchor:** `d4a91d7b727c0eae7dd0e09ba068e250b4819b44` (Buddy `main` / D.3B dispatch base; contains D.3A merge `1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b`)

**Dispatch gate:** D.3B physical legacy-package deletion owns the active CUTOVER write lease. Do not mark D.3B `DONE` before merge. Do not invent D.3B merge/review facts. D.3 remains not `DONE` until D.3B merges.

**#536 design predecessor:** `413e808112dc85499651cf232ff71614dc4b18b6`

**DungeonMind pin:** `5ca5d688612349034f8ca490d465af166d883e6e` (DungeonMind PR #47 merge / reviewed-init provenance compatibility; consumed unchanged by #658 and this D.2C3 resume). Historical D.2C2 runtime pin was PR #46 `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b`.

**Architecture:** [`ARCHITECTURE-campaign-supergraph.md`](ARCHITECTURE-campaign-supergraph.md)

**Roadmap:** [`../Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)

**Tracker:** [`../Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)

**Integration roadmap:** [`../Roadmaps/ROADMAP-cross-surface-statblock-demo.md`](../Roadmaps/ROADMAP-cross-surface-statblock-demo.md)

**UI shell (cross-boundary):** [`ARCHITECTURE-surface-interaction-layer.md`](ARCHITECTURE-surface-interaction-layer.md)



## Why this exists



DungeonBuddy's graph work now spans storage, extraction, Graph Review, Recap, Build, Plan, Hermes, Play, mechanics, and DungeonMind whole-world adoption. This document is the concise operational map: what owns truth, how reads and writes move, what the durable product spine established, what the August semantic-adoption spine established, and what remains false.



## Objective in one sentence



Turn raw campaign prose and authored records into governed, correctable World Graph memory that every surface and Hermes can use through exact identity and revision-aware projections, without giving any surface, agent, adapter, or diagnostic analyzer silent write authority.



## Authority stack



1. `ARCHITECTURE-campaign-supergraph.md` — invariants and ownership.

2. `ROADMAP-campaign-supergraph.md` — phases and critical path.

3. `PR-TRACKER-campaign-supergraph.md` — active implementation order.

4. Owning design contracts and current handoffs — one bounded capability.

5. Tests, dogfood, adjudication fixtures, source seals, and reports — evidence that the contract is true.

6. Historical handoffs and old roadmaps — context only.



The repository anchor and external dependency pin above are context for this state guide. They do not freeze future work; after `main` advances, re-read the authority stack and re-anchor this document instead of assuming these hashes remain current.



## Durable model



```text

one world

→ one World Supergraph and graph head

→ campaign-scoped assertions/evidence/chronology/visibility

→ immutable revisions

→ replayable contribution + identity + correction history

→ many bounded projections

→ many surfaces

```



The graph owns durable object identity, relationships, attributes, evidence links, authority metadata, and replayable history. Sessions are projection focus, not graph ownership. Campaigns scope assertions; they do not create a second copy of Mirathorn by default.



## Normal publication write path



```text

Source Artifact / authored record

→ exact ExtractionRun and candidate assertions

→ Graph Review prepare against current parent revision

→ game-facing review and exact assertion selection

→ sealed proposal

→ explicit GM confirm

→ Kernel contribution / identity resolution / validation

→ immutable committed revision

→ atomic graph-head advancement

→ terminal confirm receipt

→ exact committed projection reload

```



### Publication authority rules



- Ingest proposes; it does not publish.

- Graph Review is the human reference confirmation surface.

- The sealed proposal, selected assertion IDs, parent revision, world/campaign/session scope, and receipt identity form the authority boundary.

- Stale proposals fail closed.

- A terminal receipt means publication is known. A subsequent read failure may retry the exact committed projection, never re-confirm.

- Agents may later prepare or propose through typed capabilities, but they must reuse this protocol and cannot bypass GM confirmation.

- Worldbuilding draft elevation is a separate authority decision; draft lore must not be relabeled as played canon to make promotion convenient.



## Correction write path



Architecture already says approved graph corrections are durable authored authority and must survive reconstruction. Contribution-level supersession and retraction remain source-revision-shaped: superseding one contribution removes its support from every assertion the contribution carried. That is correct for replacing a source revision and too broad for a human correction to exactly one defective extracted assertion when unrelated assertions from the same source contribution remain valid.



PR #534 closed that gap with a governed Kernel operation:



```text

published assertion + historical source authority

→ explicit human adjudication/correction target

→ targeted assertion-correction Kernel operation

→ preserve original source contribution as historical authority

→ publish separate authored correction authority

→ retire/contradict only the targeted current assertion

→ immutable descendant revision

→ deterministic replay to the corrected head

```



The synthetic/replay-safe Kernel contract is implemented and merged. It has **not** yet been applied to Eldyrwild. Do not emulate a real correction by direct snapshot editing, a projection exception, a global predicate reversal, or whole-contribution supersession unless the entire source revision is actually being replaced.



## Read path



```text

World Graph revision (head or explicit pin)

→ projection request

   worldId

   campaignId

   focus

   admissibility

   scope mode

   exact node IDs / query

   bounds

→ projection / retrieval result

→ surface or Hermes

→ graph-admitted source anchors for evidence

```



### Read authority rules



- Graph objects are addressed by durable IDs.

- A request reads one coherent revision.

- Visibility and campaign scope fail closed.

- Relationships resolve by exact endpoint IDs within the same admitted projection.

- Hermes discovers facts through graph retrieval and opens only admitted source anchors.

- A graph miss produces a coverage diagnostic or abstention, not arbitrary Markdown search.

- Cache and conversation history may improve continuity or latency; neither is authority.

- Conformance/adjudication reports may explain what a relationship means; they do not become a second graph or mutate the selected revision.



## Candidate versus committed authority



Before confirmation, Graph Review presents an unpublished candidate review lens. After a terminal receipt for the exact review binding, candidate authority ends.



```text

candidate

  preview/review material for an exact run

  may be accepted, rejected, unresolved, or inspect-only



committed

  exact World Graph revision named by the terminal receipt

  affected objects opened by exact durable IDs

  survives graph reload/retrieval

```



The product must not blend these into a hybrid view or use candidate labels to stand in for missing durable objects.



## Product authority spine



### PR380A / GitHub #412 — recap projection contract



Canonical recap prose, mentions, node views, relationships, evidence, and focus metadata are produced from an exact World Graph snapshot plus the selected canonical recap. Recap no longer needs a session preview graph as runtime authority.



### PR380B / GitHub #437 — shared object consumption



Recap and Build consume the same exact-ID World Graph object contract. Recap prose chips, relationship traversal, and Build's pointer-only context resolve durable objects without importing candidate or latest-ingest authority.



### PR380C / GitHub #443 — post-confirm authority transition



Graph Review owns committed-transition state for a typed review binding. On a terminal receipt it freezes the binding, requests the exact committed revision, opens affected objects by durable ID, preserves the receipt on read failure, retries only the exact read, and never re-confirms merely because projection failed.



This closes the post-confirm authority lie. It does not yet replace the pre-confirm preview-union candidate lane or persist receipts across browser reload.



## DungeonMind whole-world semantic spine



The August chain is now part of current state and must not be reconstructed from stale July roadmap text.



| PR | Durable/current meaning |

|---|---|

| #521 | Generalized exact Buddy world-object bridge without product-authority cutover |

| #522 | Whole-world conformance inventory; real adoption gaps fail closed |

| #523 | Re-pin after DungeonMind graph-v5/world-object-v2 and emit the exact residual ledger |

| #525 | Re-pin after DungeonMind PR #28; semantic gaps reduce to 59 relationships |

| #526 | Every relationship residual receives source-grounded adjudication, ownership, and next action |

| #528 | Re-pin after DungeonMind PR #29; relationship state moves `287/59 → 291/55`; remaining relationship debt is Buddy-owned |

| #530 | Three governed explicit adapters move effective state `291/55 → 294/52` without mutating the World Graph |

| #531 | Adjudication continuity carries only across proven descendants with unchanged durable shape/source grounding; effective conformance composes the exact current interpretation |

| #534 | Targeted structural edge-assertion correction: contradict exactly one active support and publish a replacement in one CAS-fenced descendant, with replay and integrity fail-closed proofs |

| #536 | Current-support-aware relationship conformance: durable contradicted/historical edges remain inspectable but do not count as current semantic residuals |



### Post-#566 CUTOVER anchor



PR #566 is merged and non-publishing. Its locked repair authority is

`96cc26fc…` and proves exactly four in-memory node-kind changes:



```text

nodes[item_shatter_mages_tower].kind

nodes[mystery_stone_bridge_river_name].kind

nodes[loc:guilds].kind

nodes[item:torvak-hemp-caravan].kind

```



The five dual-sense residual edges were later packaged as DungeonMind v6 endpoint aspects by Buddy #588 rather than remaining current package-construction blockers. The active re-anchor report keeps canonical Buddy truth separate from

that projection, replaces raw v4 relationship blocker totals with effective

conformance / #566 owning-proof ledgers, and confirms zero unaccounted durable

elements in both views. CUTOVER remains `NOT_READY` because observational

correspondence, snapshot drift/catch-up, living-write ownership, and the

product-authority switch remain unproved. After DungeonMind PR #30

and Buddy PR #571, `WORLD_OBJECT_KIND` is cleared and the 28 identity-lifecycle

shadow fields left `ATTRIBUTE_ASSERTION` **on the pre-`alias_remove` world**.

After PR #583/#585, current lifecycle through `alias_remove` is proven.

Captain/Thrin packaging is `DONE` in #587. Dual-sense packaging is `DONE` in #588.

DungeonMind #31/#32/#33 published v6 aspects and the atomic existing-world

adoption/replay runtime. #602 sealed the exact Eldyrwild adoption-v2 bundle.

The first real PostgreSQL attempt STOPped on contribution evidence identity;

#609 repaired the Buddy export. DungeonMind PR #34 independently accepted

the exact post-#609 snapshot into empty PostgreSQL against unchanged #33

runtime. Exact adoption is no longer Case B acceptance debt. Buddy PR #614

accepted the observational-correspondence design and DungeonMind PR #35

merged the bounded read-only correspondence implementation; its Cycle 3

exact-membership residual is closed by DungeonMind PR #36 (`DONE`: exact

adopted-membership receipt V3, `membership_sha256`, steward-supervised

Eldyrwild V2→V3 promotion; head `6a249b48…`, merge `9a19584d…`, Review

Cycle 3 PASS). The whole-world authority transfer is `CUTOVER_COMPLETE` per

[`HANDOFF-CUTOVER-whole-world-authority-transfer.md`](../Plans/HANDOFF-CUTOVER-whole-world-authority-transfer.md).

The remaining CUTOVER write-side lane is D.3B physical legacy-package

deletion (`DOING` / active lease / Buddy `cutover/delete-legacy-graph-engine`;

dispatch base `d4a91d7b727c0eae7dd0e09ba068e250b4819b44`). Predecessor D.3A / #665 is

`COMPLETE` / MERGED (accepted head `189ffd50157534d192b2af008c48a76d12ccbc4c`; merge `1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b`;

3 formal review cycles; Cycle 3 PASS-equivalent `5059851179`). D.3 is not

`DONE`. Pinned exact-snapshot catch-up is `DEFERRED` (activates only on an

observed `STALE`).



### Current Eldyrwild semantic state



Two governed real-world corrections have now crossed the full design → Kernel → canonical write → replay → formal-current-baseline path. Lysandra remains live through C₁ (`contribution:4c65f668dc95ef4f`). Session-24 false cube→Karsemine location is contradicted without replacement through C₂ (`contribution:6c13bc0f8edf4377`). Historical X₁/X₂ remain inspectable and non-current; current truth contains X₁′ through C₁ and no longer projects X₂.



**Immutable adjudication domain** (`rev:3413bf6f5044cf2680233f5e37c90dcf`):



- relationship semantic count: `346`;

- effectively represented: `294`;

- effective relationship residuals: `52`;

- retained `uses_statblock` mechanics attachments: `2`;

- remaining DungeonMind-owned relationship debt in the exact adjudication domain: `0`;

- original adjudication revision: unchanged historical authority.



**Previous formal effective-conformance baseline** (`P = rev:b90646fb5b135988bd7842cde858c96e`):



- relationship semantic count: `369`;

- effectively represented: `311`;

- effective relationship residuals: `58`;

- retained `uses_statblock` mechanics attachments: `3`;

- parent-relative Lysandra exit delta from Lysandra `P_live`: semantic `0` / represented `+1` / residual `−1` / mechanics `0`.



**Historical pre-closure effective-conformance baseline** (`Q₃ = rev:ba3abde1bfc3659795bcd77bb55eb9f7`):



- relationship semantic count: `367`;

- effectively represented: `311`;

- effective relationship residuals: `56`;

- retained `uses_statblock` mechanics attachments: `3`;

- parent-relative C₃ exit delta from `R_prev`: semantic `−1` / represented `0` / residual `−1` / mechanics `0`.



Previous formal baselines after #549 and Q₄ remain historical (`368 / 311 / 57 / 3` and `366 / 311 / 55 / 3`). Do not carry historical `346 / 294 / 52 / 2`, `369 / 311 / 58 / 3`, or Q₄ values forward as though they were the post-#566 canonical baseline.



The exact post-#583 canonical CUTOVER head is `rev:0c644e56b45bcaac709012206e3e41c2` with payload SHA `0640d7ef…`:



- canonical effective relationship inventory: `323 / 314 / 9 / 3`;

- approved four-kind migration projection: `323 / 318 / 5 / 3`, in memory only;

- live parent `rev:5a7c13ae45c49a65b402920499be72ed` / `2632870e…` is historical;

- the five dual-sense edges were later packaged as DungeonMind v6 endpoint aspects by Buddy #588 rather than remaining current package-construction STOPs.



The residual classes still distinguish Buddy source corrections, compound assertions that are not one atomic relationship, identity-not-relationship cases, insufficient-evidence cases, and unadjudicated residuals. Different classes may require different write authority and therefore different PRs.



### First real correction — closed



```text

historical defective edge X₁:

  npc_lysandra --threatens--> cultists_of_longmont



current corrected edge X₁′:

  cultists_of_longmont --threatens--> npc_lysandra



C₁: contribution:4c65f668dc95ef4f

P_live: rev:dfdf38edbefd734d108832e92467b208

Q_live: rev:b90646fb5b135988bd7842cde858c96e

```



### Second real correction — closed



```text

historical defective edge X₂:

  item-001 --located_in--> pc:karsemine



replacement:

  none (contradiction without replacement)



C₂: contribution:6c13bc0f8edf4377

P: rev:b90646fb5b135988bd7842cde858c96e

Q: rev:b8dfc063bc13a4fb297e83f5f9b313d9

```



### Third real correction — closed



```text

historical defective edge X₃:

  npc_lysandra --leads--> pc:caelynn



replacement:

  none (contradiction without replacement)



C₃: contribution:222c55dadacfa67f

P: rev:b8dfc063bc13a4fb297e83f5f9b313d9

Q₃ / R_current: rev:ba3abde1bfc3659795bcd77bb55eb9f7

```



Integrity heal, Lysandra, Session-24 cube, Session-24 false-leads, closure, PR #566, #587 alias package, #588 dual-sense package, DungeonMind #31/#32/#33, #602 adoption-v2 bundle, #609 evidence identity, DungeonMind #34 exact PostgreSQL existing-world adoption proof, Buddy #614 correspondence design, and DungeonMind #35 read-only observational correspondence are complete. The next step is the exact adopted-membership receipt V3 implementation; do not reopen packaged alias/dual-sense work, redispatch the #34 proof, the #614 design, or the #35 implementation, or treat exact adoption or read-only correspondence as product-authority cutover.



## Current surface state



| Surface | Current graph role | Remaining gap |

|---|---|---|

| Ingest | Creates exact extraction candidates and routes to Graph Review | Primary workflow still carries preview-union-era candidate/materialization concepts |

| Graph Review | Prepares/selects/confirms; post-confirm reads exact committed revision | Direct exact-run candidate presentation; targeted correction UX/protocol is not yet implemented |

| Recap | Reads canonical prose through World Graph recap projection | Shared coordinator/cache/invalidation polish |

| Build | Reads an incoming exact graph object as pointer-only context; authors source documents | Cross-surface pinned agent context and governed worldbuilding elevation |

| Plan | Reads graph objects/references; Hermes is graph-first | Cross-route agent continuity and exact bound mechanics consumption |

| Hermes | Graph retrieval, admitted anchors, same-thread continuity in Plan | Governed writes through human protocol; app-level cross-surface identity |

| Statblock Workbench | Generates, renders, edits, validates, and can publish governed Threat mechanics through its publication bridge | Remaining product/dogfood successors are separate from whole-world semantic correction |

| Play | Existing independent product | World Graph projection/admissibility migration and exact mechanics resolution |



## Product-state vocabulary



Keep these visibly and semantically distinct:



- source prose or authored document;

- extraction candidate;

- inspect-only candidate;

- prepared/sealed proposal;

- terminal confirm receipt;

- committed World Graph object/revision;

- adjudication finding;

- effective conformance interpretation;

- authored graph correction;

- historical source assertion;

- currently active corrected assertion;

- statblock candidate;

- validated definition;

- immutable saved mechanics;

- proposed Threat/statblock binding;

- committed binding;

- Plan graph reference;

- Play runtime instance.



## Current next gates



The PR tracker is the sequencing authority. At this anchor the current gates are:



1. CUTOVER is `CUTOVER_COMPLETE`. DungeonMind owns living Eldyrwild World Graph authority at `D_B=rev:680c246047d67f9fe0293ee90526f670`. Do not redispatch the whole-world transfer, #620 completion, or DungeonMind #34–#37. Do not re-enable Buddy World Graph writers after `D_B`.

2. Fix-forward only on newly observed, reproducible post-cutover failures. Confirm PR #577 remains closed unmerged.

3. In parallel, direct exact-ExtractionRun candidate review, PR380D projection coordination, Ingest simplification, fresh durable-memory dogfood, Hermes governed writes, and Play projection migration retain their tracker statuses.



Closed in this sequence: integrity heal `DONE`, Lysandra `#537` + live exit `DONE`, first effective re-anchor `DONE`, Session-24 `#545` + live exit `DONE`, second effective re-anchor `DONE`, Session-24 false-leads `#550` + live exit `DONE`, third effective re-anchor to `R_current = Q₃` `DONE`, Session-25 descendant residual adjudication `DONE`, Session-25 false-hires C₄ `#559` + canonical `Q₃→Q₄` live exit `DONE`, fourth effective re-anchor to `Q₄` `DONE`, relationship semantic closure `DONE`, PR #566 non-publishing kind-repair authority `DONE`, CUTOVER re-anchor `#568` `DONE`, PR #571 DungeonMind v5 re-pin `DONE`, identity-lifecycle history `#575` `DONE`, Kernel `alias_remove` `#580` `DONE`, exact-six Eldyrwild identity-shadow `alias_remove` `#583` `DONE`, identity lifecycle through `alias_remove` `#585` `DONE`, Captain/Thrin alias package `#587` `DONE`, dual-sense relationship package `#588` `DONE`, DungeonMind `#31/#32/#33` `DONE`, exact Eldyrwild adoption-v2 bundle `#602` `DONE`, first PostgreSQL attempt `STOPPED` on evidence identity, durable contribution evidence identity `#609` `DONE`, DungeonMind `#34` exact PostgreSQL existing-world adoption proof `DONE`, CUTOVER observational-correspondence DESIGN `#614` `DONE`, DungeonMind `#35`/`#36`/`#37` `DONE`, Buddy `#619`/`#620` `DONE`, and the live whole-world authority transfer `CUTOVER_COMPLETE`. PR #577 is a closed unmerged forensic STOP.



## Fast diagnostic questions



When adding or reviewing a feature, ask:



- What exact durable identity owns this object or assertion?

- Which graph revision is being read or corrected?

- Is this candidate, committed memory, historical source authority, effective interpretation, saved mechanics, or runtime state?

- Who is authorized to write it?

- What explicit confirmation, correction target, or receipt proves the transition?

- If this is a correction, what remains historical and what becomes current?

- Does the chosen correction primitive affect unrelated assertions from the same contribution?

- Can a stale async response attach to a different run, campaign, session, revision, or thread?

- Does failure preserve the last known durable authority?

- Is any path silently falling back to preview, latest-ingest, Markdown, labels, current head, or diagnostic overlays?

- Can the graph be reconstructed with approved corrections intact?

- Which obsolete path is deleted when this becomes production-ready?



If those questions do not have exact answers, the capability is not yet on the continuity spine.
