# REPORT — CON-READY Authoring v2 current-contract census v1

**Created:** 2026-09-18  
**Status:** COMPLETE — V2-0 census closes; V2-1 may be designed from these findings  
**Canonical path:** `Docs/Reports/REPORT-CON-READY-authoring-v2-current-contract-census-v1.md`  
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY / campaign memory authoring`  
**Census base:** `main@f1f0a1de28e5d81e48619c6bf64f8d3a3c1dcf81`  
**Parent plan:** `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`

---

## 1. Question answered

V2-0 was required to answer:

> What exact current governed contract receives a human-authored node / claim / edge / correction proposal and turns it into an immutable World revision while preserving source/evidence identity?

Answer:

> **The post-CUTOVER Graph Review authoring seam already exists.** Buddy's existing `POST /api/live/graph-authoring/prepare` → `POST /api/live/graph-authoring/commit` path seals a deterministic `grauth:` operation against the current DungeonMind World parent, admits the exact source pair, materializes a GraphContribution-compatible publication, and publishes/recover through DungeonMind World authority. It does not require or write the retired Buddy authored-overlay/Union store.

The owning continuity witness is:

`tests/test_cutover_graph_review_authoring_continuity.py`

That witness tripwires the legacy Buddy overlay writer and proves native publication for:

- object;
- link-existing;
- relationship.

`merge_objects` remains intentionally inexpressible through the current native manual-authoring seam and must fail closed.

No new backend World-write architecture is required before Authoring v2 can resume product work.

---

## 2. Current governed write authority

### HTTP seam

```text
POST /api/live/graph-authoring/prepare
POST /api/live/graph-authoring/commit
```

Route authority:

`apps/live_control_server/routes/graph_authoring.py`

The route explicitly marks legacy file-store merge-reconciliation materialization retired and directs callers to Graph Review prepare/commit on DungeonMind World Graph authority.

### Prepare

Owner:

`apps/live_control_server/services/graph_object_authoring_prepare.py`

The current request can carry:

```text
campaignId
campaignRel?
sessionId?
worldId?
sourceRunId?
sourceGraphId?
sourceProjectionId?
proposals[]
operatorNote?
```

Current proposal vocabulary includes:

```text
object
link_existing
relationship
merge_objects
```

but native expressibility is deliberately:

```text
EXPRESSIBLE_KINDS =
  object
  link_existing
  relationship
