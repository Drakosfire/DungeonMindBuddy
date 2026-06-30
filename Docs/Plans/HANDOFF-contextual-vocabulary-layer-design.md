# HANDOFF — Evolving Contextual Vocabulary Layer Design

## 0. Purpose

This handoff is for the next **Designing agent**. The workstream has crossed out of "dogfood the current graph ingest" and into **design + implementation of the next graph-memory architecture layer**.

The next design target is an **evolving contextual vocabulary layer** for graph-memory extraction and identity resolution:

```text
worldbuilding docs + campaign recaps + registries + prior graph observations
→ evolving vocabulary / lexicon artifacts with provenance and authority
→ prompt-time contextual vocabulary packets
→ more stable node extraction, endpoint binding, predicate choice, and comparator diagnostics
```

The vocabulary layer must **not** be hardcoded to Session 23, Campaign 2, or any single corpus. It must grow from ingested sources and remain provenance-grounded, inspectable, and reviewable.

Current branch:

```text
experiment/ontology-taxonomy-ladder
```

Current committed head at this handoff:

```text
eed58c9 Add corpus anchor index and cross-class node reconciliation.
```

Current local caveat:

```text
evals/graph_memory_layer/artifacts/graph_ingest_runs/
```

is still untracked local dogfood artifact output. Do not assume it should be committed.

## 1. Re-anchor Sources

Before designing or editing, read these in order:

1. `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md`
2. `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md`
3. `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`
4. `Docs/Anchors/CORPUS-ANCHOR.md`
5. `corpus/CORPUS-INDEX.json`
6. `Backlog.md` top READY graph entries

Important anchor correction:

- The graph-memory goal is **not** a session-local graph.
- The graph substrate is a **campaign + worldbuilding union supergraph**.
- A recap projection is a scoped lens over that graph.
- Vocabulary must support global identity and session-focus overlays, not just one extraction run.

Corpus anchor:

```text
Docs/Anchors/CORPUS-ANCHOR.md
corpus/CORPUS-INDEX.json
scripts/build_corpus_index.py
```

Regenerate after corpus hierarchy changes:

```bash
PYTHONPATH=. python scripts/build_corpus_index.py
```

Primary corpus root:

```text
corpus/eldyrwild-markdown/
```

Do not treat `corpus/Eldyrwild and Campaign Unprocessed/` as the primary source. It contains pipeline artifacts.

## 2. What Has Shipped Recently

### 2.1 Staged Edge Extraction Experiment

Commit:

```text
a6a2312 Add staged edge extraction experiment and enrich production edge pass.
```

Key files:

```text
src/graph_memory/extraction/staged_edge_extraction.py
evals/graph_memory_layer/run_staged_edge_s23_experiment.py
tests/test_graph_memory_staged_edge_extraction.py
```

The staged experiment split edge extraction into:

1. relation observation
2. endpoint binding
3. predicate normalization
4. final edge assembly

The experiment was run against Session 23 stored pass outputs:

```text
out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z/
```

Key result:

```text
Baseline edge recall: 8/21 = 0.381
Staged mini trials: still 8/21
Strong edge-stage trial: still 8/21
```

Interpretation:

- Under-emission was real; staged observation produced many relation candidates.
- Model strength was not the main bottleneck.
- The remaining edge ceiling is dominated by identity / endpoint alignment, vocabulary, and relation coverage.

### 2.2 Enriched One-Shot Edge Prompt

Production edge pass in:

```text
src/graph_memory/extraction/category_candidate_graph_extractor.py
```

was enriched to include:

- Source Packet
- compact node summaries with descriptions and evidence refs
- predicate catalog
- relationship extraction sweep
- 10–30 edge expectation

The one-shot edge prompt emitted more plausible edges, but gold comparison still stayed at `8/21`.

### 2.3 Cross-Class Exact-Label Node Reconciliation

Commit:

```text
eed58c9 Add corpus anchor index and cross-class node reconciliation.
```

