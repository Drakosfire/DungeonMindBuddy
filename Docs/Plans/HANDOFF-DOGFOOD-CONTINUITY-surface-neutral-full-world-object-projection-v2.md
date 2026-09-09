---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / full World-object projection
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW → MERGE → HUMAN DOGFOOD
  - Canonical handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v2.md`
  - Supersedes: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v1.md`
  - Branch: `dogfood-continuity/surface-neutral-full-world-object-projection-v1`
  - Suggested PR title: `DOGFOOD-CONTINUITY: project complete World objects across surfaces`

  ## Product invariant
  A selected graph object has one complete admitted World view at an exact World
  revision. Ingest, Plan, Build, Play, and Agent consume that same semantic object.
  Surface/campaign/session context may rank, annotate, or constrain actions; it
  must not redefine object truth.

  ## Temporal boundary
  "Current World object" means current **authority revision**, not reduced
  fictional-present state. Source time, occurrence time, valid time, and unresolved
  temporal qualifiers exposed by authority must survive projection losslessly.

  ## Agent boundary
  Selected-object Agent context uses the same full-object projection as UI
  surfaces. Generic/open-ended Agent search retains its existing retrieval-scope
  policy in this PR; changing its default campaign/world lens is a successor.
---

# HANDOFF — DOGFOOD-CONTINUITY: surface-neutral full World object projection v2

**Created:** 2026-09-08  
**Status:** CODE Cycle 3 repairing Cycle 2 HOLD (`5157501379` on `4e3d04e622543c315c27005c4e36863eaad33b6d`). Stage 4 remains NOT DONE.  
**Canonical handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v2.md`  
**Supersedes:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / full World-object projection`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW → MERGE → HUMAN DOGFOOD  
**PR:** #697  
**Cycle 1 reviewed head:** `612c30f9a5a33fb26a5ad7853070464583e7b216`  
**Implementation branch:** `dogfood-continuity/surface-neutral-full-world-object-projection-v1`  
**Product predecessor:** PR #696 merge `3e2abc0c7f8ce523b071716eb13bcf18d7979a2a`  
**Accepted #696 head:** `8f93138000c699a5d1249955003c91042f2053b1`

> This v2 handoff keeps the v1 full-object/cross-surface program but corrects two design ambiguities found in Review Cycle 1: temporal semantics and Agent retrieval scope. Where v2 conflicts with v1, **v2 wins**. Where v2 is silent, v1 remains supporting design context only.

---

## §0 Re-anchor

What is true now:

```text
PR #696                             MERGED
Stage 2C durable source coverage    23 source.artifact / 23 source.revision
historical ingest runs              53 unchanged
World authority                     DungeonMind 54330, read-only from Buddy
World head                          rev:680c246047d67f9fe0293ee90526f670
APP-STATE                           Buddy 54331
DungeonMind #52                     MERGED `d8f7a9f0d6b256f5cf4588987520bf286f1eade3`
                                    accepted head `bd0423da7ba917cb4010f173eeda2a3903430233`
PR #697                             DRAFT
#697 implementation                 CODE — `WorldGraphRetrievalService.get_complete_object`
#697 implementation head          `73ebf4976264b2a5bd1941419eee6868fc807c6a`
#697 live §13                    RECORDED — `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-pr697-complete-object-live-witnesses.md`
#697 Cycle 1                         DESIGN HOLD closed
#697 Cycle 2                         HOLD — `5157501379` on `4e3d04e622543c315c27005c4e36863eaad33b6d`
#697 Cycle 3                         CODE — UI partial honesty + Agent pre-model payload; production UI build required on this head
Stage 4                             NOT DONE
```

The human dogfood failure remains the trigger:

```text
C2S25 → Karsemine

S25 Lysandra evidence
  World edge visible
  exact S25 APP-STATE source durable
  source prose visible                     PASS

S24 Hunter's Mark evidence
  World edge visible
  exact S24 APP-STATE source durable
  source prose blank                       FAIL

S24 Lysandra evidence
  World edge visible
  exact S24 APP-STATE source durable
  source prose blank                       FAIL

manual_seed membership evidence
  World edge visible
  no recap span exists                     HONEST NO EXCERPT
```

