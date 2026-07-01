# Graph Memory Extraction Spike Anchor

**Status:** Spike anchor  
**Created:** 2026-07-01  
**Workstream:** Graph Memory / extraction taxonomy / pass design / consolidation dogfood  
**Base branch:** `main`  
**Primary handoff:** `Docs/Plans/HANDOFF-prime-design-graph-memory-extraction-taxonomy.md`  

## 1. Purpose

This anchor freezes the starting point for a multi-PR spike exploring Graph Memory extraction structure. It is a shared map for later implementation PRs, not a runtime implementation plan, and it does not authorize corpus mutation, canon promotion, or approved-memory writes. The immediate goal is to prepare safe, comparable dogfood work across recap and worldbuilding beds before any extraction behavior changes.

The spike is not asking whether contextual vocabulary is useful. The previous dogfood pass already showed that vocabulary is directionally useful but secondary. The spike is asking which structural extraction changes are worth implementing next: safer consolidation, dedicated passes, minimal node-type expansion, or some combination of those.

This document therefore records the baseline dogfood set, manual review surfaces, must-improve / must-not-regress ledger, review gates, guardrails, and likely PR ladder for future agents.

## 2. Authoritative source docs

| Path | Why it matters |
|---|---|
| `Docs/Plans/HANDOFF-prime-design-graph-memory-extraction-taxonomy.md` | Primary extraction-taxonomy handoff named by this spike; currently missing on this branch, so later agents must restore or identify the intended archived source before treating it as authoritative. |
| `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-MANUAL-REVIEW.md` | Detailed manual review report establishing that vocabulary helps but the larger pressure is extraction structure, consolidation, party context, and qualitative review. |
| `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` | Durable architecture boundary: reusable campaign/worldbuilding union supergraph contracts belong in `src/graph_memory`, while evals remain proof machinery. |
| `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` | Current path-ownership map for graph-memory implementation, eval examples, artifacts, and proven extraction pipeline components. |
| `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md` | Older operational anchor for the union-supergraph / recap-projection workstream, including Session 23 projection goals and the no-hand-authored-local-graph constraint. |
| `Backlog.md` | Current dated observations, especially Mirathorn governance retrieval/ingest pressure and live C2 dogfood lessons that may affect bed selection. |

The missing primary handoff and the older workstream anchor must be reconciled, not treated as competing truths. The vocabulary-ablation report supplies the immediate extraction-structure evidence; the workstream anchor supplies the durable union-supergraph and `/plan` projection direction. Later code PRs should explicitly align those threads before changing graph contracts or extraction passes.

## 3. Current extraction baseline

The table below is the baseline extraction shape this spike is starting from; it is not a complete architecture and does not pre-decide the final taxonomy.

| Pass | Current role | Known pressure |
|---|---|---|
| `actor_pass` | Extracts named non-party NPCs, characters, and creatures. Party PCs are deterministic anchors, not LLM-discovered actors. | Monsters/adversaries are lumped into generic character/actor handling; PC actions are under-captured. |
| `location_pass` | Extracts regions, towns, roads, cities, and sublocations. | Same-label collisions with object/collective outputs remain a problem. |
| `collective_pass` | Extracts factions, councils, guards, organizations, parties, and groups. | Overbroad; can flatten institutions into places or duplicate places as organizations. |
| `object_pass` | Extracts items, devices, artifacts, objects, products, and resources. | Product/resource/fauna explosion in worldbuilding docs. |
| `thread_pass` | Extracts mysteries, clues, warnings, unresolved phenomena, and narrative threads. | Useful for mysteries, but can become a dumping ground for jobs/events/encounters. |
| `beat_pass` | Extracts recap-local scene or beat scaffolding. | Useful source-local structure, but not yet enough for durable encounter/job modeling. |
| `edge_pass` | Extracts relationships over consolidated nodes. | Too broad; edge recall and predicate direction remain weak. |

## 4. Dogfood beds for this spike

| Bed ID | Scope | Primary source | Gold / review artifact | Registry requirement | Why this bed is included |
|---|---|---|---|---|---|
| Bed 1 — C1S1 Stonebridge / Glowkindle Rats | Campaign 1 Session 1 recap, including raw and normalized recap text. | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 1 - Recap 3-27-24.md`; `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md` | `evals/graph_memory_layer/examples/session_1_candidate_graph_gold/` and vocabulary-ablation manual-review artifacts. | Present: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json`. | Small enough for manual review; exposes cross-class duplicate labels, missing rat-clearing job, missing combat encounter shape, PC action/participation gaps, and the invalidated party-registry lesson. |
| Bed 2 — Mirathorn worldbuilding | Mirathorn city / worldbuilding docs rather than recap prose. | Current corpus root present at `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/`. | `evals/graph_memory_layer/examples/mirathorn_city_world_doc/`; `evals/graph_memory_layer/examples/mirathorn_city_candidate_graph_gold/`; vocabulary-ablation manual-review artifacts. | Not a session-recap party-registry bed. | Exposes governance/institution flattening and resource/product/fauna object explosion; protects against C1S1-only overfitting. |
| Bed 3 — C2 live-campaign recap bed | Live Campaign 2 recap projection bed, defaulting to Session 23 while noting current Session 24 files. | Default present: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate Battle.md`; `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md`. Current Session 24 alternatives also exist as `Session 24 - Mireward Gate Battle.md` and `_normalized/Session 24 - Mireward Gate Battle.md`; choose deliberately in the follow-up PR. | Session 23/24 projection and graph-ingest dogfood artifacts where available; later PRs should materialize comparable projection artifacts before review. | Present: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_party_registry.json`. If that registry disappears, C2 session-recap extraction comparison is blocked/conditional. | Keeps the spike tied to live campaign utility, checks rendered `/plan` projection behavior, and prevents optimizing only for old C1S1 and static worldbuilding. |

