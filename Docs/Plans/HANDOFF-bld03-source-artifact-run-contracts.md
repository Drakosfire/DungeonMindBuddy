# HANDOFF — BLD-03 SourceArtifact and ExtractionRun contracts

- **Created:** 2026-07-22
- **Status:** DRAFT — dispatch only after BLD-02 is merged and re-anchored
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld03-source-artifact-run-contracts.md`
- **Suggested branch:** `agent/bld03-source-artifact-run-contracts`

## Shared vocabulary

| Term | Definition |
|---|---|
| SourceArtifact | Durable identity and authority descriptor for source material, independent of session occurrence. |
| ExtractionRun | Durable review bundle and lifecycle record produced from one source artifact and profile. |
| Source span | Stable evidence unit within the source artifact. |
| Recap adapter | Compatibility mapping from current campaign/session recap descriptors into generic contracts. |

## §1 Mission

A worldbuilding source with no session identity can be registered as a
SourceArtifact and produce a durable, reviewable ExtractionRun while existing
recap preview runs remain readable through an explicit adapter.

**Invariant:** Source identity, provenance, and run status are durable and
source-domain-aware; no generic contract fabricates a session to satisfy a
recap-only shape.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`, worldbuilding source-domain boundary |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-03 |
| Repository rules | `AGENTS.md`, `.cursor/rules/responses-api-structured-extraction.mdc`, `.cursor/rules/external-agent-pr-loop.mdc` |
| Base revision | Dispatch-time immutable merge SHA of BLD-02; current `8ff2339f` is reference only |
| Predecessor contract | Existing recap artifact descriptors, source spans, candidate graph manifests, and graph preview status routes |
| Exact input consumed | Source-document record/content digest, optional campaign/session scope, source domain/class, extraction profile, and source text |
| Named successor | BLD-04 source-adapter extraction runtime |
| What remains false | No worldbuilding extraction profile, Build UI, Graph Review UI, or graph publication |
| Explicit non-goals | Prompt changes, category tuning, PDF/OCR, UI replacement of recap ingest, graph-head mutation, parallel corpus index |

Read in order:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
3. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
4. Existing recap artifact and graph preview models/services
5. Existing source-span/provenance and candidate graph schemas
6. Existing recap preview tests and fixtures

If a durable field cannot be made source-domain-neutral without changing
promotion semantics, stop and report it as a successor contract.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| World source registration | No generic source artifact | Register worldbuilding source with nullable campaign/session | Yes | SourceArtifact contract |
| Recap source mapping | Recap descriptors are session-shaped | Map recap descriptor without losing identity/provenance | Yes | Recap adapter |
| Span generation | Span indexes are run-specific | Stable source artifact/span references | Yes | Source-span contract |
| Run creation | Preview status is path/recap-oriented | Durable run manifest keyed by run ID and source artifact ID | Yes | ExtractionRun registry |
| Run reload | Callers infer state from artifact paths | Query exact run status and bundle locations | Yes | Run registry route |
| Invalid source scope | Legacy functions may reject/null-assume | Validate domain/scope matrix explicitly | Yes | Contract validator |
| Replay | Existing manifests are read-only artifacts | Same source digest/profile yields deterministic run identity policy | Yes | Registry |

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `src/graph_memory/source_artifact.py` | Source identity, domain, authority, visibility, and scope contract |
| Create | `src/graph_memory/extraction_run.py` | Run lifecycle and review-bundle contract |
| Create | `src/graph_memory/source_spans.py` | Stable source span and evidence reference contract |
| Create | `src/graph_memory/provenance.py` | Provenance/index contract shared by source domains |
| Modify | `src/graph_memory/extraction/graph_extraction_options.py` | Optional scope and profile-facing contract seam |
| Create | `apps/live_control_server/services/source_artifact_registry.py` | Server-owned source artifact persistence/query |
| Create | `apps/live_control_server/services/graph_run_registry.py` | Server-owned run manifest/status/query |
| Modify | `apps/live_control_server/routes/graph_preview.py` | Generic run status/read endpoints while preserving recap routes |
| Modify | `apps/live_control_server/routes/workspace_documents.py` | Link source document records to source artifacts |
| Create | `tests/test_source_artifact.py` | Contract and scope validation |
| Create | `tests/test_extraction_run.py` | Lifecycle and review-bundle contract |
| Create | `tests/test_graph_run_registry.py` | Durable status/reload/replay proof |
| Modify | `tests/test_live_recap_ingest_graph_preview_api.py` | Existing recap preview compatibility proof |

