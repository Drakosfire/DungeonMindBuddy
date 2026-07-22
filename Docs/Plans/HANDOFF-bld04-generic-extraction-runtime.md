# HANDOFF — BLD-04 generic extraction runtime and profile protocol

- **Created:** 2026-07-22
- **Status:** PREPARED / DRAFT — may be stacked against the BLD-03 head; ACTIVE / MERGEABLE only after BLD-03 merge, rebase, and immutable merge-SHA re-anchor.
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld04-generic-extraction-runtime.md`
- **Suggested branch:** `agent/bld04-generic-extraction-runtime`

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract changed? | Decision |
|---|---:|---:|---|
| Run recap and sessionless worldbuilding sources through one production controller | Yes | Yes | Include |
| Introduce explicit versioned extraction-profile selection | No — required to prevent the generic controller from retaining hidden recap policy | Yes | Include |
| Tune worldbuilding categories/prompts | Yes | Yes | Successor: BLD-08 |
| Add Build/Graph Review UI | Yes | Yes | Successors: BLD-06/07 |

**Selected capability:** one source-domain-neutral extraction execution boundary
whose behavior is selected by an explicit profile rather than embedded recap
assumptions.

## §1 Mission

The production extraction runtime can process recap and sessionless
worldbuilding SourceArtifacts through explicit source adapters and versioned
extraction profiles, producing source-anchored exact ExtractionRuns without
fabricating session identity or hiding prompt/schema policy inside the generic
controller.

**Invariant:** every reviewable candidate is tied to a validated SourceArtifact
and source span, and every LLM call is governed by an explicit profile ID/version
whose executable prompt/schema/vocabulary behavior is inspectable.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` and the Build roadmap |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-04 |
| Predecessor | BLD-03 canonical SourceArtifact, source spans, and ExtractionRun |
| Repository rules | `AGENTS.md`, `.cursor/rules/responses-api-structured-extraction.mdc`, model policy, `.cursor/rules/external-agent-pr-loop.mdc` |
| Base revision | Dispatch-time immutable merge SHA of BLD-03 |
| Exact input consumed | validated SourceArtifact, source text/spans, explicit profile ID/version, and model-policy-resolved structured-output client |
| Named successor | BLD-08 bounded worldbuilding profile and pilot |
| What remains false | no Build UI, generic Graph Review binding, graph publication, PDF/OCR, or worldbuilding quality claim |
| Explicit non-goals | category tuning, latest-run inference, eval runner as runtime, direct graph writes, prompt-only JSON parsing |

### Locked extraction-profile contract

The generic runtime must not own recap category policy implicitly. Introduce a
versioned profile protocol whose implementation owns or references:

```text
profile_id
profile_version
admitted source domains/document classes
enabled pass IDs and order
pass instructions or prompt templates
structured-output schema IDs/versions
vocabulary/context policy
source-domain semantic defaults
post-extraction validation policy
```

BLD-04 extracts the current runtime recap behavior into an explicit
`RecapExtractionProfile` without intentionally changing prompts, pass order,
schemas, or output semantics. A minimal worldbuilding plumbing profile may exist
only to prove null-session execution; category quality/tuning belongs to BLD-08.

Current prompt instructions embedded in
`category_candidate_graph_extractor.py` must be parameterized through the
profile seam. They may not remain hidden global policy while the controller is
called generic.

Read in order:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. BLD-03 canonical source/run contracts
3. `.cursor/rules/responses-api-structured-extraction.mdc`
4. model policy
5. `src/graph_memory/extraction/category_candidate_graph_extractor.py`
6. current recap runner/service and owning tests
7. existing eval runner only as a consumer/reference, never architecture owner

