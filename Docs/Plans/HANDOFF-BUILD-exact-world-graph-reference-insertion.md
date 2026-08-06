---
pr_body_template: |
  ## Handoff pointer
  - Conversation: Build Exact World Graph Reference Insertion
  - Flow / agent: BUILD
  - Direction: DESIGN → CODE
  - Handoff: Docs/Plans/HANDOFF-BUILD-exact-world-graph-reference-insertion.md
  - PR / branch: bld/exact-world-graph-reference-insertion

  ## Verification pointer
  - Base: 9d4f5a3005f87d07147c03d8eee499af3bd57aa3
  - Head: (implementation)
  - Verification: see §7 evidence ledger

  The checked-in handoff, cumulative code diff, nano commits, and independently
  rerun verification are the review contract. The PR description is transport
  metadata only. Document sync is a separate operation.
---

# HANDOFF — Build inserts and reopens one exact World Graph reference

**Created:** 2026-08-06.
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-BUILD-exact-world-graph-reference-insertion.md`
**Conversation name:** `Build Exact World Graph Reference Insertion`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**Design agent:** DungeonBuddy design agent — `Build Exact World Graph Reference Insertion`
**Code agent:** BUILD code agent — use the same exact conversation name
**PR title:** `BUILD: insert exact World Graph reference into Canvas`
**Slice identity:** `BLD-REF-02`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Design-time base:** `9d4f5a3005f87d07147c03d8eee499af3bd57aa3` (main after PR #507 and PR #508)

> **Dispatch gate:** Dispatch is prohibited until the worker has reproduced that current main can search and inspect a World Graph object from Build but cannot insert that object into the active Markdown Canvas and round-trip it as an exact scoped reference. If current main already passes the complete §7 live proof, stop: this mission is invalid or the operator was running stale assets.
>
> This checked-in handoff is the complete implementation authority. Do not compress it into the PR body, rewrite it as a smaller plan, revive the abandoned PR #432/#497 bundle, or substitute an implementation that merely stores a label and resolves against whichever graph head happens to be current.

## Shared vocabulary

| Term | Definition in this slice |
| --- | --- |
| **Build document** | The exact admitted `worldbuilding_source` selected by `/build?documentId=<uuid>` and owned by `MarkdownCanvasSession`. |
| **Exact graph node** | One durable World Graph `nodeId`; labels and aliases are presentation/search inputs only. |
| **Exact graph scope** | The complete verified tuple `{ worldId, campaignId, scopeMode, revisionId }` extracted from the loaded projection snapshot. No field may be synthesized. |
| **Scoped graph chip** | A graph-node Markdown reference carrying one exact node ID plus one complete exact graph scope. |
| **Legacy graph chip** | The already-supported graph-node Markdown reference carrying node ID and label but no stored graph scope. It remains readable and writable without automatic migration. |
| **Partial scope** | Any reference carrying one or more scope fields without all four valid fields. Partial scope is invalid; it is not legacy. |
| **Canvas insertion command** | A neutral document-bound mutation owned by `MarkdownCanvasSession` that inserts one supported Markdown reference through the current private TipTap editor after exact editable admission. |
| **Insertion lease** | The exact document/session/editor authority that must still be live when an insertion invocation executes. |
| **Activation request** | One chip click bound to its exact document, node ID, and stored scope while Build changes or verifies its graph lens. |
| **Route pin** | Build’s existing campaign + `graphRevision` URL lens, used to make the stored scope visible and load it through the one existing Build projection owner. |
| **Current verified lens** | The projection whose request and response identities passed `verifyWorldGraphProjectionResponse`; a loading, stale, mismatched, unavailable, or failed projection is not current authority. |
| **Exact reopen** | Clicking a scoped chip opens the same node ID only after the loaded projection matches all stored scope fields. |
| **Fallback** | Any attempt to substitute current head, a different campaign/revision, a label/alias match, corpus resolution, or arbitrary source data when the exact scoped node cannot be loaded. All such fallbacks are prohibited for scoped chips. |

## Agent flow and nano-commit contract

Use `BUILD` throughout. Keep the implementation in nano commits. Expected story:

1. `test(build): reproduce missing exact reference insertion loop`
2. `feat(graph-reference): persist exact graph scope on reference chips`
3. `feat(canvas): add document-bound reference insertion command`
4. `feat(build): insert and reopen exact scoped graph references`
5. `test(build): prove save reload stale lease and pinned reopen`

The exact count may differ, but each commit must tell one discrete contract or proof story. Do not bundle heading-bar work, rename controls, Statblock tooling, graph performance, presentation polish, or documentation tracker sync.

## Review and doc-sync contract

The reviewer must identify the exact PR/branch/head SHA, inspect the cumulative diff and nano-commit sequence against this handoff, and independently rerun the owning proofs. The PR description is not evidence.

`Backlog.md`, the SI execution plan, architecture status tables, and post-merge completion markers are a separate document-sync operation. This implementation PR may create this handoff but must not opportunistically rewrite adjacent roadmap or tracker documents.

---

## §1 Mission and merge-ready invariant

### Mission

An operator can insert a World Graph object selected through Build’s shared Tool Host into the active Markdown Canvas as an exact scoped chip so that Save, hard reload, and chip activation return to the same durable node at the same verified graph revision.

### Merge-ready invariant

One admitted Build document, one current verified Build projection scope, and one exact selected graph node produce one backward-compatible scoped Markdown reference whose Canvas-owned insertion, durable serialization, reload, and activation remain bound to exact document, node, world, campaign, scope-mode, and revision identities; partial scope, stale leases, mismatched projections, unavailable pins, and ordinary misses fail closed without document mutation or fallback to labels, corpus, another campaign, or current head.

### Pre-dispatch critique

| Question | Answer |
| --- | --- |
| Can one invariant govern every claimed observable path? | **Yes.** Search selection, insertion, serialization, reload, lens transition, and reopen are all stages of one exact-reference round trip. |
| What adversarial sequence is most likely to falsify it? | Insert node A at revision R1 → save → graph head advances to R2 or route changes → hard reload → click chip → implementation resolves A from R2/current lens or by label instead of loading R1. |
| Would the proposed §7 evidence detect that failure? | **Yes, only if** E6/E7 assert the serialized scope, force a different current lens before activation, observe the route pin and exact projection request, and verify the opened card’s node ID and revision. A same-head happy path alone is insufficient. |
| Which owning boundary is easiest to under-test? | The reload/activation boundary: unit tests can prove parsing and resolution while missing that the real Build route never publishes a chip runtime or opens the stored revision. |
| What fact would force this slice to stop or split? | If exact reopen requires a second graph loader, backend/schema change, Plan production import, raw editor exposure, or a new reference syntax not backward-compatible with existing Markdown, stop for architecture review. |

---

## §2 Context, authority, and boundaries

### Re-anchor ledger

| Predecessor | Status | Merge / authority |
| --- | --- | --- |
| MC-01 shared Markdown Canvas — PR #426 | DONE | `7d98074d434a5310d21d4fe645e497789e0a3114` |
| MC-02a neutral graph reference loop — PR #431 | DONE | neutral `graphReference/**`, existing graph-node chip syntax |
| BLD-REF-01 Build search/inspect — PR #506 | DONE | exact Build lens, Find Existing, shared Projection Host |
| Build workspace composition — PR #507 | DONE | merge `19752690ee7a573141925aabcf352043da15bbe0` |
| Workbench Threat publication — PR #508 | DONE | merge/current base `9d4f5a3005f87d07147c03d8eee499af3bd57aa3` |
| World Graph resident-revision optimization — PR #509 | ACTIVE at design time | adjacent performance work; not this capability |

### Authority table

| Field | Required content |
| --- | --- |
| Parent architecture | `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` |
| Sequencing authority | `Docs/Plans/PLAN-surface-interaction-hoist-build-first.md`, SI-04 behavior; its old status table is stale and must not send implementation back to SI-01 |
| Canvas authority | `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`; `MarkdownCanvasSession` owns editor/document mutation |
| Graph authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; projections are read-only exact snapshots |
| Neutral reference predecessor | `Docs/Plans/HANDOFF-pr431-surface-neutral-graph-reference-loop.md` and landed `graphReference/**` |
| Composition predecessor | `Docs/Plans/HANDOFF-BUILD-build-workspace-composition.md` and PR #507 |
| Repository process | `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`, repository rules, docs-relevance-first jumpstart |
| Base revision | `9d4f5a3005f87d07147c03d8eee499af3bd57aa3`; re-anchor immediately before implementation |
| Exact input consumed | Accepted Build document; verified `WorldGraphProjection.snapshot`; exact `GraphReferenceSearchItem.nodeId`; active private TipTap editor owned by the Canvas session |
| Historical donor only | Closed PR #432 and draft PR #497. Mine behavior only; do not merge, rebase onto, bulk cherry-pick, or restore their bundled Build shell/navbar/extraction/candidate-assist design. |
| Named successor | `BUILD: add Canvas heading controls and document rename` |

### What remains false

No graph-node creation/write, no candidate-assisted search, no document library, no Statblock generator in Build, no heading Save/Reload/Discard bar, no rename/light metadata edit, no Threat-card polish, no graph/Hermes latency repair.

### Explicit non-goals

Plan parity as a whole; Plan production refactor; corpus fallback changes; relationship traversal redesign; graph revision retention policy; server projection API changes; automatic migration of legacy chips.

### Known live fixture

PR #508 published a real Threat suitable for E11:

* **Label:** Mireward Latchling
* **Node ID:** `threat:authored:d16d43d376833e38caf46dd19b1dd17f`
* **Campaign:** `longmont-c2`
* **Historical verified revision:** `rev:3413bf6f5044cf2680233f5e37c90dcf`
* **Binding:** `threat-statblock-binding:07ab38b331085b426bb69474`

The node ID and exact projection revision are evidence identities, not display copy. If that historical revision is no longer loadable, do not silently switch the acceptance claim to “current head.” Record the exact retention/runtime failure and obtain an operator decision on whether a newly verified pinned fixture may replace it.

### Read authoritative inputs in this order

1. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
2. `Docs/Plans/PLAN-surface-interaction-hoist-build-first.md` — SI-04 behavior only
3. `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`
4. `Docs/Plans/HANDOFF-pr431-surface-neutral-graph-reference-loop.md`
5. `Docs/Plans/HANDOFF-BUILD-build-workspace-composition.md`
6. Current implementations of:
   * `MarkdownCanvasSession.tsx`
   * `MarkdownCanvas.tsx`
   * `runbookReferences.ts`
   * Markdown import/export
   * `GraphReferenceSearch.tsx`
   * `GraphNodeChipRuntime.tsx`
   * `BuildReferenceCapability.tsx`
   * `BuildReferenceSearchProjection.tsx`
   * `useBuildWorldGraphProjection.ts`
7. Owning tests listed in §4 and §7
8. PR #432/#497 only as historical behavior evidence after current authority is understood

### Re-anchor rule

Before code changes:

```bash
git fetch origin main
git rev-parse origin/main
git merge-base --is-ancestor 9d4f5a3005f87d07147c03d8eee499af3bd57aa3 origin/main
```

If main moved, inspect every intervening change touching:

* `apps/live-control-ui/src/api/liveApi*`
* `apps/live-control-ui/src/worldGraph/**`
* `apps/live-control-ui/src/graphReference/**`
* `apps/live-control-ui/src/tiptap/**`
* `apps/live-control-ui/src/markdownCanvas/**`
* `apps/live-control-ui/src/buildSurface/**`
* `apps/live-control-ui/src/surfaceInteraction/**`
* `apps/live-control-ui/src/agentInteraction/**`

PR #509 may change graph load performance or resident revision authority. Reuse a landed verified projection seam if compatible, but do not absorb cache/residency optimization into this PR. Stop if it changes exact revision availability or response verification semantics materially.

---

## §3 Observable-path and adversarial-sequence inventory

### Observable paths

| Path | Current behavior on base | Required behavior | Same invariant as §1? | Owning boundary |
| --- | --- | --- | --- | --- |
| Build → Tools → Find Existing | Search and View exist; Insert is absent because Build does not supply `onInsert` | Exact result exposes Insert only when the Canvas and verified projection are authorized | Yes | Build context + neutral search projection |
| Insert under ready editable Canvas | No Build insertion path | One invocation inserts one scoped graph chip at the current selection and marks the existing document dirty | Yes | `MarkdownCanvasSession` + TipTap command |
| Insert while loading/conflict/save in flight/editor absent | No path | Insert disabled or fails truthfully; no editor/document mutation | Yes | Canvas admission + Build projection |
| Save inserted chip | No inserted chip to save | Shared Edit Save serializes one canonical scoped Markdown link through existing CAS | Yes | Markdown serializer + Canvas save |
| Hard reload | Existing unscoped chips reload; scope is not persisted | Scoped chip reconstructs all attrs exactly and document reopens clean | Yes | Markdown parser + local/server reconciliation |
| Click scoped chip while Build already has the stored scope | Build has no chip runtime | Resolve exact node ID from the exact current projection and open shared Projection Host | Yes | Build chip runtime + resolver + Projection Host |
| Click scoped chip while Build has another revision/campaign lens | No exact stored scope exists | Push a visible route pin, load through the one existing Build projection owner, verify all scope fields, then open exact node | Yes | Build route/lens + projection loader + pending activation |
| Stored pinned revision unavailable | Not represented | Show truthful unresolved/error state; do not mutate document and do not use head/corpus/label fallback | Yes | Build activation + projection error path |
| Node absent at stored revision | Not represented | Exact miss names node ID/revision; no alias/label rebind | Yes | exact resolver |
| Legacy unscoped graph chip | Resolves by exact node ID under current projection | Preserve existing syntax and current-lens behavior; do not auto-pin or rewrite on unrelated save | Yes | parser/serializer/runtime compatibility |
| Partial scoped chip | Cannot exist in current schema | Treat as invalid; never strip partial fields and reinterpret as legacy | Yes | normalization + parser + node rendering |
| Build document A → B | Search/View/Save leases revoke | A’s retained Insert/click/pending activation cannot mutate B, change B’s route lens, or open A’s projection | Yes | session command + Build lease cleanup |
| Build → Plan → Build | Shared hosts and chip runtime are global/stacked | Build runtime unregisters; Plan behavior stays unchanged; returning binds only current Build document | Yes | runtime provider stack + App route |
| Explicit repeated Insert clicks | Not applicable | Each accepted user invocation inserts once; explicit repeats may intentionally create multiple chips; StrictMode/effect replay must not duplicate one invocation | Yes | event/command boundary |

### Ordered adversarial sequences

| Sequence | Required safe outcome | Owning proof |
| --- | --- | --- |
| Search node A at scope S1 → retain insert callback → switch document A→B → invoke retained callback | No insertion, dirty change, route change, or projection open under B | E3/E8 |
| Search A at S1 → route/lens changes to S2 before Insert click completes | Callback revalidates current item/load key; stale S1 item cannot insert | E4 |
| Insert A at S1 → Save → hard reload while graph head is S2 → click chip | Stored S1 is loaded/verified and A opens from S1; S2 is never substituted | E5/E7/E11 |
| Click scoped chip → route pin begins loading S1 → user changes route to S2 or document B before response | Pending activation is revoked; late S1 response cannot reopen or overwrite current route state | E8 |
| Scoped chip has correct node ID but one missing/duplicate/unknown scope field | Reference is invalid and cannot activate; no legacy downgrade | E2 |
| Scoped chip points to node A but visible label says B | Durable node ID wins; label never changes resolution | E2/E6 |
| Pinned projection responds with wrong campaign/revision/scope | Existing projection verification rejects it; no card opens | E6/E9 |
| Insert occurs immediately before Save | Existing editor update marks dirty before Save capture; serialized scope is included in committed Markdown | E3/E5 |
| Insert is attempted during prepare/commit | Editable admission fails; no mutation is hidden behind the in-flight Save | E3 |
| Legacy chip is loaded and document is saved without editing it | Legacy Markdown remains legacy and semantically stable; no synthetic scope is added | E2/E5 |

---

## §4 Files in scope (allowlist)

Every changed path must appear below or fit the bounded test-only exception. The code agent must report the actual path list and stop on any production path not named here.

### Handoff authority

| Action | Path | Purpose |
| --- | --- | --- |
| Create | `Docs/Plans/HANDOFF-BUILD-exact-world-graph-reference-insertion.md` | Complete design, durable-format, boundary, and verification authority |

### Durable reference representation and neutral graph-reference runtime

| Action | Path | Purpose |
| --- | --- | --- |
| Modify | `apps/live-control-ui/src/tiptap/references/runbookReferences.ts` | Extend graph-node attrs with optional complete exact scope; canonical validation/href behavior; preserve legacy chips |
| Modify | `apps/live-control-ui/src/tiptap/extensions/RunbookReferenceNode.ts` | Retain scoped attrs in the TipTap atom and insertion command |
| Modify | `apps/live-control-ui/src/tiptap/extensions/RunbookReferenceView.tsx` | Activate a graph chip with its full normalized attrs rather than node ID alone |
| Modify | `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts` | Parse legacy and canonical scoped graph-reference Markdown; reject malformed/partial scope |
| Modify | `apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.ts` | Serialize scoped graph references canonically and legacy references unchanged |
| Create | `apps/live-control-ui/src/graphReference/scopedGraphReference.ts` | Neutral conversion/comparison helpers between exact projection scope and flat persisted reference attrs |
| Modify | `apps/live-control-ui/src/graphReference/types.ts` | Add full-reference chip activation seam while retaining current Plan callback compatibility |
| Modify | `apps/live-control-ui/src/graphReference/GraphNodeChipRuntime.tsx` | Publish optional full-reference activation; preserve provider stack and legacy `onSelectNode` behavior |
| Modify | `apps/live-control-ui/src/graphReference/GraphReferenceSearch.tsx` | Support truthful insertion availability/result copy without owning document mutation |
| Modify | `apps/live-control-ui/src/graphReference/index.ts` | Export only the neutral scoped-reference helpers/types needed by consumers |

### Canvas-owned insertion authority

| Action | Path | Purpose |
| --- | --- | --- |
| Modify | `apps/live-control-ui/src/markdownCanvas/markdownCanvasTypes.ts` | Define one neutral reference-insert command/result on the Canvas session; no graph projection imports |
| Modify | `apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.tsx` | Keep the editor private, revalidate editable document authority, and insert through the existing TipTap reference command |

### Build publication, insertion, and exact reopen

| Action | Path | Purpose |
| --- | --- | --- |
| Modify | `apps/live-control-ui/src/buildSurface/reference/useBuildWorldGraphProjection.ts` | Attach the verified projection scope to Build search items only after exact response verification |
| Modify | `apps/live-control-ui/src/buildSurface/reference/buildBuildSurfaceInteractionPublication.ts` | Extend the Build reference binding with insertion availability/invocation while retaining one shared Tool projection |
| Modify | `apps/live-control-ui/src/buildSurface/reference/BuildReferenceSearchProjection.tsx` | Pass exact Insert into neutral search and surface bounded insertion failure state |
| Modify | `apps/live-control-ui/src/buildSurface/reference/BuildReferenceCapability.tsx` | Bind scoped insertion to current document/load key; publish Build chip runtime; route-pin and complete exact pending activation; revoke stale work |

### Owning tests

| Action | Path | Purpose |
| --- | --- | --- |
| Create or Modify | `apps/live-control-ui/src/tiptap/references/runbookReferences.test.ts` | Legacy/scoped validation, canonical query ordering, malformed/partial rejection |
| Modify | `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.test.ts` | Parse canonical scoped Markdown and preserve exact values |
| Modify | `apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.test.ts` | Export canonical scoped Markdown; legacy no-op round trip |
| Modify | `apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.test.tsx` | Editor-private insertion, editable admission, dirty update, stale document rejection |
| Create | `apps/live-control-ui/src/graphReference/scopedGraphReference.test.ts` | Exact scope mapping/comparison and no partial downgrade |
| Create or Modify | `apps/live-control-ui/src/tiptap/extensions/RunbookReferenceView.test.tsx` | Scoped attrs, not node ID alone, cross the NodeView → runtime activation boundary |
| Modify | `apps/live-control-ui/src/graphReference/GraphNodeChipRuntime.test.tsx` | Full attrs reach active provider; unmount restores prior runtime; legacy callback remains |
| Modify | `apps/live-control-ui/src/graphReference/GraphReferenceSearch.test.tsx` | Insert enabled/disabled/error behavior without changing View |
| Modify | `apps/live-control-ui/src/graphReference/resolveGraphReference.test.ts` | Exact ID and scope mismatch/miss remain fail-closed; no label/corpus fallback for scoped chips |
| Modify | `apps/live-control-ui/src/buildSurface/reference/useBuildWorldGraphProjection.test.tsx` | Search items receive the exact verified scope and never receive mismatched/stale scope |
| Modify | `apps/live-control-ui/src/buildSurface/reference/buildBuildSurfaceInteractionPublication.test.ts` | One Build tool projection publishes insertion binding only for admitted coherent state |
| Modify | `apps/live-control-ui/src/buildSurface/reference/BuildReferenceSearchProjection.test.tsx` | Real search row exposes View + Insert and truthful disabled/failure states |
| Modify | `apps/live-control-ui/src/buildSurface/reference/BuildReferenceCapability.test.tsx` | Exact insert, same/different-scope activation, route pin, stale callbacks, delayed projection revocation |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx` | Insert → dirty → shared Save → remount/reload → chip exists and activates exact scope |
| Modify | `apps/live-control-ui/src/App.test.tsx` | Real `/build` route completes shared Tool → Insert → Canvas → Save/reload → Projection loop with singular hosts |

### Bounded discovery exception

* **Directory:** `apps/live-control-ui/src/tiptap/`
* **Maximum additional paths:** 2
* **Allowed path kinds:** `*.test.ts` or `*.test.tsx` only
* **Decision rule:** include only an existing owning test file required to prove the exact TipTap node attr or Markdown round trip when the listed parser/serializer tests cannot mount that boundary without becoming incoherent. Record the path and reason in the handback.

No production path qualifies under bounded discovery.

---

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
| --- | --- |
| `apps/live-control-ui/src/planSurface/**` production | Plan is behavioral precedent, not the shared API. Preserve Plan through neutral compatibility tests; do not import or refactor Plan to make Build work. |
| `apps/live-control-ui/src/surfaceInteraction/**` production | Shared Tool/Edit/Projection hosts are landed predecessors. Build extends its existing binding, not host semantics or DOM ownership. |
| `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx` production | Existing projection/runtime registration is authority; a provider semantic change is a stop/split. |
| `apps/live-control-ui/src/api/**` production | No new backend endpoint or typed API is required. Existing exact projection request is sufficient. |
| `apps/live-control-server/**` and graph-store/kernel paths | No graph write, schema, retention, or projection API change. |
| World Graph resident-cache/performance work from PR #509 | Adjacent optimization has a different invariant. Re-anchor to it if merged; do not absorb it. |
| `BuildSurfacePage.tsx` bare-entry behavior | PR #507 established Canvas-first entry. This slice starts from an admitted document. |
| Build heading Save/Reload/Discard, rename, metadata editing | Named immediate successor after exact reference insertion. |
| Statblock generator or Workbench publication in Build Tool Host | Separate composition/tool-publication capability. PR #508 only supplies a real Threat fixture. |
| Candidate-assisted Find Existing | Separate retrieval/authoring behavior; no auto-seed or candidate state. |
| Graph node creation, connection, merge, or publication | Governed graph-write lane; this slice is read + Markdown reference only. |
| Threat hover/glance presentation redesign | MAGIC-D3 product successor; current chip presentation may remain metadata-heavy. |
| Corpus fallback changes | Scoped graph chips never use corpus fallback; existing non-graph/corpus behavior remains untouched. |
| Automatic upgrade of legacy chips | A migration is a separate durable operation. Legacy syntax must remain stable. |
| Closed PR #432 / draft PR #497 bulk reuse | They bundle preloaded docs, navbar write controls, local checkpoints, extraction inspection, and candidate-assist under stale architecture. |
| Backlog, roadmap, plan-status, or architecture-status edits | Post-merge document sync, not implementation proof. |

---

## §6 Implementation contract and conditional matrices

### Behavioral contract

```text
Input:
  exact admitted Build document/session
  exact verified Build World Graph projection
  exact selected GraphReferenceSearchItem
  private current TipTap editor owned by MarkdownCanvasSession
Output:
  one scoped graph-node reference inserted at the current Canvas selection,
  represented durably in canonical Markdown, reloadable into the same attrs,
  and activatable through the shared Projection Host at the stored scope
Invariant:
  §1 merge-ready invariant, unchanged
Failure behavior:
  no editable admission/editor -> insertion unavailable; no mutation
  stale document/load key/item -> no-op or truthful insertion error; no mutation
  absent/partial/invalid exact scope -> no scoped insert and invalid activation
  scoped revision unavailable/mismatched -> exact unresolved/error; no fallback
  node missing at stored revision -> exact miss; no label/alias/corpus rebind
  route/document replaced during pending activation -> revoke pending request
Replay / idempotency:
  one accepted Insert invocation -> one chip mutation
  explicit second invocation -> a second chip is allowed
  StrictMode/effect replay -> no invocation and no duplicate insertion by itself
  same scoped Markdown -> same normalized attrs and canonical Markdown
  legacy Markdown -> legacy attrs and legacy Markdown, unless the operator explicitly replaces it
Trust boundary:
  Verifies:
    admitted document identity and editable phase
    live private editor presence
    current Build load key/generation
    exact projection snapshot scope
    exact selected node membership
    complete scoped-reference fields
    exact pinned response identity before reopen
  Records or trusts without proving:
    display label and summary from the verified projection
    existing server CAS after Canvas prepare/commit validates it
```

### Durable scoped-reference format

The existing legacy syntax remains valid and unchanged:

```markdown
[Mireward Latchling](#dmb-ref:graph-node:threat:authored:d16d43d376833e38caf46dd19b1dd17f)
```

New Build insertion writes a canonical scoped form:

```markdown
[Mireward Latchling](#dmb-ref:graph-node:threat:authored:d16d43d376833e38caf46dd19b1dd17f?world=eldyrwild&campaign=longmont-c2&scope=campaign&revision=rev%3A3413bf6f5044cf2680233f5e37c90dcf)
```

**Contract:**

* The node ID remains the exact existing `refId`; it is not slugified, lowercased, or replaced by the label.
* Scope query keys are exactly `world`, `campaign`, `scope`, `revision` in that canonical serialization order.
* Values are trimmed and percent-encoded as URL component values. Decoding must reject malformed encoding.
* `scope` is exactly `campaign` or `world`.
* A scoped graph reference is valid only when all four keys occur exactly once with nonempty valid values.
* Unknown or duplicate scope keys make the scoped reference invalid.
* Scope keys are legal only for `kind=ref` + `refType=graph-node`.
* No scope keys means legacy behavior. Some scope keys means invalid **partial scope**, never legacy.
* The serializer canonicalizes valid scoped attrs. It does not synthesize scope for legacy attrs.
* The parser/exporter must preserve opaque case-sensitive IDs and revisions exactly after percent decoding/encoding.
* Visible label is escaped Markdown presentation only and never participates in exact identity.

The in-memory TipTap attrs should remain flat and serializable. Expected semantic fields:

```ts
{
  kind: "ref";
  refType: "graph-node";
  refId: string;
  label: string;
  graphWorldId: string | null;
  graphCampaignId: string | null;
  graphScopeMode: "campaign" | "world" | null;
  graphRevisionId: string | null;
}
```

Exact property names may vary only if the same field-level contract, canonical Markdown, and compatibility proofs remain intact. Do not hide the scope in the label, title text, localStorage-only state, a parallel sidecar, or route history without durable Markdown representation.

### Canvas insertion command

The Canvas session must add one neutral reference mutation, conceptually:

```ts
insertReference(attrs: RunbookReferenceAttrs): Promise<DocumentCommandResult<void>>
```

**Requirements:**

* The Canvas retains the current TipTap `Editor` privately; Build never receives `Editor`, `getEditor`, or arbitrary command-chain access.
* The command uses exact editable admission and invalidates on document replacement.
* The command ID is Canvas-owned and stable, e.g. `document.reference.insert`; Build must not define a duplicate string.
* The command validates supported normalized attrs before mutation.
* `insertMarkdownReference` remains the neutral TipTap mutation helper.
* A successful insertion relies on the existing non-programmatic editor update to persist local state and mark dirty; do not create a second dirty-state store.
* During preparing or committing, editable admission is false and insertion is blocked.
* A stale retained invocation after unmount/document replacement is rejected before calling the editor chain.
* A failed editor command returns a truthful failure; Build may show bounded inline status in the existing Tool projection.

### Build insertion publication

Build’s existing reference binding remains the only Tool projection binding. Extend it with:

* insert availability/reason
* `insertExact(reference)`

**Requirements:**

* Insert is available only when:
  * one exact document is admitted;
  * Canvas editable admission is true;
  * Build projection is ready and coherent for the live load key;
  * the selected item still exists canonically in that projection;
  * exact scope can be extracted from that projection.
* `useBuildWorldGraphProjection` may attach exact scope to each item only after response verification succeeds.
* `GraphReferenceSearch` keeps View available when Insert is disabled.
* Insert does not close/reopen the document, create a graph object, or mount a private toolbar.
* Search insertion receives the item’s scoped `RunbookReferenceAttrs`; the callback must re-resolve the canonical item by exact `refId`, compare the complete stored scope, and revalidate the live load key at invocation time.

### Scoped chip activation and route pin

Build must publish a chip runtime while the exact Build document lease is active. The neutral runtime passes full normalized reference attrs to Build; Plan’s existing node-ID callback remains compatible.

**Activation rules:**

1. Normalize and validate the reference.
2. If legacy unscoped:
   * resolve exact `refId` only against the current verified Build projection;
   * do not label/alias/corpus rebind;
   * do not synthesize or persist a scope.
3. If scoped and current projection scope equals stored scope:
   * resolve exact node ID and open through existing `openGraphReference`.
4. If scoped and current scope differs:
   * verify stored world/campaign/scope can be represented by the existing Build graph request mapping;
   * push a user-visible Build route lens using `campaign` and `graphRevision`, preserving `documentId`;
   * retain one activation request bound to document ID + normalized attrs + exact scope;
   * allow the existing `useBuildWorldGraphProjection` owner to load and verify the pin;
   * open only after loaded scope equals the stored tuple and exact node ID is present.
5. If the projection fails, mismatches, or misses:
   * open/emit a truthful exact unresolved/error state;
   * clear the pending activation;
   * do not retry against head or another source.
6. If the document, route, lease, or requested scope changes before completion:
   * revoke the pending activation;
   * delayed completion is a no-op.

Do not add a hidden second `postWorldGraphProjection` fetch path for chip activation. The one Build lens/projection owner remains authoritative and the URL makes a cross-revision activation observable and reversible with browser Back.

### Commit point

```text
Before commit:
  insertion exists only in the exact document's local TipTap/local-draft state;
  document is dirty; graph state is unchanged
Commit point:
  existing Canvas Markdown prepare/commit succeeds for the exact document/revision
After commit:
  canonical scoped Markdown is durable under the committed workspace revision;
  local state advances through existing receipt/verification behavior
Truthful result after a post-commit failure:
  preserve the committed receipt and scoped Markdown; report verification failure
  through existing Canvas state; never delete/rewrite the chip or claim it unsaved
  solely because a later graph projection cannot load
```

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Find Existing + Insert | Search loading; Insert absent/disabled | Canonical item + exact scope + editable Canvas inserts | Zero results explicit | Graph unavailable; View/Insert unavailable truthfully | Projection mismatch → error, no insert | Old load-key item no-op | Reopen Tool after current projection is ready |
| Canvas insertion | Document loading/noninteractive → blocked | One atom inserted and dirty | Editor command returns false → bounded error | Editor absent → blocked | Invalid attrs/admission → blocked | Old document command rejected | Explicit click after current session is ready |
| Save/reload | Existing Save phases | Canonical scoped Markdown persists and reloads clean | N/A | Existing save error semantics | CAS/digest conflict remains conflict | Old document Save no-op | Existing reload/discard/Save behavior |
| Scoped chip activation | Pending exact route pin/load | Exact stored scope + node opens | Exact node missing → unresolved | Pinned revision unavailable → error/unresolved | Wrong response scope/revision → error | Pending request revoked | User may click again after dependency recovers |
| Legacy chip activation | Current projection loading → defer/error | Exact node ID in current verified lens opens | Exact miss; no label fallback | Graph unavailable → unresolved | Conflicting identity → error | Old runtime no-op | Reclick under current verified lens |
| Partial/invalid chip | N/A | Never success | N/A | N/A | Render invalid / activation blocked | N/A | Requires explicit operator correction, not automatic migration |

**Fallback audit:**

* Scoped graph chips: no fallback.
* Legacy graph chips: current verified projection only, exact node ID only.
* Non-graph/corpus reference behavior: unchanged and outside this slice.
* Relationship traversal from an already opened exact card: existing behavior, using the currently pinned projection.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
| --- | --- | --- | --- |
| Scoped node ID | Exact `refId` must equal a node ID in the exact stored projection | No first-win; miss is unresolved | No |
| Stored world ID | Must equal verified projection snapshot world | Mismatch is error | No |
| Stored campaign ID | Must equal verified projection/request campaign | Mismatch is error | No |
| Stored scope mode | Exact enum and equal to verified response | Mismatch is error | No |
| Stored revision ID | Exact opaque ID and equal to verified response revision | Mismatch/unavailable is error | No current-head substitution |
| Label/alias | Display/search only | Never resolves a scoped chip | No |
| Legacy graph chip | Exact node ID under current verified lens | Miss remains miss | No label/corpus fallback |
| Partial scope | Invalid durable reference | Never interpreted as legacy | No |
| Document identity | Canvas route/session/record IDs must match | Mismatch blocks insertion and activation | No |
| Load key/generation | Callback must match current coherent projection | Mismatch/stale callback no-op | No |
| Rename/deletion/rebind | Stored node ID remains authority; label may become stale | Missing node is unresolved | No automatic rebind |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
| --- | --- | --- | --- | --- | --- |
| Insert scoped chip | Canonical Markdown link with exact node ID + four scope query fields | Parser recreates identical semantic attrs; serializer returns canonical equivalent | One accepted invocation inserts once; explicit repeats allowed | New parser accepts old and new; no auto-migration | Undo/editor deletion before Save; normal document revision history after Save |
| Save document | Existing workspace Markdown revision/content digest | Scoped chip survives hard reload in same document | Existing CAS rules | No workspace schema change | Existing conflict/reload/discard controls |
| Load legacy chip | Existing no-query graph-node link | Remains legacy after no-op save | No synthetic scope | Fully supported | Operator may explicitly replace with a newly inserted scoped chip |
| Activate scoped chip | URL route pin + transient pending request; no new persistent UI state | Stored Markdown remains sole long-lived scope authority | One pending activation per current click/document; stale completion ignored | No localStorage migration | Browser Back restores prior lens; closing projection does not alter document |
| Graph projection | Existing read-only API response | Response verified against request | Existing request generation rules | No backend/schema change | Route/lens change or retry |

### D. Predecessor-to-consumer mapping

Grounding sources: current canonical TypeScript contracts at base `9d4f5a30…`, exact PR #508 Threat identity, and existing Build projection verification.

| Predecessor field / outcome | Real shape and optionality | Consumer field / behavior | Transformation | Proof fixture/test |
| --- | --- | --- | --- | --- |
| `WorldGraphProjection.snapshot.worldId` | required string in verified response | `graphWorldId` | trim; no synthesis | projection + scoped helper tests |
| `snapshot.campaignId` | required string | `graphCampaignId` | trim; exact | projection tests |
| `snapshot.scopeMode` | `campaign` or `world` | `graphScopeMode` | exact enum | parser/helper tests |
| `snapshot.revisionId` | opaque required string | `graphRevisionId` | trim; preserve case/content; percent encode in Markdown | serializer/parser tests |
| `GraphReferenceSearchItem.nodeId` | exact durable graph node ID | `RunbookReferenceAttrs.refId` | no slug/label mapping | capability test with Latchling-shaped ID |
| Search item label | presentation string | `label` | normalized display only | serializer test |
| `referenceFromGraphNode(node)` | legacy graph-node attrs | scoped attrs | add verified scope through neutral helper | scoped helper test |
| `MarkdownCanvasSession.lookupAdmission("editable")` | exact result/failure code | Insert availability | no Build-local phase reconstruction | Canvas + capability tests |
| private TipTap `Editor` | nullable current editor | neutral insert command | stored only in Canvas session; never exported | Canvas test |
| `insertMarkdownReference` | boolean editor-chain result | mutation success/failure | focus + insert existing atom | existing helper + session test |
| Build loadKey / generation | structured current projection identity | callback/pending activation authority | exact equality; stale no-op | capability adversarial tests |
| route `campaign`, `graphRevision` | existing Build lens inputs | exact scoped activation | push visible pin; preserve document ID | App/capability tests |
| `verifyWorldGraphProjectionResponse` | null on exact verified response; message on mismatch | activation gate | reuse unchanged | projection mismatch tests |
| `openGraphReference` | shared Projection Host action | exact object open | pass resolved node + exact graph scope | App/capability test |
| PR #508 Latchling node | exact node ID and historical revision | E11 dogfood target | search by label, assert ID, insert exact scope | manual evidence |

---

## §7 Evidence required to merge

Every result must state provenance: author-local, independently rerun local, CI, or operator manual/dogfood.

| ID | Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Merge-blocking stop condition |
| --- | --- | --- | --- | --- | --- | --- |
| E0 | The insertion gap exists on the implementation base | built current main + source | baseline/manual | Open real Build, search/view an object, inspect Tool row | View exists; Insert absent; no scoped Markdown support | Base already completes E11, making mission invalid |
| E1 | Scoped reference has one canonical durable representation | reference normalization + parser/exporter | contract/round-trip | focused reference + Markdown tests | exact attrs → canonical Markdown → identical attrs; opaque IDs preserved | lossy scope, unstable serialization, or unsafe parser acceptance |
| E2 | Legacy compatibility and malformed fail-closed behavior | parser/normalizer/node | adversarial/compatibility | legacy, complete, partial, duplicate-key, unknown-key, bad encoding, non-graph scope cases | legacy unchanged; complete valid; malformed invalid; no partial downgrade | existing chip rewrite/breakage or partial treated as legacy |
| E3 | Canvas alone owns insertion mutation | `MarkdownCanvasSession` | contract/adversarial | mount session/editor; insert under ready/loading/saving/doc replacement | one ready insertion; dirty update; all invalid/stale states no editor-chain call | raw editor exposed, duplicate local store, stale mutation, or hidden insert during Save |
| E4 | Build Insert is bound to exact live item/scope/load key | Build capability + search projection | integration/adversarial | ready projection → Insert; then retained item after lens change | exact scoped attrs inserted once; stale item no-op | label-derived ID, missing scope, or stale insertion |
| E5 | Insert → Save → hard reload preserves chip and clean state | Build page + Canvas + parser/serializer | integration/round-trip | insert, shared Edit Save, remount/reload exact document | committed canonical Markdown; chip present; status clean | chip lost, scope lost, duplicate chip, or false dirty reload |
| E6 | Same-scope chip opens exact object | Build chip runtime + resolver + shared Projection Host | integration | click scoped chip while exact projection already ready | exact node ID/card and graph scope open; no route change required | label/corpus resolution or missing exact scope |
| E7 | Different-scope chip pins and reopens exact revision | route/lens/projection/capability | adversarial integration | load document under S2; click chip stored at S1; resolve S1 response | URL pins S1; one existing loader request; verified S1; exact node opens | hidden second loader, current-head substitution, or open before verification |
| E8 | Stale document/route/pending activation cannot leak | Build lease + runtime provider | adversarial | A click pending → B doc/route/unmount → delayed A resolve | no route rewrite, Canvas mutation, stale card, or resurrected runtime | any A effect under B |
| E9 | Failure states are truthful and fallback-free | parser + projection verification + resolver | failure injection | missing pin, wrong response scope, missing node, graph unavailable | exact error/unresolved; document intact; no head/label/corpus retry | fallback or document mutation |
| E10 | Plan and shared hosts remain compatible/singular | neutral runtime + real App | regression/integration | focused Plan/runtime tests; Build→Plan→Build | Plan chip behavior unchanged; one Tool/Edit/Agent/Projection host | Plan production edits required or duplicate/global stale runtime |
| E11 | Real operator loop works with a published Threat | built app + real backend/store | operator dogfood | scenario below with Mireward Latchling | exact scoped chip survives Save/reload and reopens exact pinned Threat | developer harness, hidden IDs required for operation, wrong revision, or failed round trip |
| E12 | Package and allowlist remain clean | package/diff | build/inspection | typecheck, build, diff commands | pass; only §4 paths | unapproved path or production build failure |

### Required commands

Run from repository root unless stated:

```bash
git fetch origin main
git rev-parse origin/main
git status --short
git diff --check
git diff --name-only <BASE>...HEAD
git diff --stat <BASE>...HEAD -- \
  Docs/Plans/HANDOFF-BUILD-exact-world-graph-reference-insertion.md \
  apps/live-control-ui/src/tiptap/references \
  apps/live-control-ui/src/tiptap/extensions/RunbookReferenceNode.ts \
  apps/live-control-ui/src/tiptap/extensions/RunbookReferenceView.tsx \
  apps/live-control-ui/src/tiptap/markdown \
  apps/live-control-ui/src/markdownCanvas \
  apps/live-control-ui/src/graphReference \
  apps/live-control-ui/src/buildSurface/reference \
  apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx \
  apps/live-control-ui/src/App.test.tsx

cd apps/live-control-ui
npm test -- --run \
  src/tiptap/references/runbookReferences.test.ts \
  src/tiptap/markdown/markdownToTiptap.test.ts \
  src/tiptap/markdown/calloutMarkdown.test.ts \
  src/tiptap/extensions/RunbookReferenceView.test.tsx \
  src/markdownCanvas/MarkdownCanvasSession.test.tsx \
  src/graphReference/insertMarkdownReference.test.ts \
  src/graphReference/scopedGraphReference.test.ts \
  src/graphReference/GraphReferenceSearch.test.tsx \
  src/graphReference/GraphNodeChipRuntime.test.tsx \
  src/graphReference/resolveGraphReference.test.ts \
  src/buildSurface/reference/useBuildWorldGraphProjection.test.tsx \
  src/buildSurface/reference/buildBuildSurfaceInteractionPublication.test.ts \
  src/buildSurface/reference/BuildReferenceSearchProjection.test.tsx \
  src/buildSurface/reference/BuildReferenceCapability.test.tsx \
  src/buildSurface/BuildSurfacePage.test.tsx \
  src/App.test.tsx
npm run typecheck
npm run build
npm run preview -- --host 0.0.0.0
```

Also rerun the existing focused predecessor sets if any neutral contract changes:

```bash
npm test -- --run \
  src/planSurface/components/PlanSurfaceCanvas.test.tsx \
  src/planSurface/PlanSurfaceShell.test.tsx \
  src/surfaceInteraction/toolHost \
  src/surfaceInteraction/editHost \
  src/agentInteraction/AgentInteractionProvider.test.tsx
```

If an exact listed test file does not exist on the re-anchored base, use its current owning equivalent and record the substitution. Do not create an unrelated test shell solely to make the command text pass.

### Minimal live / dogfood proof (E11)

**Existing surface used:** real Command Board → Build, shared Tool/Edit/Projection hosts, real live-control backend, real World Graph store.

**Smallest realistic scenario:**

1. Run the re-anchored backend and built preview where possible.
2. From Command Board, click Build; choose `longmont-c2` only if no safe context exists.
3. Confirm one Markdown Canvas is admitted and editable.
4. Open Tools → Find existing object.
5. Search **Mireward Latchling**.
6. Confirm the selected row’s exact node ID is `threat:authored:d16d43d376833e38caf46dd19b1dd17f` and record the loaded exact scope.
7. Use View once to prove the current exact object, then close it.
8. Place the caret in the Canvas and choose Insert chip.
9. Confirm one visible graph chip appears and the document becomes dirty.
10. Open shared Edit → Save; wait for a committed/clean state.
11. Capture the committed Markdown reference or a safe parsed-attrs report showing exact node ID + four scope fields. Do not dump unrelated corpus content.
12. Change the current Build graph lens away from the chip’s stored revision, or reload the document under current-head mode.
13. Hard reload the exact document URL; confirm the chip survives and the document is clean.
14. Click the chip.
15. Confirm Build visibly pins/loads the chip’s stored campaign and revision through the existing projection path.
16. Confirm the shared Projection Host opens Mireward Latchling with the same exact node ID and stored revision.
17. Navigate Build → Plan → back to the exact Build document; confirm singular hosts and no stale projection/runtime.

**Evidence captured:**

* base and execution head SHA;
* document ID;
* before/after workspace revision and clean status;
* canonical scoped reference with safe IDs only;
* exact node ID;
* stored and loaded `{worldId, campaignId, scopeMode, revisionId}`;
* number of projection requests if observable;
* screenshots or concise observations of search row, chip, committed status, pinned lens, and exact card;
* whether dev server or built preview was used;
* exact failure and route state if any.

The operator must not paste a hidden node ID or revision into product state to make Insert or reopen work. Inspecting developer tooling after the interaction to record evidence is allowed.

### Baseline failure protocol

For any required command already failing on base:

1. Run the same command on base and head.
2. Record the exact base failure and whether head adds another failure.
3. Do not call the gate green.
4. Obtain an explicit operator waiver if that command remains an acceptance gate.
5. Never use PR #509 or another active branch’s known failure as permission to weaken exact-reference proofs.

---

## §8 Required review handback

The review handback must include:

1. Exact PR URL or branch/head SHA; PR number is optional transport metadata.
2. §1 Mission and merge-ready invariant copied exactly.
3. Re-anchored base SHA and intervening-main drift review, including PR #509 disposition.
4. E0 reproduction ledger.
5. Nano-commit list and the discrete contract/proof story for each commit.
6. Actual changed paths and focused diff stat limited to §4.
7. The complete §7 evidence ledger with produced result and provenance.
8. Canonical scoped Markdown example produced by tests and live proof.
9. Compatibility results for legacy, complete scoped, partial, duplicate-key, unknown-key, and malformed-encoding references.
10. Proof that Canvas does not expose raw Editor authority to Build.
11. Proof that insertion is bound to exact document and live projection load key.
12. Proof that different-scope activation uses the existing Build projection owner and visible route pin, not a second loader.
13. Exact stale document/route/pending-activation results.
14. Plan/shared-host regression results.
15. E11 live evidence with safe exact identities and revision.
16. Baseline failures and base/head comparison.
17. Operator waivers; `none` when none exist.
18. Paths outside §4; `none` or stop report.
19. Stop conditions encountered and resolution; `none` when none exist.
20. Confirmation that PR #432/#497 was not used as a merge base or bulk cherry-pick source.
21. Confirmation that no backend, graph write, Plan production, or host production path changed.
22. Named successor capabilities still false.
23. Confirmation that this handoff was implemented without compressed or omitted constraints.

---

## §9 Acceptance rubric

The reviewer accepts only when every item is true:

1. One exact scoped-reference round-trip capability was delivered — proved by E1–E7 and E11.
2. The real Build Tool projection exposes Insert only under exact current authority — proved by E4 and E11.
3. Canvas owns the editor and insertion command; Build never receives arbitrary editor authority — proved by E3 and diff inspection.
4. One accepted insertion creates exactly one chip and marks the exact current document dirty — proved by E3/E4.
5. Scoped Markdown carries exact node/world/campaign/scope/revision identities canonically — proved by E1/E2.
6. Existing legacy references remain readable/writable without automatic migration — proved by E2/E5.
7. Partial, malformed, or conflicting scope fails closed and never degrades to legacy — proved by E2/E9.
8. Shared Edit Save and hard reload preserve the chip and return clean — proved by E5/E11.
9. Same-scope activation opens the exact node — proved by E6.
10. Different-scope activation visibly pins and verifies the stored revision before open — proved by E7/E11.
11. No scoped activation falls back to current head, another campaign, label/alias, corpus, or arbitrary sources — proved by E7/E9.
12. Document/route/runtime replacement revokes stale insertion and activation — proved by E8.
13. Build uses one existing projection owner; no hidden second graph load path was added — proved by E7 and diff inspection.
14. Plan behavior and shared host singularity remain intact — proved by E10.
15. The real Mireward Latchling loop passes without a developer harness — proved by E11.
16. Current package typecheck/build pass or exact base/head failures have an explicit waiver — proved by E12.
17. No path outside §4 changed — proved by changed-path inspection.
18. No backend, graph write, Plan production, or host production contract was changed.
19. Heading/rename, Statblock Tool publication, candidate-assist, document library, presentation polish, and performance work remain false.

### Stop conditions

Stop and report rather than expanding if implementation discovers:

1. **Current main already passes E11.** Report stale deployment/operator-path mismatch; do not create redundant code.
2. **The durable scope cannot be represented backward-compatibly in existing Markdown links.** Propose a dedicated reference-format design/migration slice.
3. **Exact activation requires a second graph loader or backend route.** Report the missing neutral projection-navigation contract; do not hide a parallel fetch in Build.
4. **The exact pinned revision cannot be requested or verified through the existing Build projection path.** Report graph retention/runtime authority conflict and its effect on the mission.
5. **Canvas must expose raw TipTap Editor or arbitrary command-chain access to Build.** Stop for Canvas mutation-interface architecture review.
6. **Insertion requires changing shared Tool/Edit/Projection Host production semantics.** Name the host invariant failure and split.
7. **Plan production code must change to preserve compatibility.** The neutral contract is not backward-compatible; stop and redesign it.
8. **A graph node/edge/attribute write or Workbench publication path appears necessary.** This slice is reference insertion only.
9. **A legacy-chip migration is required.** Migration is a separate durable capability.
10. **Candidate-assisted search, extraction inspector, navbar controls, local checkpointing, rename, document library, Statblock tooling, or presentation polish enters the diff.** Split it.
11. **PR #432/#497 is proposed as implementation base or bulk donor.** Stop; map only one behavior to current contracts.
12. **PR #509 or later main changes exact projection request/verification semantics materially.** Re-anchor and revise this handoff before code proceeds.
13. **A production path outside §4 is required.** Produce a stop report; do not silently expand.
14. **E11 can pass only by manually injecting IDs, storage, API calls, or a test-only fixture into the product flow.** The product capability is still missing.
15. **Any scoped-reference miss falls back to label, corpus, current head, or another campaign.** This violates the central invariant and blocks merge.

Use this stop-report shape:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```

### Completion checklist for dispatch

* [ ] Re-anchor SHA recorded.
* [ ] E0 reproduced on the re-anchored base.
* [ ] PR #509/intervening-main overlap assessed.
* [ ] One exact invariant copied into the code-agent task.
* [ ] Durable scoped syntax accepted as part of this one capability.
* [ ] Legacy/partial compatibility rules understood.
* [ ] Exact allowlist copied without globs.
* [ ] No Plan/host/backend production path authorized.
* [ ] E11 environment and Mireward Latchling fixture available or exact blocker recorded.
* [ ] Code agent uses conversation name `Build Exact World Graph Reference Insertion`.
