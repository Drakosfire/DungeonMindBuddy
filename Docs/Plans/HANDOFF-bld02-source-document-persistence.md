# HANDOFF — BLD-02 safe worldbuilding workspace persistence

- **Created:** 2026-07-22
- **Status:** PREPARED / DRAFT — may be stacked against the BLD-01 head; ACTIVE / MERGEABLE only after BLD-01 merge, tracker re-anchor, rebase, and immutable merge-SHA anchoring.
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld02-source-document-persistence.md`
- **Suggested branch:** `agent/bld02-source-document-persistence`

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract changed? | Decision |
|---|---:|---:|---|
| Extend workspace documents with an explicit worldbuilding source kind and metadata | Yes | Yes | Include |
| Preserve safe prepare/commit semantics for approved worldbuilding roots | No — required to make the same document capability truthful | Yes, existing writer contract evolved | Include |
| Create immutable graph evidence SourceArtifacts | Yes | Yes | Successor: BLD-03 |
| Launch extraction | Yes | Yes | Successor: BLD-06 |

**Selected capability:** a worldbuilding source is an authored workspace document
that can be created, committed, reopened, discarded, and restored safely.

**Why the included rows share one invariant:** the workspace record and writer
are the two owning boundaries of one source-document persistence capability; a
record that cannot commit safely is not independently useful.

## §1 Mission

A Build caller can create, classify, safely commit, reopen, discard, and restore
an explicit `worldbuilding_source` workspace document without using Plan’s
session-prep semantics or silently losing unsupported Markdown.

**Invariant:** every worldbuilding workspace write is bound to an opaque
server-issued document ID and current registry revision, resolved through a
server-owned target policy, and either preserves the supported representation
or fails visibly before mutation.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`, Phase 2 |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-02 |
| Identity authority | `Docs/Design/CONTRACT-workspace-document-identity-v1.md` |
| Repository rules | `AGENTS.md`, `.cursor/rules/dungeonbuddy-environment.mdc`, `.cursor/rules/external-agent-pr-loop.mdc` |
| Base revision | Dispatch-time immutable merge SHA of BLD-01 |
| Predecessor contract | `WorkspaceDocumentRecord`, workspace-document routes, `tiptap_markdown_write.py`, and BLD-01 Markdown adapter |
| Exact input consumed | Server-issued workspace document ID, explicit source metadata, registry revision, registry-owned target, and semantic Markdown |
| Named successor | BLD-03 immutable SourceArtifact and exact ExtractionRun contracts |
| What remains false | No SourceArtifact, extraction, candidate graph, Graph Review handoff, or graph-head mutation |
| Explicit non-goals | Separate source registry, browser-controlled paths, bulk migration, PDF ingestion, graph identity semantics |

### Locked identity decision

BLD-02 extends the existing workspace registry. It does **not** create a second
source-document registry.

```text
WorkspaceDocumentRecord.kind += worldbuilding_source
```

The workspace document remains an opaque server-issued UUID. The record gains
explicit metadata for source domain, document class, authority, visibility, and
optional campaign/session scope. The client never supplies or infers the target
path.

BLD-02 does **not** create a graph evidence SourceArtifact. BLD-03 later creates
a distinct immutable SourceArtifact from a committed revision and links it by:

```text
workspace_document_id
workspace_document_revision
content_sha256
```

Workspace IDs and SourceArtifact IDs are separate namespaces and may not be
joined by rewriting strings, labels, or paths.

Read in order:

1. `Docs/Design/CONTRACT-workspace-document-identity-v1.md`
2. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
3. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
4. `apps/live_control_server/services/workspace_document_registry.py`
5. `apps/live_control_server/routes/workspace_documents.py`
6. `apps/live_control_server/services/tiptap_markdown_write.py`
7. BLD-01 shared Markdown adapter
8. existing registry and writer tests