Stop if the current extractor cannot preserve recap semantics while accepting a
profile, if a profile requires new graph identity semantics, or if production
would need to import `evals/`.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Boundary |
|---|---|---|---:|---|
| Profile selection | recap behavior embedded/defaulted | exact known profile ID/version required before execution | Yes | Profile registry/controller |
| Recap extraction | campaign/session options required | recap adapter + recap profile preserve behavior | Yes | Adapter/profile/controller |
| Worldbuilding source | no generic production path | adapter executes with session null using explicit plumbing profile | Yes | Adapter/controller |
| Prompt/schema selection | embedded instructions and parser conventions | selected from profile and Responses API strict schema | Yes | Profile/client boundary |
| Source evidence | current source-span packet | every positive candidate resolves to exact SourceArtifact/span | Yes | Extractor/validator |
| Refusal | generic exception risk | failed run with explicit refusal diagnostic | Yes | Controller |
| Incomplete response | parser/default risk | failed run; never empty success | Yes | Controller |
| Schema failure | JSON parsing may accept close shapes | strict structured-output failure persisted | Yes | Client/controller |
| Candidate validation | downstream preview may fail | non-reviewable exact run with diagnostics | Yes | Validator/run registry |
| Retry/reload | path-oriented rerun | exact run policy from BLD-03; no latest substitution | Yes | Controller/registry |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `src/graph_memory/extraction/extraction_profile.py` | Typed profile protocol, ID/version, admission, prompt/schema/vocabulary contract |
| Create | `src/graph_memory/extraction/recap_extraction_profile.py` | Explicit profile preserving current recap execution semantics |
| Create | `src/graph_memory/extraction/source_adapter.py` | Generic source adapter protocol and normalized input |
| Create | `src/graph_memory/extraction/recap_source_adapter.py` | Existing recap descriptor/source mapping |
| Create | `src/graph_memory/extraction/worldbuilding_source_adapter.py` | Markdown source normalization with null session support |
| Modify | `src/graph_memory/extraction/category_candidate_graph_extractor.py` | Consume profile-selected passes/instructions/schemas and preserve evidence |
| Modify | `src/graph_memory/extraction/graph_extraction_options.py` | Exact source/profile/model policy options without mandatory session |
| Create | `src/graph_memory/extraction/graph_preview_runner.py` | Production source-domain-neutral controller and run lifecycle |
| Create | `apps/live_control_server/services/graph_preview_runner.py` | Live service wiring to canonical controller/registries |
| Modify | `apps/live_control_server/services/recap_graph_preview_ingest.py` | Preserve recap behavior through explicit adapter/profile |
| Create | `tests/test_extraction_profiles.py` | Profile admission/version/recap behavior and unknown-profile proof |
| Create | `tests/test_source_adapters.py` | Recap and null-session worldbuilding mapping |
| Create | `tests/test_graph_preview_runner.py` | Lifecycle and failure-injection proof |
| Create | `tests/test_category_candidate_graph_extractor.py` | Profile-selected prompt/schema and mandatory evidence proof |
| Modify | `tests/test_graph_memory_category_graph_preview_runner.py` | Existing recap regression through the production seam |

**Bounded discovery exception:** Not applicable — every expected path is listed.

## §5 Explicitly out of scope

| Path/capability | Why |
|---|---|
| `src/graph_memory/extraction/worldbuilding_extraction_profile.py` | BLD-08 owns category quality/tuning |
| `src/prompts/**` | No opportunistic second prompt authority; profile implementations own/reference executable templates through the declared seam |
| `evals/graph_memory_layer/graph_preview_runner.py` | Remains an eval consumer/reference |
| `apps/live-control-ui/src/buildSurface/**` | Build UI belongs to BLD-05/06 |
| Graph Review files | BLD-07 |
| `src/graph_memory/extract_promote_ops.py` | No publication changes |
| `corpus/**`, eval gold | No content or gold mutation |
| PDF/OCR | BLD-09 |

## §6 Implementation contract

```text
Input:
  canonical SourceArtifact + source spans + explicit profile ID/version +
  model-policy-resolved structured-output client.

Output:
  canonical ExtractionRun with candidate graph, evidence refs, validation,
  profile/model metadata, diagnostics, and reviewable/failed status.

Invariant:
  no execution without exact admitted profile; no reviewable candidate without
  evidence/schema/validation success; null session remains null.

Failure behavior:
  unknown/inadmissible profile → fail before model call
  source/digest/span mismatch → failed/non-reviewable run
  refusal/incomplete/schema error → named failed run, no empty graph fallback
  validator failure → non-reviewable run
  model/API failure → stable retryable failure with exact run identity

Replay / idempotency:
  same artifact digest + profile/version + model policy → BLD-03 run policy
  changed source/profile/model policy → distinct run input
  retry after partial output → resume or new exact run; never overwrite success
  reload returns exact profile/source/run metadata

Trust boundary:
  Verifies source admission, profile identity/version, prompt/schema selection,
  evidence refs, model policy, structured response state, validation, and run
  lifecycle. Semantic truth remains proposed until human review.
```

### §6A State and fallback matrix

