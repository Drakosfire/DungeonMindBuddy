# Magic Moment Dogfood — R0-B

**Date:** 2026-07-30  
**Operator:** GM (guided dogfood)  
**Repository SHA:** pending capture from live session  
**World / campaign:** `eldyrwild` / `longmont-c2`  
**Graph revision:** pending capture from Hermes response  
**Result:** `IN_PROGRESS`

## Intent

Prove the user-facing Hermes path can investigate a difficult question across
the admitted unioned graph and produce a grounded, editable Threat description.

## Questions attempted

### Question 1 — meat corruption / Mireward / Shepherds

Hermes correctly reported that the meat-goo and cult-corruption threads are
concrete, while a literal buried or singing entity is not established. It
connected the Mireward hotspot, the unresolved Shepherd lead, and the
wall/ceiling meat creature with the wolf-head imagery. It recommended
escalating the existing meat-linked ceiling climber rather than inventing a
new mystery.

### Question 2 — swamp fear / kin denial / cult framing

Hermes connected the swamp link to the Shepherd or Shepherd's flock, the
Mireward crisis to cultists, and the stronger meat-corruption thread to
tainted meat, trance-like behavior, and fleshy constructs. It proposed a
flesh-born corruptor or meat-driven influence acting through existing
cultists, without inventing a new cult name.

### Question 3 — festival cover story / thin Mireward garrison

> If Mirathorn’s festival story is a lie and Mireward’s spears are thin, what
> Threat exploits that gap — and what corpus support do we have for what is
> actually coming up the road?

Hermes identified the already-established rebel faction at Mirathorn Gates as
the likely threat that could exploit a false festival cover story. It connected
the faction to disruption at the gates and threats against the Captain, while
keeping the Mireward Road support narrower than the prose implied.

This was a good honesty result: Hermes explicitly said the available source
anchors were unreadable/unsupported and declined to quote or invent exact road
details. It still used retrieval-meta phrasing (“in graph terms,” “the graph
confirms”) that should move into chips/evidence support rather than the
campaign-facing answer.

### Question 4 — float goat → mutated Threat description

> Learn about float goats, then write up a mutated float goat statblock
> description that I can copy and paste. Be verbose.

This is the first probe that produced the requested authoring artifact. Hermes
identified Bubbles as a named float goat with a flood-survival arc, then
produced a copy-pasteable **Mutated Float Goat** description with flavor tags
and an in-play description. It stopped short of inventing AC, HP, speed, or
actions and offered those as a separate future step.

Content assessment: **provisional pass** for the editable-description portion
of R0-B. The result is useful and pasteable, but it still says “In the graph”
in the campaign-facing prose. It also introduces “alchemical runoff,”
“river-haunted,” and similar mutation details without labeling them as
creative additions. The future authoring skill should preserve the creative
brief while making the established-vs-proposed boundary explicit.

## Dogfood feedback — authoring needs a copyable dynamic markdown block

The response contains the desired artifact, but it is embedded in a long
conversation transcript. The operator wants the authoring skill to instruct
Hermes to emit a dedicated dynamic UI markdown artifact for sections intended
to be copied into a ThreatDraft or another document.

The missing capability is both behavioral and infrastructural:

- **Skill instruction:** when the user asks for a copyable section, produce a
  structured markdown artifact rather than only prose in the answer.
- **Tool/UI contract:** render that artifact in a distinct card with
  `Copy markdown`, optional edit-before-copy, clear title, and a stable
  artifact identity.
- **Boundary:** copied markdown should contain the campaign-facing description,
  not “in the graph” language or internal trace metadata. Provenance and
  uncertainty support should remain adjacent as chips/evidence controls.

This is not currently available, so the existing response is a provisional
content pass with avoidable copy friction.

## Durable identities

- retrieval session: not shown; Hermes session pointer was accepted
- selected / matched node IDs: `mystery:session3:mirathorn_festival`,
  `event:longmont-c2:session-22:mireward-road`,
  `node:rebel_group_mirathorn_gates`, plus 5 more hidden by the trace preview
- admitted source anchors: 3 visible, plus 11 more hidden by the trace preview
- graph revision: `rev:480267555eda00356cdb6d843b08b93c`
- graph head status: not shown; trace reports `fresh_graph_revision_used: yes`
- draft / Threat IDs: not created; R0-B does not require automated handoff

### Trace metadata captured

- trace ID: `agent-trace-8599af8cd4d4`
- focus: `session-24`
- world / campaign: `eldyrwild` / `longmont-c2`
- admissibility: `gm`
- process: `hermes_graph_agent` / `process_isolated`
- total duration: `61977ms`
- graph tool activity: 6 events
- visible diagnostics: `result_truncated`, `unreadable_source_anchors`,
  `too_many_targets`, `dmb_world_graph_retrieval_error_v1`
- visible warnings: incomplete source verification; recovered cardinality /
  retrieval errors and answered from landed claims
- token usage: not reported

