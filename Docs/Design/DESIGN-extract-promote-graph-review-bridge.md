# Design — Extract Promote → Graph Review Bridge

**Status:** ACTIVE REFERENCE — product binding ladder for governed World Graph publication  
**Date:** 2026-07-17  
**Updated:** 2026-07-17 — anchored after GitHub PR #363 (`fdd7ec82`)  
**Sequencing authority:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md) (PR011A*)  
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md) Phase 8  
**Contracts:** [`CONTRACT-agent-tool-authored-prep-contributions-v0.md`](CONTRACT-agent-tool-authored-prep-contributions-v0.md) (`preview_write` / `confirm_commit`)  
**Authoring surface:** [`DESIGN-graph-object-authoring-surface.md`](DESIGN-graph-object-authoring-surface.md)

This document captures the product path from a reviewed ingest extract to an
advanced World Supergraph head. It does not invent a competing PR sequence;
tracker slices own delivery order.

---

## Where we are (2026-07-17)

`main` includes merge commit `fdd7ec82` (GitHub PR **#363**). That work delivered
the governed publication boundary:

```text
GET  /api/live/extract-promote/status
POST /api/live/extract-promote/prepare
POST /api/live/extract-promote/confirm
```

Shared ops live in `src/graph_memory/extract_promote_ops.py`. The boundary seals
a revision-bound proposal, permits assertion-level selection, creates a
`GraphContribution`, advances the immutable World Graph head, and reports the
committed revision truthfully (including post-publication audit degradation and
pinned rebuild replay).

Separately, `/ingest` already does most of the user-facing precursor work:

```text
paste/select recap
→ normalize
→ run extraction
→ validate candidate graph
→ materialize preview union store
→ open Graph Review
```

Graph Review already loads preview-ready ingest runs and renders extracted
objects. Its selected run is still represented primarily by `manifestPath`, and
there is **no connection** from that selection to the promotion API.

```text
Ingested recap
    ↓
Validated preview graph
    ↓
Graph Review displays it
    ↓
          MISSING BRIDGE
    ↓
Prepare governed contribution
    ↓
GM confirms
    ↓
World Graph head advances
```

The difficult Kernel and publication work is done. The missing work is the
**product binding and review UX**.

---

## Product boundary (locked)

**The button belongs in Graph Review.** It must not be an automatic final step
in `IngestionModule`.

| Surface | Owns |
|---|---|
| **Ingest** | Creating proposed memory (extract + preview) |
| **Graph Review** | Judging and committing it (`preview_write` → `confirm_commit`) |

That matches the declared architecture: Graph Review/Ingest is the correction
cockpit; durable writes follow proposal-bound confirmation into
`GraphContribution` and atomic graph-head advancement.

Visible flow:

```text
Ingest Recap
→ Open Graph Review
→ Review & merge
→ inspect proposed objects and relationships
→ Merge N changes into campaign memory
→ open the newly committed graph objects
```

“One button” means one obvious primary action, **not** unreviewed one-click
publication. The first button opens review; the final button is explicit
proposal-bound confirmation.

---

## Implementation ladder (PR011A)

Reframe Phase 8 write-path work as:

```text
DONE   PR011A-foundation — extract/promote shared ops + HTTP boundary (#363)

NEXT   PR011A1 — server-owned ingest-run → promotion binding
NEXT   PR011A2 — Graph Review prepare / review panel
NEXT   PR011A3 — confirm, durable reload, and end-to-end dogfood

THEN   PR011B  — expose the same preview_write / confirm_commit capability
                 to Hermes without a second agent-specific write path
```

The human Graph Review button is the **reference implementation** of
`confirm_commit`. Hermes later launches the same proposal and hands control to
the same GM review/confirmation surface.

### PR011A1 — Bind selected ingest run to promotion

**HTTP prepare is `runId`-only** (`dmb_extract_promote_prepare_request_v2`).
Source and candidate paths are resolved from the graph-ingest run manifest by
`resolve_promotable_ingest_run`. Registry-gated evidence under
`out/graph_memory/runs/` is allowed; durable world-graph trees
(`out/graph_memory/worlds/`, configured `world_graph_root` when not the broad
`out/` default) remain denied. Browser path fields are rejected (`extra=forbid`).
CLI path-based prepare is unchanged.

Promote the existing read-only graph-ingest run registry into a server-owned
resolution seam:

```text
resolve_promotable_ingest_run(run_id)
    → validated manifest
    → normalized source artifact + digest
    → candidate graph artifact
    → extraction profile
    → campaign/session scope
    → promotability diagnostics
```

**Replace** the product-facing prepare request (forward-only; no compatibility
mode). Operator CLI may keep internal path-based ops.

From (operator bootstrap / current HTTP):

```json
{
  "candidateGraphPath": "...",
  "sourceUri": "...",
  "sourceRevisionId": "..."
}
```

To (product):

```json
{
  "runId": "graph-ingest:longmont-c2:session-25:...",
  "nodeIds": ["optional-node-selection"]
}
```

**Must prove:**

- unknown, failed, invalid, or non-preview-ready runs cannot prepare;
- campaign/session mismatches fail;
- source and candidate paths are resolved from the manifest by the server;
- the graph store can never become evidence;
- the proposal remains pinned to the current graph head;
- no browser-supplied manifest, source, or candidate path is accepted.

### PR011A2 — Graph Review proposal panel

Add `extractPromoteApi.ts` and typed frontend contracts.

Place **Review & merge** in `GraphReviewSessionToolbar` or the Graph Review
header. Enable only when:

- a live ingest run is selected;
- its candidate graph is valid;
- its source revision is resolvable;
- the World Graph is initialized;
- the run has not already been superseded or merged.

Calling the button performs **prepare**, then opens a review sheet — not a
diagnostics dump.

The sealed `reviewPackage` remains authority. The UI must not parse Kernel
proposal internals as its presentation model. Add a typed review projection:

```ts
interface ExtractPromotionReviewItem {
  assertionId: string;
  kind: "object" | "relationship" | "attribute" | "alias";
  label: string;
  action: "create" | "connect_existing" | "update";
  identityOutcome: string;
  summary: string;
  evidenceSummary?: string;
  warnings: string[];
}
```

Review sheet shows game-facing counts and items (new objects, connections to
existing, relationships, unresolved mentions, rejected assertions). Initialize
accepted items as selected. Explicit zero-selection disables confirmation.
Unresolved and rejected items remain visible but unselected.

### PR011A3 — Confirm, reload, prove the durable object

Final button copy: **Merge N changes into campaign memory**.

Sends sealed proposal binding + selected assertion IDs. Does **not** ask the
browser for an arbitrary `confirmingPrincipal` string or expose an
`allowLiveWorld` checkbox — those become server-owned capability/session policy
for the product route.

After confirmation:

1. Read `committed_revision_id`.
2. Reload World Graph projection at that revision.
3. Refresh Graph Review run/catalog state.
4. Replace preview projection with durable graph objects.
5. Open or highlight newly created/connected objects.
6. Surface a compact success receipt (counts + `rev:abc → rev:def`).

**Failure behavior (explicit):**

| Outcome | UX |
|---|---|
| Stale proposal | “The campaign graph changed. Review the refreshed proposal.” |
| Already applied | Success/no-op; open existing revision |
| Publication failed | No head advancement; retry after correction |
| Published, audit degraded | Show committed revision, reload it; **do not** retry confirmation |
| Zero selected | Disable confirmation |
| Unresolved mentions | Leave unresolved; never silently merge by label |

---

## First complete dogfood (acceptance story)

Use a Session 25 object that creates something new and connects to existing
Mireward context — **Hesta and the apothecary** are the preferred candidate.

```text
Paste Session 25 recap
→ run graph extraction
→ open Graph Review
→ inspect Hesta and the apothecary
→ see suggested connection to Mireward Reach
→ Review & merge
→ confirm selected assertions
→ World Graph head advances
→ Hesta opens as a durable graph object
→ relationship to Mireward is clickable
→ source evidence opens
→ Plan and Hermes can retrieve Hesta from the new revision
→ reload proves the object persists
```

That proves the intended object journey from source prose to durable, reusable
campaign memory — not merely that a button returned HTTP 200.

---

## Non-goals (this ladder)

- Automatic publish at the end of IngestionModule.
- Browser-supplied filesystem paths for product prepare/confirm.
- A second Hermes-only write protocol (PR011B reuses this path).
- Replacing Graph Review with autonomous agent commits.
- Compatibility mode that keeps path-based HTTP prepare alongside `runId`.

---

## Related runtime seams

| Seam | Role |
|---|---|
| `src/graph_memory/extract_promote_ops.py` | Shared prepare/confirm orchestration |
| `apps/live_control_server/routes/extract_promote.py` | HTTP boundary (#363) |
| `src/graph_memory/ingestion/graph_ingest_run.py` | Run manifest + preview readiness |
| Graph Review workbench (`apps/live-control-ui/.../graphReviewWorkbench/`) | Correction cockpit / future button home |
| CLI `scripts/promote_extract_contribution.py` | Operator path-based bootstrap (may remain) |
