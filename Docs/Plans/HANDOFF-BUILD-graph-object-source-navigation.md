---
pr_body_template: |
  ## Handoff pointer
  - Conversation: CON-READY
  - Flow / agent: BUILD
  - Direction: DESIGN → CODE
  - Handoff: `Docs/Plans/HANDOFF-BUILD-graph-object-source-navigation.md`
  - Branch: `agent/con-ready-graph-object-source-navigation`

  ## Verification pointer
  - Base: `be0244ea8f6b7d3cc4dc52fe4b186efe556b31d1`
  - Merged predecessor: PR #567
  - Verification: see §7 and the latest numbered review handback

  The checked-in handoff, cumulative code diff, nano commits, and independently
  rerun verification are the review contract. The PR description is transport
  metadata only. Document sync is a separate operation.
---

# HANDOFF — BUILD: Graph object → original source navigation

**Created:** 2026-08-12.
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-BUILD-graph-object-source-navigation.md`
**Conversation name:** `CON-READY`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**Design agent:** CON-READY steward
**Code agent:** BUILD
**Implementation branch:** `agent/con-ready-graph-object-source-navigation`
**PR title:** `BUILD: open graph evidence in source`
**Base:** `main` at `be0244ea8f6b7d3cc4dc52fe4b186efe556b31d1`
**Merged predecessor:** PR #567 — `INGEST: initialize a new world's graph from reviewed source`
**Roadmap slice:** `CR02C — graph object → relevant source passage navigation`
**Primary CON-READY story:** `CR-U5 — I can follow a world object back to its source`
**Secondary story advanced:** bounded support for `CR-U16 — Navigation is part of the answer`
**Named successor:** `CR03 — Hermes Source Follow-Through` (`CR-U6` / `CR-U7`)

> **Dispatch gate:** Dispatch is prohibited until capability decomposition is complete, one independently useful mission remains, the merge-ready invariant and required evidence survive critique, every expected path is known, required contract matrices are resolved, and every acceptance claim has an owning proof.
>
> This checked-in handoff is the complete authority. The worker must not compress, omit, replace, or rewrite it before implementation. The PR description is only a transport pointer; it cannot substitute for the handoff, code diff, nano-commit story, or verification evidence.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Evidence badge** | A projected graph evidence row carrying durable `evidence_ref_id`, `source_artifact_id`, `source_span_ref_id`, source domain, and open/highlight capability derived from graph evidence. |
| **SourceArtifact A** | The exact admitted source revision named by the evidence badge. For this slice it must be a `worldbuilding` SourceArtifact with workspace-document lineage. |
| **Source span S** | The exact persisted `SourceSpanIndexEntry.source_span_id` named by the evidence badge and bound to A's content digest. |
| **Build document D** | The active `worldbuilding_source` workspace document derived server-side from A's `workspace_document_id`; the browser never chooses D as source authority. |
| **Exact navigation** | D's current saved Markdown digest still equals A's digest; the Build reader may therefore land on S's saved-source line range. |
| **Stale navigation** | D still exists and is the same admitted workspace document, but current saved Markdown no longer equals A. The current document may open, but the old line range must not be presented as exact. |
| **Capability** | One coherent GM-visible behavior: choose admitted graph evidence and reach its original Build source truthfully. |
| **Owning boundary** | The layer where a guarantee becomes true: source-navigation service/route, graph-card evidence interaction, or Build reader landing behavior. |
| **Invariant** | The single property every changed layer and observable path establishes or proves. |
| **Stop condition** | A discovered fact that invalidates this bounded navigation contract and must be reported instead of expanding into historical source storage, arbitrary source browsing, or Hermes source access. |

## Agent flow and nano-commit contract

Use BUILD for the implementation even though the capability crosses a read-only server resolver and Build/Plan/Graph Review presentation seams. The product outcome is source navigation into Build; do not split backend resolution into a second PR merely because it is server code.

Keep nano commits discrete. A strong sequence would tell stories such as:

1. `API: resolve admitted graph evidence to Build source`
2. `UI: preserve source navigation evidence on graph cards`
3. `BUILD: land rich reader on exact source span`
4. `PROOF: cover stale/tampered/hard-reload source navigation`

Do not bundle unrelated cleanup or CR02B correction work.

