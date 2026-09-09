---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / full World-object projection
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW → MERGE → HUMAN DOGFOOD
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v1.md`
  - Branch: `dogfood-continuity/surface-neutral-full-world-object-projection-v1`
  - Suggested PR title: `DOGFOOD-CONTINUITY: project complete World objects across surfaces`

  ## Product invariant
  A selected graph object has one complete World view at the selected World
  revision: all admitted truth, including historical/superseded relationships,
  with source time, occurrence time, and valid time preserved. Ingest, Plan,
  Build, Play, and Agent selected-object context may add focus, ranking,
  chrome, and actions, but they must not change which admitted World facts belong
  to the object or flatten those temporal lanes.

  ## Verification pointer
  - Current World authority is read-only DungeonMind.
  - APP-STATE supplies exact durable source bytes for provenance hydration.
  - Current session/campaign are focus metadata, never object-truth eligibility.
  - TemporalEnvelopeV1 lanes stay distinct; this is not a current-state reducer.
  - Full-object reads must be bounded by one authoritative World operation plus
    one batched APP-STATE source read, with no per-edge/source N+1 path.
  - Generic Agent graph-query World-scope default is a named successor.
---

# HANDOFF — DOGFOOD-CONTINUITY: surface-neutral full World object projection v1

**Created:** 2026-09-08  
**Status:** DESIGN HOLD after Review Cycle 1 (`5148560899` on `612c30f9`); superseded by v2. CODE resumed on v2 after DungeonMind #52 merge.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / full World-object projection`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW → MERGE → HUMAN DOGFOOD  
**Current main at handoff creation:** `0d3dd6ce024f92bdcc7eacc4573f277ed8af2cfe`  
**Product predecessor:** PR #696 merge `3e2abc0c7f8ce523b071716eb13bcf18d7979a2a`  
**Accepted #696 head:** `8f93138000c699a5d1249955003c91042f2053b1`  
**Implementation branch:** `dogfood-continuity/surface-neutral-full-world-object-projection-v1`  
**Suggested PR title:** `DOGFOOD-CONTINUITY: project complete World objects across surfaces`

| Field | Value |
|---|---|
| Branch / isolated checkout | `dogfood-continuity/surface-neutral-full-world-object-projection-v1` |
| Runtime/state ownership | Read-only World 54330 + APP-STATE 54331. No DB writes. Dogfood API/UI 8000/5173 if used; serialize with any leftover dogfood on those ports. 54329 unused. |

> Repository law: [`AGENTS.md`](../../AGENTS.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). Current steward anchor: [`STEWARDS-ANCHOR-con-ready.md`](STEWARDS-ANCHOR-con-ready.md). Temporal lanes: [`../Design/CONTRACT-temporal-envelope-v1.md`](../Design/CONTRACT-temporal-envelope-v1.md). Stage 2C witness: [`../Reports/REPORT-stage-2c-broad-source-adoption.md`](../Reports/REPORT-stage-2c-broad-source-adoption.md).

---

## §0 Re-anchor: what is actually true now

PR #696 is merged. Stage 2C materially expanded durable APP-STATE source coverage:

```text
source.artifact / source.revision    23 / 23
historical ingest runs               53 unchanged
World head                           rev:680c246047d67f9fe0293ee90526f670
World writes from Stage 2C           0
new source revisions                 22
C2S25 historical revision            preserved exactly
```

The human follow-up after Stage 2C found the next concrete product failure.

C2 Session 25, Karsemine:

```text
S25 Lysandra edges
  evidence points at S25
  exact S25 APP-STATE bytes exist
  source prose appears                 PASS

S24 Hunter's Mark · holds
  evidence points at S24
  exact S24 APP-STATE bytes exist
  relationship remains visible
  source prose remains empty           FAIL

S24 Lysandra · commands
  evidence points at S24
  exact S24 APP-STATE bytes exist
  relationship remains visible
  source prose remains empty           FAIL

Questionable Company · member of
  manual_seed evidence
  no recap source span                 HONESTLY NO RECAP EXCERPT
```

This establishes two distinct facts:

1. Stage 2C source durability is not the blocker for S24 evidence.
2. Buddy's selected-object projection/hydration is still scoped by the document/session path that happened to open the object.

The current historical recap service makes the limitation explicit:

```text
build_historical_recap_world_projection(...)
  loads one exact source.revision: the current recap
  requests World projection with scope_mode="campaign"
  apply_durable_source_provenance(...)
    receives exactly one source_artifact_id + digest + markdown
    skips every evidence record from another source artifact
```

The direct DungeonMind adapter already establishes the opposite focus law:

> `focus.kind=session` is presentation-only. It changes focus flags/ranking, not graph admission.

Therefore the current failure is Buddy product projection, not DungeonMind temporal focus.

### Current-main bookkeeping note

