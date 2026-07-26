# HANDOFF — BLD-03 canonical SourceArtifact and ExtractionRun contracts

- **Created:** 2026-07-22
- **Status:** PREPARED / DRAFT — may be stacked against the BLD-02 head; ACTIVE / MERGEABLE only after BLD-02 merge, rebase, and immutable merge-SHA re-anchor.
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld03-source-artifact-run-contracts.md`
- **Suggested branch:** `agent/bld03-source-artifact-run-contracts`

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract changed? | Decision |
|---|---:|---:|---|
| Graduate the existing source-artifact and source-span evidence contracts for sessionless worldbuilding | Yes | Yes | Include |
| Introduce exact durable ExtractionRun identity/lifecycle and adapt recap manifests | No — the source evidence contract is incomplete without a durable review bundle consumer | Yes | Include as one contract family |
| Execute LLM extraction | Yes | Yes | Successor: BLD-04 |
| Build or Graph Review UI | Yes | Yes | Successors: BLD-05/07 |

**Selected capability:** establish one canonical source-to-review-bundle contract
family by evolving the repository’s existing evidence/span/run authorities.

**Why included rows share one invariant:** every exact run must bind one immutable
source revision and resolvable source spans; splitting those contracts would
create an unusable intermediate or invite duplicate identities.

## §1 Mission

A committed worldbuilding workspace revision with no session identity can become
a canonical immutable SourceArtifact with stable source spans and participate in
a durable exact ExtractionRun, while existing recap manifests remain readable
through an explicit adapter rather than a parallel authority.

**Invariant:** source identity, evidence references, and exact run status are
owned by one canonical contract family; no generic path fabricates a session or
creates shadow source/span/run vocabularies.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-03 |
| Workspace predecessor | BLD-02 committed `worldbuilding_source` record/revision |
| Existing authorities | `src/graph_memory/evidence/source_artifact.py`, `src/graph_memory/source_span.py`, `src/graph_memory/ingestion/graph_ingest_run.py` |
| Repository rules | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc` |
| Base revision | Dispatch-time immutable merge SHA of BLD-02 |
| Exact input consumed | committed workspace document UUID/revision, content digest, source metadata, source text, optional campaign/session scope, and existing recap manifest shape |
| Named successor | BLD-04 source-adapter extraction runtime and profile protocol |
| What remains false | no extraction execution, Build UI, Graph Review generic binding, or graph publication |
| Explicit non-goals | new top-level duplicate contracts, prompt changes, PDF/OCR, identity resolution, graph-head mutation |

### Existing-contract graduation decision

BLD-03 evolves these existing authorities:

```text
src/graph_memory/evidence/source_artifact.py
src/graph_memory/source_span.py
src/graph_memory/ingestion/graph_ingest_run.py
```

It must **not** create:

```text
src/graph_memory/source_artifact.py
src/graph_memory/source_spans.py
src/graph_memory/provenance.py
```

A new canonical
`src/graph_memory/ingestion/extraction_run.py` is allowed because the current
manifest is recap/preview shaped. When created, the same PR must make
`graph_ingest_run.py` an explicit legacy/recap adapter or loader. Both files may
not claim canonical run ownership.

The SourceArtifact produced here is distinct from the BLD-02 workspace document:

```text
source_artifact_id
workspace_document_id
workspace_document_revision
content_sha256
source_domain
artifact_kind / document_class
authority_state
visibility_state
world_id
campaign_id? / session_id?
source_uri or server-resolved locator
lineage
```

