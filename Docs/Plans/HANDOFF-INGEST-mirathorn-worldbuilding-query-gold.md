# INGEST: freeze Mirathorn worldbuilding answer gold

**Status:** ACTIVE — PRIME authors and validates this bounded gold slice; ARCHITECTURE independently reviews the exact result.

- **Base:** Buddy `main@211d97c44e5399dd22d7de28a3de2ab8d444d04c`
- **Branch:** `codex/mirathorn-worldbuilding-query-gold`
- **Checkout:** `/tmp/buddy-mirathorn-worldbuilding-query-gold`
- **Runtime/state:** none; no serving ports, operator databases, or retained World writes
- **Source:** `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md`, Build document `a5f32e92-80d1-42c8-96bd-4587321f39e7`, saved revision 2, SHA-256 `70444f40b9f16976f55620a72f802b1201efe56014a61343bb45811a33570342`

## Outcome

Create a hand-authored, source-locked question-answer gold before the next target run. This is development material, not a blind holdout: prior Mirathorn work and the existing candidate-graph gold were reviewed. Record expected answer claims, exact source lines, real graph traversal contracts where applicable, unresolved identity/entailment boundaries, and source material this slice leaves out.

This is a benchmark contract, not extraction output or graph publication. The existing Mirathorn candidate-graph gold remains useful historical material but is not silently treated as answer-quality evidence. The Shepherds Flock `0.1` profile is recorded as a selected pilot baseline only; main also contains Gazetteer `1.5`, while the execution profile and registered document class for this Build source remain unverified.

## Required questions

Cover all five goal expectations with answerable prompts and source-backed answer keys:

1. Mirathorn's location and the routes/resources that make it a trade hub.
2. Its democratic council, named representatives, roles, and their different concerns about the cult issue. Do not invent a voting process or claim formal membership when the source only states a representative role.
3. Float Goats' water-walking ability and their stated transportation/labor uses, distinguishing general Elderwyld use from the specific Mirathorn approach passage.
4. The Festival of Expansion's commemorative purpose and its stated historical connection to the Aspitome bubble.
5. Thalia's command role, resistance to accusations of guard corruption, and the source's explanation for that resistance. Keep hidden information spoiler-sensitive.

Include at least two multi-source or relationship-sensitive question forms, one answerable-with-caution case, and negative controls for unsupported details. Keep answer facts separate from graph paths. A path counts as graph traversal only when it lists connected source/target node selectors, exact predicates, direction, and evidence fact IDs, and its steps pass the native write-admission contract. Elara → city council → Mirathorn is a recorded representation gap: `leads` is mapped and endpoint-admitted, but `governs` is extraction-legal and absent from native write mapping. It must not be called a supported native multi-hop path until the owning contract changes. Representative concerns remain separate source-backed facts, with no inferred `member_of` edges. Generic Float Goats and the festival may be answered from source-backed descriptions/passages; correctness does not require a species or event node. Record each question's audience and explicit hidden-fact exclusions.

## Source and quality rules

- Bind every claim to the exact path, saved revision, and SHA-256 above. Store only short quote anchors and line ranges; the validator must fail if the source bytes change.
- Phrase gold claims at the level the source states. Record explicit distinctions between source fact, cautious synthesis, and unsupported detail.
- Record the selected pilot baseline and available Gazetteer `1.5` behavior separately. The `0.1` baseline excludes `event`, ecology and products and extracts named individuals rather than generic species; Gazetteer `1.5` supports recurring festival definitions and retains livestock details on associated place descriptions. Neither profile snapshot proves which one executed for this saved source.
- Separate answer correctness from typed Graph representation. Do not require Festival/Float Goat entity nodes solely to answer their source facts; don't turn Mirathorn's approach scenery into an enduring world fact or played event.
- Pin both extraction vocabulary and the actual native write-qualification mapping, candidate-to-native kind conversion, and Buddy's exact DungeonMind world-object-v5 dependency and predicate endpoint snapshot. Extraction legality alone does not prove native publication admission. Every path marked supported must have admitted endpoints, edge-contiguous direction, and question evidence dependencies; unmapped or endpoint-unverified paths remain explicit gaps.
- The pinned DungeonMind vocabulary is commit `33db6c526aa8568cc2a1eeb686aab2a5f3b5ca28`, blob `7eee30a5c10e1a407a3687e050f06eab55bc08a3` ([world-object-v5.json](https://github.com/Drakosfire/DungeonMind/blob/33db6c526aa8568cc2a1eeb686aab2a5f3b5ca28/src/dungeonmind_dnd/vocabularies/world-object-v5.json)). Its `dnd5e:leads` endpoint admits NPC → faction; Buddy's explicit native mapping has no `governs` entry. The gold records the Elara → council → Mirathorn chain as a representation gap, not a supported native path.
- Require GM/player audience on questions. GM-only answers may use Thalia's hidden enchantment; player-safe answers must exclude it as a dependency and explicitly forbid its disclosure.
- Keep omissions explicit, including the extensive livestock/product material and unstructured approach/scene details. This gold slice does not claim full-document recall.
- Do not copy model answers into the gold, run a provider, edit source/corpus files, mutate the graph, publish candidates, or infer current database readiness.

## Exclusive write set

- This handoff.
- `evals/graph_memory_layer/examples/mirathorn_worldbuilding_query_gold_v1/gold.json`
- `evals/graph_memory_layer/validate_mirathorn_worldbuilding_query_gold_v1.py`
- `tests/test_mirathorn_worldbuilding_query_gold_v1.py`

No extraction profile, production schema, candidate graph, retrieval implementation, UI, API, provider configuration, database, corpus, or runtime changes. A discovered contract change outside this benchmark returns to PRIME for a separate bounded slice and ARCHITECTURE review.

## Owning-boundary verification

- Validate source/profile/predicate hashes, exact quote anchors, fact references, graph path endpoints/predicates/continuity, profile representation requirements, native predicate mapping versus extraction vocabulary, audience scope, and uniqueness constraints with a deterministic no-network validator.
- Run focused tests proving valid gold passes; stale source, profile or predicate digest, absent quote, invalid bounds, dangling fact IDs, unsupported/disconnected graph paths, dropped player hidden-fact exclusions, and missing required expectations fail.
- Manually inspect every accepted answer claim against its cited source lines; verify each required fact is represented and each documented omission/profile gap remains visible.
- Run Ruff and `git diff --check`; inspect the complete base→head diff.

After this gold is independently reviewed, use it to guide a separate bounded ingestion improvement and run the pipeline against the exact saved revision. No extraction or provider run is part of this slice.