This is not a Stage 2C durability failure. Buddy can see cross-session graph structure, but object-detail provenance hydration is still bound to the currently loaded source artifact.

The operator also clarified that Karsemine is only the witness:

> **For every selected node, show the complete admitted World object across all ingested material. Once we can do that correctly and fast, narrower views may be layered on top.**

And:

> **This must be the same object semantics in Ingest, Plan, Build, Play, and Agent.**

---

## §1 One capability

### Capability

**Surface-neutral complete World-object projection v1**

### Merge-ready invariant

> Given a selected World `node_id`, Buddy obtains one revision-pinned, GM-admissible, World-cross-campaign object projection containing the complete admitted one-hop neighborhood, selected-node attributes/assertions, evidence identities, and lossless temporal semantics exposed by DungeonMind; hydrates every eligible evidence span from its exact durable APP-STATE source revision in one bounded batch; and supplies that same semantic object to Ingest, Plan, Build, Play, and selected-object Agent context. Current surface/campaign/session context may rank, highlight, annotate, or govern actions, but may not determine which admitted World facts belong to the object. No graph writes, current-fiction-state reduction, source re-adoption, filesystem provenance fallback, or per-edge/per-source N+1 behavior is introduced.

### Independent usefulness

After this PR, wherever a user opens a graph object, the product can answer:

> **What does the current DungeonMind World revision know about this object?**

It does **not** yet answer the different question:

> **What is true about this object at the latest point in fictional time?**

That distinction is normative.

---

## §2 Critical terminology — what “current” means

### Current World object

In this handoff:

> **“Current World object” means the complete admitted object at the selected/current DungeonMind World revision.**

It does **not** mean:

- facts reduced to the fictional present;
- only relationships whose valid time includes a presumed “now”;
- latest-session-only facts;
- latest-source-only facts;
- a destructive replacement of older assertions by newer ones.

Think:

```text
World revision R
    ↓
all admitted assertions touching node N at R
    ↓
retain provenance + temporal qualification
    ↓
complete semantic object projection
```

Not:

```text
World revision R
    ↓
try to infer fictional "now"
    ↓
collapse history to one present-state answer
```

### Why this matters

The graph is intentionally append/history oriented. Multiple admitted assertions may describe:

- repeated observations of the same persistent relationship;
- an event that happened earlier but was learned later;
- a state that begins or ends;
- a correction or superseding interpretation;
- an assertion whose fictional time is unknown;
- contradictory assertions that authority has not yet reduced.

This PR must preserve those distinctions rather than silently flatten them.

---

## §3 Temporal semantics are part of the object contract

DungeonMind already has a canonical temporal substrate through `TemporalEnvelopeV1` / `GraphContributionAssertion.temporal_scope`.

The relevant semantic lanes are:

```text
source_time
  where/when the assertion was recorded or observed

occurrence_time
  when the described event happened in the fiction

valid_time
  during what interval the state/relationship was true
```

Transaction/revision time remains owned by graph revision/contribution metadata and is not invented inside the temporal envelope.

### Required preservation rule

> **If authoritative DungeonMind object/attribute/relationship/evidence data exposes temporal semantics, Buddy must preserve them losslessly through the full-object read, product response, client adapter, shared semantic model, and selected-object Agent context.**

This includes:

- V1 `source_time`;
- V1 `occurrence_time`;
- V1 `valid_time`;
- legacy/unresolved temporal fields that DungeonMind exposes as unresolved semantic payload;
- campaign/session qualifiers that are temporal or tenancy metadata;
- explicit absence/unknown values without invented precision.

### Forbidden flattening

Do not reduce this:

```text
edge: Karsemine — holds → Hunter's Mark
temporal:
  source_time: session-24
  occurrence_time: null
  valid_time: null
```

into merely:

```text
Karsemine — holds → Hunter's Mark
session_ids: [session-24]
```

Session provenance is not a substitute for occurrence or valid time.

Likewise, if authority exposes two assertion-semantic records such as:

```text
A:
  predicate: commands
  valid_time: S13 → S18

B:
  predicate: commands
  valid_time: S21 → open
```

Buddy must not collapse them into one timeless `commands` statement merely because the endpoints/predicate match.

### Current-state reduction is explicitly out of scope

This PR does **not** implement:

- a fictional “now” clock;
- timeline ordering across incompatible calendars/time systems;
- current-state reduction;
- temporal conflict resolution;
- interval closure inference;
- “latest wins” semantics;
- model-generated temporal interpretation;
- timeline UI.

If a consumer wants “what is true now?” later, that will be a reducer/view over the preserved temporal assertions—not a reason to discard history here.

---

## §4 Authority model

```text
DungeonMind World @ exact revision
  owns:
    node identity
    admitted attributes/assertions
    admitted relationships
    evidence identity
    campaign tenancy
    visibility/admissibility
    temporal semantics
    source-artifact/source-revision binding when exposed

Buddy APP-STATE
  owns:
    exact durable source bytes
    immutable source revision identity

Surface context
  owns:
    origin surface
    current document/run
    narrative campaign/session focus
    selected object
    available actions

Full-object product projection
  joins these without changing World truth
```

### Forbidden authority inversion

Buddy must not:

- reconstruct graph truth from source files;
- use the current document to decide which World facts exist;
- use current campaign/session as an object-detail admission wall;
- choose a latest APP-STATE source revision for convenience;
- infer missing temporal bounds;
- declare a newer assertion to supersede an older one unless DungeonMind already exposes that semantic;
- remove historical assertions to create a cleaner “present” object;
- generate biography/summary prose and treat it as graph truth.

---

## §5 Selected-object authoritative read

The product wants a **complete selected object**, not a whole-World dump.

A successful logical read must represent, for the selected node at one exact World revision:

```text
selected node
all admitted selected-node attributes/assertions
all admitted incoming one-hop relationships
all admitted outgoing one-hop relationships
all related endpoint nodes needed to understand those relationships
all supporting evidence refs exposed for those facts
campaign tenancy/scope
lossless temporal semantics exposed for selected-node facts
authoritative source binding metadata needed for exact provenance hydration
explicit completeness/truncation state
```

### Scope

The authoritative read is World-cross-campaign.

Current campaign/session may be passed as focus metadata for:

- focus flags;
- rank hints;
- UI highlighting;
- Agent relevance annotation.

They must not suppress otherwise admitted facts.

### Completeness

A response called `complete` must not silently inherit existing low retrieval caps such as 12 nodes / 24 relationships.

If DungeonMind cannot provide the complete selected-node one-hop neighborhood with explicit completeness semantics:

> **STOP and require a DungeonMind read-contract successor.**

Buddy must not fake completeness by unioning search/projection fragments.

---

## §6 Exact multi-source provenance hydration

For every evidence record supporting the selected object:

```text
DungeonMind evidence identity
    ↓
exact authoritative source artifact + revision/digest binding
    ↓
deduplicate bindings
    ↓
ONE bounded APP-STATE batch read
    ↓
exact source bytes
    ↓
resolve source span/excerpt if possible
    ↓
attach provenance to correct semantic fact
```

### Exact identity requirement

Stage 2C permits multiple immutable source revisions beneath one artifact identity.

Therefore forbidden:

```text
latest source revision for artifact X
```

Required:

```text
exact authority-supported source revision/digest
```

If DungeonMind does not expose enough information to bind evidence safely to an exact durable source revision:

> **STOP. Do not infer from filename, session, chronology, latest revision, or span prefix.**

### Provenance statuses

Retain structured distinctions such as:

```text
excerpt_ready
no_source_span
source_not_durable
unsupported_source_media
source_binding_unavailable
span_unresolvable
```

Missing prose must never hide the graph fact.

---