## Review and doc-sync contract

Formal review numbering begins at `Review Cycle 1` for this PR. Review the cumulative diff against this handoff. A later fix commit does not increment the cycle until another formal review is posted. The checked-in handoff, current code, and independently rerun evidence are authoritative; the PR body is not.

---

# §1 Mission and merge-ready invariant

## 1.1 Current user-visible failure

CR01 and merged PR #567 now let a GM:

```text
Import rich source
→ extract source-backed objects/relationships
→ review them
→ initialize the chosen world's graph
→ open a graph object card
```

But the graph object still cannot perform the ordinary product action promised by its provenance. Plan's current `Inspect source/evidence` action merely opens the card's Details disclosure. The evidence may contain an exact SourceArtifact and source span, but the GM still has to find the source document and passage manually.

That means `CR-U5` remains false.

## 1.2 Mission

> **As a GM inspecting a source-backed world object, I can choose one of its admitted evidence passages and open the corresponding Build source so that I can read the richer original material without manually hunting for the document.**

## 1.3 Independently useful outcome

For a Glass Orchard object such as Hesta:

```text
Hesta graph object
→ Evidence and source
→ [Read source] on one explicit evidence row
→ Build opens Hesta's admitted source document
→ clean saved source opens in Read mode
→ reader lands at/near the cited passage when the bytes are still exact
```

The GM does not need artifact IDs, repository paths, span-index files, or a terminal.

## 1.4 Merge-ready invariant

> **For one graph evidence row naming SourceArtifact A and source span S, DungeonBuddy re-resolves A and S server-side, derives the Build workspace document D only from A's durable workspace lineage, and permits source landing only for that admitted document; when D's current saved Markdown digest still equals A, Build may highlight/scroll to S's exact line range, while source drift, missing or foreign lineage, mismatched document identity, unavailable span, or dirty local edits are surfaced truthfully without applying a stale highlight, discarding local work, mutating graph/source state, parsing a filesystem path from the browser, or granting arbitrary source discovery authority.**

Every change and proof must reduce to this invariant.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every entry is the same evidence A/S → server-derived D → exact-or-stale Build landing operation. |
| What adversarial sequence is most likely to falsify it? | Graph object cites A/S → source D is edited after admission → old evidence link is clicked → UI blindly applies old lines to new bytes. That would visually fabricate provenance. |
| Would §7 detect that failure? | Yes. Route tests force digest drift; Build integration tests require `stale` + no highlight; live dogfood repeats an old evidence link after a saved source change. |
| Which owning boundary is easiest to under-test? | The Build reader line mapping because MDAST positions are body-relative after YAML frontmatter is stripped while SourceSpan line numbers cover the full saved Markdown. A dedicated frontmatter-offset test is mandatory. |
| What fact would force stop/split? | If truthful CR-U5 requires preserving/rendering historical worldbuilding source bytes that are not currently stored immutably, stop. Historical source revision storage is a separate durable contract and may not be invented in this slice. |

---

# §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` + `Docs/Roadmaps/ROADMAP-con-ready.md` |
| Repository rules | Product story beats architecture completion; no hidden Eldyrwild assumption; source stays first-class; provenance must be useful navigation; Hermes may not gain arbitrary source/filesystem access. |
| Base revision | `be0244ea8f6b7d3cc4dc52fe4b186efe556b31d1` |
| Predecessor contract | Merged PR #567 first-world graph initialization + merged PR #565 rich source reader |
| Exact input consumed | One projected `GraphProjectionEvidenceBadge` naming A and optional S; server-owned SourceArtifact registry, SourceSpanIndex, workspace-document snapshot |
| Named successor | `CR03 — Hermes Source Follow-Through` |
| What remains false | Existing-world duplicate/correction UX (CR02B), historical worldbuilding source revision browsing, Hermes source follow-through, relationship-specific provenance landing where no node evidence row exists |
| Explicit non-goals | Source mutation/revert, SourceArtifact migration, arbitrary artifact listing/search, graph publication, asset serving, Playable Layer, new ontology, Hermes/model tool access |

Read these current-base authorities before coding:

