# Graph Memory Runtime Category Pipeline Integration Handoff

**Status:** Implementation handoff  
**Created:** 2026-07-01  
**Workstream:** Graph Memory extraction spike  
**Depends on:** PR 00–10  
**Next implementation PR:** runtime preview runner option plumbing  
**Mode:** Planning only; no runtime behavior change

This handoff defines the next implementation path for wiring the category-decomposed Graph Memory extraction stack into runtime preview graph ingestion. It is not itself a runtime integration PR and must not change extraction behavior, API behavior, corpus content, graph writes, `/plan`, or canon state.

## 1. Purpose

The extraction spike now has enough evidence to plan a deliberately gated runtime preview integration. PRs #236–#242 established the path from encounter/job taxonomy through candidate graph support, optional encounter/job extraction, deterministic party participation attachment, opt-in encounter/job edge guidance, dynamic pass-targeted vocabulary selection, and deterministic projection dogfood.

PR #242's Glowkindle deterministic dogfood report is the stable expected shape for the preview stack: a quest node, a combat encounter node, party participation/pursuit edges, source-supported encounter/job edges, validation diagnostics, and explicit proof that no corpus, canon, graph-memory writes, runtime wiring, or `/plan` integration occurred.

The next implementation must expose the new extraction stack as a preview-only, explicitly gated runtime path, not as default production memory behavior.

## 2. Current runtime path

The current runtime-facing service path is:

```text
apps/live_control_server/services/recap_graph_preview_ingest.py
  -> build_recap_graph_preview_bundle(...)
  -> GraphPreviewRunnerOptions(...)
  -> run_graph_preview_extraction(...)
  -> extract_category_candidate_graph(...)
  -> CategoryGraphExtractionOptions(...)
```

The service is responsible for normalized recap lineage, reusable run lookup, output run directory allocation, and translating high-level runtime parameters into `GraphPreviewRunnerOptions`. The current high-level knobs are:

- `extract_graph`
- `graph_model_id`
- `candidate_graph_path`
- `force_graph_run`

Current behavior categories:

| Runtime input | Current behavior |
|---|---|
| `candidate_graph_path` supplied | Wraps an existing candidate graph fixture/artifact into the preview graph-ingest run, validates it, and bypasses LLM extraction. |
| `extract_graph=false` | Builds source span bundle / provenance artifacts and a manifest only. |
| `extract_graph=true` | Allows the runner to perform category-decomposed candidate graph extraction with an LLM/client. |
| `materialize_recap_preview_supergraph` | Can build or locate a preview union store from a graph ingest run after a candidate graph is available. |

The runner already has `allow_llm`, `category_client`, and `candidate_graph_path` controls. When `allow_llm` is true and no candidate graph fixture is supplied, it calls `extract_category_candidate_graph(CategoryGraphExtractionOptions(...))` with campaign/session/source-span/model fields. Runtime does **not** currently expose encounter/job flags, party attachment flags, encounter/job edge guidance, or dynamic vocabulary context-node plumbing.

## 3. New extraction capabilities to expose

Post-spike extraction capabilities that are not yet deliberately wired through runtime preview ingestion:

- `enable_encounter_job_pass`
- `enable_party_participation_attachment`
- `enable_encounter_job_edge_guidance`
- `enable_dynamic_node_vocabulary_packet`
- `dynamic_node_vocabulary_nodes`

Existing packet options that should remain available to implementation code, but not necessarily surfaced directly to UI, are:

- `enable_node_vocabulary_packet`
- `node_vocabulary_packet`
- `enable_edge_vocabulary_packet`
- `edge_vocabulary_packet`

The runtime implementation should not expose every low-level extraction option directly to the UI at first. The recommended first runtime surface is a profile parameter:

```text
graph_extraction_profile
```

Recommended profile values:

```text
current_default
category_baseline
category_encounter_job_preview
```

Suggested behavior:

```text
current_default:
  preserve current behavior / do not change defaults

category_baseline:
  use category-decomposed extraction without encounter/job extensions

category_encounter_job_preview:
  enable encounter_job_pass
  enable party participation attachment
  enable encounter/job edge guidance
  optionally enable dynamic vocabulary only when supplied context nodes are available
```

Because `extract_graph=true` already uses category-decomposed extraction in the current runner, this document uses `current_default` rather than implying there is still a separate compact runtime default.

## 4. Required runtime defaults

Defaults must preserve current behavior.

Required default rules:

- `extract_graph` remains false unless the caller explicitly asks for extraction.
- Encounter/job options remain disabled unless an explicit preview profile enables them.
- Dynamic vocabulary remains disabled unless explicit context nodes are supplied or a later PR implements safe retrieval.
- Party participation attachment remains disabled unless the encounter/job preview profile is selected.
- No graph memory writes.
- No canon promotion.
- No corpus mutation.
- No production retrieval changes.