During handoff creation, two accidental zero-byte scratch files were created and immediately removed on `main`. No pre-existing repository content changed; the resulting tree is the same product tree as after #696. The visible cleanup history leaves current `main` at `0d3dd6ce024f92bdcc7eacc4573f277ed8af2cfe`. Do not conceal or reinterpret those commits during review.

### §0E Review Cycle 1 DESIGN HOLD

Reviewed exact head `612c30f9a5a33fb26a5ad7853070464583e7b216` as GitHub review `5148560899`. Verdict: **DESIGN HOLD before CODE**.

This rebrief closes the two Cycle 1 blockers in the dispatch contract. It does not start implementation.

| Finding | Repair in this head |
|---|---|
| “Current World object” was undefined and could be read as latest-fictional-time / latest-wins | Define current = all admitted truth at the selected World revision; require `TemporalEnvelopeV1` / equivalent lossless temporal payload on assertions and relationships; fingerprint temporal identity |
| Generic Agent `campaign → world` default bundled into Layer E | Keep Agent selected-object parity; name generic open-ended query World-scope default as a successor |
| #696 / Stage 2C sync paths named in acceptance but not leased | Add `ROADMAP-demo-ready-c1-c2-to-of-conks.md` and `STEWARDS-ANCHOR-con-ready.md` to §4 |

CODE starts only after a later review cycle accepts this rebrief.

---

## §1 Product ruling — full object first, focus later

The operator has set the product semantics explicitly:

> **Karsemine is only the example. This is true for every node.**

And:

> **When a graph object is selected, I want its edges and related nodes across all ingested material in the World. Once we can project the whole thing correctly and quickly, we can experiment with narrower/focused views.**

And across surfaces:

> **This is not an Ingest feature. When writing in Plan or Build, running Play, or asking the Agent, the same graph object must expose the same rich current World projection.**

### Normative product law

> **A selected World object has one complete admitted World view at the selected World revision. Surface, document, campaign, session, and interaction context may annotate, rank, highlight, or offer different actions; they must not determine which admitted World facts belong to the object, and they must not drop or flatten historical/superseded assertions.**

Define:

```text
current World object
  = all admitted object truth at the selected World revision
  ≠ only facts currently true at the latest fictional tick
```

This slice is append-oriented graph history as a **read**. Later Agent/ingest writes may add, supersede, close, or correct assertions through governed contribution paths. This PR does not authorize writes and must not imply destructive overwrite or “latest session wins.”

Equivalently:

```text
World object identity + exact World revision + admissibility
                         ↓
             complete object truth
                         ↓
      surface-neutral product projection
                         ↓
       ┌────────┬────────┬────────┬────────┬────────┐
       │ Ingest │  Plan  │ Build  │  Play  │ Agent  │
       └────────┴────────┴────────┴────────┴────────┘
              focus/chrome/actions only
```

### What “all ingested material” means

For this capability it means:

- all assertions/evidence admitted into the **selected** DungeonMind World revision for the selected object, including ended/superseded relationships still present at that revision;
- world-global assertions;
- campaign-scoped assertions from **every campaign in that World**;
- incoming and outgoing relationships touching the selected object;
- related endpoint nodes needed to understand those relationships;
- object attributes/assertions;
- the canonical temporal envelope (source time, occurrence time, valid time) where authority carries it;
- every supporting evidence identity exposed by the authoritative read;
- exact source prose when the supporting source revision is durable in APP-STATE and its evidence span is resolvable.

It does **not** mean arbitrary files that were never admitted to World authority.

### Current campaign/session become context, not eligibility

Examples while viewing C2 Session 25:

```text
Karsemine — Lysandra S25        INCLUDED, focus-highlightable
Karsemine — Hunter's Mark S24  INCLUDED, prior-session context
Karsemine — Lysandra S24       INCLUDED, prior-session context
C1-only Karsemine assertion    INCLUDED if the same World object has admitted C1-scoped truth
world-global Karsemine fact    INCLUDED
```

A future UI may offer:

```text
All
Current campaign
Current session
Recent
High confidence
Why this matters now
```

Those are **view filters over an already-complete object projection**, not alternate graph reads that redefine object truth.

---

## §2 One capability

### Capability name

**Surface-neutral full World-object projection v1**

### Merge-ready invariant

> Given a selected World `node_id`, Buddy can obtain one revision-pinned, GM-admissible, World-cross-campaign object projection containing the complete admitted one-hop object neighborhood and object attributes available from DungeonMind at that World revision — including historical/superseded facts and their lossless temporal envelopes — then hydrate every eligible evidence span from its exact durable APP-STATE source revision in a bounded batch. Ingest, Plan, Build, Play, and Agent selected-object context consume that same semantic projection. Current campaign/session/surface context is preserved only as focus/ranking/action metadata. No graph writes, source re-adoption, filesystem provenance fallback, current-state reduction, temporal-lane flattening, or per-edge source fetch is introduced.

### Named successor (intentionally false)