Stop if extending the existing registry would require parsing IDs, labels, or
paths as identity, or if Plan/runbook behavior cannot remain compatible.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Create worldbuilding source | Registry accepts `plan | runbook` | Server issues UUID for `worldbuilding_source` with explicit metadata | Yes | Registry + route |
| Load/reopen | Reads existing record | Exact UUID returns identity, metadata, revision, status, and content status | Yes | Registry + route |
| Update metadata | Existing CAS semantics | Explicit metadata update requires current revision when supplied | Yes | Registry |
| Discard/restore | Existing retained lifecycle | Worldbuilding source uses the same retained audit lifecycle | Yes | Registry + route |
| Prepare write | Restricted Plan/eval targets | Resolve registry-owned approved worldbuilding target and return non-mutating preview | Yes | Writer |
| Commit write | Existing two-phase update | Commit validates token, registry revision, file state, and supported Markdown | Yes | Writer |
| Unsafe target | Rejected for existing kinds | Reject traversal, absolute paths, root escape, and kind/policy mismatch | Yes | Target resolver |
| Unsupported Markdown | Converter may warn/flatten | Return diagnostics and block lossy commit | Yes | Adapter + writer route |
| Stale registry/file revision | Existing conflict behavior | 409/no mutation; dirty client state remains recoverable | Yes | Registry/writer |
| Plan/runbook compatibility | Existing callers | Byte/behavior-compatible existing paths | Yes | Existing tests |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `Docs/Design/CONTRACT-workspace-document-identity-v1.md` | Adopt `worldbuilding_source` and explicit metadata while preserving UUID and namespace rules |
| Modify | `apps/live-control-ui/src/api/types.ts` | Typed worldbuilding workspace metadata and request/response contracts |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Existing workspace API client support for the new kind and lifecycle |
| Modify | `apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts` | Surface conversion diagnostics and commit-blocking state |
| Modify | `apps/live_control_server/services/workspace_document_registry.py` | Extend discriminator and validate source metadata without a second registry |
| Modify | `apps/live_control_server/routes/workspace_documents.py` | HTTP contract for worldbuilding workspace records |
| Modify | `apps/live_control_server/services/tiptap_markdown_write.py` | Registry-owned worldbuilding target policy and safe two-phase writes |
| Modify | `tests/test_workspace_document_registry.py` | Worldbuilding UUID, metadata, lifecycle, CAS, and compatibility proof |
| Create | `tests/test_tiptap_markdown_write.py` | Target, revision, diagnostic, prepare, and commit proof |
| Create | `apps/live-control-ui/src/api/liveApi.test.ts` | Client contract and error-mapping proof |

**Bounded discovery exception:** Not applicable — every expected path is listed.

## §5 Explicitly out of scope

| Path or capability | Why |
|---|---|
| `apps/live-control-ui/src/App.tsx` | Build route belongs to BLD-05 |
| `apps/live-control-ui/src/buildSurface/**` | Build UI is a successor |
| `src/graph_memory/**` | Immutable evidence and run contracts belong to BLD-03 |
| `apps/live_control_server/services/recap_graph_preview_ingest.py` | Recap extraction is not part of workspace persistence |
| `corpus/**`, `evals/**` | No canon, source batch, or gold mutation |
| Any direct graph write | Source persistence and graph publication are separate systems |
| Separate source-document registry | The identity decision is to evolve the existing workspace registry |

## §6 Implementation contract

```text
Input:
  server-issued workspace document ID, kind=worldbuilding_source,
  explicit metadata, expected registry revision, registry-owned target,
  and semantic Markdown.

Output:
  WorkspaceDocumentRecord plus prepare/commit responses containing exact UUID,
  revision, target-safe display metadata, diagnostics, digest, and truthful
  mutation state.

Invariant:
  No unsafe, stale, discarded, unsupported, or unregistered write mutates the
  filesystem; existing Plan/runbook behavior remains compatible.

Failure behavior:
  unsafe target → stable client error; no mutation
  unknown UUID → 404
  discarded/no target → blocked write
  stale registry or file state → 409; no mutation
  lossy conversion → diagnostics + blocked commit

Replay / idempotency:
  same UUID + revision + content + file state → same prepare digest/token meaning
  changed content/revision/file state → old token invalid
  duplicate create request → explicit new UUID unless a declared idempotency key is added
  repeated valid commit → existing truthful already-applied/conflict semantics

Trust boundary:
  Verifies: UUID record, kind, metadata matrix, revision, target policy,
  containment, content digest, writer token, and file state.
  Does not prove: narrative truth, graph meaning, or promotion eligibility.
```