Key files:

```text
src/graph_memory/identity_resolution.py
src/graph_memory/extraction/category_candidate_graph_extractor.py
tests/test_graph_memory_identity_resolution.py
```

New helper:

```python
reconcile_cross_class_label_collisions(nodes, edges=None)
```

Purpose:

- The category extractor runs one observation pass per node type.
- A single proper noun can surface as multiple nodes with different type classes.
- Examples observed:
  - `Mireward Reach` as `location` and `organization`
  - `Edge` as `location` and `organization`
  - `Elderwild Reach` as `location` and `faction`
  - `Wizard's College` as `location` and `organization`
  - `Golden Fields` as `location` and `organization`

This duplicate-label pattern is generalizable across S22/S23 and across models. A/B checks showed:

```text
S22 gpt-5.4-mini: 4 collisions, node recall unchanged
S22 gpt-5.4:      2 collisions, node recall unchanged
S22 gpt-5.3:      1 collision,  node recall unchanged
S23 stored:       2 collisions, edge recall unchanged, node recall lowered by one spurious match
```

Important weakness:

- Current code may be too broad.
- Holdout inspection found a likely false merge risk:

```text
the_shepherd               character
faction_shepherd_cult      faction
```

Both had label `"the Shepherd"`. The current broad cross-class exact-label merge can collapse actor + collective labels. This may be wrong: a person and an eponymous cult/faction are distinct concepts.

Recommended follow-up:

- Narrow cross-class merge to the proven **place ↔ collective** case first.
- Add a test pinning that actor ↔ collective exact-label pairs do **not** merge.
- Re-run the S22/S23 A/B after narrowing.

### 2.4 Corpus Anchor Index

Commit:

```text
eed58c9 Add corpus anchor index and cross-class node reconciliation.
```

Key files:

```text
scripts/build_corpus_index.py
Docs/Anchors/CORPUS-ANCHOR.md
corpus/CORPUS-INDEX.json
tests/test_build_corpus_index.py
.cursor/rules/anchor.mdc
Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md
evals/graph_memory_layer/FIXTURE-STATUS.md
```

Confirmed corpus roots:

```text
corpus/eldyrwild-markdown/                   canonical markdown corpus
corpus/Eldyrwild and Campaign Unprocessed/   pipeline artifacts
corpus/_drafts/                              drafts
```

Primary corpus inventory at time of index:

```text
corpus/eldyrwild-markdown/ → 428 markdown files
Campaign 1 canonical recaps: 17
Campaign 1 normalized recaps: 17
Campaign 2 canonical recaps: 25
Campaign 2 normalized recaps: 32
```

Worldbuilding root:

```text
corpus/eldyrwild-markdown/Elderwyld/
```

Major worldbuilding branches include:

```text
Elderwyld/Cities and Towns/
Elderwyld/Events/
Elderwyld/Inns and Shops/
Elderwyld/Migrating Forest/
Elderwyld/Roads/
Elderwyld/Shephards Flock/
Elderwyld/Wilderness/
```

This index is intended to support the vocabulary-layer work by making corpus scope explicit and regeneratable.

## 3. What We Learned

### 3.1 Prompt Context Is Currently Too Thin

Current node extraction prompts receive:

- Source Packet paragraphs
- party anchor block
- one pass-specific instruction
- default node type

They do **not** receive a campaign/world vocabulary packet.

Current edge pass receives:

- Source Packet
- consolidated node list
- predicate catalog
- relationship sweep instructions

Current staged relation observation receives:

- Source Packet
- consolidated node summaries
- beat summaries
- ignored/deferred items
- predicate catalog
- generic relation affordances

But neither path receives a durable contextual vocabulary that says:

- known canonical names
- known aliases
- known do-not-merge pairs
- likely entity kind
- containment / parent-location hints
- prior sessions where entity appeared
- corpus refs / hub paths / authority
- unresolved ambiguity notes