## §7 Cross-surface semantic identity

The same selected object must have the same underlying semantic payload from:

```text
Ingest
Plan
Build
Play
Agent selected-object context
```

Surface-specific chrome/actions may differ.

### Semantic identity key

At minimum:

```text
(world_id, revision_id, node_id, admissibility)
```

### Semantic fingerprint

Tests/debug evidence should compute a deterministic fingerprint over sorted semantic content including:

```text
revision_id
node_id
selected-node attribute/assertion identities
relationship edge/assertion identities + direction
related node ids
evidence ref ids
campaign tenancy/scope
exact durable source revision ids/digests when available
provenance status
canonical temporal semantic payload for every temporally qualified fact
```

Do not include:

- originating surface;
- UI order;
- focus rank;
- available buttons/actions;
- presentation copy.

### Temporal parity regression

Cross-surface parity must fail if two surfaces contain the same edge ID but different temporal semantics.

Example:

```text
Surface A
  edge X
  valid_time: S5 → S12

Surface B
  edge X
  valid_time: S5 → open
```

Those are **not** semantically identical.

---

## §8 Ingest, Plan, Build, and Play directives

### Ingest

Historical recap load may remain lightweight for document rendering/mention detection.

Opening a graph object must call the shared full-object seam:

```text
recap mention
  → node id
  → full World object read
  → batched multi-source provenance
  → shared semantic object
```

C2S25 Karsemine must be able to show S24 and S25 evidence together when exact bindings/spans exist.

### Plan

Plan must consume the same shared semantic object. Plan may add authoring actions and source navigation; it may not maintain a Plan-specific graph assembler.

### Build

Separate **read truth** from **write/insert admission**.

A Build document may inspect the full same-World object across campaign scopes while existing insertion/write restrictions remain unchanged.

Broad read must not broaden Build write authority.

### Play

Play's World section consumes the same semantic object. Runbook occurrence, Threat, and Combat context remain Play-local additions.

The current Scene/Beat/Runbook must not restrict World object membership.

---

## §9 Agent directive — selected object belongs here

The Agent must not receive a sixth graph-object semantics.

### In scope

When a surface has an active selected graph object, publish sufficient identity/context to Agent:

```text
world_id
node_id
revision_id or exact/head binding
origin surface
focus campaign/session
```

Before the model call, Agent selected-object context must resolve through the **same full-object service** used by UI surfaces.

The Agent receives:

- the same selected-node facts;
- the same one-hop relationships;
- the same evidence identities;
- the same provenance statuses/excerpts allowed by citation policy;
- the same temporal semantics;
- the same completeness/truncation state;
- the same semantic fingerprint or equivalent structured payload.

This is required for #697.

### Citation boundary

Structured World memory is not automatically quotation authority.

Exact APP-STATE excerpts may be supplied only under the existing source/citation contract. Graph summaries/labels must not masquerade as source quotations.

---

## §10 Agent directive — generic retrieval policy does NOT belong here

The existing generic/open-ended Agent graph retrieval path currently has its own search-scope policy, including campaign-scoped behavior.

#697 must **not** globally change that default merely to satisfy selected-object parity.

### Why

Generic discovery/search policy independently changes:

- recall;
- relevance/noise;
- token volume;
- ranking;
- latency;
- cross-campaign bleed;
- evaluation expectations;
- interpretation of surface focus.

It is independently useful, independently testable, and independently revertible.

Therefore it is a separate capability under repository decomposition law.

### Required #697 behavior

```text
Selected object
  → complete World-cross-campaign semantic object

Generic/open-ended Agent search
  → preserve current retrieval-scope behavior
```

Do not change the global default of `AgentWorldGraphQueryContextRequest.scope_mode` in this PR unless a narrowly necessary compatibility change leaves behavior identical.

### Named successor

Record a successor capability along the lines of:

**Agent World-memory retrieval policy**

Questions for that successor:

- Should open-ended Agent search query the whole World by default?
- Should current campaign/session instead be strong ranking signals over World-wide retrieval?
- When should the Agent expand a retrieved node to its complete object?
- How should token/latency budgets constrain graph discovery without redefining graph truth?
- What evaluation set proves useful cross-campaign recall without overwhelming current-session relevance?

A likely candidate architecture may be:

```text
search whole World
    ↓
rank strongly by current campaign/session + user query
    ↓
select bounded relevant node identities
    ↓
expand selected/relevant nodes through full-object projection
```

But that is **not decided by #697**.

### Architectural law

> **Graph truth scope and retrieval search scope are separate contracts.**

Selected-object truth should be complete. Discovery may intentionally be selective.

---

## §11 Performance and observability

“The whole thing at need and fast” remains a merge requirement.

Expected logical operation budget per selected-object request:

```text
DungeonMind authoritative object read     1 logical operation
APP-STATE exact source batch read          1 operation
per-edge World reads                       0
per-edge APP-STATE reads                   0
filesystem provenance reads                0
post-response click provenance fetches     0
```

If DungeonMind requires authoritative pagination/cursors internally, that may still be one logical product operation, but it must preserve deterministic completeness semantics and may not degrade into arbitrary Buddy-side unioning.

Record at least:

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
relationship_count
attribute/assertion_count
evidence_count
temporally_qualified_fact_count
distinct_source_binding_count
durable_source_hit_count
durable_source_miss_count
excerpt_count
completeness
truncated_fields
```

Do not log source prose.

Warm local witnesses remain:

- Karsemine;
- one unrelated ordinary object;
- one practically high-degree C1/C2 object.

Repeated ordinary-object server total above ~750 ms is an investigation threshold, not an accepted baseline.

---

## §12 Required automated evidence

### Full-object semantics

Prove:

1. prior-session edges remain under later-session focus;
2. other-campaign facts remain under current-campaign focus;
3. world-global facts remain;
4. incoming + outgoing relationships preserve direction;
5. all selected-node attributes/assertions are represented;
6. related endpoint nodes required by relationships are represented;
7. evidence refs supporting returned facts are represented;
8. explicit partial/truncation cannot masquerade as complete.

### Temporal preservation

Prove:

9. `source_time` survives authority → Buddy response → client semantic model;
10. `occurrence_time` survives independently of source session;
11. `valid_time` survives independently of source session;
12. unresolved/legacy temporal payload exposed by authority is not silently dropped or rewritten;
13. unknown temporal values remain unknown—no invented session/date;
14. same edge identity + different temporal semantics produces different semantic fingerprint;
15. current-session focus/ranking does not mutate temporal payload;
16. no current-fiction-state reduction occurs.

### Provenance

Prove:

17. S25 evidence hydrates from S25 exact source;
18. S24 evidence hydrates from S24 exact source while focus remains S25;
19. multiple revisions under one artifact never resolve by “latest”;
20. manual-seed/no-span evidence remains visible without fabricated prose;
21. missing durable source leaves the graph fact visible with honest status;
22. exact source batch read executes once for N bindings;
23. zero runtime filesystem provenance reads.

### Cross-surface parity

Using one canonical full-object fixture/response, prove identical semantic fingerprint through:

```text
Ingest
Plan
Build
Play
Agent selected-object context
```

Surface actions/chrome/focus order may differ.

### Build safety

Prove broad read does not broaden insertion/write admission.

### Agent safety

Prove:

- selected-object Agent context uses shared full object;
- temporal semantics survive into the structured Agent context;
- completeness/truncation survives;
- graph summaries do not become citation authority;
- **generic Agent retrieval default remains behaviorally unchanged**.

Cycle 3 UI/Agent repairs are proven by:

```text
uv run pytest tests/test_world_graph_object_projection.py -k 'not source_markdown_batch'
cd apps/live-control-ui && npm test -- --run \
  src/graphReference/ResolvedGraphObjectProjection.test.tsx \
  src/buildSurface/BuildGraphObjectContext.test.tsx \
  src/playSurface/reference/PlayGraphObjectSheet.test.tsx
