# Graph Memory Vocabulary Ablation Dogfood - Manual Review

Date: 2026-06-30
Model: `gpt-5.4-mini`
Scope: expanded vocabulary ablation beds, manually reviewed

**Update (2026-06-30):** C1S1 was rerun with a real Campaign 1 `_party_registry.json` (session 1 roster). The original C1S1 run invoked `build_party_context_for_campaign` but had **no registry file**, so party anchors were empty. Findings about "missing party identity" in the first manual review are **invalid for the product pipeline** and are superseded by §3.5 and the revised §4.

## 1. Re-anchored Goal

The goal is not to make a one-off extractor match a hand-authored gold file by exact labels. The goal is a generalizable ingestion pathway that can take in corpus, worldbuilding, personal, and campaign material; construct a stable global knowledge graph; support LLM context enhancement; and project useful slices into the command board.

That means the important question is:

```text
Does contextual vocabulary help the extraction pipeline preserve stable identity, source-grounded structure, and useful relationship shape without forcing unsupported canon?
```

Gold remains useful as a review key, but strict gold matching is not the product definition. The product definition is a graph that a GM can query and inspect: people, places, factions, events, mysteries, institutions, and containment should be recognizable, source-grounded, and projected coherently.

## 2. Artifacts Reviewed

- Metric report: `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-EXPANDED-BEDS.md`
- Prompt review: `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-PROMPT-REVIEW.md`
- Manual review bundle: `evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/baseline_vs_edge_and_node_manual_review.json`
- Manual review summary: `evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/baseline_vs_edge_and_node_manual_review.md`
- Raw candidate graphs:
  - `evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/c1s1-stonebridge_baseline_candidate_graph.json`
  - `evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/c1s1-stonebridge_edge_and_node_packet_candidate_graph.json`
  - `evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/mirathorn-city_baseline_candidate_graph.json`
  - `evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/mirathorn-city_edge_and_node_packet_candidate_graph.json`

The primary qualitative comparison below focuses on `baseline` vs `edge_and_node_packet`, because that is the clearest before/after version of "no vocabulary" vs "node and edge vocabulary injected."

## 3. High-Level Verdict

Contextual vocabulary is directionally useful, but not ready to promote as-is.

It helps most when the task is:

- recognizing source-relevant names that the baseline omitted;
- stabilizing some obvious location containment;
- nudging the edge pass toward more concrete relationship predicates;
- exposing whether packet content itself is malformed or too suggestive.

It hurts or remains weak when the task is:

- preserving institutional structure (Mirathorn);
- keeping species/resources/products at the right graph granularity;
- avoiding duplicate cross-class nodes caused by same-label entries;
- modeling events/encounters/jobs as first-class graph objects;
- recovering operational/job/encounter edges even when party anchors are present.

The strongest positive bed is still C1S1 for vocabulary-assisted recognition and relationship shape. The strongest warning bed is Mirathorn: vocabulary improved location projection but weakened institutional/global identity.

## 3.5 Corrected C1S1 Rerun — Party Registry Present

After adding `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json` with session `1` roster (`baergrom`, `bonogo`, `caelynn`, `ephanna`, `karsemine`, `stafl`) and rerunning `--bed c1s1-stonebridge`:

| Variant | Nodes | Edges | Node recall | Edge recall | Recognition | Party anchors | Collective + member edges |
|---|---:|---:|---:|---:|---:|---|---|
| `baseline` | 47 | 28 | **0.769** | **0.292** | 6/7 | 6 inserted | yes / 6 |
| `edge_and_node_packet` | 47 | 25 | 0.692 | 0.292 | **7/7** | 6 inserted | yes / 6 |

Diagnostics now show `session_graph_context_warnings: []` and `inserted_party_anchor_slugs: ['baergrom', 'bonogo', 'caelynn', 'ephanna', 'karsemine', 'stafl']`.

**What changed vs the invalid first run:**