The model is inventing vocabulary independently in each pass, and deterministic code tries to reconcile after the fact.

### 3.2 Hardcoded Aliases Are the Wrong Long-Term Move

Experiment-only code currently has `_BINDING_TOKEN_ALIASES` in:

```text
src/graph_memory/extraction/staged_edge_extraction.py
```

Examples include:

```text
refugees ↔ survivors
meat / monsters / horde / wave
tripod / tripods
meatwing / meatwings / flying
```

This helped diagnose failure modes, but it is not a product architecture. It is gold/corpus-shaped patching.

The next architecture should replace this with a **source-derived, evolving vocabulary artifact**.

### 3.3 Comparator Aliases Are Also Dangerous

Backlog currently has an entry suggesting alias/synonym signals for `node_match_score`, e.g. `Edge Survivors ↔ Edge refugees`.

This is risky if implemented as a hand-coded comparator alias table. It teaches the metric the answer key.

Better:

- derive alias hypotheses from corpus + recap evidence
- carry provenance and authority
- use the same vocabulary artifact in:
  - extraction prompts
  - deterministic endpoint binding
  - comparator diagnostics
  - union-supergraph reconciliation

### 3.4 Session 24 Gold Nuance

There is Session 24 gold in:

```text
evals/graph_memory_layer/examples/session_24_manual_projection_dogfood/session_24_manual_gold_graph.json
```

But per:

```text
evals/graph_memory_layer/FIXTURE-STATUS.md
```

Session 24 is **projection dogfood gold**, not candidate-graph extraction gold like S22/S23.

Do not casually treat S24 projection gold as the same benchmark as Session 22/23 candidate graph gold. If the design agent needs S24 extraction gold, first locate or author the proper fixture shape and document the authority difference.

## 4. Weaknesses In The Current Project

### 4.1 Vocabulary Is Implicit, Fragmented, And Late

Vocabulary currently lives in several disconnected places:

- source prose
- party registry / party context
- NPC registries
- extracted local node labels
- staged-edge experiment alias dict
- comparator label similarity
- corpus hub paths / README files
- planning corpus manifest source roles

There is no central artifact that says:

```text
For this extraction scope, these are the relevant names, aliases, kinds,
authority levels, known ambiguities, and do-not-merge rules.
```

### 4.2 The Extractor Re-Invents Identity Per Pass

Category extraction is decomposed by node type:

```text
actor pass
location pass
collective pass
object pass
thread pass
beat pass
edge pass
```

This decomposition is good for coverage, but it creates dual-typed duplicate labels:

```text
Mireward Reach       location + organization
Edge                location + organization
Elderwild Reach     location + faction
Wizard's College    location + organization
```

This is a symptom of missing contextual vocabulary. The model is unsure whether a proper noun is a place, polity, faction, or institution, so different passes all claim it.

### 4.3 Edge Recall Depends On Stable Node Identity

Session 23 staged edge trials showed:

```text
best live edge recall stayed 8/21
```

An ideal-edge probe showed:

```text
dedup + perfect Tier-1 edges could reach 13/21
```

But live extraction did not reach that because:

- containment edges were often not observed
- `governs` sometimes targeted `Mireward Town Leadership` instead of `Mireward Reach`
- `Edge Survivors` vs `Edge refugees` diverged
- `First meat wave` event aggregator was missing or modeled as creature/faction nodes

These are vocabulary/ontology failures before they are edge-prompt failures.

### 4.4 Comparator Scores Can Reward Wrong Matches

In S23, before cross-class reconciliation, `node:edge-refugees` could match the wrong live `Edge` organization node via span/source boost. Removing the duplicate lowered node recall by one, but made the metric more honest.

Design implication:

- Do not optimize only recall numbers.
- Inspect matched-pair semantics.
- Add diagnostics for "match may be wrong but scored high due source overlap."

### 4.5 Corpus Indexing Is Still File-Tree Level