```text
Agent generic/open-ended graph search/query default
  campaign → World scope
```

Selected-object Agent parity stays in this PR. Changing `AgentWorldGraphQueryContextRequest.scope_mode` for queries with no selected object does not.

### Independently useful outcome

After this PR, selecting Karsemine from any supported surface should answer the same underlying question:

> “What does this World revision know about Karsemine?”

That includes facts recorded earlier, facts whose valid time has ended, and facts whose occurrence time is not the current session.

The surface can answer a second question differently:

> “What can I do with Karsemine here?”

Do not conflate those questions.

---

## §3 Authority model

```text
DungeonMind World @ exact revision
  owns:
    node identity
    admitted attributes/assertions
    admitted relationships
    campaign tenancy
    evidence identity
    source-artifact/source-revision bindings
    visibility/admissibility
    TemporalEnvelopeV1 / equivalent temporal payload
      source time
      occurrence time
      valid time

Buddy APP-STATE
  owns:
    exact durable source bytes
    immutable source revision identity

Surface context
  owns:
    current surface
    current document/run
    narrative campaign/session focus
    selection
    available actions

Product full-object projection
  joins these without changing World truth
```

### Forbidden authority inversion

Do not:

- use current document contents to decide which World edges exist;
- use current campaign as an admission wall for object detail;
- use current session as an admission wall for object detail;
- reconstruct/union graph truth in Buddy from multiple partial reads;
- infer a source revision by choosing “latest” APP-STATE revision;
- guess a source digest from a filename/title/session;
- treat missing source prose as evidence that the graph relationship is absent;
- reduce object truth to “facts true at the latest fictional tick”;
- erase an ended/superseded relationship merely because a later assertion exists;
- flatten session/source time into occurrence time;
- infer `source_time == occurrence_time` because the source is a session recap;
- treat `session_ids` as a substitute for the temporal envelope.

---

## Selected-object read contract — not whole graph dump

The product requirement is **complete selected-object detail**, not “download the entire World every time somebody clicks a chip.”

### Required request semantics

Prefer a dedicated surface-neutral Buddy contract, for example:

```text
POST /api/live/world-graph/object-projection

{
  schema: "dmb_world_graph_object_projection_request_v1",
  worldId,
  nodeId,
  admissibility: "gm",
  revisionPin: null | exact_revision,
  focus: {
    campaignId: null | narrative_campaign,
    sessionId: null | narrative_session,
    surfaceId: "ingest" | "plan" | "build" | "play" | "agent"
  }
}
```

Exact route/model naming is implementation latitude. Semantics are not.

The request does **not** expose a campaign scope mode that can silently narrow object truth. The authoritative graph read beneath it is World-cross-campaign.

If reuse of `WorldGraphObjectRequest` is cleaner, the service must force the equivalent of:

```text
scope_mode = "world"
```

and treat any campaign/session carried alongside it as narrative focus only.

### Required response semantics

The selected-object response must contain enough structured information for both UI and Agent consumers:

```text
snapshot
  world_id
  revision_id
  head_revision_id
  is_head
  admissibility

selected node
  identity / label / kind / aliases / summary
  campaign tenancy where applicable

all selected-node attributes/assertions
  TemporalEnvelopeV1 or equivalent lossless temporal payload
    source time
    occurrence time
    valid time
    honest absent/unresolved when authority does not carry a lane

complete one-hop adjacency
  every admitted incoming edge
  every admitted outgoing edge
  related endpoint identity + label/kind/summary needed for rendering
  predicate + direction
  campaign scope
  session ids as focus/source metadata only, never as a temporal-lane substitute
  temporal envelope / equivalent payload for the relationship assertion
  evidence refs

provenance
  evidence identity
  exact source binding when authority exposes it
  durable APP-STATE source revision when present
  excerpt/span when safely resolvable
  honest unavailable reason otherwise

completeness
  complete | partial
  explicit truncated fields/counts/reason

focus metadata
  current campaign/session flags/rank hints only

telemetry
  counts + timing fields described below
```

### Complete means complete

Existing retrieval request models have low default/hard bounds (`12` nodes, `24` relationships, etc.). Those bounds cannot silently define “the whole object.”

For this capability:

- a normal successful full-object response must include every admitted one-hop relationship touching the selected node at the pinned World revision;
- every related endpoint node required by those relationships must be represented;
- every admitted selected-node attribute must be represented;
- every evidence ref supporting those selected-node facts must be represented;
- if an authority safety ceiling prevents completeness, return `partial`/truncation explicitly and **do not present the object as complete**.

### DungeonMind contract stop condition

Buddy must not simulate completeness by unioning overlapping partial projections.

If the mounted DungeonMind read contract cannot provide a complete selected-node one-hop neighborhood with explicit completeness semantics **and** a lossless temporal payload for assertions/relationships that already carry `TemporalEnvelopeV1` / `temporal_scope` in authority, stop implementation and report a required **DungeonMind read-contract successor**. Do not rebuild graph traversal authority in Buddy. Do not invent temporal lanes from session ids.

