---
pr_body_template: |
  ## Outcome

  Surfaces and agent runtimes can perform deterministic, revision-pinned World Graph retrieval and open only graph-admitted evidence anchors so that PR010B can give Hermes factual read tools without any parallel Markdown fallback.

  ## Scope and verification

  - Implementation base: `23959e4cfdb4f3cad181f0cdcae695d21c8fc1af`
  - Canonical handoff: `Docs/Plans/HANDOFF-pr344-world-graph-retrieval-source-anchor-admission.md`
  - Actual changed paths: report from `git diff --name-only`
  - Verification: report every §7 command with exact result and provenance
  - Waivers: report `none` or name each explicit operator waiver
  - Deferred successors: PR010B Hermes graph-retrieval dogfood; PR011 governed tool runtime
---

# HANDOFF — PR010A World Graph retrieval + source-anchor admission

**Created:** 2026-07-13
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr344-world-graph-retrieval-source-anchor-admission.md`
**Implementation base:** `23959e4cfdb4f3cad181f0cdcae695d21c8fc1af` — merge commit for GitHub PR #343.
**Suggested branch:** `agent/pr010a-world-graph-retrieval-contract`

> **Dispatch gate:** The worker must read this complete handoff. Do not replace it with the PR-body summary. If `main` has moved beyond the implementation base, rebase or branch from current `main`, record the new immutable base, and verify that the roadmap, tracker, projection contracts, and file seams below have not materially changed. A material conflict is a stop condition.

---

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision |
|---|---:|---:|---:|---:|---:|---|
| Deterministic, revision-pinned graph search, exact lookup, bounded traversal, evidence admission, and anchor-bound source reading | Yes | Yes | API only; no new UI | Yes | Yes | **Include — selected capability** |
| Hermes agent/session loop using these reads | Yes | Yes | Existing Agent Interaction behavior changes | Yes | Yes | **Successor — PR010B** |
| Delete manifest/corpus/lexical Hermes tools and Live fallback | Yes | No new contract, but independently revertible demolition | Existing product path changes | Yes | Yes | **Successor — PR010B after replacement is usable** |
| Agent Interaction UI redesign or app-level provider lift | Yes | Yes | Yes | Yes | Yes | **Successor — PR011** |
| Embeddings, vector search, generalized GraphRAG ranking, ontology generation | Yes | Yes | No | Yes | Yes | **Reject from this slice** |
| Graph writes, drafts, preview-write, confirmation, correction escalation | Yes | Yes | Yes | Yes | Yes | **Successor — PR011** |

**Selected capability:** One graph-only retrieval and evidence-admission contract, exposed through the Graph Kernel and live-control API.

**Why the included behavior is one capability:** Search, exact lookup, traversal, evidence admission, and source-anchor reading are the required stages of one invariant: every factual result and every source byte returned to a consumer must be authorized by the same immutable World Graph revision and request context. The anchor reader is not an independent document browser; it can only consume an anchor emitted by this retrieval contract.

**Named successors:**

- **PR010B:** real Hermes agent/session loop, tool registration, same-thread pronoun continuity, graph-only dogfood, and replacement-path demolition.
- **PR011:** app-level Agent Context, cross-surface continuity, complete typed tool registry, draft/preview/confirm capabilities.
- **PR009:** Play projection migration remains a parallel product lane.

---

## §1 Mission

```text
Surfaces and agent runtimes can perform deterministic, revision-pinned World Graph retrieval and open only graph-admitted evidence anchors so that PR010B can give Hermes factual read tools without any parallel Markdown fallback.
```

**Invariant**

```text
Every returned graph fact, relationship, attribute, evidence anchor, and source excerpt is admitted and revalidated against one explicit World Graph revision plus world/campaign/focus/admissibility context; an ordinary miss, unavailable graph, stale source, or invalid anchor never triggers another discovery plane.
```

**Mission falsification test**

```text
This is not one slice if implementation must also run an LLM, create or resume Hermes sessions, alter Agent Interaction UI/thread persistence, delete the legacy Hermes path, add graph writes, or implement a second retrieval backend.
```

---

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` Phase 7 / PR010A; `Docs/Plans/PR-TRACKER-campaign-supergraph.md` PR010A; `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Design/ANCHOR-agent-interaction-hermes.md` Gate 1 |
| Repository rules | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md`; `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`; `Docs/Design/CONTRACT-graph-kernel-boundary.md` |
| Base revision | `23959e4cfdb4f3cad181f0cdcae695d21c8fc1af` |
| Predecessor contract | PR007A projection models and Kernel APIs: `WorldGraphProjectionRequest`, `WorldGraphProjection`, `WorldGraphQueryContext`, `project_world_graph`, `search_world_graph_projection`; route `POST /api/live/world-graph/projection` |
| Exact input consumed | Immutable World Graph head or explicit `revisionPin`; `worldId`; `campaignId`; focus; admissibility; operation-specific query or exact IDs; explicit bounds |
| Named successor | PR010B Hermes graph-retrieval dogfood |
| What remains false | Hermes is still not the answering agent; no tool loop/session mapping; legacy manifest/corpus tools remain; Agent Interaction still has transitional Live/Hermes behavior |
| Explicit non-goals | LLM calls; Hermes integration; UI work; browser persistence; graph writes; ingestion changes; Play migration; embeddings; generalized GraphRAG; source discovery outside graph admission; compatibility fallback |

Read these authoritative inputs in order before changing code:

1. `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` — graph-only retrieval boundary and PR010A/PR010B split.
2. `Docs/Plans/PR-TRACKER-campaign-supergraph.md` — PR010A public contract, success criteria, and non-goals.
3. `Docs/Design/ARCHITECTURE-campaign-supergraph.md` — authority, revision, admissibility, provenance, and Kernel boundaries.
4. `Docs/Design/ANCHOR-agent-interaction-hermes.md` — target tool vocabulary and Gate 1 behavior.
5. `Docs/Design/CONTRACT-graph-kernel-boundary.md` — application code imports operations through `graph_memory.kernel` only.
6. `src/graph_memory/projection/world_projection.py` — real projection vocabulary and models.
7. `src/graph_memory/kernel/world_projection.py` — revision loading, integrity verification, projection construction, and existing deterministic search.
8. `apps/live_control_server/services/world_graph_projection.py` and `apps/live_control_server/routes/world_graph_projection.py` — service/route error conventions.
9. `tests/test_graph_kernel_world_projection.py`, `tests/test_world_graph_projection_routes.py`, `tests/test_graph_kernel_public_api.py`, and `tests/test_graph_kernel_boundaries.py` — owning predecessor proofs.
10. Approved real-data acceptance inputs under `graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1/`, especially `006-tripod-null-calf-threat-prep.json` and `001-mirathorn-world-hub.json`.

### Authority precedence

```text
1. Current repository architecture, roadmap, and tracker on main
2. This checked-in handoff
3. Graph Kernel boundary contract and PR007A public schemas/tests
4. Current implementation and approved contribution bundle
5. Historical handoffs, reports, experiments, Project Sources, and chat summaries
```

If the predecessor shape differs materially from the mapping in §6D, stop. Do not invent a near-equivalent contract or silently revise the handoff.

---

## §3 Observable-path inventory

| Observable path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---:|---|
| Natural-language graph search | PR007A performs deterministic node/attribute matching inside a projection query context; relationship text is not a first-class search input and outcome semantics are implicit | Return deterministic ranked graph matches, relationship/attribute context, revision snapshot, explicit outcome, bounds, and admitted anchors | Yes | Kernel retrieval + service/route |
| Search with exact seed node IDs | No dedicated retrieval contract | Exact seeds are included or reported missing; no label/alias rebinding | Yes | Kernel retrieval |
| Exact object lookup | Consumers inspect projection arrays | Resolve exact durable node ID; active durable redirect may resolve to survivor with explicit diagnostic; never interpret label/alias as ID | Yes | Kernel retrieval |
| Bounded neighborhood traversal | Projection exposes adjacency, but no operation-level depth/bounds/outcome contract | Traverse deterministically from exact seeds with depth 1–2, endpoint-relative direction, cycle safety, admissibility, and caps | Yes | Kernel retrieval |
| Evidence lookup for node/relationship/attribute | Projection contains evidence/source artifact arrays, but no target-scoped anchor contract | Return active support and opaque anchors associated with an exact graph target | Yes | Kernel retrieval |
| Graph-admitted source read | Existing citation/document paths accept corpus/path-shaped identifiers | Accept only an opaque anchor emitted by this contract; revalidate it against the pinned revision/context before reading bounded content | Yes | Kernel retrieval/source reader + service/route |
| Ordinary search or exact-ID miss | Empty arrays/implicit diagnostics | Return HTTP 200 with outcome `empty` and coverage diagnostics; no secondary lookup | Yes | Kernel retrieval + route |
| Partial evidence | Projection may contain an object without readable source text | Return `partial`, target data, and explicit missing/unreadable-anchor diagnostics; no fallback | Yes | Kernel retrieval |
| Result exceeds cap | Existing projection query context has hard internal caps | Return bounded data with outcome `truncated`, exact truncation diagnostics, and stable ordering | Yes | Kernel retrieval |
| Graph/head/revision unavailable | Projection returns stable service errors | Retrieval returns outcome `unavailable` for a valid request whose graph/revision cannot be opened; it does not consult another source | Yes | Service/route |
| Graph integrity or contract failure | Projection fails closed | Return stable `dmb_world_graph_retrieval_error_v1`, HTTP 409 for integrity failure or 422 for invalid contract; no partial content | Yes | Kernel/service/route |
| Source artifact changed since admitted revision | No revision-bound graph source reader | Fail closed with `source_integrity_error`; return no excerpt | Yes | Source reader/service/route |
| Unsupported source URI or locator | No graph retrieval reader contract | Anchor remains inspectable as unreadable; evidence result is `partial`; read request returns `partial` with no content and a named diagnostic | Yes | Kernel/source reader |
| Anchor from another revision/context | No opaque anchor contract | Exact anchor mismatch returns `denied` or `empty` according to §6A; never rebind by evidence ID/path | Yes | Kernel/source reader |
| Same pinned request replay | Current projection is deterministic for an immutable revision | Same request and revision produce semantically identical ordered result and anchor IDs | Yes | Kernel tests |
| Unpinned request after head advances | Resolves current head at call time | New request may see new head; result truthfully names resolved revision; previously emitted anchor remains tied to its old revision | Yes | Kernel/service |

No row may introduce manifest lookup, corpus-index lookup, arbitrary repository search, vector fallback, or path-based source input.

---

## §4 Files in scope — allowlist

Every changed path must appear below.

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Create | `src/graph_memory/retrieval/__init__.py` | Export retrieval contract models only; no storage access |
| Create | `src/graph_memory/retrieval/models.py` | Strict request/result/anchor/error schemas and explicit bounds/outcomes |
| Create | `src/graph_memory/retrieval/source_reader.py` | Safe, bounded, graph-authorized resolution for supported URI/locator families; no arbitrary-path interface |
| Create | `src/graph_memory/kernel/world_retrieval.py` | Kernel-owned revision loading, search, exact lookup, traversal, evidence admission, anchor derivation/revalidation, and source read operations |
| Modify | `src/graph_memory/kernel/__init__.py` | Export the PR010A operations through the legal application boundary |
| Modify | `src/graph_memory/kernel/contracts.py` | Record the implemented PR010A public operation names; no placeholder behavior |
| Create | `apps/live_control_server/services/world_graph_retrieval.py` | Map Kernel outcomes/errors to stable service contracts using configured graph/repository roots |
| Create | `apps/live_control_server/routes/world_graph_retrieval.py` | Expose strict no-query-param POST operations under `/api/live/world-graph/retrieval` |
| Modify | `apps/live_control_server/main.py` | Register only the new retrieval router |
| Create | `tests/test_graph_kernel_world_retrieval.py` | Owning Kernel proofs for deterministic search/traversal/evidence/anchors/outcomes/no fallback |
| Create | `tests/test_world_graph_retrieval_routes.py` | Exact route, schema, HTTP, malformed-request, unavailable, integrity, and anchor-read proofs |
| Modify | `tests/test_graph_kernel_public_api.py` | Prove PR010A operations are exported and reserved placeholders are absent |
| Modify | `tests/test_graph_kernel_boundaries.py` | Prove live-control uses `graph_memory.kernel`, not world-storage or legacy retrieval internals |
| Create | `tests/fixtures/world_graph_retrieval/api-contract-v1.json` | Canonical serialized examples generated from real temporary-root operations, including success, empty, truncated/partial, unavailable, integrity error, and source read |

**Bounded discovery exception:**

```text
Directory: tests/
Maximum additional paths: 1
Allowed path kinds: an existing test module that is already the owning boundary for FastAPI registration or import restrictions
Decision rule for including a path: the declared guarantee cannot be proved from the allowlisted test modules without duplicating an existing repository-wide guard
Required report when a path is added: name the path, owning guarantee, and why the existing allowlisted tests cannot own the proof
```

No production path may be added under this exception. If another production path is required, stop and report.

---

## §5 Files and capabilities explicitly out of scope

| Path, ownership layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `integrations/hermes/plugins/dungeonbuddy/**` | Tool registration and legacy-tool demolition belong to PR010B |
| `apps/live_control_server/services/live_agent_loop.py` | Hermes/Live orchestration is PR010B |
| `apps/live_control_server/routes/live.py` | Existing Agent Interaction query route is not migrated in PR010A |
| `apps/live-control-ui/**` | No UI, API client, thread, trace, or panel changes in this contract slice |
| `src/live_play/manifest_context_query.py` and `src/live_play/live_query_context.py` | Transitional retrieval remains untouched until PR010B replacement is usable |
| Manifest files, corpus indexes, lexical/vector search modules | They are forbidden dependencies, not compatibility inputs |
| World Graph storage, contribution merge, identity, publication, or ingestion code | PR010A is read-only and must consume existing Kernel/projection contracts |
| `graph_data/approved_contribution_bundles/**` | Acceptance input is immutable for this slice; do not alter content to make tests pass |
| Roadmap, tracker, Hermes anchor, `.hermes.md` | Already reanchored by PR #343; implementation does not redesign authority |
| PR009 Play surface work | Parallel capability with a different user outcome |
| PR011 writes/drafts/preview/confirm or app-level provider | Separate capability and security boundary |
| New CLI, management page, debug dashboard, search UI, report UI, or dogfood notes system | Verification must use tests and existing data, not create another product surface |
| Embeddings, external vector database, LLM ranking, query rewriting, ontology inference | Full GraphRAG sophistication is not needed for Gate 1 |

Nearby code is not authorization. Do not delete legacy retrieval in PR010A; the roadmap deliberately assigns that demolition to PR010B after the replacement is exercised by Hermes.

---

## §6 Implementation contract and conditional matrices

### §6 core contract

```text
Input:
  Strict operation-specific request containing:
  - worldId
  - campaignId
  - focus
  - admissibility
  - optional revisionPin
  - exact query/target/seed fields
  - explicit bounded limits

Authoritative data:
  - one immutable World Graph revision selected through existing Kernel projection loading
  - active graph nodes, relationships, attributes, assertion support, evidence refs, and source artifacts from that revision
  - no manifest, corpus index, repo search, arbitrary path, or model memory

Output:
  - stable retrieval result with resolved revision snapshot
  - explicit outcome: enough | partial | empty | denied | truncated | unavailable
  - deterministic graph objects/relationships/attributes
  - opaque graph-admitted source anchors
  - machine-readable coverage, admissibility, truncation, and integrity diagnostics
  - bounded source content only after exact anchor revalidation

Invariant:
  Every returned graph fact, anchor, and source byte is authorized by the same graph revision and request context; no miss or error invokes another discovery plane.

Failure behavior:
  invalid request -> HTTP 422 dmb_world_graph_retrieval_error_v1
  integrity/contract failure -> HTTP 409 dmb_world_graph_retrieval_error_v1
  unexpected internal failure -> HTTP 500 dmb_world_graph_retrieval_error_v1 without raw exception/path leakage
  ordinary miss -> HTTP 200 outcome=empty
  graph/revision absent -> HTTP 200 outcome=unavailable
  unsupported locator/URI -> HTTP 200 outcome=partial with no source body
  stale source bytes/hash mismatch -> HTTP 409 source_integrity_error with no source body

Replay / idempotency:
  same input + same revision -> semantically identical ordered result and anchor IDs
  same input without revision pin after head advance -> may return new revision; snapshot names it truthfully
  retry after unavailable -> safe; no writes occurred
  duplicate delivery -> no state change

Trust boundary:
  Verifies:
  - request schema and bounds
  - world/revision integrity through existing Kernel projection path
  - campaign/focus/admissibility context
  - exact IDs and active redirects
  - graph association between assertions, evidence, and source artifacts
  - anchor membership in the exact request context and revision
  - safe URI resolution and locator evaluation
  - source digest where a revision/content digest is available

  Records or trusts without proving:
  - semantic truth of the source prose beyond graph acceptance state
  - quality/completeness of graph extraction
  - whether an omitted source contains a fact absent from the graph

  Rejects:
  - arbitrary paths or URIs supplied by callers
  - unknown/mismatched anchors
  - unsupported admissibility policy
  - storage/manifest/run selectors
  - fallback discovery
  - stale or integrity-failing source content
```

This is read-only. There is no commit point and no persistence mutation.

### §6.1 Public operation and schema contract

Expose these POST operations under router prefix `/api/live/world-graph/retrieval`; reject all query parameters:

| Operation | Route | Request schema |
|---|---|---|
| Search | `/search` | `dmb_world_graph_search_request_v1` |
| Exact object | `/object` | `dmb_world_graph_object_request_v1` |
| Neighborhood | `/neighborhood` | `dmb_world_graph_neighborhood_request_v1` |
| Evidence | `/evidence` | `dmb_world_graph_evidence_request_v1` |
| Source anchor read | `/source-anchor/read` | `dmb_world_graph_source_anchor_read_request_v1` |

The first four return `dmb_world_graph_retrieval_result_v1`. Source reading returns `dmb_world_graph_source_anchor_read_v1`. All route/service failures use `dmb_world_graph_retrieval_error_v1`.

All models are strict, camelCase on the wire, `extra="forbid"`, and reject query parameters. Do not reuse the projection response schema and silently add fields to it; retrieval is a new caller-facing contract.

#### Common request context

```text
worldId: non-empty string
campaignId: non-empty string
focus: existing WorldGraphProjectionFocus shape
admissibility: existing policy vocabulary; PR010A may support only the policies the projection layer supports
revisionPin: optional exact rev:* identifier
```

#### Search request

```text
queryText: non-empty string
seedNodeIds: optional exact durable node IDs, default []
bounds:
  maxNodes: default 8, hard maximum 12
  maxRelationships: default 16, hard maximum 24
  maxAttributes: default 24, hard maximum 32
  maxSourceAnchors: default 24, hard maximum 32
```

Search must include label, alias, kind, role, summary, attribute text, relationship predicate/label, and related-node display text. Reuse or extend deterministic PR007A lexical ranking; do not add embeddings or an LLM. Tie-break by durable IDs. `seedNodeIds` are exact only and are reported missing rather than rebound.

#### Exact object request

```text
nodeId: exact durable graph node ID
bounds: same result caps as search
```

An active durable identity redirect may resolve the requested ID to its survivor. The result must include requested and resolved IDs plus a diagnostic. No label, alias, normalized-key, or first-match fallback is permitted.

#### Neighborhood request

```text
seedNodeIds: 1..8 exact durable IDs
maxDepth: 1 or 2; default 1
bounds: same hard maxima as search
```

Traversal is deterministic, cycle-safe, bounded, and endpoint-relative. A missing seed is reported. A seed must never be inferred from its label. Relationships and related nodes remain from the same snapshot.

#### Evidence request

```text
target:
  kind: node | relationship | attribute
  id: exact node_id | edge_id | assertion_id
bounds.maxSourceAnchors: default 24, hard maximum 32
```

Return only active support admitted into the projection/revision. Each source anchor must identify the graph target/assertion it supports without exposing an arbitrary filesystem path as caller input.

#### Retrieval result

At minimum:

```text
schema
operation
outcome
snapshot:
  worldId
  campaignId
  revisionId
  headRevisionId
  isHead
  focus
  admissibility
requestSummary
matchedNodeIds
matchReasons
nodes
relationships
attributes
sourceAnchors
coverage
trustBoundary
diagnostics
```

`sourceAnchors` are bounded, stable, ordered records. At minimum:

```text
anchorId
revisionId
evidenceRefId
sourceArtifactId
sourceDomain
sessionId
supportingGraphObjectIds
supportingAssertionIds
readable
locatorKind: heading | json_pointer | unsupported
```

Do not expose a raw caller-usable path field. A UI-safe display label may be included, but source opening must still use `anchorId`.

#### Outcome semantics

| Outcome | Exact meaning |
|---|---|
| `enough` | Requested target/matches were found and requested data was returned without truncation or a known evidence gap |
| `partial` | Some requested graph data exists, but one or more seeds, evidence links, source anchors, URI schemes, or locators are unavailable/unreadable; no fallback was attempted |
| `empty` | No admissible match/target/evidence exists for an otherwise valid request |
| `denied` | The exact anchor or target is known to be outside the supplied context/admissibility, or an anchor is valid only under another context; return no protected content |
| `truncated` | Useful data is returned, but one or more explicit caps were hit; diagnostics name every cap |
| `unavailable` | The valid request cannot open the requested world/head/revision; no alternate source is consulted |

Outcome precedence when multiple conditions apply:

```text
unavailable > denied > truncated > partial > enough > empty
```

Integrity failures are errors, not `unavailable`.

### §6.2 Opaque source-anchor contract

`anchorId` must be deterministically derived from canonical JSON containing all of:

```text
schema version
worldId
campaignId
focus
admissibility
revisionId
evidenceRefId
sourceArtifactId
locator/sourceSpan identity
```

Recommended visible prefix: `source-anchor:v1:` followed by a lowercase SHA-256 hex digest. The exact canonicalization belongs in one function and must have round-trip tests.

`read_source_anchor` accepts only the request context, `anchorId`, and `maxChars`. It must:

1. Load the requested revision through the same integrity-checked Kernel path.
2. Reconstruct the admissible retrieval/source-anchor set for that exact context.
3. Exact-match the supplied `anchorId`.
4. Resolve only the graph-owned source artifact and locator associated with that anchor.
5. Verify source integrity where required.
6. Return bounded content or a stable non-content outcome/error.

It must not accept `path`, `uri`, `locator`, `evidenceRefId`, or `sourceArtifactId` as substitutes for `anchorId`.

#### Required v1 URI/locator support

| Source artifact URI | Evidence locator | Required behavior |
|---|---|---|
| `repo://<repo-relative-path>` | `heading:<exact heading text>` | Resolve under repository root only; reject escape/symlink-outside-root; verify available SHA-256/source revision; exact heading match after stripping Markdown heading markers; return heading section bounded by next heading of same or higher level |
| `graph-data://<relative-path>` | `jsonptr:<RFC 6901 pointer>` | Resolve through the revision-bound active contribution payload whenever possible; do not trust an arbitrary repo path; exact JSON Pointer; return bounded pretty JSON/text for selected value |

Other URI schemes or locator forms are not discovered elsewhere. Emit an anchor with `readable=false`, `locatorKind=unsupported`, and `partial` diagnostics. Do not add a general file reader.

#### Source read result

At minimum:

```text
schema
outcome
snapshot
anchorId
evidenceRefId
sourceArtifactId
sourceDomain
locatorKind
mediaType
content
contentSha256
lineStart
lineEnd
truncated
trustBoundary
diagnostics
```

Rules:

- `maxChars` default 4,000; hard maximum 12,000.
- No raw absolute path appears in response or diagnostics.
- For `repo://`, source digest mismatch returns HTTP 409 `source_integrity_error` and no content.
- For `graph-data://`, inability to resolve the revision-bound contribution or JSON pointer is an integrity/contract error, not permission to read a similarly named repo file.
- Multiple exact heading matches are ambiguous and fail closed; do not take the first.
- Content truncation is explicit and deterministic.

### §6A State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Search | Synchronous load of one revision; no fallback | `enough` or `truncated` from graph only | `empty` | `unavailable` | 409/422/500 stable error | Explicit pin remains historical; unpinned call reads current head | Safe and deterministic for pin |
| Exact object | Same | Exact survivor or explicit active redirect | `empty` | `unavailable` | Fail closed | Retracted/unsupported object is `empty`; redirect is explicit | Safe |
| Neighborhood | Same | Bounded deterministic traversal | `empty` or `partial` for missing seeds | `unavailable` | Fail closed | Uses selected revision only | Safe |
| Evidence | Same | Active support + anchors | `empty` | `unavailable` | Fail closed | Uses selected revision support ledger | Safe |
| Source-anchor read | Reconstruct exact context/anchor set | Bounded verified content | Unknown anchor -> `empty`; unsupported locator -> `partial` | Missing source -> `unavailable` | Stale hash/invalid pointer/escape -> 409 | Anchor is bound to revision/context; no rebinding | Safe; same pin/anchor deterministic |

**Named fallback sources:** none. Every row has no fallback.

### §6B Identity matrix

| Situation | Required matching rule | Ambiguity behavior | Fallback permitted? | Persistence consequence |
|---|---|---|---|---|---|
| Exact node ID | Exact projected durable ID; active durable redirect may resolve to survivor with diagnostic | Multiple/cyclic/invalid redirect is integrity failure | No | None; read-only |
| Search label or alias | Ranked search only; return multiple deterministic candidates | Preserve multiple results; never first-win | No | None |
| Exact object label/alias | Prohibited as object identity | Return invalid request or empty according to request shape | No | None |
| Normalized key | Prohibited as identity; token normalization may affect ranking only | Never rebind | No | None |
| Relationship ID | Exact `edge_id` only | Missing -> empty | No | None |
| Attribute ID | Exact `assertion_id` only | Missing -> empty | No | None |
| Rename | Durable ID remains identity; display label may differ by revision | Historical pin retains old revision display | No | None |
| Deletion/retraction | Not projectable in selected revision -> empty | No resurrection from source text | No | None |
| Anchor ID | Exact digest and exact context/revision membership | Mismatch -> denied/empty; never resolve by evidence/path | No | None |
| Source path | Never caller identity | Reject if supplied | No | None |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| Retrieval request/result | No new persisted state; strict API schemas | Serialize -> validate -> serialize preserves semantic fields and aliases | Same immutable revision and request returns deterministic ordering and anchor IDs | Forward-only v1; no compatibility mode for manifest/corpus retrieval | Revert PR removes API with no data migration |
| Anchor derivation | Derived `source-anchor:v1:<digest>`; not stored | Same canonical input produces same ID | Duplicate derivation deduplicates by anchor ID | Version is included in digest/input | No persisted cleanup |
| Source read | No persisted state | Same valid anchor + immutable revision + unchanged verified source returns same bounded content | Safe duplicate read | Unsupported locator remains explicit; do not migrate by guessing | No mutation |
| Unpinned current-head request | Resolves head at request time | Response names actual revision | Later call may differ after head advance | Expected behavior, not stale-cache compatibility | Caller may use old explicit pin |

### §6D Predecessor-to-consumer mapping

**Grounding sources:**

- `src/graph_memory/projection/world_projection.py`
- `src/graph_memory/kernel/world_projection.py`
- `apps/live_control_server/routes/world_graph_projection.py`
- `graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1/contributions/006-tripod-null-calf-threat-prep.json`
- `graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1/contributions/001-mirathorn-world-hub.json`

| Predecessor field / outcome | Real shape and optionality | Retrieval field / behavior | Transformation | Proof fixture/test |
|---|---|---|---|---|
| `WorldGraphProjectionRequest.world_id` | required string | common `worldId` | Preserve | Kernel + route contract tests |
| `campaign_id` | required string | `campaignId` | Preserve | Same |
| `focus` | `WorldGraphProjectionFocus`, `none` or `session` | common `focus` | Reuse exact model/vocabulary | Same |
| `admissibility` | string; projection currently supports `gm` | common `admissibility` | Reuse predecessor validation; do not pretend player policy exists | Unsupported-policy test |
| `revision_pin` | optional string | `revisionPin` | Preserve exact revision IDs | Head/historical pin tests |
| Projection snapshot | world/campaign/revision/head/isHead/focus/admissibility | retrieval snapshot | Preserve exact meanings | Fixture + route tests |
| Node view | exact `node_id`, label, kind, role, aliases, summary, focus, evidence/source IDs | retrieval node | Preserve; add retrieval relevance reasons separately | Tripod search test |
| Relationship view | exact edge/source/target/predicate/label/session/visibility/campaign/epistemic/evidence/source IDs | retrieval relationship/path | Preserve; derive endpoint-relative direction for traversal | North Gate traversal test |
| Attribute view | exact `assertion_id`, subject, predicate, label, value/text, epistemic/visibility/campaign/temporal/support/evidence/source IDs | retrieval attribute | Preserve | Attribute search/evidence test |
| Evidence view | evidence ID, artifact ID, domain, optional session/locator/span | source anchor input | Combine with source artifact and request snapshot; hash to opaque anchor | Anchor derivation tests |
| Source artifact view/store record | artifact ID, domain, URI, campaign, optional session and extra digest fields | anchor metadata/read resolver | URI is backend-only; never caller input | Repo heading and graph-data JSON pointer tests |
| Projection `world_graph_unavailable` / revision not found | stable predecessor error | retrieval outcome `unavailable` | Map only absence; preserve diagnostics without path leakage | Route unavailable test |
| Projection integrity error | stable 409 error | retrieval 409 error schema | Fail closed; do not map to unavailable | Mutation/fault-injection test |
| Tripod source | `graph-data://...006-tripod-null-calf-threat-prep.json`, `jsonptr:/accepted_assertions/N` | readable JSON-pointer anchor | Resolve revision-bound contribution payload | Real-bundle source-read test |
| Mirathorn source | `repo://corpus/.../The City of Mirathorn.md`, `heading:The City of Mirathorn`, SHA-256 metadata | readable heading anchor | Safe repo-root resolution + digest + exact heading section | Real-bundle heading test |

Do not invent alternate locator vocabulary for the acceptance bundle.

---

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command or scenario | Expected evidence |
|---|---|---|---|
| Strict schemas, bounds, aliases, and outcome enum | Model serializer | `uv run pytest -q tests/test_graph_kernel_world_retrieval.py -k "model or schema or bounds or round_trip"` | Exact validation and serialization assertions |
| Natural-language search finds `threat:tripod-null-calf` | Kernel retrieval | `uv run pytest -q tests/test_graph_kernel_world_retrieval.py -k "tripod and search"` | Match ID, reasons, attributes, revision snapshot |
| Relationship text participates in search | Kernel retrieval | Same test module, relationship-ranking case | Query matches through predicate/label/related node without LLM |
| Exact ID does not rebind by label/alias | Kernel retrieval | Same test module, identity cases | Exact miss remains empty; redirect is explicit |
| Depth-bounded North Gate traversal | Kernel retrieval | `uv run pytest -q tests/test_graph_kernel_world_retrieval.py -k "tripod and neighborhood"` | Deterministic nodes/edges, endpoint-relative direction, max depth/caps |
| Active support becomes opaque anchors | Kernel retrieval | Same test module, evidence/anchor cases | Anchor IDs bind context/revision and associate target/assertion IDs |
| `graph-data://` JSON-pointer read | Kernel source reader | Same test module, real-bundle source-read case | Revision-bound selected assertion content; no repo path input |
| `repo://` heading read with digest | Kernel source reader | Same test module, Mirathorn heading case | Exact bounded section and verified digest |
| Unknown/mismatched anchor cannot read another source | Kernel source reader | Same test module, anchor-negative cases | Empty/denied; no content; no rebinding |
| Source drift fails closed | Kernel source reader | Same test module, mutate temp source after graph publication | 409-equivalent Kernel error, no content |
| Graph miss never invokes fallback | Kernel/import boundary | Same test module plus `tests/test_graph_kernel_boundaries.py` | Monkeypatched legacy functions remain uncalled; imports/grep forbid fallback modules |
| Route success and exact wire shape | FastAPI route | `uv run pytest -q tests/test_world_graph_retrieval_routes.py -k "success or contract"` | Exact schemas, camelCase, no query params |
| Route invalid/malformed request | FastAPI route | Same route module | 422 stable retrieval error, including nested/extra fields |
| Unavailable vs integrity distinction | Service/route | Same route module | Unavailable HTTP 200 result; integrity HTTP 409 error |
| API fixture is produced from real operations | Serialization/route | Route tests compare real temporary-root results with `tests/fixtures/world_graph_retrieval/api-contract-v1.json` | Fixture matches service output, not hand-written approximations |
| Kernel export and application import boundary | Public API/guard | `uv run pytest -q tests/test_graph_kernel_public_api.py tests/test_graph_kernel_boundaries.py` | New functions exported; live-control does not import storage or legacy retrieval internals |
| Projection predecessor remains green | Regression | `uv run pytest -q tests/test_graph_kernel_world_projection.py tests/test_world_graph_projection_routes.py tests/test_agent_world_graph_query_context.py` | No PR007A/PR008B regression |
| Full focused slice | All owning boundaries | `uv run pytest -q tests/test_graph_kernel_world_retrieval.py tests/test_world_graph_retrieval_routes.py tests/test_graph_kernel_public_api.py tests/test_graph_kernel_boundaries.py tests/test_graph_kernel_world_projection.py tests/test_world_graph_projection_routes.py tests/test_agent_world_graph_query_context.py` | Exact pass count recorded |
| Lint | Changed Python paths | `uv run ruff check src/graph_memory/retrieval src/graph_memory/kernel/world_retrieval.py src/graph_memory/kernel/__init__.py src/graph_memory/kernel/contracts.py apps/live_control_server/services/world_graph_retrieval.py apps/live_control_server/routes/world_graph_retrieval.py apps/live_control_server/main.py tests/test_graph_kernel_world_retrieval.py tests/test_world_graph_retrieval_routes.py tests/test_graph_kernel_public_api.py tests/test_graph_kernel_boundaries.py` | Clean or truthful base/head comparison |
| Scope | Repository diff | `git diff --check` | Clean |
| Scope | Repository diff | `git diff --stat 23959e4cfdb4f3cad181f0cdcae695d21c8fc1af...HEAD -- <all §4 paths>` | Focused stat matches allowlist |
| Scope | Repository diff | `git diff --name-only 23959e4cfdb4f3cad181f0cdcae695d21c8fc1af...HEAD` | No unexpected paths |

### Required acceptance scenarios inside the automated suite

The temporary graph must be initialized from the checked-in approved bundle using existing Kernel/bootstrap helpers. Do not handcraft a simpler graph for the primary acceptance cases.

1. Search: `What do we know about Tripod Null-Calf at the North Gate?`
2. Assert `threat:tripod-null-calf` is matched from the published graph vocabulary.
3. Traverse at depth sufficient to reach the gate-battle/North Gate context, within declared bounds.
4. Fetch evidence for the Tripod node and one attribute/relationship.
5. Read one `graph-data://` JSON-pointer anchor.
6. Search/open Mirathorn and read its `repo://...` exact-heading anchor with digest verification.
7. Query a phrase deliberately absent from the graph while monkeypatching legacy manifest/corpus/lexical lookup entry points to raise if invoked; result must remain `empty` and patches uncalled.
8. Mutate the temporary repo source after anchor emission; read must fail closed as stale/integrity error.
9. Reuse an anchor with a different revision or campaign/focus context; no content is returned.
10. Repeat an identical pinned request; ordering and anchor IDs are identical.

### Minimal live proof

```text
Not applicable — PR010A is a backend contract slice. The approved real contribution bundle is exercised through temporary-root Kernel/service/route integration tests, which own the guarantees more directly than a browser or manual UI scenario. Do not add a UI or CLI solely for proof.
```

### Baseline failure protocol

For any required command already failing on base:

- run the same command on base and head with the same environment;
- record exact base/head results;
- identify whether head adds failures;
- do not call the gate green;
- name the explicit operator waiver if the failing command remains an acceptance gate.

| Command | Base result | Head result | New failure introduced? | Acceptance effect | Waiver |
|---|---|---|---:|---|---|
| Fill in handback | Fill in handback | Fill in handback | Yes / No | Blocked or acceptable with explicit waiver | `none` or exact waiver |

---

## §8 Required implementation handback

The PR body or handback must include:

1. Implementation base SHA and head SHA.
2. Actual changed paths.
3. Focused diff stat limited to §4.
4. Every §7 command/scenario with exact result.
5. Provenance of each result: author-local, independently rerun local, CI, or manual.
6. The exact generated API-contract fixture cases and confirmation they came from real temporary-root service operations.
7. Baseline failures with base/head comparison.
8. Explicit operator waivers; write `none` when none exist.
9. Paths outside §4; write `none` or include a stop report.
10. Stop conditions encountered and their resolution; write `none` when none exist.
11. Deviations from §6 matrices; write `none` when none exist.
12. Confirmation that no manifest, corpus-index, repo search, arbitrary-path, vector, LLM, or Hermes dependency is present in the retrieval implementation.
13. Confirmation that PR010B remains false: no Hermes session/tool loop, no Agent Interaction migration, no legacy-path deletion.
14. Confirmation that PR011 remains false: no writes, drafts, preview/confirm, provider lift, or cross-surface runtime.
15. Confirmation that the complete handoff was implemented without compression or omitted constraints.

The handback must explicitly enumerate:

```text
Retained temporarily:
- Legacy manifest/corpus/Hermes retrieval paths.

Reason:
- PR010A establishes the replacement contract but does not yet make the Hermes product path use it.

Remaining consumer:
- Current transitional Live/Hermes query paths and their tests.

Required deletion PR:
- PR010B for Hermes product-path replacement and demolition.
- PR012 only for a leftover with a named remaining consumer after PR010B.
```

---

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true.

- [ ] Exactly one capability was delivered: graph-only retrieval plus anchor-bound source reading — proved by the full focused §7 suite.
- [ ] Natural-language search finds `threat:tripod-null-calf` from the approved graph — proved by `test_graph_kernel_world_retrieval.py` Tripod search case.
- [ ] Search considers relationship text without LLM/vector fallback — proved by the relationship-ranking Kernel case.
- [ ] Exact object lookup never rebinds from a label or alias; any active redirect is explicit — proved by Kernel identity cases.
- [ ] Bounded traversal reaches the expected Tripod/North Gate context from one pinned revision with deterministic endpoint-relative edges — proved by the neighborhood case.
- [ ] Evidence lookup emits revision/context-bound opaque anchors tied to active graph support — proved by evidence/anchor tests.
- [ ] `read_source_anchor` accepts no path/URI/locator substitute and revalidates exact anchor membership — proved by model/route negative tests and Kernel anchor tests.
- [ ] Required `repo://` heading and `graph-data://` JSON-pointer reads work from real approved-bundle inputs — proved by the two source-reader acceptance cases.
- [ ] Stale source bytes, path escape, malformed pointer, ambiguous heading, and graph integrity failures return no content and fail closed — proved at Kernel and route boundaries.
- [ ] Outcomes follow §6A: enough/partial/empty/denied/truncated/unavailable are distinct and integrity errors are not mislabeled unavailable — proved by model/service/route tests and canonical fixture.
- [ ] A graph miss remains a graph miss and no fallback function/module is called — proved by monkeypatch and import-boundary tests.
- [ ] Same pinned request returns stable ordering and anchor IDs — proved by deterministic replay test.
- [ ] Application/service code imports graph operations only from `graph_memory.kernel` — proved by `tests/test_graph_kernel_boundaries.py`.
- [ ] The real predecessor vocabulary and identifier shapes are preserved — proved by mapping tests and the generated API fixture.
- [ ] No UI, Hermes, LLM, graph-write, ingestion, Play, embedding, or legacy-deletion capability was smuggled into the diff — proved by allowlist/diff inspection.
- [ ] No path outside §4 changed — proved by `git diff --name-only`.
- [ ] Baseline failures and waivers are reported truthfully.
- [ ] PR010B and PR011 remain explicitly unimplemented and unclaimed.

---

## §10 Reviewer protocol

1. Restate the mission and invariant before reviewing files.
2. Inspect the public models first. Confirm no path/URI/manifest/run/store selector exists in any caller request.
3. Verify every operation loads or derives from one revision through the existing Kernel/projection integrity path.
4. Trace one Tripod search end-to-end through model -> Kernel -> service -> route -> serialized fixture.
5. Trace one source anchor from graph assertion/evidence/artifact -> anchor digest -> exact read revalidation -> bounded content.
6. Attempt to forge or reuse an anchor under another context; verify no content leaks.
7. Audit search, exact lookup, traversal, evidence, and source read for hidden fallback imports or calls.
8. Inspect deterministic ordering, tie-breaking, deduplication, caps, and outcome precedence.
9. Verify source resolution rejects absolute paths, `..`, symlink escape, unsupported schemes, ambiguous headings, and invalid JSON pointers.
10. Verify source digest drift is an integrity failure with no body.
11. Confirm route validation catches malformed nested requests before default FastAPI 422 bodies leak through.
12. Verify the canonical API fixture is generated from real operations and includes ordinary miss/unavailable/integrity examples.
13. Run the exact §7 commands independently using the external-agent review script/process.
14. Compare actual paths with §4 and reject adjacent Hermes/UI/cleanup work.
15. Confirm the successor demolition remains deferred to PR010B.

---

## Stop conditions

Stop and report rather than broadening the slice when implementation discovers:

- the approved graph cannot associate evidence/source artifacts with active assertions without changing contribution or storage contracts;
- source-anchor reading requires accepting a caller path, URI, locator, manifest route, or corpus search;
- the required Tripod/North Gate traversal cannot be expressed with deterministic depth <= 2 and declared caps, and solving it requires generalized GraphRAG;
- supporting the current acceptance bundle requires a third URI scheme or locator family not named here;
- player-facing admissibility must be invented or expanded beyond the existing projection policy;
- a new persisted anchor registry, cache, database, session store, or migration is needed;
- an LLM or Hermes runtime is required to make the retrieval contract useful;
- legacy retrieval must be deleted before the new contract can be tested;
- a production file outside §4 is required;
- current `main` authority conflicts with this handoff;
- a base failure needs an operator waiver before acceptance.

Use this report:

```text
Stop condition:
Why the current mission cannot absorb it:
New public/durable contract discovered:
Affected observable paths:
Affected ownership layers:
Required path outside scope:
Proposed successor slice:
Tracker or authority update needed:
Operator decision required:
```

The worker must not resolve a stop condition by silently expanding PR010A.

---

## Final dispatch check

- [x] Capability decomposition selects one independently useful outcome.
- [x] Mission and invariant are explicit.
- [x] Authority and immutable base are named.
- [x] Success, miss, unavailable, integrity, stale, traversal, anchor-read, and replay paths are inventoried.
- [x] Every expected production/test path is allowlisted or covered by one bounded test-only exception.
- [x] State/fallback, identity, persistence/replay, and predecessor mappings are explicit.
- [x] No fallback source exists in the contract.
- [x] Every acceptance guarantee maps to an owning §7 proof.
- [x] PR010B and PR011 are named successors and remain false.
- [x] No PR has been opened by the handoff author.