Read in order:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`
3. `Docs/Design/CONTRACT-workspace-document-identity-v1.md`
4. BLD-02 merged contract and implementation
5. `src/graph_memory/evidence/source_artifact.py`
6. `src/graph_memory/source_span.py`
7. `src/graph_memory/ingestion/graph_ingest_run.py`
8. current graph-ingest run registry, preview routes, and tests

Stop if promotion or evidence consumers require a competing source vocabulary,
if old recap manifests cannot be mapped field-by-field, or if the source/run
contract cannot remain server-path-resolved.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Workspace revision → SourceArtifact | No canonical explicit transition | Create immutable artifact with explicit workspace foreign keys/digest | Yes | SourceArtifact service/contract |
| Existing graph evidence artifact load | Minimal/recap assumptions | Existing artifact authority accepts worldbuilding/null session without losing old fields | Yes | Evidence contract |
| Source-span creation | Current resolver contract exists | Stable span IDs namespaced by source artifact revision/digest | Yes | Source-span contract |
| Candidate evidence lookup | Existing refs resolve through source span | Same resolver works for recap/worldbuilding | Yes | Evidence resolver |
| Exact run creation | Current graph-ingest manifest is recap/preview shaped | Canonical ExtractionRun keyed by durable run ID and source artifact ID | Yes | Run contract/registry |
| Run reload/status | Callers may infer from paths/latest | Exact ID reload; no latest substitution | Yes | Registry + route |
| Partial bundle | Current artifacts may be incomplete | incomplete/failed, never reviewable | Yes | Run validator |
| Recap manifest compatibility | Existing manifest requires campaign/session | Explicit adapter preserves recap scope and vocabulary | Yes | Legacy adapter |
| Superseded source/run | Existing semantics vary | Old records remain readable and explicitly superseded | Yes | Registry |
| Replay | Path-based rerun conventions | explicit deterministic/reused/new-run policy | Yes | Registry |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/graph_memory/evidence/source_artifact.py` | Graduate canonical source evidence identity, scope, digest, lineage, and workspace foreign keys |
| Modify | `src/graph_memory/evidence/__init__.py` | Export the canonical evolved contract |
| Modify | `src/graph_memory/source_span.py` | Graduate stable source-span/evidence references without a parallel module |
| Create | `src/graph_memory/ingestion/extraction_run.py` | Canonical source-domain-neutral exact run and review-bundle contract |
| Modify | `src/graph_memory/ingestion/graph_ingest_run.py` | Explicit recap/legacy manifest adapter into canonical ExtractionRun |
| Modify | `src/graph_memory/ingestion/__init__.py` | Export canonical run and compatibility adapter intentionally |
| Create | `apps/live_control_server/services/source_artifact_registry.py` | Server-owned artifact creation/load/query from committed source revisions |
| Create | `apps/live_control_server/services/graph_run_registry.py` | Canonical exact run persistence/status/query |
| Modify | `apps/live_control_server/routes/graph_preview.py` | Exact generic run read/status endpoints while preserving recap entry adapters |
| Modify | `apps/live_control_server/routes/workspace_documents.py` | Explicit committed workspace revision → SourceArtifact transition endpoint or service binding |
| Create | `tests/test_source_artifact.py` | Source identity, scope, lineage, and workspace namespace tests |
| Create | `tests/test_source_span_contract.py` | Span stability and evidence resolution tests |
| Create | `tests/test_extraction_run.py` | Lifecycle/reviewability/diagnostic/supersession tests |
| Create | `tests/test_graph_run_registry.py` | Exact reload, replay, partial-write, and path-containment tests |
| Modify | `tests/test_live_recap_ingest_graph_preview_api.py` | Real recap-manifest adapter compatibility proof |

**Bounded discovery exception:**

```text
Directory: tests/fixtures/graph_memory
Maximum additional paths: 2
Allowed path kinds: minimal canonical SourceArtifact or legacy recap-manifest JSON fixtures
Decision rule: only when a real predecessor shape cannot be proved with existing fixtures
Required report: path, source provenance, and why the fixture is necessary
```

## §5 Explicitly out of scope

