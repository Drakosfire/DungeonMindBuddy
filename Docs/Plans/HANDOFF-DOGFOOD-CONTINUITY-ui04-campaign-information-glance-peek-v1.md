# HANDOFF — DOGFOOD-CONTINUITY: UI-04 campaign-information glance + peek v1

**Created:** 2026-09-17  
**Status:** MERGED — PR #733 at `fd9a42501c8616d27fa1436a7b66fc6a6dfe3347` (accepted head `d10c66dcd980d3b9dd9d7594938feb22413677a0`)  
**Canonical path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui04-campaign-information-glance-peek-v1.md`  
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY / UI language / Stage 4 WOW`  
**Steward outcome:** **B — one bounded UX defect dominates**  
**Design base:** `main@b7d44a07bdbfc420f64396456704aba2fabb5af8`  
**Human evidence:** `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`  
**PR topology:** `serial`  
**Implementation branch / PR:** `dogfood-continuity/ui04-campaign-information-glance-peek-v1` / #733  
**Named successor:** [`HANDOFF-DOGFOOD-CONTINUITY-ui05-floating-world-object-peek-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-ui05-floating-world-object-peek-v1.md) — floating Peek inspector after post-merge duplicate-close dogfood; unauthorized #734 closed without merge

> This is an implementation handoff, not permission to redesign campaign-memory semantics. The first click must become useful without pretending the graph knows things it does not know.

---

## §0 Mission

The Stage 4 human WOW pass is recorded and **not satisfied**.

The first World reference failed before the operator could appreciate the campaign memory behind it:

```text
pill draws attention
→ hover is empty or graph-shaped
→ click says "World Object"
→ nested Details / Advanced
→ huge captured prose
→ relationship rows such as "Misty Step · possesses"
→ operator is unimpressed and confused
```

Later exploration proved the underlying interaction can create pull:

- the **hole** glance was useful;
- closing Peek preserved the recap;
- C1 **Cultists / Dustwalker Leads** exposed surprising cross-campaign connection;
- operator: **“want more / impressed.”**

The bounded product question is therefore:

> **When a recap pill earns attention, can glance and Peek repay it with compact campaign information instead of graph chrome?**

### Primary invariant

```text
recap pill
→ truthful compact campaign glance
→ table-readable campaign-memory Peek
→ related campaign fact/object
→ close
→ same recap context
```

At every layer, graph identity, storage vocabulary, raw provenance, and destination-surface machinery are secondary.

---

## §1 Protect these accepted behaviors

Do not regress:

1. **Pills draw the eye.** The inline affordance is working.
2. **A useful glance can work.** “Swarms located in the hole” was useful.
3. **Peek is contextual, not navigation.** Closing the object returns to the recap intact.
4. **Cross-campaign memory creates pull.** C1 Cultists → C2 Dustwalker material made the operator want more.
5. **Threat specialization remains specialized.** Do not replace existing Threat glance/sheet behavior with the generic object treatment.
6. **Browse/write separation remains truthful.** This slice does not make ordinary recap browsing authorable.

---

## §2 Current-state hypothesis

The human pass exposed one presentation boundary with several symptoms.

### Chip

Ordinary recap pills encode role/kind through multiple colors, but the graph currently contains wrong kinds. A visually strong `ITEM` treatment therefore makes semantic error louder.

### Glance

The generic glance is built from:

```text
title
type
summary
"Why it matters here"
focus evidence / synthesized relationship + "this session"
```

That framing is too interpretive and too graph-derived.

Useful evidence already exists in resident node data, but it should be stated as a campaign fact rather than a judgment about importance.

### Peek

The ordinary recap Peek currently nests:

```text
World object
  → generic graph card
      → type/title/campaign
      → summary
      → relationship target · predicate
      → raw relationship provenance excerpt/domain
      → Details
      → Advanced
      → Continue in Build
```

This is structurally truthful and humanly backwards.

The selected object is omitted from relationship copy, so direction is hard to read:

```text
Misty Step · possesses
the wall crack and tunnel below it · located in
```

Raw captured recap prose and `session_recap` source vocabulary dominate space that should communicate campaign facts.

### Session continuity

The same pass found two navigation failures in the exact browsing path:

1. `Session 27` was rewritten to `longmont-c2:27`, after which the recap became unavailable.
2. Switching from C2 Session 26 to C1 retained Session 26 even though that session does not exist in C1.

These are not the visual design mission, but they abort the journey used to judge it. They are therefore serialized as **Gate 0** in this same lane.

---

## §3 Candidate-outcome worksheet

| Candidate | Decision | Why |
|---|---|---|
| Preserve inline pills as noticeable interaction affordances | **KEEP** | Human pass says they create curiosity. |
| Use ordinary pill color as ontology/kind truth | **CHANGE** | Wrong kinds are real; UI must not amplify uncertain ontology. |
| Generic glance title + compact truthful campaign fact | **INCLUDE** | Directly addresses first hover. |
| “Why it matters here” editorial framing | **REMOVE from ordinary glance** | Operator explicitly rejected it; present facts, not interpretation. |
| Redundant “this session” suffix | **REMOVE** | Focus is already contextual. |
| Empty glance filler/debug copy | **REJECT** | Do not fabricate usefulness. |
| Generic complete-object payload | **KEEP as data authority** | Retrieval is not the defect. |
| “World Object” outer chrome | **REMOVE from ordinary recap Peek** | Says nothing useful to the GM. |
| Selected-object-aware relationship sentences | **INCLUDE** | Fixes target-first graph grammar. |
| Raw relationship excerpt/domain in default scan path | **DEMOTE** | Provenance remains available, but not as the primary object presentation. |
| Huge summary/prose in default scan path | **BOUND / DISCLOSE** | Preserve bytes; reduce default visual footprint. |
| Continue in Build as primary recap-object action | **DEMOTE** | Known navigation trap; not campaign information. |
| Focus session qualified rewrite on Ingest | **GATE 0 REPAIR** | Aborts recap reading. |
| Carry stale C2 session into C1 | **GATE 0 REPAIR** | Aborts campaign switching. |
| Fix hybrid monsters / Swarms kind | **SPLIT — semantic successor** | Real, but not this dispatch. |
| Add missing PC / swarm pills | **SPLIT — semantic successor** | Real, but not this dispatch. |
| Deduplicate Thalia / enrich Ogonob | **SPLIT — semantic successor** | Requires memory-quality work. |
| Preserve open Peek across browser refresh | **SPLIT — NAV successor** | Observed, not the first-minutes blocker. |
| Tools/Author Node inventory redesign | **SPLIT** | Reached later in free exploration. |
| Highlight text → tell Agent it is a node → author the rest | **PARK** | Strong product direction; not this slice and not 7A1 by stealth. |
| 7A1 contextual Ask | **DO NOT DISPATCH** | Remains queued. |
| 16-question semantic gauntlet | **DO NOT DISPATCH** | Semantic thinness is known but presentation fails first. |

---

# §4 Product contract

## 4.1 Chip — attention without false ontology confidence

Ordinary recap pills remain visually distinct from prose.

For ordinary campaign-memory references:

> **Color means “interactive campaign memory,” not “this ontology classification is trustworthy.”**

Do not use strong ordinary role/kind-specific palette differences to imply reliable semantics while `item` / `threat` classification is known thin.

Allowed:

- one coherent ordinary-reference treatment;
- focus/keyboard/selected states;
- existing review/delta state where that state is actually meaningful;
- existing specialized Threat behavior when the payload already qualifies for the established Threat path.

Not allowed:

- “fixing” wrong kinds in frontend aliases;
- treating `item` as `threat` based on label heuristics;
- new color legend for graph ontology.

The operator should still notice pills. This is **not** a de-emphasis pass.

---

## 4.2 Glance — facts, not graph explanation

Ordinary glance should answer:

```text
What is this?
What compact campaign fact do we already know about it here?
```

Preferred scan order:

```text
Label
quiet type/role, if present
compact summary, if present
one useful current-focus relationship/fact, if present
```

### Rules

- Remove the ordinary `Why it matters here` heading.
- Do not append `this session` merely because the relationship is focus-anchored.
- A focus relationship must be rendered in subject-aware order.
- If there is no useful summary or relationship, render only truthful available identity/type. No “unknown,” no debug ids, no invented filler.
- Do not hide a wrong kind by rewriting it. Make type secondary enough that wrong semantic classification does not become the entire hover experience.
- Threat glance remains on the established Threat path.

Examples of desired tone:

```text
the hole
Location
Swarms located in the hole.
```

not:

```text
the hole
LOCATION
Why it matters here
Swarms located in the hole this session.
```

---

## 4.3 Peek — campaign-memory sheet, not graph-object inspector

The ordinary recap Peek consumes the same complete-object payload and exact revision/focus authority.

It changes presentation, not data authority.

### Header

The selected object's label is the object identity.

Do not render a redundant outer **World Object** title.

A quiet type / campaign stamp may remain.

Close remains obvious and returns to the same recap context.

### Summary

Campaign summary is useful when concise.

The default scan path must not become a wall of captured source prose.

Use a bounded presentation:

- visually clamp / limit the ordinary summary;
- preserve the full existing value behind an explicit disclosure if needed;
- do not model-summarize, truncate stored data, or invent replacement prose.

### Relationships

Relationships are campaign statements about the selected object.

The row must include the selected subject and respect edge direction.

For selected object **Ogonob**:

```text
Ogonob possesses Misty Step.
```

not:

```text
Misty Step · possesses
```

For an incoming edge, the related object becomes the subject.

Session/campaign stamps may stay compact when they add temporal/cross-campaign meaning.

Do not leak raw ids or `session_recap` into the ordinary relationship line.

### Provenance

Raw captured excerpts, source domains, evidence counts, graph identity, and revision details remain available but secondary.

Ordinary relationship rows must not dump full captured recap paragraphs by default.

The existing source/evidence contract is preserved; this slice may move that material under one quiet disclosure.

Do not remove source-read capability.

### Disclosures

The recap Peek should not feel like:

```text
World Object → card → Details → Advanced
```

Prefer one compact ordinary scan path and at most one clearly secondary disclosure for source/technical material.

Implementation may reuse the shared card with an explicit `campaign-memory` / `recap` mode rather than fork a second object renderer.

Do not globally change Plan/Build/Play card semantics merely to make Recap work.

### Actions

`Continue in Build` is not campaign information.

Do not leave it as a primary action in the ordinary recap Peek.

Preserve the underlying pointer/deep-link capability if still needed, but demote it behind secondary actions/disclosure or omit it from the recap presentation.

---

# §5 Gate 0 — Focus-session continuity repair

This gate is serialized before visual dogfood in the same implementation PR.

It is part of this lane because the bugs abort the exact Campaign → Session → recap journey needed to evaluate UI-04.

## 5.1 Ingest/Recap owns recap URL session identity

On ordinary Ingest recap browsing:

```text
?campaign=longmont-c2&session=session-27
```

must remain the recap identity.

The shared World Graph lens may consume that context.

It must not rewrite the Ingest recap URL into Plan-qualified lens syntax such as:

```text
session=longmont-c2:27
```

while ordinary recap browsing is active.

Qualified Plan graph-lens focus remains valid where Plan explicitly owns it.

Do not solve this by making the recap endpoint accept arbitrary qualified session IDs.

## 5.2 Campaign switch chooses a valid target-campaign session

Interactive campaign switch is an atomic context change.

If the operator is on:

```text
C2 / session-26
```

and switches to C1, do not retain `session-26` unless C1 actually offers it.

Resolve a valid target-campaign session from the target campaign's numeric recap artifacts, using the product's normal default/latest policy, and synchronize the URL/request to that exact value.

Do not issue a transient invalid C1/session-26 recap request simply because it was the old campaign's focus.

### Preserve explicit hard-link semantics

A direct hard load with an explicit session absent from the artifact listing may continue to fail truthfully as currently designed.

The bug is **interactive campaign context carry-over**, not “all invalid requested sessions must be silently replaced.”

## 5.3 STOP boundary

If fixing Gate 0 requires backend recap identity changes, new durable session vocabulary, or a broad AppChrome/router rewrite:

**STOP and return to steward.**

Do not absorb that into UI-04.

---

# §6 State / authority boundaries

This slice owns **presentation over already-trusted World Graph payloads** plus recap selection continuity.

It does not change:

- World Graph node/edge semantics;
- extraction prompts/models;
- candidate generation/admission;
- kind classification;
- identity resolution;
- source admission;
- revision selection contract;
- Agent context;
- graph authoring/write authority.

The selected recap World/campaign/revision/focus remains the exact authority for complete-object reads.

Do not fetch a second “prettier” object from another source.

Do not add a client-side semantic repair layer.

---

# §7 Expected write lease

Use a strict subset where possible.

## Gate 0 — session continuity

| Action | Path | Purpose |
|---|---|---|
| MODIFY | `apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx` | campaign/session selection must stay valid and URL-coherent |
| MODIFY if required | `apps/live-control-ui/src/graphLens/sessionCampaignContext.ts` | prevent Plan-qualified focus syntax from becoming Ingest recap identity |
| MODIFY if required | `apps/live-control-ui/src/graphLens/WorldGraphLensContext.tsx` | shared lens must consume Ingest context without rewriting it |
| MODIFY | `apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.test.tsx` | exact regression witnesses |
| MODIFY if required | `apps/live-control-ui/src/graphLens/sessionCampaignContext.test.ts` | surface-specific URL ownership regression |
| MODIFY if required | existing `WorldGraphLensContext` focused test | prove no Ingest URL rewrite |

## Chip + glance

| Action | Path | Purpose |
|---|---|---|
| MODIFY | `apps/live-control-ui/src/graphReference/GraphNodeHoverToken.tsx` | factual glance hierarchy |
| MODIFY | `apps/live-control-ui/src/graphReference/nodeGlancePresentation.ts` | remove editorial/redundant focus wording; subject-aware fact |
| MODIFY | `apps/live-control-ui/src/graphReference/graphReference.css` | ordinary pill/glance hierarchy; no false ontology color promise |
| MODIFY | `apps/live-control-ui/src/graphReference/GraphNodeHoverToken.test.tsx` | glance product-language regression |
| MODIFY | `apps/live-control-ui/src/graphReference/nodeGlancePresentation.test.ts` | resident-data fact synthesis regression |

## Peek

| Action | Path | Purpose |
|---|---|---|
| MODIFY | `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.tsx` | recap-specific Peek composition; remove redundant World Object / primary Build action |
| MODIFY | `apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.tsx` | pass explicit campaign-memory presentation mode if needed |
| MODIFY | `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx` | campaign-memory hierarchy/disclosure behavior |
| MODIFY | `apps/live-control-ui/src/graphObjectCard/graphObjectDisplay.ts` | subject-aware directional relationship copy |
| MODIFY if required | `apps/live-control-ui/src/graphObjectCard/types.ts` | explicit presentation mode / view-model support only |
| MODIFY | existing focused graph-object card/display tests | protect Plan defaults + prove campaign-memory behavior |
| CREATE if no focused projection test exists | `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx` | recap Peek witness only |

## Steward lease expansion after Review Cycle 1 handback

Review Cycle 1 localized the remaining disclosure problem to the existing technical-details wrapper. The worker's repair requires one adjacent production path not named in the original §7 table.

Explicitly add to the UI-04 Peek lease:

| Action | Path | Purpose |
|---|---|---|
| MODIFY | `apps/live-control-ui/src/graphReference/CompleteWorldObjectAdvancedDetails.tsx` | allow recap campaign-memory Peek to reuse the existing technical identity body inside the single Source disclosure without nesting a second Advanced disclosure; default behavior for all non-recap consumers must remain unchanged |

The accepted shape is additive/fail-safe: recap may request a bare body; default callers still receive the existing `Advanced` disclosure.

This expansion does not authorize broader changes to complete-object semantics or non-recap presentation.

## Durable report

CREATE:

`Docs/Reports/REPORT-DOGFOOD-CONTINUITY-ui04-campaign-information-glance-peek-v1.md`

No other production path is authorized without steward lease expansion.

---

# §8 Required regressions

## Gate 0

1. Hard load `/ingest?campaign=longmont-c2&session=session-27`.
2. Allow shared World Graph lens hydration/validation to settle.
3. URL remains `session=session-27`; no `longmont-c2:27` rewrite.
4. Recap remains available; no mystery switch to an unavailable recap identity.
5. From C2/session-26, switch campaign to C1.
6. The selected session becomes a valid numeric C1 recap session according to normal campaign default policy.
7. URL, picker, recap request, and displayed recap agree.
8. A direct explicit unavailable hard link still fails truthfully instead of being silently rewritten.

## Chip / glance

9. Ordinary recap pill remains visibly interactive and keyboard-accessible.
10. Ordinary role/kind colors do not pretend to be reliable ontology semantics.
11. Useful location glance can render:
    `the hole / Location / Swarms located in the hole.`
12. Ordinary glance does not render `Why it matters here`.
13. Focus-derived relationship does not append redundant `this session`.
14. Missing summary/context produces truthful identity-only glance, not debug filler.
15. Threat hover still uses the specialized Threat campaign glance.

## Peek

16. Opening a recap object does not display a redundant outer `World Object` heading.
17. Object label is the primary identity.
18. Default summary footprint is bounded; full stored content is not destroyed.
19. Relationship direction is readable with the selected subject:
    `Ogonob possesses Misty Step`.
20. Incoming relationship sentence reverses subject/object correctly.
21. Ordinary relationship rows do not show `· session_recap`.
22. Full raw source excerpt is not dumped under every relationship by default.
23. Source/provenance remains reachable through secondary disclosure.
24. `Continue in Build` is not a primary recap Peek action.
25. Following a relationship keeps the same Peek grammar and exact revision/focus.
26. Close returns to the recap without remount/navigation.
27. C1 object can still expose C2 relationship/campaign stamps; cross-campaign pull is preserved.
28. Plan/default card behavior remains unchanged unless explicitly covered by the new presentation mode.

---

# §9 Manual WOW witness

Automated PASS is insufficient.

Dogfood on the same real campaign memory that produced the report.

Minimum journey:

### C2

1. Open Campaign 2 Session 27.
2. Wait long enough to reproduce the previous focus-rewrite window.
3. Confirm Session 27 remains selected and readable.
4. Hover/click **hybrid monsters** if still present.
   - Do **not** judge this slice on whether its kind was semantically repaired.
   - Judge whether wrong kind is secondary rather than the whole experience.
5. Hover/open **the hole**.
6. Confirm the useful campaign fact is fast to understand.
7. Follow a relationship such as Swarms/Ogonob where available.
8. Find a relationship equivalent to Misty Step and judge whether direction is now obvious.
9. Close the Peek and continue reading.

### Campaign switch

10. Move to Session 26.
11. Switch to Campaign 1.
12. Confirm the product does not carry invalid C2 Session 26 into C1.

### C1 pull witness

13. Open Guard / Cultists / Dustwalker-connected material where available.
14. Confirm the cross-campaign information that previously created “want more / impressed” is easier—not harder—to understand.

Ask the operator:

> **Does the first pill now make you want to inspect the next one, or does it still feel like looking at a graph database?**

Record the answer verbatim.

---

# §10 Acceptance

Implementation may claim after deterministic tests:

```text
RECAP FOCUS-SESSION CONTINUITY = PASS
UI-04 CAMPAIGN-INFORMATION GLANCE/PEEK = PASS
```

Stage 4 remains human-gated.

Only after the manual witness may steward record:

```text
STAGE 4 / RECAP WOW = PASS | HOLD
```

This slice does **not** establish:

```text
SEMANTIC COVERAGE = PASS
OBJECT KIND QUALITY = PASS
MENTION/PILL RECALL = PASS
AGENT ANSWERABILITY = PASS
AUTHORING UX = PASS
SEMANTIC MODEL SELECTION = PASS
```

---

# §11 Named successors remain false

Do not absorb:

- PC pill coverage;
- swarm mention pill coverage;
- item-vs-threat correction;
- Ogonob enrichment;
- Thalia duplicate repair;
- semantic gauntlet;
- 7A1 contextual Ask;
- Agent tuning;
- Author Node/Tools inventory redesign;
- refresh-preserves-open-Peek;
- full graph-load performance work;
- Play paint / Combat;
- graph ingestion/model changes.

---

# §12 Parked product direction — do not dispatch

Human free exploration reached toward:

> **highlight recap text → tell the Agent “this is a node” → have it author the rest**

Preserve this as product direction.

It is **not** UI-04 and it is **not** permission to reopen 7A1.

The browse/write boundary remains explicit until a later steward slice designs selection → Agent → governed authoring authority end to end.

---

# §13 Worker dispatch

When dispatched, the implementation worker must:

1. start from current `main` containing this ACTIVE handoff;
2. open exactly one PR using the proposed branch/title or a steward-approved equivalent;
3. implement Gate 0 first;
4. keep the same PR for the campaign-information presentation;
5. stop on any required production path outside §7;
6. do not “help” by correcting graph kinds, adding pills, changing extraction, or wiring Agent authoring;
7. write the durable report;
8. request formal review on one exact head SHA.

The reviewer judges the product invariants above, not resemblance to any previous prototype.
