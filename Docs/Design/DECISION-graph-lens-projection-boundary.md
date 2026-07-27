# DECISION — Graph lens projection boundary

**Created:** 2026-07-25
**Status:** ACCEPTED — governs projection layering from the mention-linker hoist forward.
**Supersedes:** nothing. **Superseded by:** nothing.
**Authority for:** completed graph-lens hygiene slices (PR #414 / #416 / #423 / #427 handoffs under `Docs/Plans/archive/2026-07-26/graph-lens-projection-handoffs/`), PR380B (Recap/Ingest UI migration), and any future surface that renders prose beside World Graph nodes.

> **Numbering lesson (2026-07-25):** Do not name successor slices by guessed GitHub PR numbers in authority docs. Use content slugs. Planned `#413` collided with an unrelated open PR; the hoist landed as `#414`. Archive rename to `HANDOFF-pr414-…` completed 2026-07-26.
>
> **Doc-sync (2026-07-26):** PR #416 merged (`6410e047`). Sequencing table and archived handoffs updated in the same batch so re-anchors do not still say “dispatched.”
>
> **Doc-sync (2026-07-26, later):** PR #423 merged (`eb2d40ba`). `migrate-union-mention-path` archived; `normalize-union-direction-vocabulary` dispatched via `Docs/Plans/HANDOFF-normalize-union-direction-vocabulary.md`.
>
> **Doc-sync (2026-07-26, after #427):** PR #427 merged (`7a024363`). `normalize-union-direction-vocabulary` archived; graph-lens hygiene sequencing complete; next product gate is PR380B.

## Context

PR #412 (PR380A, merged `7a22e6c8aff4c8903d517538739e58de73778d23`) landed the revision-pinned recap projection contract. It took five REQUEST_CHANGES rounds, and every one of them was about CommonMark parsing — shortcut reference links, nested link labels, case-insensitive autolink schemes, unindented and multiline reference titles, and angle-bracket destinations containing spaces. None of them were about recaps.

That is the signal this decision responds to. Reading `src/graph_memory/projection/world_recap_projection.py` (744 lines) by responsibility:

| Region | Lines | What it actually is |
|---|---:|---|
| CommonMark scanner + mention splicer | ~470 (63%) | A general capability: given Markdown and node identities, splice `dmb-node:` links without corrupting existing Markdown |
| `WorldGraphRecap*` models + `_adapt_*` functions | ~190 (26%) | A hand-copied restatement of the `WorldGraphProjection*` models |
| Trust boundary strings, recap source pairing | ~40 (5%) | Genuinely recap-specific |

Three further observations grounded the decision:

1. **`dmb-node:` is already a cross-surface protocol on the consumer side.** The Plan surface parses it in `graphAwareReferenceResolver.ts` (`parseGraphNodeLocator`, `buildWorldGraphNodeIndex`), `resolvePlanRelationshipTarget.ts`, `markdownToTiptap.ts`, `PlanSurfaceCanvas.tsx`, and `GraphReviewProjectionLane.tsx`. Notably `buildWorldGraphNodeIndex` takes the *generic* `WorldGraphProjection`, not the recap fork. The UI already treats producing-and-consuming `dmb-node:` as universal; only the backend *producer* is filed under a recap-specific name.

2. **A second, unprotected mention implementation already exists.** `recap_projection.py::_project_markdown_mentions` (the union-supergraph preview path) performs the same alias-regex match and calls the same `splice_node_link_spans`, but a search for protected-range handling in that module returns nothing. On a static read it appears to carry none of the five protections PR #412 added. The "what if a second consumer duplicates this" risk is not hypothetical; it has already happened and is running in production.

3. **`splice_node_link_spans` is already shared by three call sites** (`world_recap_projection.py`, `graph_gold_review.py`, `graph_authoring_overlay_projection.py`) while living in a recap-named module. Its own docstring calls it "the single place that turns a located mention span into the literal markdown link text" — but the *protection* that must run before it is not similarly shared.

4. **The hand-written adapters have already drifted once.** Review of PR #412 caught `source_excerpt_is_full_paragraph` and the highlight spans missing from the recap adaptation. Every field added to the world models must be manually re-copied into the recap models forever, with a reviewer as the only check.

## Decision

### 1. Markdown mention linking is a surface-neutral capability with its own module

The CommonMark protection scanner and mention splicer move to `src/graph_memory/projection/markdown_mentions.py`. Its public signature takes **text plus identity bindings** and returns **neutral mentions plus neutral diagnostics**. No graph view type, no recap type, and no surface vocabulary may appear in that signature:

```python
def project_markdown_mentions(
    markdown: str,
    bindings: Sequence[MentionBinding],   # (surface, node_id) pairs
) -> tuple[str, list[MarkdownMention], list[MarkdownMentionDiagnostic]]:
```

Ambiguity resolution (a surface owned by more than one node is left unlinked and reported) belongs **inside** this module, because it is a property of text-to-identity binding, not of recaps.

Surface-specific entry points become thin adapters that build bindings and map neutral results into their own wire types.

### 2. Surface response schemas may stay distinct; presentation views must be derived, not hand-copied

A per-endpoint wire schema is legitimate — it lets the recap contract version independently of the generic projection contract at an HTTP boundary. That is retained.

What is not retained is the parallel hand-written class tree. A surface presentation view must be **derived** from the generic `WorldGraphProjection*` view (field projection or generated narrowing) such that adding a field to the generic view cannot silently fail to reach the surface view. The drift found in PR #412 review must become structurally impossible rather than reviewer-detected.

### 3. Relationship direction vocabulary is normalized once, at the kernel/world projection boundary

The kernel emits `outbound` / `inbound`; surfaces want `outgoing` / `incoming`; `adapt_relationship_direction` translates per-surface. This is a naming divergence, not a projection concern. It is fixed once where `WorldGraphProjection` is produced, and per-surface translation is deleted.

### 4. The general shape is a graph lens over a document

A projection is: **exact snapshot identity + node/edge views + focus overlay + trust boundary + optionally a prose body with mentions spliced in.** The document is the only variable.

- Recap = that lens with a canonical normalized recap as the document.
- Session Prep = the same lens with a prep doc.
- Hermes answers = the same lens with answer text.
- Graph Review = the same lens with no document plus an authoring overlay.

`focus_overlay_from_world` is already generic to "any session-focused lens" and merely lives in the recap file today. Naming this shape is the point of this record; mechanically collapsing all four surfaces onto one implementation is **not** authorized by it.

## Sequencing

| Slice (content slug) | Content | Status |
|---|---|---|
| `hoist-graph-mention-linker` | Hoist the linker to `markdown_mentions.py`, parameterized by bindings, byte-for-byte identical output | **merged** as GitHub PR #414 (`5c19d433`) — archived `HANDOFF-pr414-hoist-graph-mention-linker.md` |
| `derive-recap-views-normalize-direction` | Derive recap views from generic views; normalize `direction` at the kernel boundary | **merged** as GitHub PR #416 (`6410e047`) — archived `HANDOFF-pr416-derive-recap-views-normalize-direction.md` |
| `migrate-union-mention-path` | Migrate `recap_projection._project_markdown_mentions` onto the hoisted linker, closing the unprotected second implementation | **merged** as GitHub PR #423 (`eb2d40ba`) — archived `HANDOFF-pr420-migrate-union-mention-path.md` |
| `normalize-union-direction-vocabulary` | Close the Union-compatible snake_case direction vocabulary at the shared adjacency wire-model boundary | **merged** as GitHub PR #427 (`7a024363`) — archived `HANDOFF-pr427-normalize-union-direction-vocabulary.md` |
| PR380B | Recap/Ingest UI migration; consumes the World Graph recap route + hoisted linker | **unblocked** — graph-lens hygiene complete; product migration not started |

The hoist was deliberately a pure move with a characterization-test invariant. `derive-recap-views-normalize-direction` was the genuine contract change: direct generic-model reuse for recap nested views plus closed `outgoing`/`incoming`/`related` vocabulary at the World Graph boundary. `migrate-union-mention-path` closed the unprotected second mention implementation. `normalize-union-direction-vocabulary` closed the dual Union wire-direction contract. All four hygiene slices are now on `main`.

### Next gate

**No graph-lens hygiene slice in flight.** The next product gate is PR380B.

1. **PR380B** — migrate Recap/Ingest UI (and shared object navigation) onto the World Graph recap route (`POST /api/live/world-graph/recap-projection`). Satisfies Backlog `[READY] Recap View / ingest must project world graph`.
2. Any durable Union store/contribution direction migration remains explicitly deferred and must not be folded into PR380B.

Do not combine PR380B with a storage migration or a new graph-lens hygiene slice.

## Consequences

**Accepted costs.** One more module in the projection package. A re-export shim in `recap_projection.py` for `splice_node_link_spans` so the two service callers do not change in a pure-move PR. Neutral mention/diagnostic types that surface adapters must map.

**What this buys.** The five CommonMark fixes are paid for once. A fourth surface wanting graph chips in prose gets protection by construction instead of rediscovering the same five bugs. The generic-vs-presentation split becomes explicit rather than implied by filenames.

## Non-goals

- Not collapsing `WorldGraphProjection`, `RecapGraphProjection`, and the union-supergraph projection into one runtime path.
- Not changing what gets linked, what counts as ambiguous, or any projected output byte in the hoist slice (`hoist-graph-mention-linker` / PR #414).
- Not introducing a plugin/registry abstraction for surfaces. Three named consumers do not justify a framework.
- Not touching the frontend. `dmb-node:` consumers are already generic and stay as they are.

## Alternatives considered

**Leave the linker in the recap module until a third consumer appears.** Rejected on evidence: the second consumer already exists and is unprotected (observation 2). The forcing function has passed.

**Collapse the recap wire schema into the generic one entirely.** Rejected. Independent versioning at an HTTP boundary is worth keeping; the fix is to derive the view, not to delete the schema.

**Move the whole projection package to a generated-types pipeline.** Out of proportion to four surfaces, and it would couple this decision to a build-tooling change.

## Related

- `Docs/Plans/HANDOFF-pr412-world-graph-recap-projection-contract.md` — the slice whose review rounds produced this record.
- `Docs/Plans/archive/2026-07-26/graph-lens-projection-handoffs/` — completed PR #414 / #416 / #423 / #427 handoffs.
- `Docs/Design/CONTRACT-graph-kernel-boundary.md` — where decision 3's normalization lands.
- `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md` — sibling concern for surface vocabulary.
- `Backlog.md` `[READY] Recap View / ingest must project world graph (not session preview union)` — product intent that PR380B satisfies.
- `Backlog.md` `[READY] Hoist the Build authoring lifecycle into a shared document-bound Markdown canvas` — the same "hoist the hardened thing, migrate the first consumer without behavior change" pattern at the frontend authoring layer. Independent scope; worth reading together for the shared anti-goal discipline.