`corpus/CORPUS-INDEX.json` is only a hierarchy and file inventory. It does not extract frontmatter, names, aliases, source authority, or entity candidates.

The vocabulary layer should build on this, not mistake it for the vocabulary.

## 5. Proposed Next Architecture: Evolving Contextual Vocabulary

### 5.1 Working Definition

A contextual vocabulary layer is a regeneratable, provenance-grounded lexicon over campaign and worldbuilding sources.

It should answer:

```text
What names, aliases, entity kinds, disambiguation warnings, containment hints,
and prior-source anchors should be available when extracting this source packet?
```

It should be:

- evolving
- source-derived
- versioned
- inspectable
- reviewable
- scope-selectable
- non-canonical by default
- reusable across extraction, binding, comparison, and graph reconciliation

### 5.2 Vocabulary Is Not Config

Avoid a static config file like:

```json
{
  "Edge Survivors": ["Edge refugees"]
}
```

That would overfit and rot.

Instead, think in layers:

```text
Corpus file inventory
→ source artifacts
→ lexical observations
→ entity / alias candidates
→ reviewed vocabulary entries
→ prompt-time context packet
```

### 5.3 Suggested Object Model

Start design with these concepts.

#### SourceArtifact

Represents an input file or generated source artifact.

Fields:

```text
source_artifact_id
route
source_domain
campaign_id
session_id?
authority
document_class?
subject_class?
frontmatter?
content_hash
last_indexed_at
```

Source domains should align with graph-memory anchor:

```text
recap
worldbuilding
npc_note
location_note
faction_note
item_note
statblock
session_memory
planning_scaffold
manual_seed
```

#### LexicalObservation

Raw observed mention from a source.

Fields:

```text
observation_id
source_artifact_id
source_span_ref_id? / line range
surface_text
normalized_text
context_window_hash?
observed_kind_hint?
evidence_ref
extraction_method
confidence
```

This is not a stable entity yet.

#### VocabularyEntry

Stable-ish entry representing a known or candidate entity/vocabulary concept.

Fields:

```text
vocab_id
canonical_label
entity_kind
entity_kind_confidence
aliases[]
negative_aliases[] / do_not_merge[]
source_refs[]
corpus_refs[]
campaign_scope
world_scope
first_seen_session?
last_seen_session?
status
authority
notes
```

Possible statuses:

```text
observed
candidate
accepted
rejected
do_not_merge
needs_review
deprecated
```

Possible authorities:

```text
corpus_frontmatter
world_reference
canon_play
derived_memory
inferred_from_recap
llm_candidate
gm_reviewed
```

#### AliasCandidate

Represents possible same-entity relation between two labels/entries.

Fields:

```text
alias_candidate_id
left_surface
right_surface
left_vocab_id?
right_vocab_id?
evidence_refs[]
supporting_sources[]
contradicting_sources[]
confidence
status
reason
risk_flags[]
```

Risk flags:

```text
cross_type
eponymous_group
place_vs_polity
person_vs_cult
single_shared_token
source_span_only
gold_only_support
```

#### ContextVocabularyPacket

Prompt-time slice, scoped to an extraction task.

Fields:

```text
packet_id
campaign_id
session_id?
source_artifact_ids[]
included_vocab_entries[]
alias_hints[]
do_not_merge_hints[]
containment_hints[]
type_hints[]
predicate_hints[]
budget_policy
generated_at
```

This is what prompts should receive.

### 5.4 Authority Rules

The layer should distinguish:

- **worldbuilding reference**: setting facts, locations, statblocks, evergreen dossiers
- **canon play recap**: what happened in-session
- **derived memory**: helpful but not source-of-truth
- **planning scaffold**: useful but not canon
- **LLM inferred candidate**: never canon by itself
- **GM reviewed**: strongest local approval signal

This mirrors existing planning corpus manifest work in:

```text
src/live_play/planning_corpus_manifest.py
```

Do not invent an incompatible authority vocabulary without reading that module.

### 5.5 Prompt-Time Role