**Bounded discovery exception:** Not applicable — paths are enumerated.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why out of scope |
|---|---|
| `src/graph_memory/extraction/category_candidate_graph_extractor.py` | Runtime adapter implementation belongs to BLD-04 |
| `src/graph_memory/extraction/worldbuilding_source_adapter.py` | BLD-04 owns extraction adapters |
| `apps/live-control-ui/src/buildSurface/**` | UI belongs to BLD-05/06 |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/**` | Review handoff belongs to BLD-07 |
| `src/graph_memory/extract_promote_ops.py` | No publication semantics change |
| `corpus/**`, `evals/**` | No content or gold mutation |
| LLM prompts or model IDs | Contract slice must not tune extraction |

## §6 Implementation contract and conditional matrices

```text
Input:
  Source document identity/content digest, source_domain, document_class,
  authority/visibility, optional world/campaign/session scope, source spans,
  extraction profile name, and source lineage.

Output:
  Validated SourceArtifact and ExtractionRun records with stable IDs, bundle
  component references, status, diagnostics, and source evidence links.

Invariant:
  Worldbuilding sources may have campaign_id/session_id = null; recap adapters
  preserve their existing session semantics without making them universal.

Failure behavior:
  Invalid domain/scope combination → validation failure before registry write.
  Missing source digest/lineage → artifact not admissible for extraction.
  Missing run component → run is incomplete/unreviewable, never “ready”.
  Unknown run ID → stable not-found response.

Replay / idempotency:
  same source digest + profile + contract version → deterministic identity
  policy or explicit duplicate run with lineage;
  changed digest/profile → distinct run;
  retry after partial bundle write → resume or mark incomplete, never ready;
  reload by run ID → same manifest and component references.

Trust boundary:
  Verifies: IDs, scope matrix, digest, component references, lifecycle
  transitions, root-contained path references.
  Records or trusts without proving: semantic correctness of extracted claims.
```

### State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Source artifact load | Wait for registry | Return exact artifact | 404 | Stable service error | Reject malformed record | Digest mismatch is conflict | Safe reload |
| Run load | Wait for registry | Return exact run manifest | 404 | Stable service error | Return incomplete/invalid status | Superseded run remains readable | Retry read |
| Run status | Return current status | `reviewable` only when bundle validates | Unknown run 404 | Unavailable error | `failed` with diagnostic | No latest-run substitution | Poll exact ID |
| Recap adapter | Map known recap descriptor | Preserve recap identity | Unknown recap invalid | Existing behavior | Adapter failure | No fabricated session | Retry only same descriptor |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| Source artifact ID | Stable from explicit source identity/content policy | Collision is a contract failure | No label fallback |
| Run ID | Durable ID separate from source ID | Duplicate run is explicit, not silent overwrite | No latest-run fallback |
| Source span ID | Stable within source artifact digest | Missing/duplicate span fails validation | No paragraph-text matching |
| Session scope | Nullable for worldbuilding | Missing required recap scope fails adapter validation | No synthetic session |

### Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| Source artifact | Typed record + digest + lineage | Reload preserves all required fields | Same source identity is explicit | Recap adapter remains readable | Mark superseded, do not rewrite history |
| Run manifest | Typed lifecycle + component references | Reload returns exact status/bundle | Partial retry cannot become duplicate ready run | Existing preview artifacts are adapter-readable | Mark failed/incomplete |
| Source span index | Stable IDs and offsets/anchors | Candidate references resolve | Changed source digest creates new span namespace | Existing recap spans map through adapter | Preserve old artifact |

### Predecessor-to-consumer mapping

| Predecessor | Consumer | Transformation | Proof |
|---|---|---|---|
| Recap campaign/session descriptor | `RecapSourceAdapter` boundary | Populate generic fields and retain original descriptor | Recap compatibility test |
| Existing source-span index | Generic span contract | Add source artifact ID and explicit evidence kind | Span contract test |
| Preview/run manifest | `ExtractionRun` | Normalize status/components without changing old files | Registry reload test |
| Workspace document record | Source artifact registry | Link document identity/content digest to artifact | Route/service test |

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command | Expected evidence |
|---|---|---|---|
| Worldbuilding artifact allows null session | Contract validator | `uv run pytest tests/test_source_artifact.py` | Valid world artifact and invalid combinations |
| Run lifecycle is fail-closed | Run registry | `uv run pytest tests/test_extraction_run.py tests/test_graph_run_registry.py` | Incomplete bundles never report reviewable |
| Exact run reload works | Status/read route | Same registry tests plus graph preview route tests | Same run ID returns same manifest |
| Recap compatibility holds | Recap adapter/API | `uv run pytest tests/test_live_recap_ingest_graph_preview_api.py` | Existing recap cases remain green |
| No scope creep | Git | `git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD` | Only §4 paths |

```bash
uv run pytest tests/test_source_artifact.py \
  tests/test_extraction_run.py \
  tests/test_graph_run_registry.py \
  tests/test_live_recap_ingest_graph_preview_api.py
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing surface used: graph-preview status/read service
Smallest scenario: register one evergreen source with null session, create a
run manifest, reload it by exact ID, and load one recap descriptor through the adapter
Expected observation: world source is valid; recap shape remains compatible
Evidence captured: focused contract/registry test output
```

## §8 Required handback

1. Base and head SHA.
2. Focused diff stat limited to §4.
3. Exact result of every §7 command.
4. Provenance for each result.
5. Worldbuilding-null-session and recap compatibility evidence.
6. Base/head comparison for baseline failures.
7. Operator waivers; `none` if none.
8. Paths outside §4; `none` or stop report.
9. Stop conditions; `none` if none.
10. Confirmation that BLD-04 owns extraction execution.
11. Confirmation that no graph-head or prompt contract changed.

## §9 Acceptance rubric

- [ ] A worldbuilding SourceArtifact with no session is valid — proved by contract tests.
- [ ] ExtractionRun status is durable and fail-closed — proved by registry tests.
- [ ] Source spans and provenance resolve through stable IDs — proved by span/registry tests.
- [ ] Existing recap descriptors remain readable through an adapter — proved by recap regression tests.
- [ ] No session is fabricated to satisfy a generic contract — proved by null-session cases.
- [ ] No path outside §4 changed — proved by changed-path command.
- [ ] BLD-04 remains unimplemented and unclaimed.

## Stop conditions

Stop and report if:

- extraction execution must change in this contract PR;
- a durable store migration cannot preserve old recap manifests;
- graph promotion requires a new source-artifact field not captured here;
- source path resolution cannot remain server-owned;
- a second source registry would duplicate an existing authority.

```text
Stop condition:
Why the current mission cannot absorb it:
New contract discovered:
Affected paths:
Proposed successor slice:
Authority update needed:
```