1. `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
2. `Docs/Roadmaps/ROADMAP-con-ready.md`
3. `Docs/Plans/HANDOFF-INGEST-first-world-graph-from-reviewed-source.md`
4. `apps/live_control_server/services/source_artifact_registry.py`
5. `src/graph_memory/source_span.py`
6. `src/graph_memory/projection/focus_overlay.py`
7. `src/graph_memory/projection/recap_projection.py`
8. `apps/live-control-ui/src/graphObjectCard/buildGraphObjectCardFromNodeView.ts`
9. `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx`
10. `apps/live-control-ui/src/planSurface/reference/buildPlanGraphObjectActions.ts`
11. `apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx`
12. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewNodeGameCard.tsx`
13. `apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.ts`
14. `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx`
15. `apps/live-control-ui/src/buildSurface/BuildSourceReader.tsx`
16. `apps/live-control-ui/src/markdownReader/MarkdownDocumentReader.tsx`
17. owning tests for the above seams.

## 2.1 Ground truth that constrains the design

Current projection already preserves `source_artifact_id`, `source_span_ref_id`, `can_open_source`, and `can_highlight_span` in `GraphProjectionEvidenceBadge`. Do not create a parallel evidence identity.

Current frontend graph-card adaptation drops the span/open/highlight fields. This slice should preserve them into a plan-safe evidence view model rather than parsing IDs elsewhere.

Current Build navigation already accepts exact `documentId` from the URL and preserves unrelated query parameters when canonicalizing selection. Reuse it; do not build another document router.

Current rich source reader renders exact saved `WorkspaceDocumentSnapshot.markdown` through MDAST and intentionally does not use TipTap for Read mode. Source landing must target this reader, not editor DOM.

Current worldbuilding SourceArtifact records bind document revision + digest but their URI points to the mutable Build source path. The existing resolver explicitly refuses span resolution when current bytes differ from the artifact digest. Therefore this PR must distinguish `exact` from `stale`; it must **not** claim historical source rendering.

---

# §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Plan graph object → evidence | Details show labels/domains; `Inspect source/evidence` only opens details | Each openable worldbuilding evidence row offers explicit `Read source`; click resolves A/S server-side and navigates to Build | Yes | GraphObjectCard + Plan binding + source-navigation client |
| Graph Review node → evidence | Review details/evidence are inspect-only | Source-backed node evidence can invoke the same A/S resolver so #567 dogfood material can reach Build | Yes | GraphReviewNodeGameCard + shared source-navigation client |
| Build arrival, exact bytes | Build opens D but has no source target | Clean non-empty source opens Read and scrolls/highlights the rendered block intersecting S | Yes | BuildSurfaceShell / BuildSourceReader / MarkdownDocumentReader |
| Build hard reload | D reopens; no provenance target exists | A/S query survives; Build re-resolves server authority and repeats exact/stale result | Yes | Build source-navigation binding |
| Current source drift | No source-navigation concept | Open current D with explicit stale warning; never apply old S highlight | Yes | server resolver + Build binding |
| Dirty local draft | Existing Build defaults dirty source to Edit | Preserve dirty draft and Edit default; no discard. Explain that source target refers to saved source; if GM enters Read, highlight only against exact saved snapshot | Yes | BuildSurfaceShell / session authority |
| Wrong `documentId` paired with A/S | Build simply opens requested registered source | Resolver says D; active D mismatch blocks target/highlight and shows truthful mismatch state; no auto-rebinding based on browser claim | Yes | Build binding |
| Foreign/missing S | No path | Fail closed; no fallback to first span or global text search | Yes | source-navigation service |
| Recap/non-worldbuilding A | No path | Refuse Build-document navigation; no generic filesystem source open | Yes | source-navigation service |
| No rendered block intersects exact S | N/A | Source opens, but show `Exact passage could not be highlighted`; never scroll to a guessed paragraph | Yes | Markdown reader / BuildSourceReader |