- Node recall on baseline jumped from **0.50 → 0.77** without vocabulary help.
- Edge recall on baseline jumped from **0.04 → 0.29** because `Heroes / party`, PC nodes, and deterministic `member_of` edges now exist for endpoint binding.
- The prior "baseline misses all PCs and party aggregate" finding was a **setup gap**, not evidence that the extractor cannot preserve party continuity.

**What did not change:**

- Same-label cross-class duplication (`Stone Bridge`, pub, brewery as place + collective + object) remains in both variants.
- Operational edges (job acceptance, Grishna operates pub, cellar containment, rat fight structure) remain largely missing at ~29% edge recall.
- Vocabulary still improves present-set recognition (7/7 vs 6/7) but does not beat baseline on node recall once party context is active.

**Interpretation:** Party membership is a **deterministic context** problem solved by `_party_registry.json` + `merge_party_anchor_nodes` / `merge_party_collective`, not by vocabulary packets. Vocabulary's additive value on C1S1 is narrower than the first report claimed: recognition nudge, some `located_in` shape, richer threads — not "recovering the party."

## 4. C1S1 Stonebridge Review (Corrected Party-Context Rerun)

Artifacts: `evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/c1s1-stonebridge_baseline_candidate_graph.json` and `..._edge_and_node_packet_candidate_graph.json` (generated 2026-06-30T20:19:17Z).

### 4.1 Baseline Strengths

With party registry active, baseline already delivers the continuity structure the first report said was missing:

- deterministic PC anchors for all six roster members (`context_anchor` character nodes with resolved corpus refs);
- `Heroes / party` collective anchor;
- six deterministic `member_of` edges;
- scene nouns: `Stone Bridge`, pub, brewery, `Glowkindle`, `Grishna`, gnomes, cellar/rat/spider material.

Useful extracted edges still include containment and scene relationships (`contains`, `within`, `located_in`, `member_of`, etc.) even though many gold operational edges remain missing.

Node recall **0.77** and edge recall **0.29** — substantially above the invalid no-registry run (0.50 / 0.04).

### 4.2 Baseline Weaknesses

Cross-class duplication remains the main structural pathology:

- `Stone Bridge` as place, faction, and object;
- `The River's Edge Pub` as place, organization, and object;
- `The Wizard's Tower Brewing Co` as place, organization, and object;
- `shatter mages tower` across location/faction/object classes.

Edge recall is still weak (~29%): missing job-board placement, Grishna operates pub, Glowkindle operates brewery, party accepts job, cellar/rat fight composition, etc. These are **extraction/pass-shape** gaps, not party-context gaps.

Some edges remain semantically awkward (ownership direction, cause modeling) as in the first review.

### 4.3 Edge+Node Vocabulary Strengths

With party context present, vocabulary's clearest win is **present-set recognition (7/7 vs 6/7)** without absent-set contamination.

It still adds useful relationship and thread material in some runs:

- more `located_in` edges (8 vs 2 on baseline in this rerun);
- richer thread/mystery nodes for tower interior and rat-cellar aftermath;
- continued help surfacing `Glowkindle`, `Grishna`, and scene locations when the baseline partition misses a present-set name.

Vocabulary is **not** the primary mechanism for party identity in this bed; the registry is.

### 4.4 Edge+Node Vocabulary Weaknesses

Node recall is **lower** than baseline with party context active (0.69 vs 0.77) while edge recall is flat (0.29). Vocabulary did not unlock additional gold edge coverage in this rerun.

Cross-class duplication persists. Object pass bloat increases (18 object nodes vs 10 baseline) without improving command-board clarity.

Bad do-not-merge probe hints in the dogfood packet remain a prompt hygiene issue.

### 4.5 C1S1 Interpretation

C1S1 supports two separate conclusions:

1. **Party context is mandatory and works** when `_party_registry.json` exists — rerun falsifies using "missing PCs" as evidence against vocabulary or baseline extraction.
2. **Vocabulary is directionally useful but not dominant** once party anchors land: modest recognition gain, some relationship/thread enrichment, no edge-recall win, continued type-collision noise.

The next leverage on C1S1 is consolidation/type arbitration and event/job edge passes — not re-deriving party membership from vocabulary or actor pass alone.

## 5. Mirathorn World Doc Review

### 5.1 Baseline Strengths

The Mirathorn baseline is already strong. It captures:

- city leadership characters;
- city council representation lanes;
- `Elderwyld`, `Stormspire Peaks`, `Lake Mirathorn`, and `Mirathorn`;
- market, academy, docks, inn, temple, gates, walls, out town;
- `Shepherd's Flock`;
- `Wizard's College`;
- founding pressure from the `Lundayell Empire`;
- civic tensions, guard corruption, cult activity, and protest/festival pressure.

It also constructs useful edges:

- `Elara Swiftwind leads Mirathorn City Council`
- `Commander Thalia Ashenvale commands Mirathorn Guard`
- `Headmaster Tinkerbright leads Wizard's College`
- `Stormspire Peaks near Mirathorn`
- `Lake Mirathorn near Mirathorn`
- `Grand Market within Mirathorn`
- `Temple of the Nameless Goddess within Mirathorn`
- `Shepherd's Flock participates_in Main gates of Mirathorn`
- `Mirathorn Guard distrusts Shepherd's Flock`

This is already a useful command-board world slice.

### 5.2 Baseline Weaknesses

The baseline misses or mishandles some durable world entities:

- `Wizard's Tower Brewing Co`
- `the Nameless Goddess`
- `the Copper and Quartz Inn`
- `Grit and Grime`
- species-level entities like `Float Goats` and `Luminox Sheep`

It also flattens fauna/resource facts into item labels:

- `Tidal Turtles shells and mucus`
- `Starling Cow milk, hides, and cheese`
- `Float Goat wool, milk, cheese, and buoyancy dust`

That is not ideal for a global knowledge graph. We want species and products as related nodes, not one combined object string.

The baseline also has a meaningful direction issue:

- `Mirathorn governs Mirathorn City Council`

For command-board projection, that should be council/government governs city, or council is government_of city. Direction matters because query answering depends on it.

### 5.3 Edge+Node Vocabulary Strengths

The combined vocabulary pass improves spatial/containment structure sharply.

It emits a coherent cluster of `located_in` and `contains` relationships:

- `Mirathorn located_in Elderwyld`
- `Mirathorn located_in Stormspire Peaks`
- `Mirathorn located_in Lake Mirathorn`
- `Grand Market located_in Mirathorn`
- `Stormspire Academy located_in Mirathorn`
- `The Broken Blade Inn located_in Mirathorn`
- `Temple of the Nameless Goddess located_in Mirathorn`
- `The Great Hall`, `The Altar of Sacrifice`, `The Reflection Pool`, and `The Sanctuary` contained by the temple
- `out town within Mirathorn`
- `the main gate located_in Mirathorn`
- `Ancient stone walls located_in Mirathorn`
- `Guard towers part_of Ancient stone walls`

This is a real strength. If the command board needs a projected location hierarchy, vocabulary appears helpful.

It also captures `Wizard's Tower Brewing Co.` as a location, which the baseline missed. That is important because this is one of the cross-bed identity probes.

### 5.4 Edge+Node Vocabulary Weaknesses

The combined pass regresses institutional structure. The baseline has a more explicit council structure; the vocabulary pass flattens several leaders into direct relationships with `Mirathorn`:

- `Mayor Elara Swiftwind leads Mirathorn`
- `Merril Tealeaf leads Mirathorn`
- `Grobnok the Goblin member_of Mirathorn`
- `Rurik Stonehammer member_of Mirathorn`

