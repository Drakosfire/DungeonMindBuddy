# HANDOFF — Prime Design: R0-A / R0-B dogfood learnings

**Created:** 2026-07-30  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Branch:** `dogfood/r0-ux-and-reports-2026-07-30`  
**Tip at handoff:** `2aca9f11`  
**Related PR:** [#454](https://github.com/Drakosfire/DungeonMindBuddy/pull/454)  
**From:** R0 dogfood / implementation agent  
**To:** next design agent working on grounded authoring and the Hermes/Workbench boundary

This document is the design-facing synthesis. The raw operator reports remain the
evidence:

- [`MAGIC-MOMENT-R0-A-2026-07-29.md`](../Reports/MAGIC-MOMENT-R0-A-2026-07-29.md)
- [`MAGIC-MOMENT-R0-B-2026-07-30.md`](../Reports/MAGIC-MOMENT-R0-B-2026-07-30.md)
- [`SCRIPT-R0-A-statblock-live-dependency-proof.md`](../Runbooks/SCRIPT-R0-A-statblock-live-dependency-proof.md)
- [`PR-TRACKER-threat-statblock-authoring-projection.md`](PR-TRACKER-threat-statblock-authoring-projection.md)

## 0. Copyable pickup prompt

```markdown
You are the next Prime Design agent for DungeonMindBuddy's grounded Threat
authoring flow.

Read first:

1. `Docs/Plans/HANDOFF-prime-design-r0-dogfood-learnings-2026-07-30.md`
2. `Docs/Reports/MAGIC-MOMENT-R0-A-2026-07-29.md`
3. `Docs/Reports/MAGIC-MOMENT-R0-B-2026-07-30.md`
4. `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`
5. `Backlog.md`, especially the R0-A/R0-B entries for:
   - grounded answer → Threat seed authoring
   - graph chips in answers and queries
   - copyable markdown artifacts
   - honest Hermes liveness
   - Workbench Revise-with-AI UX

Mission: turn the R0 evidence into a bounded design for a grounded authoring
loop. The loop must preserve provenance and uncertainty while allowing the GM
to make a clearly labeled creative proposal and copy or edit the resulting
Threat description.

Do not treat the dogfood as proof that the entire Threat → accepted statblock
→ graph publication → combat lifecycle is complete. Do not start with graph
writes, combat integration, a generic chatbot redesign, or a full typed
mechanics editor.

Produce:

1. a state/interaction model separating retrieval, answer, creative proposal,
   ThreatDraft description, generated mechanics, accepted revision, and graph
   publication;
2. a proposal for response-side graph evidence chips and query-side node
   anchors;
3. a structured copyable markdown artifact contract;
4. an honest liveness/error model for long Hermes and generation turns;
5. falsification criteria and the smallest implementation slice.
```

## 1. Executive summary

R0 did not prove one monolithic “AI authoring” capability. It exposed two
different capabilities with different boundaries:

1. **R0-A / Statblock Workbench:** the durable generation and mechanics workflow
   has real seams, but the first current-provider run failed closed at
   generation validation. The product correctly refused to manufacture a
   candidate. The gate therefore did not pass from that report.
2. **R0-B / Hermes:** Hermes can perform multi-hop campaign investigation,
   preserve uncertainty, and produce a useful provisional Threat description.
   The missing step is not better retrieval alone. It is a deliberate,
   bounded transformation from grounded answer to editable authoring artifact.

The strongest design conclusion is therefore:

> Design a grounded authoring seam between Hermes research and the Statblock
> Workbench. Keep evidence/provenance inspectable in the UI, keep the default
> prose campaign-facing, and make creative additions explicit rather than
> silently canonizing them.

## 2. What R0-A actually established

The 2026-07-29 run had all three local processes available and the real
DungeonMind provider answered. The observed path was:

```text
launcher → Plan → Tools → Statblock
→ create ThreatDraft
→ real provider generate
→ provider returned definition_invalid / HTTP 422
→ no candidate
```

Durable evidence:

- draft ID/version existed: `7139872d-46f5-4af0-b033-1575e092f9d3 / 1`;
- generation request ID existed;
- Buddy recorded a terminal downstream validation failure;
- no candidate, accepted revision, or reload identity was invented;
- edit, validate, revise, accept, and reload were unreachable because no
  candidate existed.

The correct verdict in that report was `FAIL_PRODUCT`, not
`BLOCKED_DEPENDENCY`: the provider was up, but the user-facing error collapsed
field-level validation into “Generated definition failed validation.”

### R0-A product lessons

- **Failure stage must be visible.** Create succeeded while generate failed.
  The UI needs structured field/reference diagnostics, not only a terminal
  sentence.
- **Bootstrap authority is typed state, not `current_head != null`.** A null
  head is automatically freestanding only for `ready + bundleValid`. Typed
  states such as `invalid_bundle`, `inconsistent_lineage`, `blocked_existing_world`,
  and `error` require a stop or explicit operator opt-in.
- **The product door matters.** Dogfood starts at the launcher, then Plan →
  Tools → Statblock. The old `/surface` path was misleading and had to be
  removed from the instructions.
- **The edit proof must match the shipped editor.** The current dedicated
  controls prove AC, HP scalar, or ability-score editing. Typed mechanic
  fields such as attack bonus, damage, save DC, speed, activation, and usage
  are protected/review-only.
- **Revise-with-AI is an interaction problem, not merely an API problem.**
  The underlying orchestration and retry contracts exist, but the current
  panel exposes IDs and transport recovery states instead of a GM-friendly
  “tell the model what to change” flow. R0-A revise is deferred until that
  UX is cleaned up.
- **Exact identity is valuable but currently too manual.** Accepted mechanics
  are identified by `(statblock_id, revision_id, digest)`, but reopening
  requires remembered IDs rather than a comfortable authoring library.

The design must preserve the honest state split:

```text
ThreatDraft
→ generated candidate
→ local working copy
→ validation receipt
→ accepted immutable mechanics revision
```

None of those states is automatically a World Graph publication.

## 3. What R0-B actually established

Hermes was asked difficult, multi-hop questions across the admitted campaign
graph. It successfully:

- connected the Mireward, Shepherd, cult, swamp, and meat-corruption threads;
- distinguished established material from unresolved possibilities;
- rejected unsupported premises instead of turning them into canon;
- proposed Threat directions without inventing a named faction;
- identified Bubbles as a named float goat with a flood-survival history;
- produced a useful provisional “Mutated Float Goat” description with flavor
  tags and in-play prose;
- ran against a pinned graph revision and recorded tool activity, durations,
  matched nodes, source anchors, diagnostics, and recovery behavior.

The R0-B result remains `IN_PROGRESS` / provisional because the output was not
yet a durable, structured authoring handoff.

### R0-B product lessons

- **Grounding and authoring are separate operations.** Hermes can answer a
  grounded question; it does not yet reliably perform the next bounded step:
  `grounded evidence → creative brief → editable Threat description`.
- **The answer needs an explicit epistemic breakdown.** The useful categories
  are `established`, `inferred`, `creative proposal`, and `unknown`.
- **Campaign voice should be the default.** Phrases such as “in graph terms”
  and “the graph confirms” make the answer feel like an internal debug trace.
  Provenance belongs in chips, evidence cards, and expandable support.
- **A copy request needs a product artifact.** Markdown inside a long chat
  response is technically copyable but operationally poor. The user needs a
  distinct artifact with title, copy, optional edit, and stable identity.
- **Retrieval results must become reusable interaction state.** The operator
  should not manually retype names from an answer into the next question.
- **Latency is part of the product.** A spinner does not tell the operator
  whether Hermes is working, stalled, or recovering. The UI must show truthful
  elapsed time and recovery state without inventing fake retrieval stages.
- **The composer currently behaves like a blocking form.** Submitted text
  should immediately become a user transcript bubble; the composer should
  clear and support comfortable multiline questions.

## 4. Design implications

### 4.1 Use two lanes, not one blended transcript

The design should distinguish:

```text
Research lane
  question + query anchors
  grounded answer
  evidence / uncertainty support

Authoring lane
  bounded creative brief
  established / inferred / proposal / unknown
  editable Threat description artifact
  “Open as ThreatDraft” or “Copy markdown”
```

The authoring lane may use the research result, but it must not silently
promote the result to canon or mechanics.

### 4.2 Provenance belongs beside prose

Response-side references should be inspectable without forcing the model to
repeat retrieval vocabulary in every paragraph:

```text
retrieved nodes = evidence context
alias matching = presentation only
query chips = explicit user intent
```

Matching text against retrieved nodes may decorate the response, but must not
create citations or promote arbitrary text to canon. A node rail should also
show retrieved nodes that were not mentioned verbatim.

Query chips should carry stable node IDs and the pinned graph revision
separately from free text. Stale or unresolved chips must be visible errors,
not silently downgraded text.

### 4.3 Treat “creative” as an explicit output category

The Mutated Float Goat answer introduced details such as alchemical runoff and
river-haunting. Those are useful creative additions, but the interface should
label them as proposed rather than allowing them to look like recovered facts.

The authoring contract should preserve:

```text
established: supported by admitted evidence
inferred: synthesis that is not directly stated
creative proposal: newly authored material
unknown: unresolved or unsupported
```

The copied Threat description can be campaign-facing and clean. The evidence
and uncertainty envelope should remain adjacent to it rather than embedded in
the copied prose.

### 4.4 Make artifacts first-class

The minimum useful artifact shape is:

```text
artifact_id
kind
title
markdown
provenance_refs
uncertainty_notes
source_turn_id
```

The UI should provide:

- a distinct artifact card;
- `Copy markdown`;
- optional edit-before-copy;
- stable artifact identity;
- provenance and uncertainty outside the copied markdown;
- an explicit handoff action to create/open a ThreatDraft description.

This is a product contract, not a request for the model to add Markdown fences
to ordinary prose.

### 4.5 Keep generated mechanics downstream

R0-A reinforces the existing boundary:

- Hermes authors and grounds a Threat concept/description;
- the Statblock Workbench generates and validates typed mechanics;
- the server owns derived arithmetic;
- accepted mechanics remain an immutable revision;
- graph publication is a later governed operation.

Do not collapse these stages into one Hermes response or one “Create Threat”
button before the intermediate states are visible.

## 5. Recommended next design slice

Design, then implement, the smallest **Grounded Threat Authoring** slice:

1. Hermes answer returns a structured evidence envelope and epistemic labels.
2. Retrieved graph nodes render as inspectable response chips and a node rail.
3. The composer accepts explicit query-node chips tied to a pinned revision.
4. Hermes can emit a copyable Threat-description artifact on request.
5. The artifact can be edited locally and handed to a freestanding or grounded
   ThreatDraft without inventing graph pointers.

This slice should not include:

- graph publication;
- combat placement;
- automatic canon writes;
- full typed statblock editing;
- automatic Hermes-to-accepted-mechanics generation;
- fabricated progress stages.

## 6. Falsification criteria

The design is not successful merely because the UI has chips or a Copy button.
Test it with:

1. **Homonyms and aliases:** matching must not attach the wrong node.
2. **Retrieved-but-unmentioned nodes:** the rail must expose them.
3. **User-directed node not retrieved:** the query must preserve the explicit
   chip and show the retrieval mismatch rather than dropping it.
4. **Unsupported creative detail:** copied prose must not present it as
   established fact.
5. **Partial source coverage:** the answer must remain useful while showing
   unreadable or incomplete evidence.
6. **Long-running Hermes turn:** user text appears immediately, elapsed time is
   truthful, and failure/retry does not duplicate the turn.
7. **Artifact handoff:** edited markdown remains the exact user working copy;
   provenance is preserved separately.
8. **Freestanding ThreatDraft:** null graph revision must never carry unpinned
   node or source-anchor pointers.
9. **Generation validation failure:** field-level diagnostics must be visible
   before any retry or revision decision.

## 7. Current status and non-goals

The raw reports are evidence, not a claim that the whole roadmap is green:

- **R0-A:** current report is `FAIL_PRODUCT`; real provider was reachable, but
  generation returned a validation failure and the UI hid the useful details.
- **R0-B:** `IN_PROGRESS`; grounding and a provisional description were shown,
  but the reusable authoring artifact and evidence interaction are not complete.
- **R0-A revise:** explicitly deferred because the current interaction is
  operator-hostile.
- **Graph publication / combat integration:** remain later gates.

The next design review should answer one question before implementation:

> Is the primary output of Hermes a conversational answer, a grounded research
> packet, or an authoring artifact?

The dogfood evidence says it must support all three, but they should be
separate, inspectable states rather than one undifferentiated chat response.