The vocabulary packet should be injected before node extraction, not only before edge extraction.

Candidate prompt sections:

```text
## Contextual Vocabulary

Known names in scope:
- canonical label
- kind
- aliases
- source route / authority
- disambiguation warning

Do-not-merge:
- The Shepherd (person) != Shepherd cult (faction) unless source explicitly says identity.

Containment hints:
- North gate / south gate / Last Dry Bed may be sublocations of Mireward Reach if supported by source.

Type hints:
- Mireward Reach is primarily a place/settlement; civic leadership may be an organization but is not the place.
```

Important:

- Context vocabulary should guide extraction.
- It should not force unsupported facts.
- Prompts must still require source evidence for session-specific claims.

### 5.6 Deterministic Role

The same vocabulary should feed deterministic code:

- endpoint binding
- node dedup / reconciliation
- comparator diagnostics
- union-supergraph identity resolution

The design target is one shared artifact used in both prompt and code, not one prompt appendix plus unrelated Python aliases.

## 6. Exploration Plan

### Phase A — Read / Inventory Existing Corpus Signals

Read and inspect:

```text
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json
corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/*/README.md
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/
src/live_play/planning_corpus_manifest.py
src/corpus/session_recap_paths.py
```

Questions:

- What frontmatter fields already encode `document_class`, `subject_class`, `canon_layer`, `campaign_id`, `session`, etc.?
- Which hubs already list suggested reads and anchored NPCs?
- Do NPC registries include aliases, status, hub paths, setting hub paths?
- What should be indexed deterministically before any LLM is used?

Deliverable:

```text
Docs/Design/DESIGN-contextual-vocabulary-layer.md
```

with an inventory table and proposed schema.

### Phase B — Build A Shadow Vocabulary Compiler

Build deterministic read-only compiler first.

Candidate module:

```text
src/graph_memory/vocabulary/
```

Possible files:

```text
src/graph_memory/vocabulary/model.py
src/graph_memory/vocabulary/build.py
src/graph_memory/vocabulary/render.py
src/graph_memory/vocabulary/load.py
```

Input:

```text
corpus/CORPUS-INDEX.json
corpus/eldyrwild-markdown/**/*.md
campaign NPC registries
```

Output:

```text
out/graph_memory/vocabulary/...
```

or deterministic test fixtures under:

```text
tests/fixtures/graph_memory/vocabulary/
```

Do not mutate corpus.
Do not promote canon.
Do not wire runtime behavior yet.

### Phase C — Context Packet For Session 23 / S22 Comparison

Compile a vocabulary packet for:

```text
longmont-c2/session-23
```

It should include:

- party roster / party collective
- C2 NPC registry entries
- relevant Elderwyld hubs:
  - Mireward
  - Mirathorn
  - Edge of the World if present
  - Shephards Flock / meat-threat docs
- known PCs / NPCs
- aliases and do-not-merge warnings

Compare prompt packets for S22 and S23. The point is not to maximize S23 only; the point is to show the packet shape generalizes.

### Phase D — Inject Into Prompts In Shadow / Experiment Mode

Add an option to category extraction:

```text
context_vocabulary_packet: optional
```

or experiment runner only:

```text
evals/graph_memory_layer/run_contextual_vocabulary_experiment.py
```

Run:

```text
S22 existing pass-output comparable path
S23 stored run
optional S24 projection-only analysis separately
```

Measure:

- duplicate-label node collisions
- cross-class collisions
- node recall / precision proxy
- edge recall
- staged relation candidate count
- ambiguous endpoint drops
- unknown predicate drops
- "wrong object type" cases, e.g. `governs → leadership` vs `governs → place`

### Phase E — Decide Runtime Path

Only after the shadow run shows value:

- decide whether vocabulary is built per session ingest
- decide storage location
- decide review UI / promotion path
- decide how vocabulary joins union-supergraph model
- decide whether prompt injection happens in runtime category pipeline

