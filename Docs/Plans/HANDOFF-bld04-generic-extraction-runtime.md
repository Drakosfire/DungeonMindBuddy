# HANDOFF — BLD-04 generic extraction runtime

- **Created:** 2026-07-22
- **Status:** DRAFT — dispatch only after BLD-03 is merged and re-anchored
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld04-generic-extraction-runtime.md`
- **Suggested branch:** `agent/bld04-generic-extraction-runtime`

## Shared vocabulary

| Term | Definition |
|---|---|
| Source adapter | Domain-specific normalization from an admitted SourceArtifact to extraction input. |
| Extraction profile | Explicit category/schema/prompt policy selected for a source domain. |
| Candidate graph | Validated proposed graph output, not durable graph truth. |
| Extraction failure | Refusal, incomplete response, schema failure, validation failure, or source-integrity failure recorded in the run. |

## §1 Mission

The extraction runtime can process both recap and evergreen worldbuilding
SourceArtifacts through explicit adapters, producing source-anchored
reviewable candidates without fabricating session identity.

**Invariant:** Every candidate assertion is tied to a validated source artifact
and span, while recap behavior remains available through a compatibility adapter
and extraction failures remain explicit.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` and `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md` |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-04 |
| Repository rules | `AGENTS.md`, `.cursor/rules/responses-api-structured-extraction.mdc`, `.cursor/rules/model-policy.mdc` if present, `.cursor/rules/external-agent-pr-loop.mdc` |
| Base revision | Dispatch-time immutable merge SHA of BLD-03; current `8ff2339f` is reference only |
| Predecessor contract | BLD-03 SourceArtifact/ExtractionRun, current recap extraction options, candidate graph schema, source-span/provenance contracts |
| Exact input consumed | Validated SourceArtifact, source spans, extraction profile, source text, and configured model policy |
| Named successor | BLD-08 worldbuilding profile tuning |
| What remains false | Build UI, Graph Review generic loading, graph publication, PDF/OCR |
| Explicit non-goals | Prompt taxonomy tuning beyond adapter plumbing, direct graph writes, latest-run inference, arbitrary Markdown discovery, eval-only runner as production service |

Read in order:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `.cursor/rules/responses-api-structured-extraction.mdc`
3. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
4. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
5. BLD-03 source/run contracts
6. `src/graph_memory/extraction/category_candidate_graph_extractor.py`
7. Current recap runner and owning tests

If a worldbuilding adapter requires category semantics rather than runtime
plumbing, stop and move that work to BLD-08.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Recap extraction | Requires campaign/session-shaped options | Recap adapter maps to generic source input | Yes | Recap adapter |
| Worldbuilding Markdown | No generic runtime path | Worldbuilding adapter runs with null session | Yes | Worldbuilding adapter |
| Source spans | Recap-shaped/path-derived anchors | Every candidate points to source artifact/span | Yes | Extraction runtime |
| LLM response refusal | May surface as generic failure | Persist explicit refusal diagnostic and failed run | Yes | Extraction controller |
| LLM incomplete response | May parse/default incorrectly | Persist incomplete diagnostic; no empty graph fallback | Yes | Extraction controller |
| Schema invalid response | Must not become `{}` | Persist schema diagnostic and fail run | Yes | Structured-output boundary |
| Validation failure | Candidate may be unusable downstream | Run is non-reviewable with named diagnostics | Yes | Candidate validator |
| Retry | Current runner may be rerun by path | Retry exact artifact/profile with distinct or resumed run policy | Yes | Run registry/controller |

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `src/graph_memory/extraction/source_adapter.py` | Generic adapter protocol and normalized extraction input |
| Create | `src/graph_memory/extraction/recap_source_adapter.py` | Compatibility mapping for recap sources |
| Create | `src/graph_memory/extraction/worldbuilding_source_adapter.py` | Markdown worldbuilding source normalization |
| Modify | `src/graph_memory/extraction/category_candidate_graph_extractor.py` | Accept generic source/profile input and preserve evidence |
| Modify | `src/graph_memory/extraction/graph_extraction_options.py` | Profile/source-aware options without mandatory session |
| Create | `src/graph_memory/extraction/graph_preview_runner.py` | Production controller lifecycle and generic run inputs |
| Create | `apps/live_control_server/services/graph_preview_runner.py` | Live service wiring to generic controller |
| Modify | `apps/live_control_server/services/recap_graph_preview_ingest.py` | Keep recap behavior as an explicit adapter |
| Create | `tests/test_source_adapters.py` | Recap/worldbuilding mapping and null-session proof |
| Create | `tests/test_graph_preview_runner.py` | Run lifecycle, refusal, incomplete, schema, validation failure proof |
| Create | `tests/test_category_candidate_graph_extractor.py` | Source anchors and generic options proof |