cd apps/live-control-ui && npm run build
```

Live Eldyrwild §13 was not repeated; selected-object service timing was not materially changed.

---

## §13 Live acceptance witnesses

Recorded on implementation head `73ebf4976264b2a5bd1941419eee6868fc807c6a` against World head `rev:680c246047d67f9fe0293ee90526f670`. Full sanitized table: `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-pr697-complete-object-live-witnesses.md`.

```text
Karsemine five-consumer fingerprint
  790f70ea85b8dc5afa3413b52098b813cbbc8cd19bbde07cbabcbb3a9636c331
  Ingest / Plan / Build / Play / Agent selected-object
  same revision, completeness=complete

S25 Lysandra          excerpt_ready 3/3
S24 Hunter's Mark     excerpt_ready 6/6 (item-008)
manual-seed           visible, source_not_durable, no fabricated excerpt
temporal              kind=unknown retained (16 qualified facts)
unrelated             npc_glowkindle under C2 focus, complete, 521 ms
high-degree           pc:stafl 24 rels complete, truncated_fields=[]
N+1                   complete_object + one source batch per found object;
                      get_source_markdown = 0
generic Agent         scope_mode=campaign, selected_node_id=None
Build write admission tests still deny C1-object-on-C2-document
```

Human STOP after merge still requires the running UI click path. Relationship navigation was not live-clicked in this witness set.

### A — Ingest / Karsemine / C2S25

Require:

- exact World revision;
- complete object status;
- S25 Lysandra evidence + source prose;
- S24 Hunter's Mark evidence + source prose if exact authoritative binding/span resolves;
- S24 Lysandra evidence + source prose if exact authoritative binding/span resolves;
- manual-seed membership edge still visible without fabricated prose;
- temporal payload visible in trace/debug evidence for any qualified facts;
- timing/count trace.

### B — Plan / same Karsemine

Require identical semantic fingerprint and temporal payload.

### C — Build / same Karsemine

Require identical semantic fingerprint and temporal payload; demonstrate existing write/insert restrictions remain.

### D — Play / same Karsemine

Require identical semantic fingerprint and temporal payload; Play-local occurrence/Threat sections remain outside the World semantic fingerprint.

### E — Agent selected object

With Karsemine selected, record pre-model structured graph context/trace—not private reasoning.

Require same World revision + same semantic fingerprint/equivalent semantic payload including temporal qualification.

### F — unrelated object

Repeat on at least one other node so Karsemine is demonstrably a witness rather than a special case.

### G — high-degree node

Record complete counts and timing. No N+1 signature as degree/evidence count rises.

---

## §14 Explicitly out of scope

Do not absorb:

- current-fiction-state reduction;
- fictional-now semantics;
- timeline UI;
- temporal extraction/model inference;
- temporal conflict resolution;
- graph writes;
- Agent autonomous graph writes;
- generic Agent campaign→World search-default change;
- new Agent retrieval/ranking policy;
- Stage 4 copy/styling/composition redesign;
- source re-adoption/re-ingestion;
- Build write-policy broadening;
- persistent caching infrastructure;
- prefetching every graph object in a document;
- Threat/Combat redesign.

---

## §15 Stop conditions

Stop and rebrief if:

- DungeonMind cannot provide a complete selected-node one-hop read without Buddy reconstructing graph truth;
- authoritative object read drops temporal semantics that exist in durable assertions;
- temporal preservation would require Buddy to invent/reinterpret time rather than pass through authority semantics;
- authoritative evidence lacks enough exact source revision/digest identity for safe APP-STATE hydration;
- implementation requires graph writes/contribution replay;
- implementation requires a new APP-STATE schema/table merely for this read;
- implementation introduces per-edge/per-source World or APP-STATE reads;
- cross-surface parity requires separate semantic assemblers;
- Build broad read weakens write admission;
- Agent selected-object parity can only be achieved by globally changing generic Agent retrieval scope;
- source prose must be regenerated/inferred;
- production paths exceed the write lease + bounded discovery.

Report:

```text
Stop condition:
Owning boundary:
Observed capability:
Missing contract:
Why Buddy cannot safely compensate:
Proposed successor:
State-authority update required:
```

---

## §16 Write lease corrections before CODE

The v1 expected production paths remain the working implementation lease, subject to bounded discovery.

Before CODE begins, explicitly include backward-looking state-authority sync in this PR lease:

```text
Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v1.md
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v2.md
```

Required predecessor sync:

- PR #696 MERGED;
- accepted #696 head `8f93138000c699a5d1249955003c91042f2053b1`;
- Stage 2C broad exact-source adoption succeeded;
- human follow-up classified same-session provenance as working and cross-source hydration as the next barrier;
- Stage 2 remains human-STOP governed;
- Stage 4 remains NOT DONE;
- generic Agent World-memory retrieval policy is a successor, not silently completed by #697.

Do not rewrite unrelated roadmap history.

---

## §17 Acceptance rubric

- [x] One capability remains: surface-neutral complete World-object projection.
- [x] “Current” explicitly means current World revision, not fictional-present reduction.
- [x] Full object read is World-cross-campaign.
- [x] Current campaign/session are focus only.
- [x] Complete one-hop incoming/outgoing adjacency is returned or explicit partial blocks completeness claims.
- [x] Selected-node attributes/assertions and evidence are complete.
- [x] Temporal semantics exposed by authority survive losslessly.
- [x] No current-fiction-state reducer is introduced.
- [x] Same edge identity with different temporal semantics cannot fingerprint as identical.
- [x] Exact evidence→source revision binding is authoritative, never latest-artifact inference.
- [x] APP-STATE provenance hydration is one bounded batch read.
- [x] No filesystem provenance fallback.
- [x] Ingest consumes the shared semantic object when opened.
- [x] Plan consumes the same semantic object.
- [x] Build consumes the same semantic object without widening write admission.
- [x] Play consumes the same semantic object while retaining Play-local context.
- [x] Agent selected-object context consumes the same semantic object.
- [x] Generic/open-ended Agent retrieval policy remains behaviorally unchanged.
- [x] Agent World-memory retrieval policy is recorded as a successor capability.
- [x] Same node/revision yields the same semantic fingerprint across all five consumers.
- [ ] Relationship navigation loads the target through the same full-object contract.
- [x] Performance/count/temporal trace is recorded for Karsemine, one unrelated node, and one high-degree node.
- [x] No N+1 source/edge behavior.
- [x] #696 / Stage 2C predecessor state is synced into roadmap + steward anchor.
- [x] Stage 4 remains NOT DONE.
- [ ] Human STOP remains mandatory after merge.

---

## §18 Human STOP after merge

Do not auto-dispatch Stage 4 or Agent retrieval-policy work.

The human asks:

> **Can I click a node anywhere in DungeonBuddy and trust that I am seeing the complete admitted object from the current World revision—including its historical/temporal qualification and source context—quickly and consistently across surfaces?**

Run:

1. Ingest → Karsemine.
2. Plan → Karsemine.
3. Build → Karsemine.
4. Play → Karsemine.
5. Agent with Karsemine selected.
6. Repeat another node.
7. Follow a relationship and inspect the target object.
8. Inspect at least one temporally qualified fact and verify no flattening.

Classify:

```text
A — complete and correct
B — authoritative fact missing from full-object projection
C — fact present; exact source bytes unavailable
D — fact/evidence genuinely absent from authority
T — temporal semantics lost/flattened
E — trustworthy but presentation poor
P — complete but materially too slow
```

Decision:

```text
mostly A/E and performance acceptable
  → Stage 4 presentation/composition becomes a strong next candidate

meaningful B
  → projection correctness repair

meaningful C
  → source-coverage follow-up only where exact bytes can be recovered

meaningful D
  → authority/content investigation

T
  → temporal projection-fidelity repair before presentation work

P
  → profile/performance slice before styling
```

Generic Agent World-memory retrieval policy remains separately schedulable after this STOP.