---

## §5 Exact multi-source provenance hydration

The current one-recap overlay is retired as the conceptual object-detail boundary.

### Current failure

```text
selected C2S25 recap
  ↓
load C2S25 source bytes once
  ↓
for each World evidence ref
  if evidence.source_artifact_id == C2S25 artifact:
      hydrate
  else:
      blank
```

That is why S24 Hunter's Mark remains empty while viewing S25.

### Required flow

```text
full selected-object World read
  ↓
collect evidence refs supporting selected node/attributes/edges
  ↓
resolve exact authority source binding for every evidence ref
  ↓
deduplicate exact (source_artifact_id, source_revision/digest) bindings
  ↓
ONE batched APP-STATE read
  ↓
extract every resolvable span from exact durable bytes
  ↓
attach provenance to the correct node/attribute/relationship
```

### Exact source binding is mandatory

Stage 2C permits multiple immutable revisions for the same `source_artifact_id`. Therefore this is forbidden:

```text
get latest APP-STATE revision for artifact X
```

The selected evidence must resolve to an exact authoritative source revision/digest.

Use an authority-native binding already present in DungeonMind evidence/source metadata. The direct adapter already has source-revision/digest machinery for source-anchor verification; reuse an exact authority identity rather than inventing a second identity scheme.

If the currently mounted DungeonMind evidence contract does not expose enough information to map an evidence ref to an exact source revision/digest, **STOP** and report the contract gap. Do not infer the revision from:

- current session;
- source filename;
- source artifact latest revision;
- span prefix alone;
- chronology proximity.

### APP-STATE batch seam

The current source service exposes one-at-a-time exact reads. Add a bounded batch read if needed, such as:

```text
get_source_markdown_batch([
  (source_artifact_id, content_sha256),
  ...
])
```

Requirements:

- one APP-STATE transaction/read operation per selected-object projection;
- exact artifact+digest matching;
- no per-edge connection/transaction;
- return misses explicitly;
- no filesystem fallback.

### Provenance status vocabulary

Do not use vague UI/server semantics such as “No origin prose in graph memory yet.”

Internally distinguish at least:

```text
excerpt_ready
no_source_span
source_not_durable
unsupported_source_media
source_binding_unavailable
span_unresolvable
```

Graph facts remain visible when prose is unavailable.

Presentation copy for these states is Stage 4 latitude; the structured distinction belongs here.

---

## §6 Surface-neutral consumption law

The same semantic object detail must feed every surface.

A useful testable identity is:

```text
(world_id, revision_id, node_id, admissibility)
```

Given the same identity, the semantic detail fingerprint must be identical regardless of originating surface.

### Semantic fingerprint

For cross-surface tests, compute a deterministic test/debug fingerprint over sorted:

```text
revision_id
node_id
attribute assertion ids
relationship edge ids + direction
related node ids
evidence ref ids
exact durable source revision ids/digests when available
provenance status per evidence/edge
temporal semantic identity per assertion/relationship
  source-time identity
  occurrence-time identity
  valid-time interval identity (open/closed/absent)
```

Do not hash surface-specific actions/chrome/rank order into this fingerprint. Two otherwise-identical assertions with different occurrence or valid time must fingerprint differently.

---

## §7 Ingest integration

Ingest remains a document/session reading surface.

The historical recap response may stay optimized for rendering the loaded recap and its mention pills. Do **not** inflate initial recap load by hydrating the entire World detail for every mentioned node.

When the user opens/toggles a graph object:

```text
mention chip in C2S25 recap
  → selected node id
  → shared full-object projection request
  → complete World-cross-campaign object detail
  → shared graph-object presentation
```

Expected Karsemine behavior while parked on C2S25:

```text
S25 Lysandra source prose       visible
S24 Hunter's Mark source prose  visible if exact S24 evidence/source span binds
S24 Lysandra source prose       visible if exact S24 evidence/source span binds
manual_seed relationship        visible; no fabricated recap excerpt
```

The current recap projection's session/campaign node map can continue to power mention detection. It must no longer be the authority for the opened object's complete detail.

---

## §8 Plan integration

Plan already uses shared graph-reference infrastructure and `PlanReferenceObjectCard` / `ResolvedGraphObjectProjection`.

When a graph-native reference becomes the active/open object:

- resolve/open exact node identity as today;
- fetch the shared full-object projection;
- render the shared semantic object model;
- preserve Plan-only actions (`Open statblock`, source navigation, document behavior);
- current Plan campaign/session may rank/highlight facts but must not suppress other World facts.

Do not maintain a Plan-specific full-object assembler.

Corpus fallback remains fallback only when graph identity itself cannot be resolved. It is not a substitute for a thin graph detail response.

---

## §9 Build integration

