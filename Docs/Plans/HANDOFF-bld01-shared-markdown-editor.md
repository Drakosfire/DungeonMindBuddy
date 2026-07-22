# HANDOFF — BLD-01 shared Markdown editor

- **Created:** 2026-07-22
- **Status:** DRAFT — dispatch only after BLD-00 is adopted and a clean
  predecessor SHA is recorded
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld01-shared-markdown-editor.md`
- **Suggested branch:** `agent/bld01-shared-markdown-editor`

## Shared vocabulary

| Term | Definition |
|---|---|
| Capability | One reusable editor behavior delivered without requiring Build. |
| Public/durable contract | Editor props, Markdown adapter behavior, or serialized document shape consumed by a surface. |
| Owning boundary | The editor or adapter where the guarantee becomes true. |
| Stop condition | A discovered requirement that creates a second product capability or durable contract. |

## §1 Mission

Plan and the TipTap bridge spike can use one surface-neutral Markdown editor so
future surfaces can reuse editor behavior without inheriting Plan or runbook
assumptions.

**Invariant:** The shared editor owns common editing lifecycle and Markdown
conversion behavior; surface adapters own document identity, persistence
targets, and surface-specific tools.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`, Phase 1 |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-01 |
| Repository rules | `AGENTS.md`, `.cursor/rules/subagent-delegation.mdc`, `.cursor/rules/external-agent-pr-loop.mdc` |
| Base revision | Dispatch-time immutable merge SHA of BLD-00; current `8ff2339f` is a planning reference only, not a clean dispatch base |
| Predecessor contract | Existing `PlanSurfaceCanvas`, `TiptapCalloutBridgeSpike`, `markdownToTiptap`, semantic Markdown serializer |
| Exact input consumed | TipTap JSON, Markdown text, current editor props, local draft state, and surface tool descriptors |
| Named successor | BLD-02 source-document persistence and BLD-05 Build shell |
| What remains false | Build route, source registry, worldbuilding metadata, extraction, and graph publication |
| Explicit non-goals | New Markdown syntax, table/image support, writer allowlist changes, graph extraction, route/nav changes, corpus mutation |

Read in order:

1. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
2. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
3. `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx`
4. `apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.tsx`
5. `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts`
6. Existing Plan and TipTap tests

If the current editor already has a different public adapter seam, stop and
report the mapping before changing it.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Plan open/edit/export | Plan canvas owns TipTap setup and draft lifecycle | Shared editor provides setup/lifecycle; Plan adapter supplies document behavior | Yes | Shared editor + Plan adapter |
| Spike open/edit/export | Spike owns its own editor setup and tools | Spike consumes shared editor with runbook-specific tools injected | Yes | Shared editor + Spike adapter |
| Unsupported Markdown import | Converter emits diagnostics; caller behavior varies | Diagnostics remain visible and no new silent fallback is introduced | Yes | Markdown adapter |
| Dirty/reload | Each consumer has local state rules | Common dirty lifecycle is exposed; persistence remains consumer-owned | Yes | Shared editor |
| Save failure | Surface-specific hooks handle API failures | Shared editor reports lifecycle events without swallowing save errors | Yes | Surface save adapter |

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx` | Common TipTap lifecycle and editor props |
| Create | `apps/live-control-ui/src/tiptap/MarkdownEditorToolbar.tsx` | Surface-neutral toolbar projection |
| Create | `apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts` | Import/export and editor-document boundary |
| Create | `apps/live-control-ui/src/tiptap/MarkdownEditor.tsx` | Composed reusable editor component |
| Create | `apps/live-control-ui/src/tiptap/MarkdownEditorCore.test.tsx` | Core lifecycle and tool injection proof |
| Create | `apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.test.ts` | Round-trip and diagnostic proof |
| Modify | `apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.tsx` | Consume shared editor while preserving spike behavior |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx` | Consume shared editor while preserving Plan behavior |

**Bounded discovery exception:** Not applicable — every expected path is
enumerated.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why out of scope |
|---|---|
| `apps/live-control-ui/src/App.tsx` | Build route belongs to BLD-05 |
| `apps/live-control-ui/src/chrome/appChromeConfig.ts` | Build navigation belongs to BLD-05 |
| `apps/live_control_server/services/tiptap_markdown_write.py` | Source target policy belongs to BLD-02 |
| `src/graph_memory/**` | Extraction is a later backend capability |
| `corpus/**` and `evals/**` | No corpus or gold mutation in editor extraction |
| Tables, images, frontmatter, arbitrary HTML | Unsupported-format expansion is a separate decision |

## §6 Implementation contract and conditional matrices

```text
Input:
  Existing TipTap editor configuration, Markdown text, JSON content,
  surface-neutral tool descriptors, and lifecycle callbacks.

Output:
  Reusable editor component plus adapter callbacks that preserve existing
  Plan and Spike observable behavior.

Invariant:
  Common editor behavior is shared; persistence and domain behavior remain
  surface-owned.

Failure behavior:
  Unsupported Markdown → preserve existing diagnostic and caller-visible
  unresolved state; do not silently fabricate content.
  Missing required editor input → fail at the owning component boundary with
  a stable error or disabled state.

Replay / idempotency:
  same Markdown + same adapter → same imported document;
  same JSON export → same semantic Markdown subject to existing serializer
  normalization;
  retry after a failed save → editor remains dirty and save ownership stays
  with the surface adapter.

Trust boundary:
  Verifies: editor schema, adapter callbacks, diagnostics, and lifecycle state.
  Records or trusts without proving: server persistence and graph meaning.
```