For a global knowledge graph, this is worse than the baseline. The city council should be a stable collective/institution node, and council members should connect to it.

The vocabulary pass also over-explodes fauna/resource details into many object nodes:

- `Luminox Sheep wool`
- `Luminox Milk`
- `Bioluminescent Dye`
- `Float Goat wool`
- `Float Goat milk`
- `Floating Cheese`
- `Buoyancy Dust`

Some of these may be useful downstream, but as a first global graph pass they overwhelm the species-level model. They would be better handled by a dedicated ecology/resource extraction pass that can create a species-product relation shape intentionally.

Finally, the founding/history edges are not clean:

- `Lundayell Empire caused_by Mirathorn's founding...`
- `Ancient airship results_in Lundayell Empire`

Those are wrong. The model is trying to express historical causality but has the wrong predicate/object shape.

### 5.5 Mirathorn Interpretation

Mirathorn says vocabulary helps one graph dimension - spatial containment - while damaging another - institutions and historical relations.

This argues against solving everything by prompt tuning in the current edge pass. The input asks one pass to construct location hierarchy, civic institutions, resource taxonomy, founding history, threat/cult relations, and command-board projection all at once. That is too much pressure for a single edge pass.

## 6. Prompt and Pass Review

### 6.1 Node Passes

Current node passes:

- `actor_pass`: named non-party NPCs, characters, and creatures only; explicitly says not to extract player characters or traveling companions because those are supplied as party anchors.
- `location_pass`: regions, towns, cities, roads, routes, sublocations, named travel zones.
- `collective_pass`: factions, councils, guards, mercenary groups, organizations, and parties.
- `object_pass`: notable items, devices, artifacts, objects.
- `thread_pass`: mysteries, clues, warnings, events, unresolved phenomena, threads.

The pass split is reasonable, but the observed failures show a few pressure points.

#### Actor pass

The actor pass explicitly excludes player characters and companion NPCs. That is defensible for production if party anchors are always injected and then projected into the graph. In these dogfood beds, however, C1S1 still misses party membership and aggregate party structure. The pass is doing what it was told, but the pipeline does not yet compensate with a robust party/roster attachment pass for C1.

Prompt tuning alone is not the right fix. The better fix is deterministic party-anchor construction plus a party-membership edge pass. If source text names party members, the graph should be able to attach them to a party aggregate without asking the actor pass to rediscover the roster.

#### Location pass

The location pass is too permissive around same-label and route/location/object collisions. Baseline and vocabulary runs both create duplicate location/item/faction versions of the same nouns. Prompt tuning can help here:

- tell the location pass not to extract an object duplicate when a phrase is only a physical feature inside a location unless it is independently important;
- prefer one place node per named establishment;
- treat `X Brewing Co` as an establishment/location in the location pass, not as both an object and organization unless the source separately describes the legal/organizational body.

But prompt tuning will not fully solve this. The consolidation layer needs stronger cross-pass type arbitration.

#### Collective pass

The collective pass is currently overbroad: "factions, councils, guards, mercenary groups, organizations, and parties" all share one pass. This creates two problems:

- establishments can be duplicated as organizations (`The River's Edge Pub`, `Wizard's Tower Brewing Co`);
- institutions like `Mirathorn City Council` compete with city-level place nodes and individual leader nodes.

Prompt tuning can add clearer examples: council and guard are collectives; tavern/brewery are establishments unless the document discusses their staff or company as an actor. But Mirathorn suggests a dedicated institution/governance pass may be better.

#### Object pass

The object pass is creating many product/resource nodes. This can be useful for worldbuilding, but not at the same priority as stable species, factions, places, and institutions.

Prompt tuning should instruct the object pass to avoid exploding commodity lists into separate object nodes unless the item is plot-relevant, magical, unique, or likely query-worthy. For worldbuilding, product extraction should probably move to a dedicated ecology/resource pass.

#### Thread pass