## 5. Manual dogfood review surfaces

Later PRs must use manual review surfaces, not aggregate metrics alone. The vocabulary-ablation dogfood showed that aggregate recall can hide important qualitative failures: wrong endpoint direction, duplicate cross-class identities, unsupported edges, institutional flattening, and UI-noisy projections.

| Review surface | Path / route | Use |
|---|---|---|
| Manual Review UI | `/plan` → Plan toolbox → Vocabulary Review | Qualitative side-by-side inspection of baseline vs variant graph extraction. |
| Graph Gold Review | `/api/live/graph-preview/gold-review/...` and corresponding UI module if present | Quantitative gold comparison, miss tables, scorecards, and evidence diffs. |
| Rendered recap projection | `/plan` recap projection / campaign review picker | Final check that extracted graph structure is actually useful when rendered as recap pills. |
| Static/manual artifacts | `evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/` | Checked-in review artifacts used by the Manual Review UI. |
| Vocabulary-ablation runner | `evals/graph_memory_layer/run_vocabulary_ablation_expanded_beds_dogfood.py` | Reference runner for expanded-bed vocabulary dogfood; later PRs may compare against its artifacts but should not run LLM extraction in this anchor. |
| Session 1 projection dogfood runner | `evals/graph_memory_layer/run_session_1_projection_dogfood.py` | Reference projection dogfood runner for C1S1; later projection PRs should use comparable rendered-review evidence. |

## 6. Baseline “must improve / must not regress” ledger

| ID | Bed | Baseline concern | Desired movement | Review surface |
|---|---|---|---|---|
| GMX-001 | All session recap beds | Party continuity can be invalid if the campaign lacks `_party_registry.json`. | Do not trust session-recap dogfood results unless the campaign registry exists and deterministic party anchors are active. | Manual Review UI / graph diagnostics |
| GMX-002 | C1S1 | `Stone Bridge` can appear as duplicated cross-class nodes. | Reduce unsafe same-label duplication without false-merging distinct town / bridge / institution concepts. | Manual Review UI / blocked-collision report |
| GMX-003 | C1S1 | `The River's Edge Pub` can appear as place / object / organization-style duplicates. | Prefer safer establishment identity handling, or keep blocked with clear diagnostics if unsafe. | Manual Review UI / blocked-collision report |
| GMX-004 | C1S1 | Rat-clearing job is not represented cleanly as a durable job/quest/task shape. | Extract or represent the accepted job distinctly from generic thread/event prose. | Manual Review UI / Graph Gold Review |
| GMX-005 | C1S1 | Rat fight / cellar combat is not represented cleanly as a combat encounter. | Represent the combat encounter distinctly enough to attach participants, adversaries, location, and outcome. | Manual Review UI / rendered recap projection |
| GMX-006 | C1S1 and C2 recap bed | PCs are deterministic anchors, but their actions and participation are under-captured. | Attach recap actions/participation to known PC anchors without rediscovering duplicate PC nodes. | Manual Review UI / rendered recap projection |
| GMX-007 | C1S1 | Mage tower mystery is a good fit for `thread_pass`. | Preserve it as a thread/mystery; do not reclassify every mystery as an encounter or job. | Manual Review UI |
| GMX-008 | Mirathorn | Governance/institution relationships can flatten council/city structure. | Do not degrade `city council` / mayor / institution relationships into generic city edges. | Manual Review UI / Graph Gold Review |
| GMX-009 | Mirathorn | Resources, products, fauna, and commodities can explode into low-value object nodes. | Avoid worsening object clutter; later resource/ecology modeling should be deliberate. | Manual Review UI |
| GMX-010 | All beds | Edge recall metrics alone hide predicate direction, missing endpoints, and unsupported edges. | Judge edge changes qualitatively with evidence and endpoint review, not aggregate recall alone. | Graph Gold Review / Manual Review UI |
| GMX-011 | Rendered projection beds | JSON-level improvements may not translate into useful `/plan` recap navigation. | Final spike review must inspect rendered recap pills and click-through behavior. | `/plan` rendered recap projection |
| GMX-012 | Mirathorn | Vocabulary can improve spatial containment while weakening historical or institutional relationships. | Preserve location hierarchy gains only when they do not erase council, guard, mayor, or historical-cause structure. | Manual Review UI / Graph Gold Review |
| GMX-013 | All beds | Vocabulary packets can become noisy when absent probes are rendered like source-relevant names. | Keep vocabulary hygiene separate from extraction-structure claims; do not count hallucination-prone packet formatting as taxonomy proof. | Manual Review UI / prompt packet inspection |