| Path or capability | Why |
|---|---|
| `src/graph_memory/source_artifact.py` | Would duplicate `evidence/source_artifact.py` |
| `src/graph_memory/source_spans.py` | Would duplicate `source_span.py` |
| `src/graph_memory/provenance.py` | Provenance remains in the established evidence/span/contribution contracts unless a separate architecture slice proves otherwise |
| `src/graph_memory/extraction/category_candidate_graph_extractor.py` | Extraction execution belongs to BLD-04 |
| `apps/live-control-ui/src/buildSurface/**` | Build UI belongs to BLD-05/06 |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/**` | Review binding belongs to BLD-07 |
| `src/graph_memory/extract_promote_ops.py` | Publication semantics unchanged |
| `corpus/**`, `evals/**` | No content, run payload, or gold mutation |
| prompt/model changes | Contract slice only |

## §6 Implementation contract

```text
Input:
  committed workspace document UUID/revision, content digest, source metadata,
  server-resolved source locator, optional world/campaign/session scope,
  source text/spans, and a real existing recap run manifest when adapting.

Output:
  canonical SourceArtifact, source-span references, and canonical ExtractionRun
  records with exact IDs, lifecycle, bundle component refs, diagnostics,
  supersession, and reload behavior.

Invariant:
  one canonical source/span/run contract family owns both recap and
  worldbuilding; null session remains null; all persisted refs are server-owned.

Failure behavior:
  invalid workspace revision/digest → no SourceArtifact
  invalid domain/scope matrix → contract failure before registry write
  missing/mismatched span → candidate/run cannot become reviewable
  partial/missing run component → incomplete or failed, never ready
  unknown exact ID → 404
  malformed legacy manifest → adapter failure, no fabricated defaults

Replay / idempotency:
  same workspace revision + digest → same SourceArtifact identity policy
  changed workspace revision/digest → new artifact linked by lineage
  same artifact + profile/version/model policy → explicit reuse/new-run policy
  partial write retry → resume safely or mark failed; never duplicate ready run
  superseded artifacts/runs remain readable

Trust boundary:
  Verifies: namespace, digest, scope matrix, lineage, path containment,
  component refs, lifecycle transitions, and evidence resolvability.
  Does not prove: semantic correctness of extracted claims.
```

### §6A State and fallback matrix

| Path | Success | Miss | Unavailable | Integrity failure | Stale/superseded | Retry |
|---|---|---|---|---|---|---|
| Source artifact load | exact artifact | 404 | stable error | reject malformed/digest mismatch | return explicit status/lineage | safe exact reload |
| Span resolution | exact evidence | unresolved ref | stable source unavailable | blocker diagnostic | old revision still resolvable | exact ref only |
| Run load/status | exact manifest/status | 404 | stable error | incomplete/failed | visible; no latest fallback | poll exact ID |
| Recap adapter | canonical mapped run | invalid predecessor | existing dependency error | fail closed | preserve source scope | same descriptor only |

### §6B Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| Workspace document | BLD-02 UUID/revision foreign key | mismatch rejects artifact creation | none |
| SourceArtifact | canonical server ID bound to immutable digest/revision | collision is contract failure | no workspace-ID reuse |
| Source span | stable within artifact revision namespace | duplicate/missing fails validation | no text matching |
| ExtractionRun | durable ID separate from artifact | duplicate policy explicit | no latest run |
| Session scope | nullable for worldbuilding, required by recap adapter | invalid matrix fails | no synthetic session |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round trip | Replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| SourceArtifact | evolved evidence contract | exact identity/lineage/scope | same revision policy explicit | old artifacts load | supersede, never rewrite history |
| Source spans | evolved source-span contract | refs resolve to artifact revision | changed source creates new namespace | old recap refs adapt | preserve old spans |
| ExtractionRun | canonical run manifest | exact ID/status/components | resume/reuse/new-run explicit | graph-ingest manifest adapter | failed/superseded retained |

### §6D Predecessor mapping

**Grounding sources:** real current `GraphMemorySourceArtifact`, `SourceSpanRef`,
and `GraphIngestRunManifest` types plus captured existing recap manifest fixtures.

| Predecessor | Real shape concern | Canonical mapping | Proof |
|---|---|---|---|
| `GraphMemorySourceArtifact` | required campaign and permissive extras | evolve scope/lineage explicitly without shadow type | source tests |
| `SourceSpanRef` | established evidence resolver fields | preserve resolver vocabulary and add artifact revision stability only where required | span tests |
| `GraphIngestRunManifest` | required campaign/session and preview statuses | adapter maps exact fields/status/components to ExtractionRun | real fixture/API regression |
| Workspace record | mutable UUID/revision | explicit foreign key in SourceArtifact | route/service tests |

## §7 Verification ownership and commands

| Guarantee | Boundary | Command |
|---|---|---|
| Sessionless SourceArtifact and namespace separation | Evidence contract/registry | `uv run pytest tests/test_source_artifact.py` |
| Stable span evidence resolution | Source-span resolver | `uv run pytest tests/test_source_span_contract.py` |
| Fail-closed exact run lifecycle/reload | Run contract/registry | `uv run pytest tests/test_extraction_run.py tests/test_graph_run_registry.py` |
| Real recap manifest compatibility | Adapter/API | `uv run pytest tests/test_live_recap_ingest_graph_preview_api.py` |
| No parallel authorities | Diff/path inspection | changed-path checks |

```bash
uv run pytest tests/test_source_artifact.py \
  tests/test_source_span_contract.py \
  tests/test_extraction_run.py \
  tests/test_graph_run_registry.py \
  tests/test_live_recap_ingest_graph_preview_api.py
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing boundary: workspace/source registry and exact run status API
Scenario: convert one committed sessionless workspace revision into a
SourceArtifact, create/reload an incomplete then reviewable run, resolve one
span, and adapt one real recap manifest.
Expected: all exact identities and evidence survive reload; no session or latest
run is fabricated.
```

## §8 Required handback

Record base/head SHAs, changed paths, focused diff, all §7 results and
provenance, real predecessor fixture provenance, live proof, baseline failures,
waivers, stop conditions, and confirmation that BLD-04 still owns execution.

## §9 Acceptance rubric

- [ ] Existing source-artifact and source-span authorities are evolved, not shadowed.
- [ ] Workspace and SourceArtifact identities remain distinct and explicitly linked.
- [ ] A sessionless worldbuilding artifact is valid without fabricated scope.
- [ ] Exact ExtractionRun state is durable, fail-closed, and reloadable.
- [ ] Existing recap manifests map through a real adapter fixture.
- [ ] No latest-run or path-derived identity fallback exists.
- [ ] No extraction, UI, or graph publication behavior was added.
- [ ] Only §4 and approved bounded-discovery paths changed.

## Stop conditions

Stop and report if implementation requires a second source/span/provenance
vocabulary, cannot map real recap manifests, requires extraction execution,
changes Kernel publication semantics, cannot keep paths server-owned, or would
leave two canonical run contracts.