The thread pass is valuable. C1S1's edge+node vocabulary run produced useful unresolved threads: cat owl, sealed area, spider, shatter mage tower, statue foot. These are exactly the kinds of things a command board could surface as "open hooks" or "review before promotion."

The weakness is that thread nodes sometimes become a dumping ground for event summaries and causal facts. Prompt tuning should separate:

- mystery/open question;
- event/encounter;
- durable world fact;
- follow-up candidate.

That suggests an additional pass may be warranted.

### 6.2 Beat Pass

The beat pass was not the focus of this review, but it is important architecturally. Beats can provide a source-local scaffold for events and edges. Right now many event-like things are leaking into `thread_pass` or object/location nodes.

Potential use: use beats as the source-local timeline spine, then build specific event/relationship observations against that spine rather than forcing node passes to encode events as mysteries or objects.

### 6.3 Edge Pass

The edge pass currently has a broad relationship extraction sweep:

- location containment;
- authority and command;
- threat and displacement;
- knowledge and reports;
- composition and participation.

This is directionally right, but the manual review shows it is overloaded.

Strengths:

- It can produce useful containment when endpoints are clear.
- It can attach leaders and institutions.
- It can connect threats, protestors, guards, and knowledge states.

Weaknesses:

- Directionality is inconsistent (`Mirathorn governs Mirathorn City Council`; `The River's Edge Pub governs Grishna`).
- It does not reliably pick the correct institutional endpoint (`Elara leads Mirathorn` instead of `Elara leads Mirathorn City Council`).
- It creates malformed historical causality (`Ancient airship results_in Lundayell Empire`).
- It sometimes binds edges to duplicate establishment nodes rather than the stable entity.

Prompt tuning can help with direction rules:

- `operates`: actor/collective -> establishment
- `governs`: institution/leader -> polity/place
- `located_in`: child place/establishment -> parent place
- `member_of`: person -> organization, not person -> city/place
- `founded_by_settlers_from`: settlement -> origin polity/culture

But this is probably not enough. The pass is being asked to solve multiple relationship families with different directionality and endpoint policies.

## 7. Vocabulary Prompt Review

The prompt-review report surfaced important issues.

### 7.1 Do-not-merge hints are currently unsafe in the dogfood packet

C1S1 includes:

- `Stone Bridge` town vs literal stone bridge landmark
- `Wizard's Tower Brewing Co` place vs organization

These were intended as probes, but they are not source-derived in a reliable form, and they actively encourage duplicate same-label entities. They should be removed from the dogfood packet until a real compiler can produce human-readable, evidence-backed distinctions.

The prompt should never show do-not-merge hints as opaque vocabulary IDs. It should render labels and types:

```text
Do not merge:
- "The Shepherd" [actor/entity] != "Shepherd's Flock" [collective/cult]
  Reason: individual/entity vs organization/cult distinction.
```

### 7.2 Absent-set probes should not be presented as ordinary known names

The absent-set exists to measure contamination. Presenting absent foreign names in the same `Known names` list as source-relevant vocabulary risks encouraging hallucination. It also makes manual review confusing.

Future prompt shape should separate:

- source-relevant vocabulary;
- background vocabulary with textual hooks;
- contamination probes for eval only (not visible to the model);
- do-not-merge hints that are source-grounded and human-readable.

The current dogfood violates this by putting absent probes into the model-facing vocabulary packet.

### 7.3 Alias handling is too implicit

C1S1 shows `stone bridge` as an untyped known name because aliases become known names without a type hint. This is confusing to both the model and human reviewer.

Aliases should render under the parent entity:

```text
- Stone Bridge [place]
  aliases: stone bridge
```

not as a separate known name.

### 7.4 Vocabulary should be reviewed before extraction

The review-only mode is a good first step, but it should become a required gate before LLM extraction:

1. Compile vocabulary.
2. Render prompt-review packet.
3. Human approves/edits/rejects packet.
4. Run extraction.
5. Review before/after graph projection.