## 5. Recommended next implementation PR

Suggested title:

```text
graph-memory: add runtime preview extraction profile plumbing
```

Suggested branch:

```text
codex/graph-memory-runtime-preview-profile-plumbing
```

Concrete implementation scope:

1. Add a `GraphExtractionProfile` enum/literal in `graph_preview_runner.py` or the runtime service layer. Prefer runner-level ownership if diagnostics and tests need the selected profile in the manifest; prefer service-layer ownership only if it can still produce complete runner diagnostics without leaking runtime-only concepts into eval proof machinery.
2. Add an optional profile field to `GraphPreviewRunnerOptions`, defaulting to the current behavior.
3. Map profile values to `CategoryGraphExtractionOptions` only at the point where category extraction is actually invoked.
4. Fail closed with `ValueError` on unknown profile values.
5. Do not enable LLM extraction merely because a profile was supplied; `allow_llm` / `extract_graph` must still gate extraction.
6. Keep `candidate_graph_path` behavior as a fixture/artifact bypass that does not call the LLM.
7. Add manifest diagnostics showing selected profile and the enabled extraction options.
8. Add a service-layer parameter only if it follows the existing route/API pattern and does not require UI work.
9. Keep the default profile equivalent to current behavior.
10. Add tests using `FixtureCategoryGraphPassClient`, temporary output directories, and no OpenAI key.
11. Do not touch UI yet.

Minimal implementation sketch:

```python
graph_extraction_profile: str | None = None
```

Then normalize to a closed set such as:

```text
current_default
category_baseline
category_encounter_job_preview
category_encounter_job_with_dynamic_context  # optional later, not required for v0
```

The first implementation PR should be boring: add profile, map profile to `CategoryGraphExtractionOptions`, preserve defaults, add tests, and stop.

## 6. Option mapping table

| Profile | encounter_job_pass | party attachment | edge guidance | dynamic vocabulary | Notes |
|---|---:|---:|---:|---:|---|
| `current_default` | false | false | false | false | Preserve existing behavior. |
| `category_baseline` | false | false | false | false | Category-decomposed extraction only; useful if the service wants an explicit non-extension profile. |
| `category_encounter_job_preview` | true | true | true | false initially | Enables PR #238–#240 stack while leaving dynamic context out of runtime v0. |
| `category_encounter_job_with_dynamic_context` | true | true | true | true | Optional later profile only if safe context nodes are explicitly supplied. |

If the next PR chooses to implement only `current_default`, `category_baseline`, and `category_encounter_job_preview`, it should document that dynamic context stays out of profile v0 until a safe context-node source exists.

## 7. Dynamic vocabulary runtime policy

PR #241 dynamic vocabulary selection accepts supplied context nodes. Runtime must not silently scan corpus or query a durable graph to fill those nodes in the first integration PR.

For the first runtime implementation:

- dynamic vocabulary disabled by default;
- optional explicit context-node payload may be accepted only if there is an existing safe internal path;
- otherwise leave dynamic vocabulary out of runtime profile v0;
- do not add corpus scanning;
- do not add union-supergraph retrieval;
- do not infer context nodes from arbitrary files.

A future follow-up can add:

```text
preview union store -> bounded context node selector -> dynamic vocabulary packet
```

That follow-up is not PR 12 / the next runtime plumbing PR. The first runtime integration rule is: dynamic vocabulary remains disabled unless explicit context nodes are supplied through a safe, reviewed path.

## 8. Manifest and diagnostics requirements

The next implementation PR should preserve the existing graph-ingest run manifest style and add profile diagnostics without requiring new artifact formats unless tests need them.

The manifest and/or runtime status response should surface:

- selected extraction profile;
- `allow_llm` / `extract_graph` value;
- `model_id`;
- candidate graph path;
- pass count;
- enabled encounter/job options;
- dynamic vocabulary enabled/disabled;
- party attachment enabled/disabled;
- edge guidance enabled/disabled;
- candidate graph validation status;
- node/edge/beat counts;
- estimated cost;
- warnings/errors.

For profile-enabled extraction, preserve these artifacts if already available:

- `candidate_graph.json`
- `pass_outputs.json`
- `pass_telemetry.json`
- `consolidation_diagnostics.json`
- `candidate_validation_report.json`
- `graph_ingest_run_manifest.json`
- `source_span_index.json`
- `provenance_index.json`

The manifest should make dropped edges, predicate validation issues, and any skipped option reasons visible rather than relying on logs alone.

