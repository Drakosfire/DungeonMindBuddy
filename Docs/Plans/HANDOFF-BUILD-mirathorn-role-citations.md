# PRIME handoff — deterministic Gazetteer role citations

**Status:** COMPLETED — merged as `44f63d962951974edfe8d7f0f84f15a058271f87`; this implementation lease is closed.
**Base:** DungeonMindBuddy `main@3a890b9ec8b4e4c9924779249fe8570b7ecf9d1c`  
**Branch:** `codex/mirathorn-role-citations-v17`  
**Topology:** serial, one PR  
**Runtime/state ownership:** none. Do not change serving processes, databases, retained World data, or ports.

## Outcome

Add a separately versioned Gazetteer profile `worldbuilding_gazetteer_v1@1.7` that restores a missing source citation for a character role only when all of these are true:

1. A source-span row is an exact `Role: <value>` field, with or without Markdown emphasis.
2. Exactly one extracted character node has a description containing that exact normalized role value.
3. The node does not already cite that source span.

The transformation may add the exact source span and quote as evidence; it must not change node identity, type, description, relationships, confidence, or any semantic claim. Non-matching role rows are ignored. A role line without one unique matching character receives a deterministic no-match or ambiguous-match diagnostic and remains unchanged. The existing source-span-index validation continues to reject invalid span structure before this profile runs. Profiles 1.0–1.6 retain their current behavior and versioned identity. Build selects 1.7, routed through the existing pinned GenerationEngine/OpenRouter DeepSeek path.

## Evidence motivating this slice

The exact saved Mirathorn revision-2 candidate produced under profile 1.6 has seven character descriptions containing their source-backed representative roles without citing the corresponding `Role:` lines. The frozen gold expects those role facts and their exact lines. Adding citations conditionally repairs provenance without asking a model to invent or reinterpret a fact.

The source-backed query gold remains the authority for the expected facts and relationships. Do not change its facts, questions, evidence quotes, or answer criteria.

## Write set

- `Docs/Plans/HANDOFF-BUILD-mirathorn-role-citations.md`
- `src/graph_memory/extraction/worldbuilding_gazetteer_role_citations.py`
- `src/graph_memory/extraction/worldbuilding_profile_catalog.py`
- `apps/live_control_server/services/worldbuilding_ge_execution.py`
- `apps/live_control_server/routes/graph_preview.py`
- `apps/live-control-ui/src/buildSurface/useBuildExtraction.ts`
- `apps/live-control-ui/src/buildSurface/useBuildExtraction.test.tsx`
- `tests/test_worldbuilding_gazetteer_profile.py`
- `tests/test_worldbuilding_ge_execution.py`
- `tests/test_worldbuilding_ge_route.py`
- `evals/graph_memory_layer/examples/mirathorn_worldbuilding_query_gold_v1/gold.json`

No other path is leased. Do not stage corpus text, source passages, private provider responses, credentials, database files, or local candidate-run outputs.

## Required verification

- Unit tests cover exact role-field parsing, negated and no-match cases, ambiguous character matches, and existing-reference idempotence; the existing source-span-index validator retains its invalid and duplicate-span checks.
- A real `run_category_pipeline` fixture proves the versioned profile adds only the exact source evidence reference and preserves all semantic fields. A neighboring no-match case remains unchanged.
- Tests prove profiles 1.0–1.6 keep their historical version/behavior and 1.7 is catalogued.
- Build uses 1.7; the route and GenerationEngine execution adapter accept 1.7 while retaining source digest/revision/provider pinning and rejecting unsupported versions.
- Reprocess the preserved 1.6 responses locally through the 1.7 deterministic postprocessor, then compare role citations with the frozen source-locked gold. No network/provider access is used for replay; preserve old run evidence unchanged.
- Update only the gold profile snapshot/catalog inventory and truthful execution metadata; keep all facts, questions, quotes, and acceptance criteria byte-for-byte semantically unchanged.
- Focused Python tests, UI hook tests, UI typecheck/build, Ruff, and exact cumulative diff checks pass.
- Request ARCHITECTURE independent review of the exact completed head. No World publication or end-to-end Agent acceptance is claimed by this slice.

## Hold

This slice does not authorize World publication, retained Graph writes, runtime restart/deployment, a new provider request, manual corpus repair, or changes to the gold acceptance expectations. Candidate replay is local and deterministic. The broader PRIME lifecycle remains active after this PR.