Build currently has a dedicated `BuildGraphObjectContext` that requests a generic graph projection and applies document-campaign admission.

This slice must separate **read truth** from **write/insert admission**.

### Read rule

If the selected node belongs to the same World as the Build document/context, opening the node may show the full World-cross-campaign object projection.

A C2 Build document may read a C1-scoped fact attached to the same World object.

### Write/insert rule

Existing object insertion/write admission remains intentionally narrower:

- campaign-scoped Build document may still reject insertion of another campaign's object/reference when that is the established write contract;
- world-scoped Build may follow its existing broader insertion rules.

Do not weaken write authority merely because read projection becomes broader.

Prefer reuse of the existing `admitBuildWorldGraphBrowse` same-World concept for read eligibility rather than `admitBuildDocumentScope` campaign equality.

`BuildGraphObjectContext` should consume the shared full-object loader rather than issuing its own whole campaign projection and selecting one node from it.

---

## §10 Play integration

Play already has `PlayGraphObjectSheet` and graph-reference occurrence context.

When a graph node/reference is opened in Play:

- World identity/edges/evidence come from the same shared full-object projection;
- Runbook occurrence context remains Play-local annotation;
- Threat mechanics remain Play/Threat specialization;
- Play actions remain Play-local;
- the World section must not become session/runbook-limited merely because the object was opened from the current Scene/Beat.

Example:

```text
Current Beat mentions Karsemine
  ↓
Play opens Karsemine
  ↓
World section shows full Karsemine object
  +
Play section says where Karsemine appears in this Runbook/current moment
```

Those are complementary layers, not competing scopes.

---

## §11 Agent integration

The Agent must not have a sixth graph semantics for a **selected** object.

### Selected object context

When a surface has an active selected graph object, publish its exact object identity into Agent surface context:

```text
world_id
node_id
revision_id/head binding
focus campaign/session
origin surface
```

Before the model call, resolve that node through the **same full-object projection service** used by UI surfaces.

The model receives structured complete object context subject to the same completeness flag, provenance statuses, and temporal envelopes. It must not receive a Plan-only or Ingest-only reduced object, and it must not receive a current-state-only reduction of that object.

### Open-ended Agent queries — not this PR

Do not dump the entire World graph into every prompt.

This PR does **not** change the generic/open-ended `AgentWorldGraphQueryContextRequest.scope_mode` default from `campaign` to `world`. That change is independently useful, independently revertible, and applies when no object is selected. It is the named successor:

```text
HANDOFF / capability:
  Agent generic graph query World-scope default
```

Until that successor, open-ended search may keep the existing campaign default. If the user then opens/selects a node from that result, expansion still uses this PR's full-object service.

### Citation boundary remains unchanged

Graph context is structured memory/navigation. Exact APP-STATE source excerpts may be supplied as source evidence only under the existing citation/evidence contract. Do not let graph summaries masquerade as quotations.

---

## §12 Shared client architecture

Prefer one shared full-object client seam under `graphReference/` or `worldGraph/`, not surface-local fetches.

Conceptually:

```text
fullWorldObjectClient.load({ worldId, nodeId, revisionPin, focus })
        ↓
GraphReference full-object binding / hook
        ↓
shared GraphObject card model
        ↓
Ingest / Plan / Build / Play
```

Relationship navigation should request the target object's complete detail using the same seam.

### Surface-specific differences that are allowed

```text
Ingest: recap context / loaded source
Plan: authoring actions / source navigation
Build: insert/edit actions and write admission
Play: runbook occurrence + Threat/Combat actions
Agent: prompt/context serialization
```

### Differences that are not allowed

```text
different edge membership
different campaign admission
different evidence membership
different source revision choice
session-specific suppression of otherwise admitted facts
surface-specific graph reconstruction
dropping ended/superseded relationships
flattening source time into occurrence time
```

---

## §13 Performance and observability are merge requirements

The operator wants “the whole thing at need and fast.” Do not postpone measurement.

### Owning-boundary operation budget

A successful selected-object read should have this shape:

```text
DungeonMind authoritative object/neighborhood read   1
APP-STATE batched durable-source read                 1
per-edge APP-STATE reads                              0
per-edge World reads                                  0
checkout/source-file reads                            0
click-time provenance fetches after response          0
```

Relationship navigation to a different node is a new selected-object request and may repeat the bounded pattern once for that target.

### Trace fields

Emit/record at least:

```text
request_id / trace_id
world_id
revision_id
node_id
origin_surface
focus_campaign_id
focus_session_id
world_read_ms
source_batch_read_ms
provenance_hydration_ms
serialization_ms
total_ms
node_count
relationship_count
attribute_count
evidence_count
distinct_source_binding_count
durable_source_hit_count
durable_source_miss_count
excerpt_count
completeness
truncated_fields
```

Do not log source prose.

### Performance acceptance

Measure rather than speculate.

At minimum record warm local measurements for:

- Karsemine;
- one additional ordinary object;
- the highest-degree/most-connected practical C1/C2 object discovered during the witness.

Merge expectation:

- one request opens the complete object;
- no N+1 signature appears as degree/evidence count rises;
- warm browser interaction feels effectively immediate for the acceptance corpus;
- if warm server total is repeatedly above **750 ms** for an ordinary object on the local durable authorities, stop and profile before merge rather than normalizing a multi-second detail click;
- if the highest-degree witness exceeds that threshold, report component timings and determine whether the authority read or source hydration is the actual bottleneck.

The 750 ms number is a merge investigation threshold, not a long-term SLO.

---

## §14 Completeness / performance interaction

Do not buy speed by silently dropping edges.

If the selected node has more relationships/evidence than the first authority call can return:

- explicit `partial` is acceptable only as a temporary fail-closed state;
- UI must not call it “complete”;
- Agent must receive truncation diagnostics;
- the PR is not accepted as satisfying the full-object invariant until the acceptance witnesses are complete.

If authoritative pagination/cursor continuation is required, it must remain one logical product operation with deterministic ordering and explicit authority semantics. Do not union arbitrary search results in Buddy.

---

## §15 Proposed implementation decomposition

Keep this as one product capability, but implement in layers inside the PR.

### Layer A — authority-native complete object read

Prove DungeonMind can provide:

```text
selected node
all touching admitted relationships
related endpoint nodes
selected-node attributes
all supporting evidence refs
exact source revision/digest binding needed for evidence hydration
lossless temporal envelope / equivalent payload for assertions and relationships
explicit completeness/truncation
```

If not, STOP for a DungeonMind contract PR.

### Layer B — batched durable provenance join

Add one APP-STATE batch source read and deterministic span hydration.

### Layer C — surface-neutral Buddy response

Return one stable full-object response/model plus telemetry/completeness.

### Layer D — shared UI consumption

Wire the shared loader/model into existing graph-object open paths for Ingest, Plan, Build, and Play. Avoid redesigning card styling.

### Layer E — Agent selected-object consumption

Publish selected object identity from surfaces and use the same full-object service for selected-object Agent context. Do not change the generic/open-ended Agent graph query `scope_mode` default.

Each layer is reviewable under the same invariant; do not split into independent user capabilities unless a stop condition forces rebrief.

---

## §4 Files in scope — write lease

Exact paths may move after bounded discovery, but expected ownership is:

### Server / contracts

| Action | Path | Purpose |
| --- | --- | --- |
| Create | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v1.md` | lane authority |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | backward sync #696 / Stage 2C merged facts; mark this slice current, not done |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | re-anchor to #696 merge + this slice current |
| Create | `apps/live_control_server/services/world_graph_object_projection.py` | surface-neutral complete object + provenance join |
| Create/modify | `apps/live_control_server/models/world_graph_object_projection.py` | strict request/response/completeness/telemetry contract if needed |
| Modify | `apps/live_control_server/routes/world_graph_retrieval.py` or a narrowly named object-projection route module | expose one product read endpoint; do not duplicate retrieval authority |
| Modify | `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py` | only exact authority metadata/completeness adaptation required by the object read |
| Modify | `src/application_state/source/service.py` | batch exact durable source read |
| Modify | `src/application_state/source/repository.py` | one-query batch repository support |
| Modify | `src/graph_memory/retrieval/models.py` or projection models only if the existing contract cannot truthfully express completeness/source binding | contract support, not graph logic |

### Shared UI/API

| Action | Path | Purpose |
| --- | --- | --- |
| Modify | `apps/live-control-ui/src/api/types.ts` | full-object wire types |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | one full-object client call |
| Create/modify | `apps/live-control-ui/src/graphReference/fullWorldObjectProjection.ts` (or nearest existing neutral seam) | shared load/adapt/fingerprint behavior |
| Modify | `apps/live-control-ui/src/graphReference/types.ts` | surface-neutral binding contract if needed |
| Modify | `apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx` | consume full detail for shared object presentation |

### Surface consumers

| Action | Path | Purpose |
| --- | --- | --- |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.tsx` | Ingest open → full detail |
| Modify | `apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx` only if shared wrapper cannot absorb it | Plan proof |
| Modify | `apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.tsx` | replace campaign projection/select-one path with shared full-object read |
| Modify | `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts` | separate world read context from campaign write admission if required |
| Modify | `apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.tsx` | Play World section consumes same semantic detail |

### Agent