## 9. API/runtime boundary

The likely runtime entry point for the first implementation is:

```text
apps/live_control_server/services/recap_graph_preview_ingest.py
```

The first implementation PR may add a service parameter, but should avoid UI work. Preferred service parameter:

```python
graph_extraction_profile: str | None = None
```

A boolean such as:

```python
encounter_job_preview: bool = False
```

is less desirable because it starts boolean soup and makes future profiles harder to reason about. Prefer `graph_extraction_profile`.

Required boundary behavior:

- Unknown profile values must fail closed with `ValueError`.
- Do not silently enable LLM extraction.
- Do not silently enable encounter/job profile when `extract_graph=False`.
- Do not change route/API behavior unless the existing route pattern already supports safely threading a new optional service parameter.
- Do not add UI controls in the first implementation PR.

## 10. Testing plan for next implementation PR

Required test locations:

```text
tests/test_graph_memory_category_graph_preview_runner.py
tests/test_live_graph_ingest_run_registry.py or equivalent runtime service tests
```

New or updated tests should prove:

1. default profile preserves current `CategoryGraphExtractionOptions` behavior;
2. `category_encounter_job_preview` maps to `enable_encounter_job_pass=True`;
3. `category_encounter_job_preview` maps to `enable_party_participation_attachment=True`;
4. `category_encounter_job_preview` maps to `enable_encounter_job_edge_guidance=True`;
5. dynamic vocabulary remains disabled unless context nodes are explicitly supplied;
6. selected profile appears in diagnostics/manifest/status;
7. unknown profile raises `ValueError`;
8. `extract_graph=False` does not run LLM even if profile is supplied;
9. `candidate_graph_path` fixture path still bypasses LLM extraction;
10. materialization path can consume the profile-generated candidate graph artifact;
11. no corpus mutation;
12. no canon promotion.

Testing should use:

- `FixtureCategoryGraphPassClient`
- temporary output directories
- no OpenAI
- no `OPENAI_API_KEY`

Suggested verification shape:

- runner-level tests inspect the captured `CategoryGraphExtractionOptions` or resulting pass behavior;
- service-level tests assert the profile is passed through only when extraction is explicitly requested;
- fixture-path tests assert a supplied `candidate_graph_path` remains a no-LLM bypass;
- manifest tests assert profile and option diagnostics are present while existing artifact paths and validation status remain compatible.

## 11. Manual dogfood gate

Before any UI or production default change, require a manual gate:

```text
Run one explicit graph preview extraction with category_encounter_job_preview on a chosen recap.
Inspect candidate_graph.json, pass_outputs.json, pass_telemetry.json, consolidation_diagnostics.json, and graph_ingest_run_manifest.json.
Compare shape to PR #242 Glowkindle dogfood report.
Confirm no corpus mutation and no canon promotion.
```

Required review questions:

- Did the graph produce useful quest/combat encounter nodes?
- Did party attachment avoid PC duplication?
- Did edge guidance improve source-supported edges?
- Did predicate validation stay clean?
- Were dropped edges visible?
- Was cost acceptable?
- Were runtime status and artifacts understandable?

The manual gate must be explicit and reviewed; passing automated tests alone should not authorize UI exposure or default changes.

## 12. Rollout plan

- Stage 0 — docs-only handoff, this PR.
- Stage 1 — runtime preview profile plumbing, no UI.
- Stage 2 — manual service/API dogfood with explicit profile.
- Stage 3 — optional UI control in `/plan` or graph review surface.
- Stage 4 — optional dynamic context from preview union store.
- Stage 5 — consider changing defaults only after manual review.

No stage should write graph memory or promote canon without a separate approval/persistence design.

## 13. Non-goals

- No runtime behavior change in this PR.
- No API change in this PR.
- No UI change in this PR.
- No extraction code change in this PR.
- No LLM run in this PR.
- No corpus scan or mutation.
- No graph memory writes.
- No approval persistence.
- No canon promotion.
- No default-on encounter/job extraction.
- No dynamic vocabulary graph retrieval.
- No union-supergraph retrieval integration.
- No /plan integration.

## 14. Acceptance checklist

- [ ] Current runtime path is documented.
- [ ] Current runner options are documented.
- [ ] New extraction capabilities are documented.
- [ ] Recommended profile model is documented.
- [ ] Default-preservation rules are explicit.
- [ ] Dynamic vocabulary runtime policy is explicit.
- [ ] Manifest/diagnostic requirements are explicit.
- [ ] Next implementation PR scope is concrete.
- [ ] Tests for next implementation PR are enumerated.
- [ ] Manual dogfood gate is defined.
- [ ] Non-goals forbid runtime/corpus/canon drift.
