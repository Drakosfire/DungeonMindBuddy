# Session29: handcrafted connected gold v1

This is an operator-authorized reference extraction of **The Meat Mind of Mireward Reach**, crafted directly from the immutable saved recap and focused canonical Elderwyld corpus references. It contains **89 intentionally typed gold-local nodes, 151 assertions, 165 literal evidence ranges, 15 paragraph coverage entries, 10 ambiguity decisions and 13 benchmark questions**. No extraction candidate, model response, accepted World or provider was consulted. No live state is changed.

The party observes Mireward from Lysandro’s second floor, rescues sleeping children from two warehouse monsters, follows a northward psychic pull and destroys the underground flesh creature with fire. The subsequent wall repairs, cure work and change in Thrin’s outlook are distinct temporal developments. Brin’s account concerns an earlier disaster in Edge. Fellinor’s inaccessible Edge stores and safe provide a future objective. The northbound bayou journey ends at camp, before arrival at Edge.

Lysandro’s house has a direct `home_of` relationship to him. Lysandro is Lysandra’s father: Session22 explicitly introduces him that way and a world dossier independently names the relationship. Session25 houses Edge refugees at Ironveil Warehouse and mentions older children there. This supports the local warehouse/refugee context. Exact membership of the rescued children remains medium-confidence contextual inference plus a separately labeled operator clarification. It is never presented as a quote from Session29. Pippa/Bubbles belong to an earlier Stone Bridge thread and provide a disambiguation contrast, not participants in this episode.

Thrin’s lifelong seed-related call is not proved identical to the local creature’s pull. The world Witness Seed reference discusses Threnn, whose identity is not merged with Thrin. Karsemine/Karesmine/Karamine and Alchemist’s/Alchamist’s Fire have explicit local spelling decisions. Hesta and Grobnok retain the actual source names. The 150-year date applies to Edge’s fort era, not the creature’s appearance.

The reference keeps plans and reports distinguishable: Ephanna **will use** Eldritch Blast during the rescue; the recap does not separately confirm that cast. Stafl shoots arrows, and Karsemine later uses Fire Bolt against restraining tentacles. Hesta creates enough cure for remaining infected refugees; that does not independently prove every dose was administered. The monsters stop **as if** direction was lost. Permanent safety, confirmed telepathic control and a cure for the seed’s lifelong call would overstate the evidence.

## Files

- `TYPE_MODEL.md`: intentional domain kinds, typed literal objects and unresolved subtype decisions.
- `gold.json`: graph nodes, richly described facts, temporal scope, modality, provenance, quantities, evidence, coverage, ambiguities and benchmark subgraphs/traversals.
- `SOURCE_MANIFEST.json`: exact original file paths and byte hashes, authority classes, duplicate policy and inspected planning material excluded from played assertions.
- `COVERAGE.md`: readable paragraph-by-paragraph coverage with exact fact IDs.
- `AMBIGUITIES.md`: unresolved identities, chronology, origin, mechanism and native binding decisions.
- `BENCHMARK.md`: expected answers and concrete failure examples.

Every fact uses one of `source_assertion`, `attributed_observation`, `contextual_inference`, `unresolved_hypothesis` or `operator_addition`. Unresolved hypotheses currently live in the ambiguity ledger rather than positive graph edges. Attributed observations identify the speaker. Operator additions have an explicit dispatch authority reference and no fabricated quotation. Event-specific unnamed groups never become global generic aliases. Gold IDs do not claim native World identities. Each retained node has an intentional domain kind and rationale; generic `entity` defaults are rejected. A fact has exactly one node `object` or typed literal `object_value`. Dimensions, direction, rest activity, relative time, generic condition sets and alias names are values, not mandatory extraction nodes. These gold-only kinds are independent of runtime admission.

Native mapping gaps are a separate complete inventory: every semantic predicate is presently **unmapped or unverified**. This slice does not inspect or change the runtime catalog, and it does not assert that every listed predicate is unsupported. Extraction quality can therefore be evaluated before deciding how each fact fits native admission.

## Reproduce validation

From the repository root:

```bash
python3 evals/graph_memory_layer/validate_session_29_connected_gold_v1.py \
  --source-root /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
python3 -m unittest discover -s tests -p test_session_29_connected_gold_v1.py
```

The validator always requires original local sources; missing or changed originals fail. It checks original byte hashes, literal codepoint/line ranges, quotation hashes, saved span membership, IDs, endpoints, evidence references, authority classes, attribution, operator provenance, coverage, mapping inventory and benchmark traversals. Its checks establish integrity and declared coverage; they do not mechanically prove every paraphrase is entailed. The negative tests corrupt provenance, sources, hashes, offsets, endpoints, coverage, modality and paths. Two tests requiring the private originals explicitly skip when those files are absent; structural negative tests still run. The expanded damage suite also rejects generic/default kinds, misclassified spells, duplicate entity/literal objects, malformed dimensions, value-as-entity regressions and weakened home relationships. No dependencies, service, database or model calls are needed.

The saved primary source remains local at `out/graph_memory/runs/longmont-c2/session-29/20261015T204654Z/normalized_recap_source.md`, SHA256 `4f963656828b553f7919ee00d3304725ddff892a13651b989f99b9b649933796`. Only focused quotes and evidence metadata are committed. UTF-8 bytes are hashed; offsets count Unicode codepoints, half-open `[start,end)`; line bounds are inclusive and start at 1. Indentation, curly punctuation and spelling are preserved wherever included in a quote. The frozen span index is used only as evidence indexing metadata.

## Independent freeze and benchmarking refs

Start base: `d03fdb67da877c604e19242d0bdc254515fe89f7`.
Handoff-first commit: `47e330a0a15394d3a0d03e1afea93f9212ce103b`, committed `2026-10-15T23:39:16Z`.
The first artifact commit `d61aa537addc568936c16305a1eb3172bddaaf4c` froze the independent extraction at `2026-10-15T23:46:55Z`. A subsequent local refinement responds to PRIME’s independent type-model review, preserving the source-first fact set; its Git revision/time are the revised end reference. Candidate comparison was not performed. See the PR head for the exact frozen end SHA. This avoids a self-referential commit hash in the artifact.