```

Prepare seals current expected parent World revision, source artifact/revision identity, deterministic `grauth:` operation id, contribution digest, confirmation token, expiry, and expressibility. Prepare advances no World head.

### Confirm / publication

Owner:

`apps/live_control_server/services/graph_object_authoring_commit.py`

with DungeonMind integration in:

`apps/live_control_server/integrations/dungeonmind/world_graph_writes.py`

The D.2C4 continuity witness proves:

```text
prepare
→ exact source pair admitted/sealed
→ confirm
→ DungeonMind immutable child revision
→ projection/search/exact-object read sees new memory
→ source anchor remains readable
```

It also proves exact retry is idempotent, lost-response recovery after a fresh API client returns the same committed revision, legacy Buddy overlay writers are not invoked, `overlay_path` / `event_log_path` are not the publication authority, and the operation id is deterministic `grauth:{sha256}`.

This is the authority V2-2 should consume rather than replace.

---

## 3. Current browse/write boundary

Current frontend law from #732 remains correct:

```text
PublishedMemoryBrowseContext != GraphReviewWriteAuthority
```

Owner:

`apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewAuthority.ts`

Write authority is currently:

```text
ExactRunAuthority
| ExplicitAuthoringAuthority
| null
```

Ordinary published-memory browse intentionally has no write authority. The current Graph Review workbench mounts ordinary Campaign + Focus-session recap with `liveRun=null`.

Therefore:

> **V2-1 must not make normal published-memory browse silently writable.**

A locally staged human proposal is safe to create from browse context. Prepare/commit remains absent until a later slice deliberately binds the proposal to explicit source/write authority.

---

## 4. Surviving authoring product infrastructure

CUTOVER intentionally preserved substantial Graph Review authoring UX.

### Source selection

`GraphProjectionReader` already supports:

```text
authoringEnabled
authoringContext
onGraphAuthoringSelection
onGraphAuthoringAction
```

`graphAuthoringSelection.ts` already models text-span selection, graph-node-reference selection, selected/normalized text, bounded surrounding text, paragraph ordinal, Tiptap positions, optional source span ref, existing node id/label, campaign/session, graph/lane context, and optional source artifact path/digest context.

This is sufficient interaction ancestry for V2-1.

### Local draft/staging

`useGraphObjectAuthoringDraft` already stages proposal state locally and persists proposals in `sessionStorage`, scoped by:

```text
campaignId + sessionId
```

Existing proposal machinery supports new object, link existing / alias intent, relationship, and merge-proposal ancestry.

For V2-1, merge is excluded because it is not natively expressible in the governed write seam and is not required to prove useful local adjudication.

### Existing-object lookup

The authoring surface already contains existing-object candidate resolution useful for:

```text
selected source text
→ search existing campaign/world objects
→ choose existing identity
→ stage link/alias intent
```

No new identity-search architecture is required for the first slice.

### Historical authoring workspace

The surviving exact-run authoring workspace is useful implementation evidence, but it currently assumes:

```text
liveRun + candidate/live projection
```

and its write-capable controls eventually feed the Graph Review prepare/commit seam.

Do not force ordinary published browse to impersonate this exact-run state.

---

## 5. Ordinary published recap source-grounding truth

Current ordinary recap browse is:

```text
Campaign + Focus session
→ WorldGraphRecapProjection
→ canonical normalized recap Markdown
→ current/pinned World snapshot
```

The current v1 recap projection explicitly returns:

```text
sourceSpans = []
```

and its trust boundary says recap mention spans are not evidence bindings and source highlighting is not available.

Therefore V2-1 must **not fabricate** `sourceSpanRefId`.

The product can still stage a truthful local source-context record from exact campaign, exact focus session, canonical recap path/artifact metadata from the selected `RecapArtifactRecord`, source artifact id/digest when available, exact selected text, surrounding text, paragraph ordinal, and ephemeral Tiptap positions.

The distinction must remain explicit:

```text
source-contextualized local proposal
!=
canonical evidence-bound World contribution
```

V2-2 owns the eventual source/admission binding needed for durable publication from ordinary published browse.

If the implementation discovers an already-authoritative span ref on the selected source record, it may preserve it. It may not derive or synthesize a span id by parsing labels, paths, offsets, or evidence ids.

---

## 6. V2-1 boundary selected by the census

The first independently useful slice is:

> **From ordinary published Campaign + Focus-session recap, let the GM highlight source text or start from an existing graph pill and stage a truthful local object / link-existing / relationship proposal, without acquiring write authority or calling prepare/commit.**

Target journey:

```text
read published recap
→ highlight phrase OR start from existing graph pill
→ Author memory
→ see exact selected campaign/source context
→ find existing object or describe new object
→ optionally stage relationship
→ review staged proposal
→ continue reading
```

The result is useful even before durable commit because it lets the GM express semantic adjudication through the product rather than fixture JSON.

This is also the right seam for later V2-2:

```text
same staged proposal
→ explicit write/source authority
→ existing governed prepare/commit
```

No proposal-schema fork is justified.

---

## 7. Explicitly not solved by V2-1

V2-1 does not publish a World revision, call graph-authoring prepare/commit, create an implicit `ExplicitAuthoringAuthority`, make published browse writable, synthesize a canonical source span, support merge_objects, export gold, add negative/source-only durable adjudication schema, add ambiguity durable adjudication schema, invoke a model/Agent, run extraction, change Candidate Graph Admission, or change DungeonMind write contracts.

Negative/source-only and ambiguity remain important V2-3 evaluation concepts, but the current local proposal union does not express them as first-class durable adjudications. Do not smuggle them into V2-1 as fake object kinds or operator-note conventions.

---

## 8. Census disposition

```text
V2-0 CURRENT MANUAL-AUTHORING CONTRACT CENSUS = PASS

Existing native Graph Review World-write authority:
  FOUND

New backend World-write architecture required before V2-1:
  NO

Ordinary published browse source context sufficient for truthful local staging:
  YES, with canonical span explicitly unavailable unless supplied

Ordinary published browse may prepare/commit in V2-1:
  NO

V2-1 can be frontend/product bounded:
  YES
```

The successor ACTIVE handoff is:

`Docs/Plans/HANDOFF-CON-READY-authoring-v2-published-recap-local-proposal-v1.md`