### Ordered adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| A has evidence S1 and S2 → user clicks S2 | Resolve S2 exactly; never first-win to S1 | component + route test |
| A/S exact → click → Build → hard reload | Same D and same exact target after re-resolution | Build integration test + dogfood |
| A/S admitted → save changed source D → click old evidence | `stale`; current source may open; no old-line highlight | route + Build test + dogfood |
| D has dirty local draft → click evidence into same D | Dirty draft survives; Edit remains default; no automatic save/discard | Build shell test |
| URL `documentId=X` changed while A/S resolve D | Target/highlight blocked as mismatch; no claim that X contains S | Build binding test |
| A + span belonging to B | 4xx contract failure; no fallback | backend adversarial test |
| A is recap artifact | 4xx unsupported-domain result; no repo path exposed | backend test |
| Source has YAML frontmatter before S | Highlight lands on correct body block after full-source→body line translation | Markdown reader test |
| Target is in unsupported/frontmatter-only region | visible no-highlight state; no guessed landing | reader/Build test |
| Navigate repeatedly | read-only and idempotent; graph/source registries and Markdown bytes unchanged | route test + dogfood |

---

# §4 Files in scope (allowlist)

Every production change must appear here.

## 4.1 Backend resolver

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/source_navigation.py` | Public read-only exact/stale navigation response; no filesystem path authority. |
| Create | `apps/live_control_server/services/source_navigation.py` | Re-resolve A/S, derive D from workspace lineage, verify scope/index/digests, classify exact vs stale. |
| Create | `apps/live_control_server/routes/source_navigation.py` | GET resolver endpoint accepting only source artifact ID + source span ID. |
| Modify | `apps/live_control_server/main.py` | Register the read-only route. |
| Create | `tests/test_live_source_navigation_api.py` | Owning contract/adversarial tests. |

## 4.2 Frontend API and shared navigation binding

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/api/types.ts` | Typed resolver response. |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Read-only resolver client. |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | Request/response contract proof. |
| Create | `apps/live-control-ui/src/sourceNavigation/sourceNavigation.ts` | Shared A/S resolve + governed Build href construction and query parsing. |
| Create | `apps/live-control-ui/src/sourceNavigation/sourceNavigation.test.ts` | Identity, URL, and mismatch tests. |

## 4.3 Graph object evidence interaction

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/graphObjectCard/types.ts` | Preserve span/open/highlight capability in evidence view model and optional source-read callback contract. |
| Modify | `apps/live-control-ui/src/graphObjectCard/buildGraphObjectCardFromNodeView.ts` | Map real projected evidence fields; no synthesized/first evidence choice. |
| Modify | `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx` | Render explicit `Read source` per navigable evidence row; keep Details useful. |
| Modify | `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.test.tsx` | Multiple-evidence and non-openable evidence behavior. |
| Modify as needed | `apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.tsx` | Pass source-evidence action callback without embedding source authority in neutral card. |
| Modify as needed | `apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx` | Thread shared source action through resolved graph projection. |
| Modify | `apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx` | Plan entry point uses governed A/S resolver and navigates only from resolved response. |
| Modify | `apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.test.tsx` | Plan click/error behavior. |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewNodeGameCard.tsx` | Graph Review entry uses same evidence resolver for #567/new-world material. |

## 4.4 Build source landing

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx` | Re-resolve A/S on Build arrival, bind result to active D/snapshot, preserve dirty Edit semantics. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx` | Exact/stale/mismatch/dirty/hard-reload composition proof. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSourceReader.tsx` | Target/stale/no-highlight status and reader target props. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSourceReader.test.tsx` | Truthful target/status behavior. |
| Modify | `apps/live-control-ui/src/markdownReader/MarkdownDocumentReader.tsx` | Optional exact full-source line range → rendered block intersection/highlight/scroll, accounting for stripped frontmatter. |
| Modify | `apps/live-control-ui/src/markdownReader/MarkdownDocumentReader.test.tsx` | Source-line, YAML-offset, duplicate/unsupported/no-match behavior. |
| Modify | `apps/live-control-ui/src/buildSurface/buildSurface.css` | Bounded passage highlight/stale status styling only. |

## 4.5 Handoff

| Action | Path | Purpose |
|---|---|---|
| Modify | `Docs/Plans/HANDOFF-BUILD-graph-object-source-navigation.md` | Implementation handback/evidence only if repository process expects it; do not rewrite authority. |

**Bounded discovery exception:**

```text
Directory: apps/live-control-ui/src/ OR tests/
Maximum additional paths: 3
Allowed path kinds: existing test files or existing tiny test/helper registration files only
Decision rule: include only when needed to exercise an already-allowlisted production seam with the repository's real harness. No production source path is authorized by this exception.
```