## 7. Concrete Experiments To Run

### Experiment 1 — Cross-Class Collision Reduction

Hypothesis:

```text
Context vocabulary reduces dual-typed same-label nodes by telling the model
which proper nouns are places, polities, factions, or people before extraction.
```

Runs:

- S22 category extraction with no vocabulary
- S22 category extraction with vocabulary
- S23 category extraction with no vocabulary
- S23 category extraction with vocabulary

Metrics:

- number of exact-label cross-class collisions
- node recall
- node precision proxy
- manual inspection of matched pairs

### Experiment 2 — Edge Endpoint Binding

Hypothesis:

```text
Vocabulary aliases and do-not-merge hints improve endpoint binding without
hardcoded corpus aliases.
```

Specific cases:

- `Edge Survivors` vs `Edge refugees`
- `Mireward Reach` vs `Mireward Town Leadership`
- `The Shepherd` vs `Shepherd cult`
- `Tripod meat monsters` vs `Giant tripod meat monsters`

Metrics:

- ambiguous endpoint drops
- unbound subject/object drops
- edge recall
- false merge count

### Experiment 3 — Containment / Location Hierarchy

Hypothesis:

```text
Worldbuilding/corpus vocabulary can prompt reliable location containment edges.
```

Specific Session 23 gold edges:

- north gate located_in Mireward Reach
- south gate located_in Mireward Reach
- north wall located_in Mireward Reach
- Last Dry Bed inn common room located_in Mireward Reach
- road to north gate located_in Mireward Reach

Metrics:

- located_in observed count
- located_in matched count
- wrong target object rate

### Experiment 4 — Event Aggregator Modeling

Hypothesis:

```text
Vocabulary can steer live extraction to model "First meat wave" as an event /
encounter aggregator rather than only creature/faction nodes.
```

Specific Session 23 gold edges:

- First meat wave threatens Mireward Reach
- Tripod meat monsters part_of First meat wave
- Flying meatwings part_of First meat wave

This is an ontology-design question. Do not blindly force the gold model without deciding whether event aggregators are the desired product ontology.

## 8. Suggested First Design Slice

Do **not** start by wiring prompts.

Start with a deterministic vocabulary compiler design and one small schema implementation.

Recommended first slice:

1. Define vocabulary DTOs in `src/graph_memory/vocabulary/model.py`.
2. Add deterministic compiler that reads:
   - `corpus/CORPUS-INDEX.json`
   - C1/C2 NPC registries
   - frontmatter from selected README/hub markdown
   - recap file paths only, not full recap content yet
3. Emit a shadow artifact:

```text
out/graph_memory/vocabulary/contextual_vocabulary_longmont-c2_s23.json
```

4. Add tests with tiny fixture corpus:

```text
tests/fixtures/graph_memory/vocabulary/
```

5. Render a prompt packet markdown section from the artifact.

Only then consider injection into category extraction.

## 9. Proposed Schema Sketch

Start narrow; let the schema evolve.

```json
{
  "schema": "dmb_contextual_vocabulary_v0",
  "version": "0.1",
  "scope": {
    "campaign_id": "longmont-c2",
    "session_id": 23,
    "source_artifact_ids": []
  },
  "sources": [],
  "entries": [
    {
      "vocab_id": "vocab:place:mireward-reach",
      "canonical_label": "Mireward Reach",
      "entity_kind": "place",
      "status": "candidate",
      "authority": "world_reference",
      "aliases": ["Mireward", "the Reach"],
      "corpus_refs": [],
      "evidence_refs": [],
      "type_hints": ["location", "settlement"],
      "do_not_merge_with": [],
      "notes": []
    }
  ],
  "alias_candidates": [],
  "do_not_merge": [],
  "containment_hints": [],
  "diagnostics": {}
}
```

Prompt packet should be a lossy view of this artifact, not the artifact itself.

## 10. Non-Negotiables