**Bounded discovery exception:** Not applicable — paths are enumerated.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why out of scope |
|---|---|
| `src/graph_memory/extraction/category_candidate_graph_schema.py` | New category/profile taxonomy belongs to BLD-08 unless existing schema is insufficient; stop if so |
| `apps/live-control-ui/src/buildSurface/**` | UI belongs to BLD-05/06 |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/**` | Review loading belongs to BLD-07 |
| `apps/live_control_server/services/extract_promote_ops.py` | No graph publication changes |
| `evals/graph_memory_layer/graph_preview_runner.py` | Existing eval runner remains an eval consumer; do not turn it into the production controller |
| `evals/**` | Runtime must not be replaced by eval-only artifacts |
| `corpus/**` | No bulk source ingestion |
| Prompt prose or category expansion | BLD-08 tuning capability |

## §6 Implementation contract and conditional matrices

```text
Input:
  Validated SourceArtifact + source spans + selected extraction profile +
  source text + model policy-resolved structured-output client.

Output:
  ExtractionRun with candidate graph, source evidence, validation report,
  diagnostics, and reviewable/failed status.

Invariant:
  No candidate is reviewable without source evidence and schema/validation
  success; no session is synthesized for worldbuilding input.

Failure behavior:
  Refusal → explicit refusal diagnostic and failed run.
  Incomplete response → explicit incomplete diagnostic and failed run.
  Schema failure → explicit schema diagnostic and failed run.
  Source/span failure → non-reviewable run; never source-free candidate graph.
  Model/API failure → stable retryable run failure with no empty-graph success.

Replay / idempotency:
  same source digest + profile + model policy → deterministic request identity;
  changed source/profile → new run;
  retry after partial failure → resume or distinct run under BLD-03 policy;
  persisted output is never silently replaced by `{}`.

Trust boundary:
  Verifies: source admission, span references, structured schema, refusal/
  incomplete state, validation, model policy resolution, and run status.
  Records or trusts without proving: semantic truth of candidate claims.
```

### State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Source admission | Await validated artifact | Controller accepts | 404/invalid artifact | Stable dependency error | Fail closed | Digest conflict | Re-admit exact artifact |
| LLM extraction | Run is `extracting` | Typed output proceeds | Empty source is explicit invalid input | Retryable failure | Refusal/incomplete/schema failure | Profile/model mismatch fails | Retry under run policy |
| Candidate validation | Run is `validating` | Reviewable only if clean | No candidates is explicit result | Validator unavailable fails run | Invalid graph is non-reviewable | Source digest mismatch fails | Re-run exact source/profile |
| Recap adapter | Map known recap | Existing behavior preserved | Unknown shape fails | Existing service error | No fabricated defaults | Session mismatch fails | Same input only |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| Source artifact | Use stable artifact ID from BLD-03 | Never use display path as identity | No |
| Source span | Reference exact source artifact/span ID | Missing span invalidates assertion/run | No text-only fallback |
| Session scope | Optional for worldbuilding | Null remains null | No synthetic session |
| Profile | Stable explicit profile ID/version | Unknown profile fails before LLM call | No default recap profile |

### Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| Extraction request | Run manifest + profile/model policy metadata | Reload identifies exact input | Retry follows BLD-03 run policy | Recap adapter remains readable | Mark failed/incomplete |
| Candidate graph | Validated candidate artifact with evidence | Every assertion resolves to source span | Never overwrite success with empty fallback | Existing candidate schema remains readable | Reject run, no graph write |
| Diagnostics | Structured failure records | Refusal/incomplete/schema state survives reload | Retry appends/updates per run policy | Existing error consumers remain safe | Preserve failure evidence |

### Predecessor-to-consumer mapping

| Predecessor | Consumer | Transformation | Proof |
|---|---|---|---|
| Recap extraction options | `RecapSourceAdapter` | Populate generic fields while retaining session | Adapter tests |
| Markdown source artifact | `WorldbuildingSourceAdapter` | Normalize paragraphs/spans with null session | Adapter tests |
| Existing category pass output | Generic candidate graph | Attach source artifact/span evidence | Extractor tests |
| OpenAI response | Extraction controller | Parse `text.format` strict schema and handle refusal/incomplete explicitly | Failure tests |

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command | Expected evidence |
|---|---|---|---|
| Recap and worldbuilding adapters map correctly | Adapter boundary | `uv run pytest tests/test_source_adapters.py` | Null-session world source and recap regression |
| Source evidence is mandatory | Extractor boundary | `uv run pytest tests/test_category_candidate_graph_extractor.py` | Source-free candidates rejected |
| Refusal/incomplete/schema failures persist | Controller boundary | `uv run pytest tests/test_graph_preview_runner.py tests/test_graph_memory_category_graph_preview_runner.py` | Named failed-run diagnostics and existing runner compatibility |
| No prompt-only JSON fallback | LLM boundary | Same controller tests + diff inspection | Strict structured-output call and explicit failure handling |
| No scope creep | Git | `git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD` | Only §4 paths |

```bash
uv run pytest tests/test_source_adapters.py \
  tests/test_category_candidate_graph_extractor.py \
  tests/test_graph_preview_runner.py \
  tests/test_graph_memory_category_graph_preview_runner.py
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing surface used: source-artifact/graph-preview controller
Smallest scenario: run one fixture-backed worldbuilding extraction and one
recap extraction, then inject refusal/incomplete/schema failures
Expected observation: successful runs retain evidence; failures are explicit
Evidence captured: focused test output and persisted run fixtures
```

## §8 Required handback

1. Base and head SHA.
2. Focused diff stat limited to §4.
3. Exact result of every §7 command.
4. Provenance for each result.
5. Successful recap/worldbuilding and failure-injection evidence.
6. Base/head comparison for baseline failures.
7. Operator waivers; `none` if none.
8. Paths outside §4; `none` or stop report.
9. Stop conditions; `none` if none.
10. Confirmation that BLD-05/06/07/08 remain successors.
11. Confirmation that no direct graph write was introduced.

## §9 Acceptance rubric

- [ ] Recap and worldbuilding sources use explicit adapters — proved by adapter tests.
- [ ] Worldbuilding extraction succeeds with null session scope — proved by source-adapter/controller tests.
- [ ] Every reviewable candidate has source evidence — proved by extractor tests.
- [ ] Refusal, incomplete, schema, and validation failures are explicit — proved by controller failure tests.
- [ ] Structured extraction uses strict Responses API schema where applicable — proved by API-call assertions and diff inspection.
- [ ] No path outside §4 changed — proved by changed-path command.
- [ ] No extraction prompt/category tuning was smuggled into runtime plumbing.
- [ ] Named successors remain unimplemented and unclaimed.

## Stop conditions

Stop and report if:

- existing extraction schema cannot represent source-domain metadata;
- prompt/category changes are required for the runtime contract;
- an eval-only path must be imported into production;
- a candidate cannot retain a stable source span;
- provider/model policy cannot resolve the selected extraction client.

```text
Stop condition:
Why the current mission cannot absorb it:
New contract discovered:
Affected paths:
Proposed successor slice:
Authority update needed:
```