If another production path is required, stop and reconcile §4 explicitly.

---

# §5 Files and capabilities explicitly out of scope

| Path/layer/capability | Why excluded |
|---|---|
| Worldbuilding SourceArtifact content snapshot/migration | Historical immutable source storage is a separate durable representation and invariant. This PR reports drift instead. |
| SourceArtifact URI semantics / registry migration | Do not change existing artifact persistence to make navigation easier. |
| CR02B existing-world correction | Bind-existing, rename, merge duplicate, add missing object, relationship editing are separate GM actions. |
| Hermes tools/runtime/prompts | CR03 owns model-visible source follow-through and must preserve a stricter admitted-source trust boundary. |
| Arbitrary source-artifact list/search | Navigation begins only from an admitted evidence A/S; no ambient source browsing. |
| Filesystem/path query parameters | Browser may not choose a repo path or line range as authority. |
| Graph ingestion/publication | Navigation is read-only and must not republish graph/source. |
| Markdown editing/revert/history UI | Build authoring remains existing authority. |
| Local source assets/image serving | Separate CR01 successor if re-promoted by dogfood. |
| New graph/evidence schema | Existing evidence badge and SourceSpanIndex are sufficient. |
| Relationship provenance redesign | Only reuse existing evidence identity where available; do not invent new relationship evidence storage. |
| General router/navigation framework | Use existing route/query conventions. |

---

# §6 Implementation contract and conditional matrices

## 6.1 Resolver contract

```text
Input:
  source_artifact_id = A
  source_span_ref_id = S

Server authority:
  SourceArtifact registry record A
  persisted SourceSpanIndex for A
  WorkspaceDocumentSnapshot for A.workspace_document_id

Output:
  schema = dmb_build_source_navigation_v1
  status = exact | stale
  sourceArtifactId = A
  sourceSpanRefId = S
  documentId = server-derived D
  worldId
  campaignId
  artifactDocumentRevision
  currentDocumentRevision
  artifactContentSha256
  currentContentSha256
  startLine
  endLine
  canHighlight = true only for exact
  message / diagnostics

Failure behavior:
  missing A → 404
  A not worldbuilding / no workspace lineage → 422
  missing or foreign S → 404/409 fail closed
  span index digest/identity mismatch → 409/500 integrity failure
  D missing/discarded/not worldbuilding/foreign world-campaign lineage → 409/422
  no fallback to another document/span/path

Replay:
  same A/S + same current D bytes → same semantic exact result
  same A/S + changed current D bytes → stale result

Trust boundary:
  Verifies A, S, D, world/campaign lineage, span index digest, current snapshot digest.
  Never trusts browser path, line numbers, title, campaign label, or document ID as source authority.
```

The endpoint may be named `/api/live/source-navigation` or a similarly scoped current-route name, but the request authority is exactly A+S. Do not accept a path or start/end line request.

## 6.2 Build URL contract

After a successful resolver call, frontend may navigate to:

```text
/build?documentId=<D>&campaign=<campaign>&sourceArtifactId=<A>&sourceSpanRefId=<S>
```

`documentId` is routing identity derived from the server result. It is **not** accepted as proof that A/S belong to D. On Build hard reload, sourceArtifactId/sourceSpanRefId are re-resolved and the returned D must equal the active accepted Build document before target state may become exact/stale.

Do not serialize line numbers into the URL as authority.

## 6.3 Build reader line mapping

SourceSpanIndex lines cover the complete saved Markdown, including leading YAML frontmatter. `MarkdownDocumentReader` parses the body after `stripLeadingYamlFrontmatter`.

The reader must therefore translate body MDAST positions back to full-source line numbers before testing intersection with `[startLine,endLine]`.

A sufficient mapping is conceptually:

```text
fullSourceLine = bodyNode.position.line + countNewlines(leadingFrontmatter)
```

Use the existing frontmatter splitter as authority; do not regex frontmatter independently.

Highlight the smallest stable rendered block(s) available from existing MDAST positions. CR-U5 requires landing near the relevant passage, not character-perfect annotation. Never alter source Markdown to add anchors.