The trace is sufficient to establish that the live Hermes turn ran against a
specific pinned revision and recorded tool activity, timings, matched graph
objects, source anchors, diagnostics, and recovery behavior. The trace UI
currently clips the durable ID lists and omits explicit `is_head` and
retrieval-session fields; those remain metadata-surface gaps, not reasons to
discard this dogfood evidence.

## What felt magical

- Hermes synthesized multiple relationships instead of answering from one
  obvious source.
- It challenged the premise that a buried/singing entity was established.
- It kept the Shepherd unresolved rather than laundering inference into canon.
- It produced useful Threat directions without inventing a named faction.

## Friction and misses

1. Response latency was long enough that the operator could not tell whether
   Hermes was working or stalled.
2. The UI did not provide meaningful live progress or a latency explanation.
3. Hermes named retrieved entities in prose, but the response did not expose
   those entities as inspectable graph chips.
4. Continuing the investigation requires manually retyping names from the
   answer into the next question.
5. The answers did not yet produce a clearly labeled
   `established / inferred / creative proposal / unknown` breakdown plus a
   paste-ready Threat description.
6. Hermes is effectively a black box to the operator. Backend traces exist,
   but they are not available as live progress or durable performance
   telemetry.
7. Submitted questions remain in the composer until the request resolves
   instead of immediately becoming a user-side transcript bubble.
8. The composer is a one-row textarea. Two lines of text already become
   cramped and partially scrolled, which makes composing a serious
   multi-part question unpleasant.
9. The paste-ready Threat description is embedded in transcript prose; there
   is no dedicated copyable markdown artifact or artifact-level edit/copy
   control.

## Dogfood feedback — composer should behave like chat

On submit, move the question immediately from the composer into the
conversation as the user's bubble and clear the composer for the next action.
The pending assistant side should then show an honest working state tied to
that same turn.

Replace the one-row textarea with a comfortable auto-growing composer:

- start at several readable lines rather than `rows=1`;
- grow with wrapped content up to a sensible maximum;
- scroll only after the maximum is reached;
- preserve keyboard submit behavior intentionally (for example,
  `Enter` submits and `Shift+Enter` adds a line, or make the choice explicit);
- keep long questions readable while Hermes is working.

## Dogfood feedback — keep retrieval machinery out of the answer voice

The Bubbles / Float Goat probe produced a useful answer, but it referred to
its own retrieval machinery repeatedly: “in graph terms,” “there’s no graph
evidence,” and “the current graph points to…”. The operator wants the agent to
answer in campaign language and let the UI carry provenance.

Preferred behavior:

- Say **“Bubbles is a named float goat tied to the Stone Bridge flood and
  later seen in Outtown”**, not “in graph terms, it is…”.
- Say **“I couldn’t substantiate a connection between Bubbles and Mireward”**,
  not “there’s no graph evidence for that.”
- Keep node identity, graph revision, source anchors, and retrieval coverage in
  chips, evidence cards, and expandable support—not in every paragraph.
- Mention the graph, retrieval, nodes, or sources explicitly only when the user
  asks how the answer was established or when a coverage limitation itself is
  the answer.

This is complementary to the graph-chip slice: chips should make provenance
more visible in the interface so the model can be less meta in its prose.

## Dogfood feedback — graph chips

The operator proposed that retrieved nodes should be matched against answer
text and rendered as chips, with the ability to point to nodes in the next
query.

Required authority boundary:

```text
retrieved nodes = evidence context
regex / alias matching = presentation only
query chips = explicit user intent
```

Inline matching must be restricted to nodes retrieved for the turn and must
not create citations or promote arbitrary text to canon. A retrieved-node
rail should expose nodes not mentioned verbatim. Clicking a chip should open
the node/evidence card and offer **Add to question**. Query chips should send
stable node IDs and the pinned graph revision separately from free text.

This is recorded as the smallest likely bridge between Hermes retrieval,
grounded authoring, and the future ThreatDraft handoff:

- backlog: **Hermes needs grounded graph chips in answers and queries**;
- related backlog: **Grounded answer → Threat seed needs an authoring skill**.

## Dogfood feedback — liveness and telemetry

Immediate UX requirement: show truthful in-flight state, elapsed time, the
active question/thread, and honest stale/recovery behavior. Do not invent
retrieval stages until the backend exposes lifecycle events.

Longer-term requirement: operationalize the existing `agent_trace` and
`tool_events` into privacy-safe turn telemetry covering total/per-tool
duration, retrieval counts, outcomes, diagnostics, worker state, and model or
provider provenance when available. Do not persist raw corpus text or full
prompt/response payloads in telemetry.

## Gate status

The authoring artifact now exists, so the content portion of R0-B is
provisionally satisfied. The overall report remains `IN_PROGRESS` until the
authoring turn’s exact trace metadata is captured and the final verdict is
recorded. The incomplete/unreadable source warnings remain honest
qualification, not automatic failure.

## Required next slice

Capture the authoring turn’s trace metadata, record the final R0-B verdict,
then re-anchor one smallest slice from the observed friction. The strongest
candidate is the graph-chip/query-anchor seam, which would let future answers
stay in campaign voice while preserving inspectable provenance.
