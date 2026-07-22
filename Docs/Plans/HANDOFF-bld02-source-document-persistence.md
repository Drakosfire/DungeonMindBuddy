# HANDOFF — BLD-02 safe source-document persistence

- **Created:** 2026-07-22
- **Status:** DRAFT — dispatch only after BLD-01 is merged and re-anchored
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld02-source-document-persistence.md`
- **Suggested branch:** `agent/bld02-source-document-persistence`

## Shared vocabulary

| Term | Definition |
|---|---|
| Source document | A user-editable Markdown document with explicit source-domain metadata. |
| Registry record | Server-owned identity and metadata for a source document. |
| Prepare/commit | The existing two-phase write protocol; prepare does not mutate the target. |
| Safe target policy | Server-owned allowlist, normalization, and root-containment rule. |

## §1 Mission

A Build caller can create, reopen, and safely commit an explicitly classified
worldbuilding source document without using the Plan session-prep path or
silently losing unsupported Markdown.

**Invariant:** Every source write is server-authorized, revision-aware,
root-contained, and either preserves the supported document representation or
fails visibly before mutation.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`, Phase 2 |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-02 |
| Repository rules | `AGENTS.md`, `.cursor/rules/dungeonbuddy-environment.mdc`, `.cursor/rules/external-agent-pr-loop.mdc` |
| Base revision | Dispatch-time immutable merge SHA of BLD-01; current `8ff2339f` is reference only |
| Predecessor contract | `WorkspaceDocumentRecord`, workspace-document routes, `tiptap_markdown_write.py`, shared Markdown adapter from BLD-01 |
| Exact input consumed | Registry request, source metadata, repo-relative target, source revision, semantic Markdown payload |
| Named successor | BLD-03 generic SourceArtifact and ExtractionRun contracts |
| What remains false | No extraction, candidate graph, Graph Review handoff, or graph-head mutation |
| Explicit non-goals | Arbitrary browser filesystem writes, bulk corpus migration, automatic canon promotion, PDF ingestion, new graph identity semantics |

Read in order:

1. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
2. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
3. `apps/live_control_server/services/workspace_document_registry.py`
4. `apps/live_control_server/routes/workspace_documents.py`
5. `apps/live_control_server/services/tiptap_markdown_write.py`
6. `apps/live-control-ui/src/api/types.ts`
7. `apps/live-control-ui/src/api/liveApi.ts`
8. Existing registry and writer tests