Scroll the first matching block into view once per source target identity, not on every React render.

## 6.4 Dirty draft rule

A source-navigation arrival must not override existing Build authoring safety:

- dirty local draft remains dirty;
- initial mode remains Edit under the existing rule;
- no save/discard/reload is triggered by navigation;
- UI may say the graph target refers to the last saved source;
- when the GM explicitly chooses Read, the saved snapshot is used;
- exact highlight is allowed only if saved snapshot digest equals A's digest;
- unsaved local edits are never represented as part of the cited source.

## 6.5 State/fallback matrix

| Path | Loading | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale | Retry/replay |
|---|---|---|---|---|---|---|---|
| Evidence `Read source` | Disable clicked row / show bounded progress | Navigate to server-derived D+A+S | Row remains usable with error text; no guessed source | Show source-navigation unavailable; card remains | Fail closed | Resolver can return stale and still navigate to current D | Same click re-resolves |
| Build target resolve | Source document may load normally; target pending | `canHighlight=true`; Read lands on S | No highlight; truthful target error | Current source remains usable | No highlight; error | stale banner, `canHighlight=false` | Hard reload re-resolves |
| Reader landing | N/A | Highlight intersecting block and scroll once | Visible `could not highlight exact passage` | N/A | No guessed block | No target supplied to reader | Re-render does not suffix/shift/scroll repeatedly |

There is **no fallback source**. Current D is shown in stale state only because A's durable workspace lineage still identifies D; it is not evidence that old S remains exact.

## 6.6 Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback? |
|---|---|---|---|
| Exact A | Registry lookup only | duplicate/malformed registry is integrity failure | No |
| Exact S | Exact span ID inside A's validated span index | missing/foreign S fails | No |
| D | Derived from A.workspace_document_id, then validated against active workspace record | mismatch fails target application | No |
| Display label/title | Presentation only | never resolves identity | No |
| URL documentId | Route request only; must equal server-derived D before source target applies | mismatch warning/no highlight | No |
| Source edit / rename | Same D may remain valid; digest controls exactness, not title | content drift → stale | No span fallback |

First-win evidence selection is prohibited. If an object has several evidence rows, the GM chooses one row explicitly.

## 6.7 Persistence/replay matrix

| Operation | Durable representation | Round-trip guarantee | Replay | Migration | Reversion |
|---|---|---|---|---|---|
| Source navigation | None newly persisted; URL carries A/S locator + D route identity | Hard reload re-resolves durable authority | idempotent read | none | remove feature; graph/source data untouched |
| Span highlight | ephemeral React/DOM state | same exact A/S + same bytes lands same block | scroll once per target identity | none | no source mutation to undo |

No new persisted format is authorized.

## 6.8 Predecessor-to-consumer mapping

**Grounding source:** current `GraphProjectionEvidenceBadge`, `GraphMemorySourceArtifact`, `SourceSpanIndexEntry`, `WorkspaceDocumentSnapshot` schemas/types on base `be0244...`.

| Predecessor field | Real shape | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| `evidence_ref_id` | required string | evidence row key/display | preserve | card adapter test |
| `source_artifact_id` | required string | resolver A | preserve exactly | adapter + API test |
| `source_span_ref_id` | nullable string | resolver S / Read source eligibility | preserve; no synthesis | adapter test |
| `can_open_source` | bool | whether Read source may be offered | preserve | card test |
| `can_highlight_span` | bool | hint only; server still revalidates S | preserve; never authority | card + route test |
| A.`workspace_document_id` | nullable durable ID | server-derived D | required for this capability | route test |
| A.`content_sha256` | required with workspace lineage | exact/stale comparison | exact equality to current snapshot digest | route test |
| A.`world_id` / `campaign_id` | nullable by general schema | first-class lineage checks for Build worldbuilding source | require coherent current record; no Eldyrwild default | route adversarial test |
| S.`source_span_id` | exact persisted string | exact target identity | equality lookup only | route test |
| S.`start_line` / `end_line` | 1-based ints | reader target range | returned only after A/S validation | frontmatter reader test |
| snapshot.`content_sha256` | exact current saved digest | exact/stale state | compare to A digest | route + Build test |

---

# §7 Evidence required to merge