| Action | Path | Purpose |
| --- | --- | --- |
| Modify | `apps/live_control_server/services/agent_world_graph_query_context.py` | selected-object full-object context only; do not change generic query scope_mode default |
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx` and/or neutral surface context types only as needed | publish selected object identity across surfaces |

### Tests

Expected owning tests alongside each modified seam, including:

```text
tests/test_world_graph_object_projection.py
existing World retrieval/direct-read tests if contract changes
application_state source repository/service tests
historical recap projection regression
shared graphReference tests
BuildGraphObjectContext tests
PlanReferenceObjectCard/ResolvedGraphObjectProjection tests
PlayGraphObjectSheet tests
Agent world graph query-context tests
```

### Bounded discovery

Up to **3 additional production paths** are allowed if existing surface-neutral seams are discovered under:

```text
apps/live-control-ui/src/graphReference/
apps/live-control-ui/src/surfaceInteraction/
apps/live_control_server/services/
```

A new schema migration, new durable table, graph write path, or DungeonMind authority mutation is a STOP/rebrief signal.

---

## §17 Explicitly out of scope

Do not absorb:

- Stage 4 natural-language copy/styling redesign;
- hiding graph taxonomy because it looks ugly;
- “current session only” toggle UI;
- ranking-policy experimentation beyond preserving current focus hints;
- new graph writes or graph authoring;
- source adoption/recovery for Stage 2C skips;
- binary/JSON source archival;
- Threat publication recovery;
- Combat mutation;
- Agent autonomous graph writes;
- generic Agent open-ended graph query `campaign → world` default (named successor);
- mutating `TemporalEnvelopeV1` / TL00 kernel schema;
- a current-state reducer or “latest wins” object view;
- model-generated biographies/summaries used as graph facts;
- new memory model;
- Build document write-policy broadening;
- Play runtime redesign;
- persistent cache infrastructure;
- prefetching every graph object in a document.

If the full object is still ugly after this PR, that is evidence for Stage 4—not permission to style inside this slice.

---

## §18 Required automated evidence

### Server semantic tests

Prove:

1. session focus does not remove prior-session edges;
2. campaign focus does not remove other-campaign edges under the same World object detail;
3. world-global facts remain present;
4. incoming and outgoing relationships are both present with correct direction;
5. selected-node attributes are complete;
6. related endpoint nodes required by every edge are present;
7. evidence refs are complete for returned object facts;
8. exact S25 evidence hydrates from S25 source;
9. exact S24 evidence hydrates from S24 source while request focus is S25;
10. two source revisions under one artifact never resolve by “latest”; exact authority binding chooses the correct revision or fails closed;
11. manual-seed/no-span evidence remains visible with `no_source_span`, not fabricated prose;
12. missing durable source leaves graph fact visible with honest provenance status;
13. source batch read executes once for N distinct evidence sources;
14. zero filesystem reads are required for provenance;
15. World head/revision remains unchanged;
16. explicit partial/truncation cannot masquerade as complete;
17. same core edge observed in multiple source sessions remains compatible support without losing source-time provenance;
18. different occurrence time remains distinct in the response and fingerprint;
19. different/open/closed valid-time intervals remain distinct and visible;
20. an ended/superseded historical relationship is not silently erased merely because a later assertion exists;
21. no `latest session wins` or `source_time == occurrence_time` reduction is introduced.

### Cross-surface semantic parity

Using one fixture/full response for the same node/revision, prove the semantic fingerprint is unchanged through:

```text
Ingest
Plan
Build
Play
Agent selected-object context
```

Surface actions/chrome may differ.

### Build safety regression

Prove broad read does not broaden write admission:

```text
C2 Build may inspect C1-scoped fact on same World object
C2 Build insertion of disallowed C1-scoped reference remains denied under existing write law
```

### Agent regressions

Prove:

- selected object uses full World detail, including temporal envelopes;
- generic/open-ended Agent graph query `scope_mode` default remains unchanged;
- focus still marks/ranks current session/campaign;
- graph summaries are not promoted to citation authority;
- truncation is explicit in Agent envelope/prompt block.

### Quality gates

Run the focused owning suites plus:

```bash
git diff --check
git diff --name-only 0d3dd6ce024f92bdcc7eacc4573f277ed8af2cfe...HEAD
```

UI build must pass if TypeScript production paths change.

---

## §19 Live product evidence before merge

Use durable `54330` World + `54331` APP-STATE. Do not mutate either authority except ordinary reads.

### Witness A — Karsemine from C2S25 Ingest

Open C2 Session 25 and select Karsemine.

Record:

```text
World revision
semantic object fingerprint
relationship count
attribute count
evidence count
distinct source bindings
complete/partial
request timing breakdown
```

Require visible relationship/source evidence including:

- S25 Lysandra evidence;
- S24 Hunter's Mark evidence;
- S24 Lysandra evidence;
- Questionable Company/manual-seed edge still visible without invented recap prose.

### Witness B — same Karsemine from Plan

Open a Plan context that can select/reference Karsemine.

Require same:

```text
revision
semantic object fingerprint
edge/evidence membership
provenance statuses
```

Plan-specific actions may differ.

### Witness C — same Karsemine from Build

Open Karsemine from Build.

Require same semantic fingerprint. Demonstrate that broad read does not weaken Build insertion/write admission.

### Witness D — same Karsemine from Play

Open Karsemine in Play/Runbook context.

Require same semantic fingerprint. Play occurrence/Threat sections may add information outside the semantic World fingerprint.

### Witness E — Agent

With Karsemine selected on a surface, ask a question that requires her graph context.

Record the pre-model graph context/trace, not private model reasoning.

Require the selected-object context to carry the same World revision and semantic fingerprint or an explicitly equivalent structured field set.

### Witness F — another node

Repeat on at least one unrelated object so Karsemine is demonstrably a witness, not special-case behavior.

### Highest-degree performance witness

Identify one practically high-degree C1/C2 node from authority data and record the full timing/count trace. This is the scaling witness.

---

## §20 Human STOP after merge

Do not auto-dispatch Stage 4.

The human STOP asks:

> **Can I now click a node anywhere in DungeonBuddy and trust that I am looking at the whole World object at this World revision, quickly, with source context wherever we possess exact durable source bytes, without historical relationships being erased?**

Concrete pass:

1. Ingest → Karsemine.
2. Plan → Karsemine.
3. Build → Karsemine.
4. Play → Karsemine.
5. Agent with Karsemine selected.
6. Repeat one other node.
7. Follow one relationship to another node and confirm the target also opens as its full object.

Classify remaining problems:

```text
A — full and correct
B — authoritative fact exists but missing from full-object projection
C — fact present; exact source bytes unavailable
D — fact/evidence genuinely absent from authority
E — full/trustworthy; presentation is ugly or hard to read
P — complete but materially too slow
```

Decision rule:

```text
mostly A/E, performance acceptable
  → Stage 4 presentation/composition is genuinely next