This matches the actual workflow the user requested: understand the prompt, the extracted graph, and whether misses were absent from vocabulary or ignored despite being present.

## 8. Where Prompt Tuning Helps

Prompt tuning is likely useful for narrow, local failures:

- directionality rules for common predicates;
- avoiding duplicate establishment-as-object and establishment-as-organization nodes;
- object pass guardrails against product-list explosion;
- clearer distinction between location, establishment, institution, and object;
- edge pass examples for `operates`, `governs`, `member_of`, `located_in`;
- rendering vocabulary context in a more human-readable and model-useful way.

Concrete prompt-tuning ideas:

1. Add endpoint direction rules to the edge pass.
2. Add "do not bind membership to a city/place when a council/guard/organization node exists" to edge pass.
3. Add "do not create object nodes for commodity products unless they are unique, magical, or plot-active" to object pass.
4. Add "establishment names are places by default; create organization only if the source discusses the staff/company as an actor" to location/collective passes.
5. Move vocabulary context before source packet for node passes, but render it as source-relevant guidance, not as a mixed known-name dump.

## 9. Where Prompt Tuning Is Probably Not Enough

Several failures look architectural rather than prompt-local.

### 9.1 Party and roster attachment

C1S1 misses the party aggregate and several PCs. The actor pass intentionally excludes player characters. The right fix is not "let actor pass extract PCs"; that risks duplicate party identity across sessions. The better fix is a deterministic party-anchor and membership pass:

```text
source + known roster + recap mentions -> party aggregate + present_at/member_of edges
```

This can relieve the actor pass from rediscovering global PC identity while still constructing session-specific party participation edges.

### 9.2 Entity type arbitration

Duplicate cross-class nodes persist. This is not just a prompt problem. The pipeline needs a type arbitration / reconciliation stage that can decide:

- same label as place + item = keep place, attach object facet only if independently warranted;
- establishment as location + organization = keep establishment node, optionally attach operator/staff as separate collective if source supports it;
- city vs council = keep city as place/polity and council as institution, do not merge.

This stage should use vocabulary, corpus refs, node descriptions, and evidence refs.

### 9.3 Institution/governance extraction

Mirathorn shows that civic structure wants its own pass. The combined edge pass flattened council relations into city-level edges. A governance/institution pass could explicitly extract:

- institution nodes;
- office/role nodes if useful;
- members/officeholders;
- governs/represents/commands relationships;
- jurisdiction targets.

This would relieve pressure from the generic collective pass and edge pass.

### 9.4 Ecology/resource extraction

Mirathorn fauna/resource material should not be flattened into dozens of object nodes in the first graph pass. A dedicated ecology/resource pass could extract:

- species/entity;
- product/resource;
- produced_by relation;
- use/economic relevance;
- location/region;
- whether the fact is world-reference vs plot-active.

This would let the core graph remain stable while still preserving useful worldbuilding detail.

### 9.5 Event/encounter/job extraction

C1S1 needs first-class modeling for:

- rat-clearing job;
- rat cellar fight;
- excavation breach;
- hidden tower exploration;
- cat owl intervention;
- spider discovery.

These are not just mysteries, objects, or edges. They are event/job/encounter structures. A dedicated event/encounter/job pass could output:

- event/encounter/job nodes;
- participants;
- location;
- trigger/cause;
- outcome;
- open follow-up.

This would reduce pressure on thread and edge passes.

## 10. Proposed Next Design Shape

The next iteration should not be "keep adding vocabulary text to the same prompt."

Recommended shape:

1. **Vocabulary compile and review gate**
   - Compile source-derived vocabulary.
   - Render readable packet.
   - Human can inspect source-relevant names, aliases, types, containment, and do-not-merge.
   - Absent-set contamination probes stay out of model-facing prompt.

2. **Core node passes**
   - actor
   - location/establishment
   - institution/collective
   - object/artifact
   - thread/open question