| Guarantee | Owning boundary | Evidence class | Command/scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| A/S alone determine source authority | server route/service | adversarial contract | `tests/test_live_source_navigation_api.py` | browser path/document/line cannot redirect resolver | any caller-selected path/line accepted |
| foreign/missing span never first-wins | service | adversarial | focused backend tests | 4xx, no fallback | another S chosen |
| world/campaign/document lineage coherent | service | contract | focused backend tests with W != Eldyrwild | exact D for Glass Orchard; foreign lineage rejected | default world/campaign fallback |
| exact vs stale is digest-truthful | service | adversarial | mutate current source after A created | exact before, stale after, same D, no false highlight authority | stale returns `canHighlight=true` |
| graph card preserves real evidence fields | adapter/card | contract | GraphObjectCard/Plan tests | multiple evidence rows remain distinct, explicit Read source per eligible row | first evidence auto-selected |
| Plan and Graph Review use governed resolver | component/workflow | integration | owning component tests | no navigation before successful resolver; errors stay on card | client parses document ID/path from A |
| Build revalidates A/S on arrival | Build shell | integration/adversarial | BuildSurfaceShell tests incl tampered documentId | active D must equal resolved D; hard reload works | target applied to foreign active doc |
| dirty draft is preserved | Build shell | regression/adversarial | dirty session → source target | Edit stays default; draft untouched; saved-source notice | discard/save/reload triggered |
| stale navigation cannot highlight old lines | Build reader | integration | stale resolver result + source snapshot | stale warning; no target passed/applied | old span highlighted |
| full-source line mapping survives frontmatter | Markdown reader | contract | target line after YAML | correct body block highlighted | off-by-frontmatter landing |
| no rendered block → no guessing | Markdown reader | adversarial | frontmatter/unsupported target | visible no-highlight state | unrelated block highlighted |
| navigation is read-only | route/workflow | regression/dogfood | compare source, graph, registry digests before/after | unchanged | any source/graph write |
| frontend/build health | UI | regression | focused vitest + `tsc -b` + `pnpm build` | green | new failure |
| scope hygiene | repo | contract | diff commands | only §4 + allowed exception | unexpected path |

## 7.1 Required backend run

From repository root, at minimum:

```bash
uv run pytest -q \
  tests/test_live_source_navigation_api.py \
  tests/test_source_artifact.py \
  tests/test_source_span_contract.py \
  tests/test_workspace_document_registry.py
```

If the implementation reuses a different owning workspace/source registry test, record the exact file and reason in the handback. Do not drop `test_source_artifact.py` or `test_source_span_contract.py` if their production contracts are consumed.

## 7.2 Required frontend run

From `apps/live-control-ui`:

```bash
pnpm exec vitest run \
  src/api/liveApi.test.ts \
  src/sourceNavigation/sourceNavigation.test.ts \
  src/graphObjectCard/GraphObjectCard.test.tsx \
  src/planSurface/reference/PlanReferenceObjectCard.test.tsx \
  src/buildSurface/BuildSourceReader.test.tsx \
  src/buildSurface/BuildSurfaceShell.test.tsx \
  src/markdownReader/MarkdownDocumentReader.test.tsx
```

Also run the existing owning Graph Review node-card test if one exists or is discovered under the bounded test exception.

Then:

```bash
pnpm exec tsc -b
pnpm build
```

## 7.3 Repo hygiene

```bash
git diff --check
git diff --stat be0244ea8f6b7d3cc4dc52fe4b186efe556b31d1...HEAD -- <§4 paths>
git diff --name-only be0244ea8f6b7d3cc4dc52fe4b186efe556b31d1...HEAD
```

## 7.4 Minimal live / dogfood proof

**Existing surfaces used:** Graph Review or Plan graph object card → Build rich source reader.

**Smallest realistic scenario:** use the already-created Glass Orchard/Hesta source and graph from the CR01/#567 dogfood when available. Do not author a synthetic source whose only purpose is to make span highlighting easy.

Required journey:

