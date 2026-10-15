# INGEST: freeze Mirathorn worldbuilding answer gold

**Status:** ACTIVE — PRIME authors and validates this bounded gold slice; ARCHITECTURE independently reviews the exact result.

- **Base:** Buddy `main@211d97c44e5399dd22d7de28a3de2ab8d444d04c`
- **Branch:** `codex/mirathorn-worldbuilding-query-gold`
- **Checkout:** `/tmp/buddy-mirathorn-worldbuilding-query-gold`
- **Runtime/state:** none; no serving ports, operator databases, or retained World writes
- **Source:** `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md`, Build document `a5f32e92-80d1-42c8-96bd-4587321f39e7`, saved revision 2, SHA-256 `70444f40b9f16976f55620a72f802b1201efe56014a61343bb45811a33570342`

## Outcome

Create a hand-authored, source-locked question-answer gold that lets future extraction and ordinary Agent runs be evaluated against Mirathorn before inference. It must record expected answer claims, the exact source lines that support them, required graph traversal shape, unresolved identity/entailment boundaries, and source material this first slice intentionally leaves out.

This is a benchmark contract, not extraction output or graph publication. The existing Mirathorn candidate-graph gold remains useful historical material but is not silently treated as answer-quality evidence or as compatible with the current `worldbuilding_shepherds_flock_v0@0.1` profile.

## Required questions

Cover all five goal expectations with answerable prompts and source-backed answer keys:

1. Mirathorn's location and the routes/resources that make it a trade hub.
2. Its democratic council, named representatives, roles, and their different concerns about the cult issue. Do not invent a voting process or claim formal membership when the source only states a representative role.
3. Float Goats' water-walking ability and their stated transportation/labor uses, distinguishing general Elderwyld use from the specific Mirathorn approach passage.
4. The Festival of Expansion's commemorative purpose and its stated historical connection to the Aspitome bubble.
5. Thalia's command role, resistance to accusations of guard corruption, and the source's explanation for that resistance. Keep hidden information spoiler-sensitive.

Include at least two multi-hop question forms, one answerable-with-caution case, and negative controls for unsupported details. Each question names the fact IDs needed to answer it, whether abstention is expected, and the expected evidence lines.

## Source and quality rules

- Bind every claim to the exact path, saved revision, and SHA-256 above. Store only short quote anchors and line ranges; the validator must fail if the source bytes change.
- Phrase gold claims at the level the source states. Record explicit distinctions between source fact, cautious synthesis, and unsupported detail.
- Record profile coverage for each expected fact. The current Shepherd's Flock profile allows character/creature/location/faction/organization/group and excludes `event`, `item`, ecology and products. Identify where required answer facts do not fit instead of changing their meaning to fit the profile.
- Keep omissions explicit, including the extensive livestock/product material and unstructured approach/scene details. This gold slice does not claim full-document recall.
- Do not copy model answers into the gold, run a provider, edit source/corpus files, mutate the graph, publish candidates, or infer current database readiness.

## Exclusive write set

- This handoff.
- `evals/graph_memory_layer/examples/mirathorn_worldbuilding_query_gold_v1/gold.json`
- `evals/graph_memory_layer/validate_mirathorn_worldbuilding_query_gold_v1.py`
- `tests/test_mirathorn_worldbuilding_query_gold_v1.py`

No extraction profile, production schema, candidate graph, retrieval implementation, UI, API, provider configuration, database, corpus, or runtime changes. A discovered contract change outside this benchmark returns to PRIME for a separate bounded slice and ARCHITECTURE review.

## Owning-boundary verification

- Validate the JSON structure, source hash, all exact line ranges/quote anchors, fact references, question references, and uniqueness constraints with a deterministic no-network validator.
- Run focused tests proving valid gold passes; stale source digest, absent quote, invalid bounds, dangling fact IDs, and missing required expectation fail.
- Manually inspect every accepted answer claim against its cited source lines; verify each required fact is represented and each documented omission/profile gap remains visible.
- Run Ruff and `git diff --check`; inspect the complete base→head diff.

After this gold is independently reviewed, use it to guide a separate bounded ingestion improvement and run the pipeline against the exact saved revision. No extraction or provider run is part of this slice.