- Do not paste corpus prose into web tools.
- Do not commit secrets or `.env`.
- Do not mutate corpus files as part of vocabulary compilation.
- Do not promote LLM-inferred aliases to canon automatically.
- Do not hardcode S23 gold labels into production matching.
- Do not optimize only for edge recall; inspect false matches.
- Do not treat S24 projection gold as candidate-graph gold.
- Do not build a static config file that will rot.
- Do not let vocabulary become an opaque magic lookup table.

## 11. Tests / Verification To Preserve

Existing focused tests:

```bash
PYTHONPATH=. python -m pytest tests/test_graph_memory_identity_resolution.py -q
PYTHONPATH=. python -m pytest tests/test_graph_memory_staged_edge_extraction.py tests/test_graph_memory_taxonomy_backed_edges.py -q
PYTHONPATH=. python -m pytest tests/test_build_corpus_index.py -q
```

Known unrelated stale failures observed earlier:

```text
tests/test_graph_memory_party_context.py::test_session_23_missing_roster_warns_and_is_empty
tests/test_graph_memory_smoke.py::test_graph_memory_smoke_runner_exits_zero
```

Those failed with current work stashed; do not attribute them to vocabulary work without rechecking.

For any vocabulary slice, add deterministic tests against tiny fixtures. Avoid tests that require real private corpus prose unless the test only inspects paths/frontmatter and does not snapshot sensitive content.

## 12. Recommended Agent Strategy

The Designing agent should not jump straight to implementation.

Recommended flow:

1. Re-anchor on files listed in §1.
2. Read current prompt construction:
   - `src/graph_memory/extraction/category_candidate_graph_extractor.py`
   - `src/graph_memory/extraction/staged_edge_extraction.py`
3. Read identity resolution:
   - `src/graph_memory/identity_resolution.py`
4. Read corpus path/manifest tooling:
   - `scripts/build_corpus_index.py`
   - `src/live_play/planning_corpus_manifest.py`
   - `src/corpus/session_recap_paths.py`
5. Inspect a few hub README/frontmatter files, but do not paste corpus content into chat unnecessarily.
6. Draft `Docs/Design/DESIGN-contextual-vocabulary-layer.md`.
7. Identify the smallest shadow compiler slice.
8. Only implement after the design has a falsification plan.

## 13. Open Questions

1. Should vocabulary entries be part of `src/graph_memory/union_supergraph` or a sibling `src/graph_memory/vocabulary` package?
2. Should vocabulary compile from frontmatter only first, then add body mention extraction later?
3. How should `document_class`, `subject_class`, and `canon_layer` frontmatter map into entity kinds and authority?
4. Where should rejected aliases / do-not-merge decisions live?
5. Is the vocabulary artifact per campaign, per session, or global with scoped packet rendering?
6. Should prompt packets include only accepted vocabulary, or also candidate aliases with warnings?
7. What is the review surface for alias promotion?
8. How does vocabulary interact with future union-supergraph global node IDs?
9. Should the comparator consume vocabulary directly, or only diagnostics produced from it?
10. How do we avoid the vocabulary becoming a second, unsafely divergent canon?

## 14. Current Best Hypothesis

The next high-leverage step is not a stronger model, not a larger edge prompt, and not a bigger alias dict.

The best next idea is:

```text
Design and wire a shadow-mode evolving contextual vocabulary layer, compiled
from corpus and recap sources with authority/provenance, then use it to ground
node extraction, edge observation, endpoint binding, and comparator diagnostics.
```

Success is not "S23 edge recall goes up once."

Success is:

- fewer duplicate cross-class proper noun nodes across S22/S23 and future sessions
- fewer ambiguous endpoint drops
- fewer wrong type/object bindings
- better diagnostics for alias candidates and do-not-merge cases
- no hardcoded gold/corpus synonyms in production code
- clear path from vocabulary candidate → reviewed alias/global node identity in the union supergraph

The Designing agent should treat this as a product architecture layer, not a benchmark patch.