3. **Specialized extraction passes**
   - party/roster attachment pass
   - governance/institution pass
   - event/encounter/job pass
   - ecology/resource pass for worldbuilding docs

4. **Relationship family passes**
   - containment/location hierarchy
   - membership/governance
   - event participation/outcome
   - knowledge/warning/report

5. **Type arbitration and identity reconciliation**
   - collapse wrong duplicate labels;
   - keep true multi-entity distinctions;
   - attach aliases and corpus refs;
   - produce human-reviewable decisions.

6. **Projection review UI**
   - before/after graph pills;
   - source evidence and prompt context;
   - vocabulary prompt for the pass;
   - extracted nodes/edges;
   - misses/extras with "same core concept?" controls;
   - accept/reject/retype/merge/defer decisions.

## 11. Product Review Surface Needed

The reports are not clear enough because they compress graph behavior into counts. The user needs a review UI that shows:

- baseline graph projection;
- vocabulary-assisted graph projection;
- node pills grouped by type;
- edge pills grouped by predicate family;
- source span evidence;
- vocabulary prompt for the active pass;
- extracted output for that pass;
- gold/comparator hints as optional overlays, not as the truth;
- controls for "same concept", "wrong type", "bad edge direction", "missing but present in source", "not important", "promote to vocabulary", "add do-not-merge".

This is the right way to understand what is being missed:

- Was the concept present in vocabulary?
- Was it present in source but ignored?
- Was it extracted under the wrong type?
- Was it extracted but not bound in edges?
- Was it over-extracted into product/object noise?
- Was the gold comparator too strict?

Until that UI exists, reports should be treated as diagnostic logs, not decision surfaces.

## 12. Concrete Follow-Up Ideas

### Immediate cleanup

- Remove the flawed C1S1 do-not-merge hints from dogfood packets.
- Stop rendering aliases as separate untyped known names.
- Keep absent-set probes out of model-facing vocabulary.
- Render do-not-merge as labels/types/reasons, not internal IDs.

### Next experiment

- Rerun baseline vs edge+node with cleaned vocabulary prompts (do-not-merge hygiene).
- **Prerequisite for session recap beds:** ensure `_party_registry.json` exists before ablation — party context is not optional for session ingestion evals.
- Add one specialized pass candidate:
  - for C1S1: event/job/encounter pass (party context now handled deterministically);
  - for Mirathorn: governance/institution + ecology/resource pass.
- Compare not only recall but manual review categories:
  - stable identity improved;
  - relationship direction improved;
  - command-board projection improved;
  - over-extraction increased/decreased;
  - human correction burden.

### UI/tooling

- Build a local graph review canvas or plan-surface module that loads the manual-review JSON bundle.
- Show baseline and assisted graph pills side by side.
- Add pass-level tabs: actor, location, collective, object, thread, edge.
- Show vocabulary context beside the extracted output for that pass.
- Let the reviewer mark core-concept equivalence even when labels do not match gold.

## 13. Current Assessment

The contextual vocabulary idea is still worth pursuing. It is not yet proven as a runtime default.

The useful signal is:

- C1S1 with party registry: baseline already preserves PC anchors and party collective; vocabulary adds modest present-set recognition and some relationship/thread enrichment.
- Mirathorn gets better at location containment and projection hierarchy with vocabulary.
- Neither bed shows foreign-name contamination in the reviewed baseline vs edge+node run.

The blocking signal is:

- same-label cross-class duplication remains (consolidation/type arbitration, not vocabulary alone);
- bad dogfood do-not-merge hints contaminated the prompt;
- institutional structure regresses in Mirathorn;
- product/resource details explode into object noise;
- event/job/encounter structure is not cleanly modeled;
- edge recall stays low even when party anchors are present (~29% on corrected C1S1).

The next move should be a reviewable graph projection workflow plus one or two specialized passes, not more aggregate metric reports.