### State and fallback matrix

| Observable path | Loading | Exact success | Ordinary miss | Dependency unavailable | Contract failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Editor mount | Render only after valid initial document | Editor ready | Empty document only when caller explicitly supplies it | Surface controls loading state | Report adapter/schema error | Caller reloads source | Re-mount with same adapter |
| Markdown import | Show initializing state | Render imported content and diagnostics | Empty Markdown becomes empty document | Preserve caller loading/error | Do not silently drop unsupported blocks | Mark source dirty if conversion is lossy | Re-import explicit source |
| Save lifecycle | Editor remains usable | Caller clears dirty state | No target is a caller-owned no-op | Caller shows unavailable | Preserve dirty state | Caller handles revision conflict | Caller may retry |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| Editor instance | React key/consumer identity controls lifecycle | Do not reuse state across document identity changes | No |
| Document identity | Adapter owns stable document identity | Shared editor does not infer identity from labels | No |
| Toolbar tool | Stable tool ID supplied by surface | Duplicate IDs are a contract failure | No |

### Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Replay behavior | Compatibility | Rollback |
|---|---|---|---|---|---|
| Import/export | Existing TipTap JSON and semantic Markdown | Preserve existing supported subset and diagnostics | Same input is deterministic | Plan/Spike consumers remain valid | Revert consumer to adapter seam |
| Draft state | Consumer-owned local draft | Shared editor exposes state only | Remount does not duplicate writes | Existing local keys remain consumer-owned | No migration in this PR |

### Predecessor-to-consumer mapping

| Predecessor | Consumer | Transformation | Proof |
|---|---|---|---|
| `PlanSurfaceCanvas` TipTap setup | `MarkdownEditorCore` | Extract common extensions, lifecycle, and callbacks | `MarkdownEditorCore.test.tsx` + Plan tests |
| Spike local Markdown bridge | `MarkdownDocumentAdapter` | Preserve existing converter/serializer calls behind adapter | `MarkdownDocumentAdapter.test.ts` |
| Surface toolbar actions | `MarkdownEditorToolbar` | Inject stable tool descriptors; do not infer Plan tools | Core test |

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command | Expected evidence |
|---|---|---|---|
| Shared editor mounts and exposes lifecycle | React component | `npm test -- --run src/tiptap/MarkdownEditorCore.test.tsx` | Green lifecycle/tool tests |
| Supported Markdown round-trips with diagnostics | Adapter | `npm test -- --run src/tiptap/MarkdownDocumentAdapter.test.ts` | Expected JSON/Markdown and diagnostic assertions |
| Plan behavior remains intact | Plan surface | `npm test -- --run src/planSurface` | Existing Plan tests green |
| Spike behavior remains intact | Spike consumer | `npm run build` plus targeted import/type checks | Build succeeds without Spike compile regressions |
| No scope creep | Git | `git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD` | Only §4 paths |

```bash
cd apps/live-control-ui
npm test -- --run src/tiptap/MarkdownEditorCore.test.tsx
npm test -- --run src/tiptap/MarkdownDocumentAdapter.test.ts
npm test -- --run src/planSurface
npm run typecheck
npm run build
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing surface used: Plan and TipTap bridge spike
Smallest scenario: open each consumer, edit one paragraph, export Markdown
Expected observation: both use the shared editor and preserve existing output
Evidence captured: focused Vitest output and changed-path list
```

## §8 Required handback

1. Base and head SHA.
2. Focused diff stat limited to §4.
3. Exact result of every §7 command.
4. Result provenance.
5. Plan and Spike live proof.
6. Baseline failures, if any, with base/head comparison.
7. Operator waivers; `none` if none.
8. Paths outside §4; `none` or stop report.
9. Stop conditions; `none` if none.
10. Confirmation that BLD-02 and BLD-05 remain successors.
11. Confirmation that this handoff was implemented without compression.

## §9 Acceptance rubric

- [ ] One reusable editor capability is delivered — proved by the focused TipTap tests.
- [ ] Plan and Spike share the common editor boundary — proved by consumer diff inspection and Plan/build verification.
- [ ] Unsupported Markdown diagnostics remain caller-visible — proved by adapter tests.
- [ ] No new persistence or graph contract is introduced — proved by §4 path check and diff inspection.
- [ ] Existing Plan behavior remains green — proved by `npm test -- --run src/planSurface`.
- [ ] No path outside §4 changed — proved by the changed-path command.
- [ ] The named successors remain unimplemented and unclaimed.

## Stop conditions

Stop and report if implementation discovers:

- tables, images, or frontmatter require a new durable representation;
- Plan and Spike cannot share a seam without changing their public behavior;
- a server persistence change is required;
- a new route, navigation item, or graph contract is required.

```text
Stop condition:
Why the current mission cannot absorb it:
New contract discovered:
Affected paths:
Proposed successor slice:
Authority update needed:
```
