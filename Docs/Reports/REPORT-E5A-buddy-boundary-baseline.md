# REPORT — E5A: Buddy inference and knowledge boundary baseline

| Field | Value |
| --- | --- |
| Status | characterization complete; no behavior cutover |
| Slice | E5A (not a migration) |
| Buddy baseline SHA | `94ae1ea927d6aa6c239085466973a11bff5cc605` (`main` at re-anchor) |
| OverMind Gate G | `f836de691bf57f2cfcee50c997ba8abe3040475a` |
| Accepted GenerationEngine | `0d01547e2d9afec68e87b4c8f7e6aaa047e8c42a` |
| Accepted DMS Generation consumer | `af4be1290c948fb7ccc4d969ab7c1e3b1aacd972` |
| Buddy DungeonMind pin | `dungeonmind[postgres] @ 63ec810a02f18c4e25af228f6fdb19d99d12579e` |
| Concurrent work left alone | [PR #721](https://github.com/Drakosfire/DungeonMindBuddy/pull/721) |

This report freezes what Buddy currently owns incorrectly, what is intentionally Buddy-owned, what GenerationEngine must learn before any consumer can move, and which smallest ordinary inference consumer should move first. It does **not** claim a query-only KnowledgeQuery seam or a GenerationEngine cutover.

Machine enforcement: `tests/test_e5a_boundary_fitness.py` (AST import allowlists over `apps/` and `src/`). E1B model-policy authority remains `tests/test_model_policy_authority.py`.

---

## 0. Re-anchor

| Fact | Value |
| --- | --- |
| Buddy `origin/main` | `94ae1ea927d6aa6c239085466973a11bff5cc605` — `docs(steward): never leave main checked out` |
| Open Buddy PRs at re-anchor | #721 only (`dogfood-continuity/candidate-generation-integrity-alignment-v1`) |
| GenerationEngine accepted pin | still `0d01547e…` (OverMind `acceptance/generation-boundary-g.toml`) |
| Python | `>=3.13,<3.14` |
| `openai` | `==2.24.0` (lock hash present) |
| `pydantic-ai-slim[openai]` | `==1.66.0` |
| `hermes-agent` | `861d69c7bba8d2ea6a1cd170e989c901c74d32d1` |
| `dungeonmind[postgres]` | `63ec810a02f18c4e25af228f6fdb19d99d12579e` |
| `GenerationClient` / `generationengine` in `apps/`+`src/` | **none** |
| `MODEL_POLICY.json` status | `buddy_owned_transition_policy` (unchanged) |

GE's OpenAI extra accepts `openai>=2.14.0`; Buddy's `2.24.0` pin is not inherently incompatible. E5A does **not** add GenerationEngine as a dependency.

Method: fresh AST import scan of `apps/` and `src/`, plus targeted reads of each active provider and DungeonMind path. `evals/`, `scripts/`, `tools/`, `extraction_lab/`, and `tests/` were inventoried only to keep them out of the runtime baseline.

---

## 1. Active inference inventory

Classifications are the handoff buckets. `src/llm/api_client.py` (`DungeonMindApiClient`) wraps raw OpenAI Responses / Chat Completions and records `action` + `elapsed_ms`. It does **not** import `openai`. Treat it as transition evidence, not a permanent Buddy inference abstraction, and do not solve E5 by hiding GenerationEngine behind the same OpenAI request/response surface.

No `apps/` file imports the OpenAI SDK directly. Hermes talks to OpenAI through `hermes_cli`; PydanticAI talks through `pydantic_ai.models.openai`.

### 1.1 `MIGRATE_LOW_LEVEL_TO_GE`

Ordinary text/structured execution. Not Batch. Not an Agent/Hermes tool loop.

#### `src/live_play/live_turn_classifier_client.py` — **first successor (see §5)**

| Field | Current |
| --- | --- |
| Callable | `OpenAILiveTurnClassifierClient.classify_turn` |
| Product action | Live Play turn routing |
| Shape | sync structured `responses.parse` |
| Schema | `LiveTurnClassificationModel` |
| Model resolution | arg → `LIVE_TURN_CLASSIFIER_MODEL` → policy action `live_turn_classifier` else `structured_generation` → `fast_smart` → **`gpt-5.3-codex`**; code fallback `gpt-4o-mini` |
| Timeout/retry | SDK default |
| Telemetry | `DungeonMindApiClient` action `live_play.classify_turn`, `elapsed_ms` |
| Failure | `ValueError` if no `output_parsed`; `classify_live_turn` may heuristic-fallback |
| Tests | `tests/test_live_play_classify_turn_llm_path.py`, `tests/test_model_policy_authority.py` |
| Candidate GE capability | `structured_text` |
| Profile default would change model? | **yes** (`structured_low_cost` → `gpt-5.1`) |
| Catalog addition required? | **yes** (`gpt-5.3-codex`) |

#### Other ordinary candidates

| Path / callable | Action | Shape | Effective model (policy present) | GE capability | Catalog add? | Profile would change model? |
| --- | --- | --- | --- | --- | --- | --- |
| `src/npc_statblock_pipeline/canonical_intent.py` `classify_intent` | NPC intent routing | sync `responses.create` JSON | `gpt-5.3-codex` via `structured_generation`; env `NPC_INTENT_CLASSIFIER_MODEL`; fallback `gpt-4o-mini` | `structured_text` | yes | yes |
| `src/ingestion/frontmatter_inference.py` `OpenAIFrontmatterInferenceClient.propose` | ingest metadata | sync `responses.parse` (`ProposedDocumentMetadata`) | `gpt-5.3-codex` via `structured_generation` | `structured_text` | yes | yes |
| `src/compiler/wiki_compiler.py` `compile_entity_page` | wiki prose | sync chat completions text | `gpt-5.3-codex` via `structured_generation`; env `DMB_WIKI_COMPILE_MODEL`; missing-policy fallback `gpt-5.4-nano` | `text` | yes | yes |
| `src/agent/synthesis.py` `synthesize_answer_async` | retrieval synthesis | async chat completions text (optional two-step) | `gpt-5.3-chat-latest` via `ruleslawyer_response_synthesis` / `retrieval_synthesis` | `text` | yes | yes |
| `src/live_play/live_query_context.py` `_run_llm_grounded_answer` | Play grounded answer | sync `responses.create` text | `gpt-5.3-chat-latest` via `ruleslawyer_response_synthesis` | `text` | yes | yes |
| `src/agent/document_planner.py` `plan_documents_async` | document selection | async chat completions JSON object | **`gpt-5.4-nano`** (policy has no `document_planning` / `query_planning` action) | `structured_text` | yes (`gpt-5.4-nano`) | yes |
| `src/ingestion/entity_extractor.py` OpenAI / `AsyncOpenAIResponsesEntityClient` | entity extract | sync+async `responses.parse`; extra sync repair `OpenAI()` | `gpt-5.3-codex` via `structured_generation` | `structured_text` | yes | yes |
| `src/ingestion/fact_extractor.py` OpenAI / `AsyncOpenAIResponsesFactClient` | fact extract | sync+async `responses.parse` | `gpt-5.3-codex` via `structured_generation` | `structured_text` | yes | yes |
| `src/graph_memory/extraction/category_candidate_graph_extractor.py` `run_pass` | category graph extract | sync `responses.create` structured text format; optional `max_retries` | `gpt-5.4-mini` via missing `graph_memory_category_extraction` action default `fast_smart_mini` | `structured_text` | yes | yes |
| `src/graph_memory/extraction/preview_candidate_graph_extractor.py` `OpenAICandidateGraphModelClient.extract_candidate_graph` | preview candidate graph | sync `responses.create` | caller-supplied `model_id` | `structured_text` / `text` as used | depends on caller | yes if profile-only |
| `src/graph_memory/extraction/staged_edge_extraction.py` staged relation observation | staged edges | sync `responses.create` structured | caller-supplied `model_id`; local `elapsed_ms` + usage cost | `structured_text` | depends on caller | yes if profile-only |

No `stream=True` / streaming client usage exists in `apps/` or `src/`. Do not claim `streaming_text` for the Buddy catalog delta.

`src/cli.py` constructs `OpenAI()` for ingest extractors and Batch jobs. The extractor wiring is ordinary inference composition; the Batch branch is `GE_CAPABILITY_GAP` (below). The file stays on the provider allowlist until both concerns move.

### 1.2 `BUDDY_HARNESS_OWNED`

| Path | Why this is not ordinary GE inference |
| --- | --- |
| `src/agent/planner.py` | Multi-turn `responses.create` with function tools (`query_session_memory`, corpus reads/writes). Product Agent/planner orchestration. |
| `apps/live_control_server/services/hermes_graph_agent.py` | Imports `hermes_cli` plugins; no direct `openai` import. Tool-loop graph Agent. Model comes from `resolve_agent_graph_openai_inference` (`gpt-5.3-codex` via `default_text_generation` / `hermes_graph_agent`, env `DUNGEONMIND_HERMES_GRAPH_MODEL`). |
| `apps/live_control_server/services/agent_graph_policy.py` | Product policy + model resolution for Hermes **and** PydanticAI. Not a provider call. |

Do not force these through GenerationEngine because they import or eventually reach OpenAI.

### 1.3 `PRODUCT_LIBRARY_BOUNDARY`

| Path | Notes |
| --- | --- |
| `apps/live_control_server/services/pydantic_ai_agent_runtime.py` | Graph Agent via `pydantic_ai`. Direct provider-adjacent import: `pydantic_ai.models.openai.OpenAIModel`. Frozen separately from the OpenAI SDK allowlist. Assess the library boundary before any GE migration. |

### 1.4 `GE_CAPABILITY_GAP`

| Path | Notes |
| --- | --- |
| `src/ingestion/openai_batch_pipeline.py` | OpenAI Batch API (`client.batches.create` / `retrieve`) targeting `POST /v1/responses`. Also imports `openai.lib._parsing._responses`. Accepted GE contract has no Batch capability. |
| `src/ingestion/schema_repair_batch.py` | Batch repair of invalid entity JSON via that pipeline. |
| `src/cli.py` Batch branch | `--use-openai-batch-api` constructs `OpenAI()` and `run_batch_job`. |

Do not shove Batch through ordinary GE generate APIs.

### 1.5 `EVAL_OR_TOOLING` (not in the runtime freeze)

Direct OpenAI appears under `evals/`, `scripts/` (e.g. `scripts/promote_stage_d_proposals.py`), `tools/` (`tools/corpus_batch.py`, `tools/batch_ingest_corpus.py`), and live pytest helpers. Those are not production architecture. The fitness tests do not scan them.

`src/cli.py` is product-tooling **and** a runtime composition root, so it **is** in the freeze.

### 1.6 Handoff examples rechecked

All named handoff examples still exist and still import OpenAI except that `src/llm/api_client.py` remains a wrapper without an SDK import, and there is still no `GenerationClient`.

---

## 2. Model-policy debt (unchanged behavior)

`MODEL_POLICY.json` stays `buddy_owned_transition_policy`. E5A did not edit it.

### 2.1 Active runtime/product-tooling readers

All of these go through `src.model_policy.load_buddy_model_policy` (E1B). Fitness: `tests/test_model_policy_authority.py`.

| Reader | What it reads | Kind |
| --- | --- | --- |
| `apps/live_control_server/services/agent_graph_policy.py` | action `hermes_graph_agent` else `default_text_generation` → `fast_smart` → `gpt-5.3-codex` | product action + alias + explicit model; env `DUNGEONMIND_HERMES_GRAPH_MODEL` override |
| `src/agent/synthesis.py` | `ruleslawyer_response_synthesis` → `retrieval_synthesis` → `gpt-5.3-chat-latest` | product action + alias; strict load |
| `src/agent/planner.py` | action `corpus_session_planner` (absent) → code fallback `gpt-5.4-mini` | missing action + code fallback |
| `src/agent/document_planner.py` | action `document_planning` / `query_planning` (absent) → `gpt-5.4-nano` | missing action + code fallback |
| `src/compiler/wiki_compiler.py` | `wiki_compile` else `structured_generation` → `fast_smart` → `gpt-5.3-codex` | product action + alias; env `DMB_WIKI_COMPILE_MODEL` |
| `src/live_play/classify_live_turn.py` | `live_turn_classifier` else `structured_generation` | product action + alias; env override |
| `src/live_play/live_query_context.py` | `ruleslawyer_response_synthesis` | product action + alias |
| `src/npc_statblock_pipeline/canonical_intent.py` | `npc_intent_classifier` else `structured_generation` | product action + alias; env override |
| `src/ingestion/frontmatter_inference.py` | `structured_generation` | product action + alias; strict |
| `src/ingestion/fact_extractor.py` | `structured_generation` | product action + alias; strict |
| `src/ingestion/entity_extractor.py` | `structured_generation` | product action + alias; strict |
| `src/graph_memory/extraction/category_candidate_graph_extractor.py` | `graph_memory_category_extraction` (absent) default role `fast_smart_mini` → `gpt-5.4-mini` | missing action + alias default; strict |

`tools/` and `scripts/` still construct `MODEL_POLICY.json` paths themselves. That is tooling, not the E1B runtime guard.

### 2.2 Policy roles vs future GE mapping

Current policy aliases:

```text
fast_smart            → gpt-5.3-codex
fast_smart_mini       → gpt-5.4-mini
retrieval_synthesis   → gpt-5.3-chat-latest
```

Current policy actions:

```text
default_text_generation          → fast_smart
structured_generation            → fast_smart
ruleslawyer_response_synthesis   → retrieval_synthesis
```

Future shape (not implemented here):

| Buddy action / reader | Eventual generic GE profile (candidate) | Parity constraint |
| --- | --- | --- |
| `default_text_generation`, Hermes/PydanticAI graph Agent | `text_fast` is the closest existing profile, but it resolves to `gpt-5.1` | **must pass explicit catalog model** `gpt-5.3-codex` until a later experiment |
| `structured_generation` and missing specialized actions that fall through to it | `structured_low_cost` currently → `gpt-5.1` | explicit `gpt-5.3-codex` |
| `ruleslawyer_response_synthesis` | `text_fast` currently → `gpt-5.1` | explicit `gpt-5.3-chat-latest` |
| planner default `gpt-5.4-mini` | `structured_low_cost` / `text_fast` | explicit `gpt-5.4-mini`; planner itself stays harness-owned |
| document planner `gpt-5.4-nano` | none of the current profiles | explicit catalog model if/when migrated |

No new generic profile is justified. The distinct requirement shapes are already `text` and `structured_text`. Image profiles are unused by Buddy.

Preserve current models first. Do not “fix” Buddy onto `gpt-5.1` / `gpt-5.6-luna` to fit the DMS cutover catalog.

---

## 3. GenerationEngine catalog / capability delta

Accepted GE `LIVE_MODELS` at `0d01547e…`:

```text
gpt-5.1, gpt-4o, gpt-5.6-luna, flux-2-pro, nano-banana-pro, gpt-image-1.5, flux-lora-i2i
```

Buddy live IDs **absent** from that catalog, with capabilities evidenced by current callers (not guessed):

| Model ID | Required GE capabilities | Evidence |
| --- | --- | --- |
| `gpt-5.3-codex` | `text`, `structured_text` | wiki / agent-policy text; live-turn + intent + frontmatter + entity/fact structured parse |
| `gpt-5.4-mini` | `structured_text` (planner also uses Responses+tools, which is **not** a GE capability) | category-graph structured `responses.create`; planner default |
| `gpt-5.3-chat-latest` | `text` | synthesis chat completions; live-query `responses.create` |
| `gpt-5.4-nano` | `structured_text` | document planner JSON chat completions (effective live model, **not** in `MODEL_POLICY.json`) |

Not added from this evidence:

- `streaming_text` — no Buddy runtime stream callers
- image capabilities — no Buddy Fal/image callers in `apps/`+`src/`
- `gpt-4o-mini` — code fallback only when policy is missing; live E1B path uses `gpt-5.3-codex`
- a new inference profile — existing profiles plus explicit catalog-model selection are enough for parity

`gpt-4o` is already in GE; Buddy does not currently select it when policy is present.

**Would existing GE profiles silently change Buddy models?** Yes, for every live consumer above. First migration must request an explicit catalog model, not `text_fast` / `structured_low_cost` defaults.

---

## 4. DungeonMind boundary inventory

Target remains query-only KnowledgeQuery. E5A classifies current read / init / contribution / publication / write debt instead of relabeling it as that target.

Pin: `dungeonmind[postgres] @ 63ec810a…`. Designated integration package: `apps/live_control_server/integrations/dungeonmind/`. Extra-boundary debt: `apps/live_control_server/services/runtime_preflight.py`.

`src/` has **no** `dungeonmind*` imports. `world_graph_authority_adapter.py` has **no** direct kernel import; it composes `world_graph_writes`.

Buddy product-local persistence (APP-STATE, Runs, workspace documents, candidate review UI state) is **not** DungeonMind publication. Those remain Buddy-owned.

### 4.1 Active classifications

| Path | Primary bucket | Import surface | Notes |
| --- | --- | --- | --- |
| `world_graph_reads.py` | `QUERY_CONSUMER` implemented as `INTERNAL_API_DEBT` | application retrieval/projection/snapshot; infrastructure postgres + semantic profiles; `dungeonmind_dnd` vocabulary; `domain.errors`; plus `contracts.evidence` / `projection` / `projection_v2` | Query-shaped consumption through kernel internals, not KnowledgeQuery. Also performs `PRODUCT_LOCAL_JOIN` (focus presentation, source-artifact titles/excerpts). **Not** already query-only. |
| `world_graph_writes.py` | `WRITE_PUBLICATION_DEBT` | `application.review_publication`, `contribution_review_v2`, postgres, canonical hashing, contracts for contribution/review/identity/capability | Buddy participates in governed publication. Conflicts with the E5 target. |
| `world_graph_initialization_adapter.py` | `WRITE_PUBLICATION_DEBT` | `application.reviewed_world_initialization`, semantic profiles, `dungeonmind_dnd` vocabulary, contribution/evidence contracts | First-world / reviewed initialization is mutation architecture. |
| `world_graph_source_admission_adapter.py` | `WRITE_PUBLICATION_DEBT` | evidence/vocabulary contracts, `domain.errors`, `infrastructure.postgres` | Source admit/put is world-knowledge mutation. |
| `contribution_mapping.py` | `WRITE_PUBLICATION_DEBT` | contribution/evidence/identity/vocabulary contracts + `domain.canonical` | Maps Buddy contribution values onto DungeonMind publication types. |
| `assertion_qualification.py` | `INTERNAL_API_DEBT` | `dungeonmind_dnd.application.world_object_vocabulary` | Kind/predicate qualification for governed writes. |
| `world_graph_authority_adapter.py` | `WRITE_PUBLICATION_DEBT` (composition) | none directly | Port adapter over writes. |
| `services/runtime_preflight.py` | `INTERNAL_API_DEBT` | `dungeonmind.infrastructure.postgres` | Outside the integration package. Connectivity/preflight, not a query contract. |

Public-contract modules in use (`dungeonmind.contracts.*`) are real, but they currently travel with internals and writes. Recorded as `PUBLIC_CONTRACT_TYPE` **imports**, not as proof the seam is already clean.

### 4.2 Tests / evals

`tests/` imports DungeonMind contracts, application helpers, in-memory repos, and postgres for cutover proofs. That is test support, not a second production integration boundary. Not frozen by E5A.

---

## 5. Successor migration queue

Ordered. E5A implements **none** of these.

### 5.1 GE catalog / capability PR (blocks ordinary Buddy inference moves)

Add to the accepted GenerationEngine catalog, with evidenced capabilities only:

```text
gpt-5.3-codex         text + structured_text
gpt-5.4-mini          structured_text
gpt-5.3-chat-latest   text
gpt-5.4-nano          structured_text   # only required before document_planner moves
```

No new profile. No Batch. No Agent. Do not change Buddy model selection in that PR either.

### 5.2 First Buddy consumer migration (selected, not implemented)

**`OpenAILiveTurnClassifierClient.classify_turn`** in `src/live_play/live_turn_classifier_client.py`.

Why this is the smallest safe ordinary slice:

- live Play runtime, not an eval
- one structured `responses.parse` call
- schema already a Pydantic model
- not Batch, not Hermes, not PydanticAI, not the planner tool loop
- `DungeonMindApiClient` already retains action + latency as an observation witness
- tests exist for routing + policy model resolution
- after §5.1, pass **explicit** `gpt-5.3-codex` (do not take `structured_low_cost` → `gpt-5.1`)
- blast radius is one adapter; `classify_live_turn` heuristic fallback can stay Buddy-owned

Do **not** re-wrap GenerationEngine behind `DungeonMindApiClient.responses_parse`.

Next ordinary inference slices after that, still blocked on catalog: `canonical_intent.classify_intent`, then `frontmatter_inference`, then `wiki_compiler.compile_entity_page`. Extractors and category-graph passes are larger.

### 5.3 KnowledgeQuery / read-boundary successor

Replace `world_graph_reads.py` application/infrastructure imports with the controlled query-only KnowledgeQuery contract. Keep Buddy `PRODUCT_LOCAL_JOIN` (focus flags, source titles) on the Buddy side of that seam. `runtime_preflight.py` should stop importing `dungeonmind.infrastructure.postgres` once a public health/query surface exists.

C3 stays `transitioning` until this lands.

### 5.4 World-write / publication retirement successor

Retire or relocate:

```text
world_graph_writes.py
world_graph_initialization_adapter.py
world_graph_source_admission_adapter.py
contribution_mapping.py
assertion_qualification.py
world_graph_authority_adapter.py  (as a publication driver)
```

This is **not** “delete Buddy persistence.” It is “Buddy must not own DungeonMind graph publication.” Requires a product decision on how Graph Review confirm/initialize works without Buddy calling `review_publication`.

### 5.5 Explicit design, not incidental migration

| Concern | Disposition |
| --- | --- |
| OpenAI Batch (`openai_batch_pipeline`, schema repair, CLI flag) | Keep as `GE_CAPABILITY_GAP` until GenerationEngine (or a conscious non-GE choice) owns Batch |
| Hermes graph Agent | Remains Buddy-owned orchestration |
| PydanticAI graph Agent | Product library boundary; do not treat `OpenAIModel` as a GE client |
| `src/agent/planner.py` tool loop | Buddy-owned; do not call it a GE text migrate |
| AgentEngine extraction | Forbidden until a real second consumer exists |

§5.1 can proceed in GenerationEngine in parallel with §5.3 design. §5.2 waits on §5.1. §5.4 must not ship as “query-only” by renaming writes.

---

## 6. Fitness tests (debt cannot grow)

| Test | Freeze |
| --- | --- |
| `test_direct_provider_sdk_imports_match_e5a_baseline` | exact `(path, module)` OpenAI/other provider SDK imports in `apps/`+`src/` |
| `test_pydantic_ai_openai_adapter_imports_match_e5a_baseline` | `pydantic_ai.models.openai` |
| `test_generationengine_is_not_imported_in_active_runtime` | empty — unused GE dependency is not progress |
| `test_dungeonmind_imports_match_e5a_baseline` | exact `(path, module)` `dungeonmind*` imports |
| `test_dungeonmind_imports_outside_integration_boundary_are_exact` | only `runtime_preflight.py` may import DungeonMind outside `integrations/dungeonmind/` |
| `test_dungeonmind_internal_imports_are_explicit_debt` | application / infrastructure / domain / `dungeonmind_dnd` tuples, distinct from `dungeonmind.contracts.*` |
| `test_model_policy_remains_buddy_owned_transition_policy` | file still exists; status unchanged |
| existing `tests/test_model_policy_authority.py` | E1B path + consumer model parity |

Allowlists are **not** target architecture. A migration PR that removes a direct import must shrink the matching frozenset in the same change.

---

## 7. Explicitly skipped / not done

- No live provider call migrated to GenerationEngine
- No Buddy model IDs added to GenerationEngine
- No unused GenerationEngine dependency
- `MODEL_POLICY.json` not deleted or rewritten
- Effective model selection unchanged
- Hermes not removed or redesigned
- AgentEngine not extracted
- Batch not forced through GE generate APIs
- KnowledgeQuery not rewritten
- DungeonMind writes/publication not removed
- Plan/Build/Play behavior unchanged
- Graph candidate semantics unchanged
- PR #721 / DOGFOOD-CONTINUITY not absorbed
- E4 public Web/API work not touched
- No new OverMind runtime consumers
- No repository/package rename

If a later PR changes a boundary file: rebase, regenerate the AST inventory, update the exact baseline, rerun these tests. Never keep a stale allowlist to win the merge.