| Path | Success | Miss | Unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|
| Profile load | exact version | unknown fails | stable dependency error | invalid profile fails | mismatch fails | reload exact profile |
| Source admission | normalized adapter input | 404/invalid source | stable error | digest/span fail closed | changed digest conflicts | re-admit exact source |
| LLM extraction | typed output | empty source invalid | retryable failure | refusal/incomplete/schema fail | profile/model mismatch | under run policy |
| Validation | reviewable run | zero candidates explicit | unavailable fails run | invalid graph non-reviewable | source mismatch fails | new/resumed run |

### §6B Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| SourceArtifact | exact BLD-03 ID/digest | mismatch fails | none |
| Source span | exact artifact/span ID | missing invalidates candidate | no text-only matching |
| Profile | exact ID + version | unknown/mixed fails | no recap default |
| Run | exact canonical run ID | no latest selection | none |
| Session | profile/domain matrix | worldbuilding null remains null | no synthetic session |

### §6C Persistence/replay matrix

| Operation | Durable representation | Round trip | Replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Profile selection | ID/version + executable config refs | exact profile reload | version change creates new input | recap profile preserves behavior | revert profile implementation |
| Extraction request | canonical run metadata | exact source/profile/model | BLD-03 policy | recap adapter remains | failed run retained |
| Candidate graph/evidence | typed artifact refs | every assertion resolves | no empty overwrite | existing candidate consumer compatible | run rejected, no graph write |
| Diagnostics | structured run records | refusal/incomplete/schema survives | retry remains inspectable | existing safe consumers | preserve failure evidence |

### §6D Predecessor mapping

| Predecessor | Consumer | Transformation | Proof |
|---|---|---|---|
| current category constants/instructions | `RecapExtractionProfile` | relocate/parameterize without semantic change | snapshot/behavior regression |
| current recap options | `RecapSourceAdapter` | exact source/profile mapping retaining session | adapter tests |
| worldbuilding SourceArtifact | `WorldbuildingSourceAdapter` | Markdown spans, null session | adapter tests |
| Responses API result | controller | strict schema/refusal/incomplete handling | failure tests |
| BLD-03 ExtractionRun | controller/registry | exact lifecycle updates | runner tests |

## §7 Verification ownership and commands

| Guarantee | Boundary | Command |
|---|---|---|
| Exact profile admission and recap semantic preservation | Profile | `uv run pytest tests/test_extraction_profiles.py` |
| Recap/worldbuilding adapter mapping | Adapter | `uv run pytest tests/test_source_adapters.py` |
| Mandatory evidence/profile-selected execution | Extractor | `uv run pytest tests/test_category_candidate_graph_extractor.py` |
| Failure persistence and exact run lifecycle | Controller | `uv run pytest tests/test_graph_preview_runner.py` |
| Existing recap path remains green | Runtime integration | `uv run pytest tests/test_graph_memory_category_graph_preview_runner.py` |

```bash
uv run pytest tests/test_extraction_profiles.py \
  tests/test_source_adapters.py \
  tests/test_category_candidate_graph_extractor.py \
  tests/test_graph_preview_runner.py \
  tests/test_graph_memory_category_graph_preview_runner.py
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing boundary: production graph preview controller
Scenario: run one recap fixture through the explicit recap profile, one
sessionless Markdown fixture through a plumbing profile, and inject unknown
profile, refusal, incomplete, schema, and validation failures.
Expected: successful runs retain exact evidence/profile metadata; every failure
is explicit and no session/latest run is fabricated.
```

## §8 Required handback

Record SHAs, paths/diff, all §7 results and provenance, recap behavior comparison,
failure-injection evidence, baseline failures, waivers, stop conditions, and
confirmation that BLD-08 still owns worldbuilding tuning.

## §9 Acceptance rubric

- [ ] Generic execution requires an exact admitted profile ID/version.
- [ ] Current recap behavior is represented by an explicit profile and remains regression-tested.
- [ ] Sessionless worldbuilding input executes without synthetic chronology.
- [ ] Every reviewable candidate resolves to canonical source evidence.
- [ ] Refusal, incomplete, schema, model, and validation failures persist explicitly.
- [ ] Production imports no eval-only runner.
- [ ] No worldbuilding category tuning or graph publication was added.
- [ ] Only §4 paths changed.

## Stop conditions

Stop if recap semantics cannot be preserved through a profile, executable prompt
or schema policy cannot be made explicit, the runtime requires eval imports,
source evidence cannot remain stable, model policy cannot resolve the client, or
worldbuilding quality changes are required for the plumbing proof.