1. Open a source-backed Hesta (or equivalent real one-shot) graph object.
2. Expand `Evidence and source`.
3. If multiple evidence rows exist, deliberately choose one non-first row when practical.
4. Click `Read source`.
5. Confirm Build opens the server-derived source document, not Eldyrwild/debug metadata.
6. Confirm clean non-empty source opens in rich Read mode and lands at/near the cited passage.
7. Hard reload the same Build URL and confirm target is revalidated and lands again.
8. Confirm source navigation itself did not alter source bytes, workspace metadata, SourceArtifact registry, span index, or World Graph.
9. Exercise source drift using a normal in-product Build save on the same document after the graph evidence exists.
10. Follow the old graph evidence again.
11. Confirm Build opens the current source with an explicit stale-source message and **does not** mark the old span as exact.
12. If a dirty local draft is practical to retain during navigation, verify it remains intact and Build defaults to Edit rather than destroying work.

No terminal/manual filesystem step may be required for the core exact navigation journey. Developer inspection may be used only to record before/after digests as evidence, not to make the feature work.

## 7.5 Baseline failure protocol

For any required command already failing on base `be0244...`:

1. run/cite the same command or exact failing subset on base and HEAD;
2. state whether HEAD adds/removes/preserves failures;
3. do not call a non-green gate green;
4. request a fresh operator waiver for this PR if the failing row remains an acceptance gate;
5. no waiver from #562/#564/#565/#567 transfers.

---

# §8 Required review handback

The handback must include:

1. Exact PR URL, branch, and head SHA.
2. §1 Mission and merge-ready invariant copied exactly.
3. Cumulative finding ledger from every formal review cycle.
4. Nano-commit list and discrete story for each commit.
5. Base `be0244...` and head SHA.
6. Actual changed paths and focused diff stat.
7. Every §7 command/scenario and exact result.
8. Provenance of each result: author-local, independent local rerun, CI, or manual/dogfood.
9. Baseline failures and base/head comparison.
10. Explicit operator waivers; `none` if none.
11. Paths outside §4; `none` or a stop report.
12. Stop conditions encountered/resolution; `none` if none.
13. Confirmation of exact/stale dogfood behavior and that navigation did not mutate graph/source authority.
14. Successors still false, especially historical immutable source browsing, CR02B correction, and CR03 Hermes follow-through.
15. Confirmation that this authoritative handoff was implemented without compressing or omitting constraints.

---

# §9 Acceptance rubric

- [ ] Exactly one independently useful capability was delivered: graph evidence → governed Build source navigation.
- [ ] A/S are re-resolved server-side and D is derived only from SourceArtifact workspace lineage.
- [ ] No browser-supplied path or line range is source authority.
- [ ] Multiple evidence rows require explicit user choice; no first-win source selection exists.
- [ ] Exact current bytes permit line landing; stale current bytes do not.
- [ ] Build hard reload revalidates A/S rather than trusting prior in-memory state.
- [ ] Dirty local drafts are preserved and never silently represented as cited source truth.
- [ ] YAML frontmatter does not shift the highlighted passage incorrectly.
- [ ] Missing/foreign source/span/document identity fails closed without fallback discovery.
- [ ] Navigation does not mutate source, graph, SourceArtifact, span index, or world registry.
- [ ] Plan/Graph Review product language is human-facing (`Read source`), not artifact/span debugging vocabulary.
- [ ] Required backend/frontend/build/hygiene evidence is recorded or freshly waived by the operator.
- [ ] No production path outside §4 changed without explicit reconciliation.
- [ ] No historical source snapshot system, arbitrary source browser, or Hermes source tool was introduced.
- [ ] Named successor CR03 remains unimplemented and unclaimed.

# Stop conditions

Stop and report rather than expanding if implementation discovers:

- exact CR-U5 requires historical worldbuilding source bytes that are not currently preserved;
- a new durable SourceArtifact content store/migration is necessary;
- evidence badges cannot identify A/S reliably without changing graph/evidence schema;
- Build cannot revalidate A/S without accepting filesystem/path authority from the browser;
- the only feasible source landing requires mutating Markdown to add anchors;
- a second independently useful search/browse/history capability appears;
- Hermes/model source access is required to prove the GM navigation story;
- a required production path is outside §4;
- current `main` or a new open PR has taken ownership of the same source-navigation authority;
- required evidence cannot be produced at the owning boundary;
- base/head failures require an operator waiver before acceptance.

Use the standard stop report:

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