### §6A State and fallback matrix

| Path | Success | Ordinary miss | Unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|
| Registry load | Exact record | 404 | stable service error | reject malformed record | return current revision | safe GET |
| Prepare | Non-mutating preview | 404/discarded/no target | stable error | fail closed | 409 | re-read then prepare |
| Commit | Exact committed revision | 404 | stable error | preserve source | 409 | only with valid prepare/current state |
| Markdown validation | Empty diagnostics for supported subset | explicit empty document allowed | N/A | block lossy content | preserve dirty state | user fixes/abandons |

### §6B Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| Workspace document ID | Opaque server UUID, equality-only | unknown is 404 | none |
| Title | Display metadata only | duplicates allowed | never identity |
| Target path | Registry-owned and normalized | mismatch/escape rejected | none |
| SourceArtifact | Not created in this slice | any attempted ID reuse is a stop | none |
| Session scope | Optional for worldbuilding | invalid metadata matrix fails | no synthetic session |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round trip | Replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Create/update/discard/restore | workspace registry v1 evolved contract | exact UUID/metadata/revision/status | CAS rules | plan/runbook readable | retained lifecycle |
| Prepare | non-mutating digest/token | exact target/revision/file state | deterministic meaning | existing writer paths valid | no mutation |
| Commit | Markdown + backup/revision state | reload returns committed content | stale/token mismatch rejects | existing targets valid | existing backup contract |

### §6D Predecessor mapping

| Predecessor | Real shape | Consumer behavior | Proof |
|---|---|---|---|
| `WorkspaceDocumentRecord.kind` | `plan | runbook` | explicitly add `worldbuilding_source` | registry tests + contract doc |
| opaque `document_id` | server UUID | unchanged equality-only identity | registry/API tests |
| `target_relpath` | registry-owned optional path | apply worldbuilding root policy server-side | writer tests |
| prepare/commit requests | document ID + Markdown + revision/token | preserve shape and extend policy | route/writer tests |
| conversion diagnostics | code/message/lossiness | preserve and block unsafe commit | adapter/client/writer tests |

## §7 Verification ownership and commands

| Guarantee | Boundary | Command |
|---|---|---|
| UUID identity and metadata lifecycle | Registry | `uv run pytest tests/test_workspace_document_registry.py` |
| Unsafe/stale/lossy writes fail without mutation | Writer | `uv run pytest tests/test_tiptap_markdown_write.py` |
| API client preserves errors and diagnostics | Frontend client | `npm test -- --run src/api/liveApi.test.ts` |
| Plan/runbook compatibility | Existing owning tests | include current registry/writer and relevant UI tests |
| No scope creep | Git | changed-path and diff checks |

```bash
uv run pytest tests/test_workspace_document_registry.py \
  tests/test_tiptap_markdown_write.py
cd apps/live-control-ui
npm test -- --run src/api/liveApi.test.ts
npm run typecheck
cd ../..
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing surface: workspace-document API
Scenario: create worldbuilding source, update metadata, prepare/commit, reload,
discard/restore, then attempt traversal, stale revision, discarded write, and
lossy Markdown commit.
Expected: valid lifecycle round-trips; every invalid write leaves source intact.
```

## §8 Required handback

Record base/head SHAs, actual changed paths, focused diff stat, every §7 result
with provenance, live proof, baseline failures, waivers, stop conditions, and
confirmation that no SourceArtifact, extraction, or graph publication was added.

## §9 Acceptance rubric

- [ ] Existing workspace UUID identity is retained and the contract doc is updated.
- [ ] `worldbuilding_source` records round-trip explicit metadata and lifecycle.
- [ ] Workspace IDs are not reused as SourceArtifact IDs.
- [ ] Unsafe, stale, discarded, and lossy writes fail closed without mutation.
- [ ] Plan and runbook persistence remain compatible.
- [ ] Browser clients cannot supply arbitrary filesystem targets.
- [ ] Only §4 paths changed.
- [ ] BLD-03 remains the immutable evidence/run successor.

## Stop conditions

Stop and report if implementation requires a second workspace/source registry,
ID parsing, client-supplied paths, SourceArtifact creation, corpus migration,
graph extraction/publication, unsupported syntax representation, or an
authentication/authorization policy change.