## 7. Expected follow-up PR ladder

1. PR 01 — Clean vocabulary packet hygiene. Goal: make source-relevant vocabulary readable and separate absent/background probes before deeper extraction comparisons.
2. PR 02 — Report blocked cross-class collisions. Goal: surface same-label/type conflicts such as Stone Bridge and pub duplicates without merging them silently.
3. PR 03 — Extend cross-class merge policy v0. Goal: add a conservative consolidation policy that improves obvious duplicates while preferring blocked merges over false positives.
4. PR 04 — Design encounter/job taxonomy decision. Goal: decide whether combat encounters and jobs/quests/tasks deserve minimal candidate node types, dedicated passes, or a different representation.
5. PR 05 — Add candidate graph contract support for encounter/job. Goal: add only the durable contract surface needed after the taxonomy decision, keeping reusable contracts under `src/graph_memory`.
6. PR 06 — Prototype encounter/job pass in evals. Goal: prove the chosen shape in dogfood machinery before any runtime integration.
7. PR 07 — Add deterministic PC participation attachment. Goal: attach actions and participation to known party-registry anchors without rediscovering duplicate PCs.
8. PR 08 — Add encounter/job edge-family extraction. Goal: test focused edge families for participants, adversaries, locations, outcomes, accepted jobs, and related evidence.
9. PR 09 — Add dynamic pass-targeted vocabulary spike. Goal: evaluate whether prior context helps specific passes once structural extraction pressure is addressed.
10. PR 10 — Materialize dogfood projection artifacts. Goal: produce comparable projection artifacts for rendered `/plan` review across the spike beds.
11. PR 11 — Write runtime integration handoff for the proven slice. Goal: summarize the proven, reviewed slice and defer unproven ideas before runtime work begins.

## 8. Manual review gates

## Gate A — consolidation diagnostics review

After blocked-collision diagnostics and merge-policy v0, manually review whether duplication improved without false merges.

## Gate B — extraction-shape review

After encounter/job pass, PC participation attachment, and edge-family extraction, manually review Manual Review UI outputs before trusting metrics.

## Gate C — rendered projection review

After projection artifacts are materialized, manually inspect `/plan` rendered recap pills and click-through behavior. This is the final dogfood gate before runtime integration handoff.

Gate C is mandatory because graph JSON can look better while the actual GM-facing surface becomes noisier. A spike result is not ready for runtime handoff until rendered recap pills and click-through behavior are reviewed directly.

## 9. Guardrails

* No corpus mutation.
* No canon promotion.
* No approved-memory writes.
* No LLM extraction in this PR.
* Do not make evals own durable architecture.
* Durable reusable graph contracts belong under `src/graph_memory`.
* `evals/graph_memory_layer` remains proof/dogfood machinery.
* Party membership is deterministic via party registry/context, not LLM extraction.
* Any session-recap dogfood bed without a party registry is not trustworthy.
* Do not let `/plan` invent graph semantics or taxonomy categories.
* Do not judge success from aggregate recall metrics alone.
* Prefer false negatives / blocked merges over false positive identity merges.
* Do not change graph extraction, prompt text, vocabulary rendering, identity resolution, candidate graph preview contracts, fixtures, UI, tests, corpus files, or generated artifacts as part of this anchor.

## 10. Repository path observations

Most required source paths for this anchor were present on `main` at the time this document was added, except paths explicitly marked conditional in the dogfood-bed table and the observations below.

* `Docs/Plans/HANDOFF-prime-design-graph-memory-extraction-taxonomy.md` was not present in the current checkout. No replacement was silently substituted; later agents should recover the intended handoff, identify an archived path, or update this anchor before relying on it as an authoritative source.
* `Docs/Design/CORPUS-ANCHOR.md` was not present; the current nearby corpus anchor path is `Docs/Anchors/CORPUS-ANCHOR.md`.
* The handoff's example Session 24 path `Session 24 - Through the Mire.md` was not present. Current C2 Session 24 recap paths use `Session 24 - Mireward Gate Battle.md` under both the raw and `_normalized` recap folders, while Session 23 remains present at the default bed paths.

## 11. Verification notes for future PRs

Future code PRs should rerun only the specific dogfood/review commands appropriate to their slice. They should not run LLM-backed extraction, regenerate artifacts, mutate canon, or promote approved memory unless their own handoff explicitly authorizes it. Every extraction-changing PR should record:

* which dogfood beds were compared;
* whether required party registries were present;
* which manual review surfaces were inspected;
* which GMX ledger rows improved, regressed, or remained unchanged;
* whether rendered `/plan` recap projection became clearer or noisier.