meaningful B
  → projection correctness repair

meaningful C
  → source coverage follow-up only where exact material can be recovered

meaningful D
  → authority/content investigation

P
  → performance/profile slice before styling
```

---

## §21 Stop conditions

Stop and report rather than improvising if:

- DungeonMind cannot return a complete selected-node one-hop neighborhood without Buddy reconstructing graph truth;
- authoritative evidence does not expose enough exact source revision/digest identity to hydrate APP-STATE safely;
- authority carries temporal_scope / TemporalEnvelopeV1 but the object read cannot preserve it losslessly;
- completeness would require graph writes or contribution replay;
- a new APP-STATE table/schema is required merely to perform the read;
- full-object projection requires loading the entire World graph per click;
- implementation introduces per-edge/per-source network or DB queries;
- cross-surface parity requires duplicating semantic object assemblers in each surface;
- Agent integration would need a separate graph semantics rather than the shared object detail;
- generic Agent query World-scope default would have to land to make selected-object parity work;
- Build read broadening would accidentally broaden write admission;
- source prose would need to be regenerated or inferred;
- a production path outside §4 + bounded discovery is required.

Report:

```text
Stop condition:
Owning boundary:
Observed authority capability:
Missing contract:
Why Buddy cannot safely compensate:
Proposed DungeonMind/Buddy successor:
State-authority update needed:
```

---

## §22 Acceptance rubric

- [ ] One capability: surface-neutral complete World-object projection.
- [ ] #696 merge and Stage 2C durable-source facts are backward-synced truthfully.
- [ ] Full object read is World-cross-campaign at the selected World revision.
- [ ] Current campaign/session are focus only, never admission filters.
- [ ] Current object means all admitted truth at that revision, not latest-fictional-time current-state.
- [ ] TemporalEnvelopeV1 / equivalent payload is preserved for assertions and relationships; source, occurrence, and valid time stay distinct.
- [ ] Ended/superseded relationships remain visible; no latest-session-wins reduction.
- [ ] Complete one-hop incoming + outgoing adjacency is returned or explicit partial blocks the completeness claim.
- [ ] Selected-node attributes/evidence are complete.
- [ ] Exact evidence→source revision binding is authoritative, never “latest artifact revision.”
- [ ] APP-STATE provenance hydration is one batched read.
- [ ] No filesystem provenance fallback.
- [ ] No graph writes/re-ingestion/source re-adoption.
- [ ] Ingest consumes the shared full-object semantic projection when a node is opened.
- [ ] Plan consumes the same semantic projection.
- [ ] Build consumes the same semantic projection without widening write admission.
- [ ] Play consumes the same semantic projection while preserving Play-local occurrence/Threat context.
- [ ] Agent selected-object context consumes the same semantic projection.
- [ ] Generic Agent graph query World-scope default remains a named successor (unchanged in this PR).
- [ ] Same node/revision yields same semantic fingerprint across surfaces, including temporal identity.
- [ ] Relationship navigation loads the target's full object through the same contract.
- [ ] Performance/count trace is recorded for Karsemine, an ordinary second node, and a high-degree node.
- [ ] No N+1 source/edge behavior.
- [ ] Stage 4 presentation remains NOT DONE.
- [ ] Human STOP remains mandatory after merge.