If the existing registry cannot safely represent source metadata without
changing Plan/runbook semantics, stop and propose a separate source registry
instead of widening the discriminator implicitly.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Create source record | Registry supports Plan/runbook kinds | Accept explicit worldbuilding source metadata | Yes | Registry |
| Load source record | Server returns registered document | Return stable identity, metadata, revision, and target policy result | Yes | Route + registry |
| Prepare write | Writer accepts restricted Plan/eval targets | Worldbuilding target is accepted only under source policy | Yes | Writer |
| Commit write | Two-phase write updates approved target | Commit preserves revision/backup/conflict guarantees | Yes | Writer |
| Unsafe target | Must be rejected | Reject traversal, absolute escape, disallowed root, and kind mismatch | Yes | Target resolver |
| Unsupported Markdown | Converter may warn/flatten | Surface diagnostics and block unsafe loss | Yes | Adapter + route |
| Stale source | Existing conflict behavior | Reject stale revision without mutation | Yes | Prepare/commit service |
| Plan/runbook compatibility | Existing callers use current kinds/paths | Existing behavior remains unchanged | Yes | Registry/writer tests |

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/api/types.ts` | Source-document metadata and request/response types |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Source registry API client calls |
| Modify | `apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts` | Expose safe conversion diagnostics to caller |
| Modify | `apps/live_control_server/services/workspace_document_registry.py` | Registry discriminator and metadata validation |
| Modify | `apps/live_control_server/routes/workspace_documents.py` | HTTP contract for source document records |
| Modify | `apps/live_control_server/services/tiptap_markdown_write.py` | Source-domain target policy and safe write behavior |
| Modify | `tests/test_workspace_document_registry.py` | Extend existing registry coverage with source metadata proof |
| Create | `tests/test_tiptap_markdown_write.py` | Target, revision, diagnostic, and commit proof |
| Create | `apps/live-control-ui/src/api/liveApi.test.ts` | Client contract and error mapping proof |

**Bounded discovery exception:** Not applicable — paths are enumerated.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why out of scope |
|---|---|
| `apps/live-control-ui/src/App.tsx` | Build route belongs to BLD-05 |
| `apps/live-control-ui/src/buildSurface/**` | Build UI is a successor |
| `tests/test_workspace_document_registry.py` | Existing test module; extend it in place rather than creating a competing registry test file |
| `src/graph_memory/**` | Generic extraction contracts belong to BLD-03/04 |
| `apps/live_control_server/services/recap_graph_preview_ingest.py` | Recap behavior must remain an adapter consumer |
| `corpus/**` | No source canon or corpus batch mutation |
| `evals/**` | No gold or benchmark migration |
| Any direct graph write | Source persistence and graph publication are separate boundaries |

## §6 Implementation contract and conditional matrices

```text
Input:
  Explicit source kind/domain/class, optional campaign/session scope,
  approved repo-relative target, Markdown revision, and semantic Markdown.

Output:
  Registry record plus prepare/commit responses containing stable document
  identity, revision, diagnostics, and truthful mutation status.

Invariant:
  No unsafe or stale source write mutates the filesystem; supported content is
  preserved and unsupported/lossy conversion is visible before commit.

Failure behavior:
  Unsafe target → stable client error; no prepare or commit mutation.
  Unknown document ID → not-found error.
  Stale revision → conflict error; current source remains unchanged.
  Unsupported/lossy content → diagnostic and blocked commit unless the
  existing contract explicitly proves losslessness.

Replay / idempotency:
  same document + same revision + same content → same prepared digest;
  changed content → new digest/revision-bound prepare;
  retry after partial failure → backup/revision rules determine safe retry;
  duplicate create with caller-supplied ID → reject or return existing record
  only under an explicit idempotency rule.

Trust boundary:
  Verifies: target normalization, root containment, kind policy, revision,
  content digest, and commit preconditions.
  Records or trusts without proving: semantic truth of Markdown or graph
  meaning.
```

### State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Registry load | Route waits for registry | Return full record | 404, no fabricated record | Stable service error | Reject invalid stored metadata | N/A | Safe GET retry |
| Prepare | Validate before write | Return digest/revision preview | 404 for unknown document | Stable unavailable error | Block before mutation | 409 conflict | Re-GET then prepare |
| Commit | Lock/validate target | Return committed revision | 404 | Stable unavailable error | Fail closed and preserve source | 409 conflict | Retry only with same valid prepare |
| Markdown diagnostic | Parse/convert | Return supported content + empty diagnostics | Empty document only if explicit | N/A | Block lossy commit | Mark dirty | User fixes or abandons |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| Registry ID | Stable server-owned ID | Unknown ID is 404 | No |
| Target path | Normalize before policy evaluation | Traversal/absolute/escape is rejected | No |
| Document kind | Kind must match target policy | Mismatch is rejected | No |
| Session scope | Optional for worldbuilding, required only for kinds that need it | Missing required scope is validation failure | No fabricated session |

### Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| Registry create/update | Existing registry record with explicit source metadata | Reload returns same identity and metadata | Duplicate policy is explicit and tested | Plan/runbook records remain readable | Revert registry write |
| Source prepare | Non-mutating digest/revision preview | Preview names exact target and source revision | Same input is stable | Existing Plan prepare contract remains valid | No mutation to roll back |
| Source commit | Markdown target plus existing backup/revision behavior | Reload reads committed content | Stale retry is rejected | Existing target allowlists remain valid | Existing backup/restore contract |

### Predecessor-to-consumer mapping

| Predecessor field/outcome | Consumer | Transformation | Proof |
|---|---|---|---|
| `WorkspaceDocumentRecord.kind` | Source document record | Add explicit worldbuilding discriminator or separate typed registry | Registry test |
| `target_relpath` | Source target policy | Normalize and evaluate against approved root | Writer target tests |
| TipTap conversion warnings | API response | Preserve diagnostic code/message and commit-blocking state | Adapter/API tests |
| Existing prepare/commit response | Build successor | Preserve revision/digest semantics | Existing writer tests |

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command | Expected evidence |
|---|---|---|---|
| Registry accepts valid worldbuilding metadata | Registry service | `uv run pytest tests/test_workspace_document_registry.py` | Valid records and invalid metadata cases |
| Unsafe target fails closed | Writer/target resolver | `uv run pytest tests/test_tiptap_markdown_write.py` | Traversal and root-escape cases reject without mutation |
| Stale revision does not mutate | Prepare/commit service | Same writer test module | Conflict response and unchanged source |
| Client maps source API errors | Frontend API client | `npm test -- --run src/api/liveApi.test.ts` | Stable error mapping |
| Existing Plan/runbook behavior remains green | Owning existing tests | Existing backend/UI test suites | No regression |
| No scope creep | Git | `git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD` | Only §4 paths |

```bash
uv run pytest tests/test_workspace_document_registry.py \
  tests/test_tiptap_markdown_write.py
cd apps/live-control-ui
npm test -- --run src/api/liveApi.test.ts
npm run typecheck
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing surface used: existing workspace-document API
Smallest scenario: create a worldbuilding record, prepare/commit one source,
reload it, then attempt traversal and stale-revision writes
Expected observation: valid write reloads; invalid writes do not mutate
Evidence captured: focused backend tests and API-client test output
```

## §8 Required handback

1. Base and head SHA.
2. Focused diff stat limited to §4.
3. Exact result of every §7 command.
4. Provenance for each result.
5. Safe write live proof.
6. Base/head comparison for any baseline failure.
7. Operator waivers; `none` if none.
8. Paths outside §4; `none` or stop report.
9. Stop conditions; `none` if none.
10. Confirmation that BLD-03 remains the successor.
11. Confirmation that this handoff was followed without omitted constraints.

## §9 Acceptance rubric

- [ ] Worldbuilding source records can be created and reopened — proved by registry tests.
- [ ] Unsafe and stale writes fail closed without mutation — proved by writer boundary tests.
- [ ] Unsupported/lossy Markdown is visible and cannot silently commit — proved by adapter/writer tests.
- [ ] Plan and runbook persistence remains compatible — proved by existing tests.
- [ ] No browser-controlled arbitrary filesystem write exists — proved by route and target-policy inspection.
- [ ] No path outside §4 changed — proved by changed-path command.
- [ ] No extraction or graph publication capability was introduced.
- [ ] BLD-03 remains unimplemented and unclaimed.

## Stop conditions

Stop and report if:

- source persistence requires a new source-artifact/run schema;
- target policy needs corpus-wide migration;
- graph extraction or promotion must happen inside the write route;
- unsupported Markdown requires a new editor node or durable syntax;
- authentication/authorization behavior must change.

```text
Stop condition:
Why the current mission cannot absorb it:
New contract discovered:
Affected paths:
Proposed successor slice:
Authority update needed:
```
