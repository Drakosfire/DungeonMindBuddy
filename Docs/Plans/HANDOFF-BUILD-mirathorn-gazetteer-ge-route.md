# BUILD — run Mirathorn Gazetteer through GenerationEngine

Status: ACTIVE; PRIME implementation; ARCHITECTURE exact-result review; DOGFOOD owns
rendered surface evaluation. Base: Buddy `main@05cfd78c31c9adfc8de47d1c699d7384fc501c2d`.
Branch: `codex/build-mirathorn-ge-route`; isolated checkout `/tmp/prime-buddy-mirathorn-current`.
Topology: parallel-independent from DOGFOOD #1183 (disjoint files and no behavioral dependency)
and MIND #1142–#1149 (do not edit their active extraction-runner, client, or extractor files).

## Outcome

When an operator explicitly chooses Build’s Gazetteer extraction for the saved Mirathorn
source, launch `worldbuilding_gazetteer_v1@1.5` through the existing GenerationEngine
OpenRouter route with `deepseek/deepseek-v4.1-flash`. Keep the Shepherd’s Flock pilot
choice and its historical run identity unchanged. Bind the request to the committed
workspace document revision, registered source artifact, and exact source digest.
Persist the extraction run and candidate evidence locally, with cost/usage evidence;
do not publish candidate knowledge to the Elderwyld World in this slice.

The operator has standing authorization for approved C1/C2 and saved worldbuilding
corpus extraction through GenerationEngine → OpenRouter DeepSeek V4.1 Flash. This
execution uses the approved route, makes no retries or fallback, and records observed
provider usage/cost. The profile's existing invocation budget is an execution safeguard,
not an authorization cap; its current six required passes fit the existing eight-pass
runner. Do not request per-run approval.

## Exact input and target

- Workspace document: `a5f32e92-80d1-42c8-96bd-4587321f39e7`
- Saved revision: `2`
- Source SHA-256: `70444f40b9f16976f55620a72f802b1201efe56014a61343bb45811a33570342`
- Document class: `lore`; source domain: `worldbuilding`
- Workspace World key: `elderwyld`; this is scope only, not the in-fiction continent identity.
- Profile: `worldbuilding_gazetteer_v1@1.5`
- Model/provider: GenerationEngine → OpenRouter → `deepseek/deepseek-v4.1-flash`, no fallback.

The exact saved source artifact is already registered. Do not alter its content, revision,
world ownership, identity, or native graph. Any provider run uses an isolated `/tmp`
copy of this exact source and required registry/index records; no source, run artifact,
or candidate is written into the user's working corpus or retained World.

## Expected write set

- This handoff.
- `apps/live_control_server/routes/graph_preview.py`
- `apps/live_control_server/services/worldbuilding_ge_execution.py`
- `apps/live-control-ui/src/buildSurface/useBuildExtraction.ts`
- `apps/live-control-ui/src/buildSurface/useBuildExtraction.test.tsx`
- `tests/test_graph_preview_routes.py`
- `tests/test_worldbuilding_ge_execution.py`

Do not edit `apps/live_control_server/services/graph_preview_runner.py` (#1142 lease),
`src/graph_memory/extraction/bounded_recap_execution.py` (#1146 lease),
`src/graph_memory/extraction/category_candidate_graph_extractor.py` (#1143/#1145/#1148/#1149
leases), DOGFOOD #1183 paths, model policy, credentials, source/corpus, deployment config,
managed-World registries, database schema, or publication code.

## Required behavior and failure cases

- `pilot` remains the current UI default and submits the exact existing profile pair.
- Explicit `gazetteer` submits profile `worldbuilding_gazetteer_v1@1.5`; returned run identity
  must match that exact profile.
- Server derives document/source/World ownership from the committed registry and registered
  artifact, verifies expected revision and hash before constructing an inference client, and
  ignores any client-supplied model/provider/World target.
- The Gazetteer 1.5 run uses GenerationEngine's bounded OpenRouter DeepSeek client required
  by its constrained edge review. It must fail before provider use on stale/missing source,
  wrong source domain/class, uncommitted or divergent bytes, unsupported profile, absent
  credential, or wrong profile/client pairing. No OpenAI fallback.
- Preserve run status, source span index, candidate graph, review bundle, private responses,
  and cost/usage observations. Retries/fallback remain disabled for this experiment.
- Candidate-only: no prepare/confirm/publish operation and no mutation of the Elderwyld graph.

## Verification

1. Route and hook tests prove exact document/revision/hash/profile selection, returned identity,
   unchanged pilot behavior, stale-source and invalid-profile rejection, and no provider call
   for failed preconditions.
2. Owning execution-service tests exercise GenerationEngine request construction, DeepSeek-only
   routing, no fallback/retry, structured pass schema, ledger persistence, and run artifacts.
3. Run the exact saved source once in the isolated `/tmp` data root through the route's owning
   extraction service. Review nodes, relationships, descriptions, and evidence spans against
   `evals/graph_memory_layer/examples/mirathorn_worldbuilding_query_gold_v1/gold.json`; record
   explicit misses and unsupported claims. This is candidate evidence, not publication or
   answer-quality proof.
4. Run the gold validator, focused Python tests, focused UI tests/typecheck, Ruff, and
   `git diff --check`; inspect the complete cumulative base→head diff.
5. Send the exact PR head to ARCHITECTURE for independent review. No merge until that review,
   required checks, and the exact-run evidence are recorded. PRIME retains merge authority.

## Exclusions and successor gates

This does not fix missing source-owner extraction, introduce `dnd5e:governs`, establish managed
World native-ID isolation, implement correction/publication, prove ordinary Agent traversal,
open source passages through Plan/Play, or close Build rendered acceptance. Those remain
separate gates in the parent Mirathorn lifecycle goal. Never describe extraction success as
published/queryable knowledge.
