# ADR — Hermes graph authority, grounding, references, and citations

**Status:** PROPOSED FOR OPERATOR ACCEPTANCE  
**Decision date:** 2026-07-14

## Context

DungeonBuddy currently overloads “evidence,” “grounding,” and “citation.” Accepted graph assertions are durable canonical memory, but the Hermes product classifier only admits an answer when a current tool completion exposes a source-anchor ID. Anchor presence is then presented as grounding even when the anchor is unreadable and unopened.

This ADR separates claim authority, provenance, source verification, and answer synthesis.

## Decision

Adopt **authority by claim class**.

The World Supergraph is authoritative for accepted graph claims. Source artifacts are authoritative for their own bounded content and provide provenance, verification, quotation, and deeper detail. Agent inferences are useful but never silently promoted to graph fact.

## Glossary

| Term | Decision definition |
|---|---|
| candidate | An identity or claim considered by retrieval but not selected as answer support. |
| match | A deterministic or model-assisted resolution result with match reasons; not factual support by itself. |
| graph object | A durable node, edge, event, or other addressable record in one graph revision. |
| graph claim | An explicit accepted assertion or accepted relationship record that makes a proposition. |
| assertion | A typed subject–predicate–object/value proposition with epistemic, canon, visibility, temporal, revision, and support metadata. |
| accepted assertion | An assertion admitted into the selected revision under governance policy. |
| derived summary | A lossy prose condensation computed from claims. It is navigation context unless separately accepted as a summary assertion. |
| materialized knowledge | The revision-pinned set of accepted objects and claims produced by the graph write lifecycle. |
| evidence ref | A graph-internal link from a claim/support record to a source artifact locator. |
| source anchor | A revision- and scope-bound handle derived from admitted support; it proves that the graph associates a claim/object with a specific source locator. |
| readable source anchor | An anchor whose URI/locator and revision-bound digest authority permit a bounded read. |
| source read | A successful integrity-checked retrieval of bounded source content for one admitted anchor. |
| provenance | The record of who/what produced a claim, through which contribution/activity, from which source, under which revision. |
| grounding | The relationship between answer claims and admitted support classes, recorded claim-by-claim. |
| graph reference | A clickable durable graph object/claim ID and revision. It is not called a source citation. |
| source citation | A clickable source anchor that was successfully opened for this turn, with bounded excerpt metadata. |
| support | The admitted basis for a claim: accepted graph authority, opened source content, or disclosed inference inputs. |
| coverage | What the selected revision models and what retrieval returned, including explicit gaps. |
| confidence | A calibrated property of an extraction/inference, not a substitute for authority. |
| uncertainty | A disclosed limitation: ambiguity, missing coverage, unreadable source, conflict, inference, or execution failure. |
| abstention | Refusal to state a requested campaign fact because no admissible support exists. |
| inference | A new conclusion assembled by Hermes from accepted claims; not an accepted graph claim. |
| synthesis | Organization or summarization of supported facts without introducing a new proposition. |
| canon | The GM-governed campaign truth state represented by accepted claims at a revision. |
| authority | Permission for a support class to justify a specific kind of statement. |
| current revision | The one immutable revision selected for the factual turn. |
| historical revision | An explicitly selected non-head revision; never mixed with current claims without labeling. |
| conversation memory | Prior visible prose and referent pointers used for intent/continuity, never factual authority. |

## Claim authority classes

| Claim class | Hermes may state as campaign fact without source read? | Required UI label | Notes |
|---|---:|---|---|
| governed identity decision | Yes | Graph fact | Stable identity/alias/merge decision in selected revision. |
| GM-authored accepted assertion | Yes | Graph fact · GM authored | First-class even when no separate prose source exists. |
| source-derived accepted assertion | Yes | Graph fact · source linked | The graph’s accepted proposition is authoritative; source read adds verification/detail. |
| accepted relationship/edge | Yes | Graph fact | Predicate/endpoints/direction/temporal metadata are explicit claims. |
| accepted explicit attribute | Yes | Graph fact | Only the explicit assertion value, not arbitrary node-card prose. |
| derived summary | No by default | Summary | May orient or seed retrieval; not claim support unless separately accepted. |
| inferred relationship | No as fact | Inference | May be stated as disclosed inference with supporting claim references. |
| provisional/disputed assertion | No as settled fact | Provisional / disputed | May be described as a graph state. |
| generated prep suggestion | No | Suggestion | Creative output, not canon. |

## What a source anchor proves

Before it is read, an admitted source anchor proves:

- the selected revision associates specified graph claims/objects with a source artifact and locator;
- the anchor was derived under the current world/campaign/focus/admissibility/revision;
- the locator has a known readability state.

It does **not** prove:

- source content was opened this turn;
- the source agrees with the graph claim;
- the source content is complete;
- the final answer used the source;
- the source supports every sentence in the answer.

## What a successful source read adds

A successful source read adds:

- integrity-checked bounded content;
- exact source artifact/anchor identity;
- digest and bounded location metadata;
- permission to quote or paraphrase details present in the opened content;
- a basis for detecting source/graph disagreement.

## Graph references versus source citations

### Graph reference

```json
{
  "kind": "graph_reference",
  "revision_id": "...",
  "object_kind": "assertion|node|relationship",
  "object_id": "...",
  "label": "..."
}
```

Use for facts drawn from accepted graph claims. Clicking opens the claim/object inspector and its provenance/support state.

### Source citation

```json
{
  "kind": "source_citation",
  "revision_id": "...",
  "anchor_id": "...",
  "source_artifact_id": "...",
  "content_sha256": "...",
  "line_start": 1,
  "line_end": 10,
  "truncated": false
}
```

Create only after a successful source read. Clicking opens the bounded source content.

### Conversation reference

A turn ID or selected referent pointer may explain continuity. It is never listed in factual support.

## Grounding and coverage states

The protocol records detailed internal state but presents a smaller user vocabulary.

### Internal claim-support states

```text
graph_accepted
source_anchor_available
source_anchor_unreadable
source_opened
source_integrity_failed
source_graph_conflict
inference_supported
unsupported
```

### Turn outcome states

```text
graph_grounded
source_verified
partial_coverage
inferred_from_graph
conflicting_authority
unsupported
abstained
execution_error
```

Rules:

- `graph_grounded`: every campaign-fact sentence maps to accepted graph claim IDs.
- `source_verified`: graph-grounded, and requested/necessary source detail was successfully opened.
- `partial_coverage`: useful accepted claims exist, but requested dimensions are absent, ambiguous, unreadable, or truncated.
- `inferred_from_graph`: conclusion is explicitly marked as inference and maps to supporting accepted claims.
- `conflicting_authority`: source and graph materially disagree; answer reports both without silent resolution.
- `unsupported`: proposed claim lacks admitted support; it must not appear as campaign fact.
- `abstained`: no useful admissible factual answer exists.
- `execution_error`: infrastructure/tool protocol failed; never masquerades as a graph gap.

## Partial-answer policy

Hermes should answer partially whenever at least one useful accepted claim is relevant and the missing portion can be named precisely.

Example:

```text
The graph identifies Tripod Null-Calf as a canonical siege scout and positional controller at the North Gate. It specifically pins gates, carts, rope lines, or cure-line access. The current source anchor is unreadable, so I cannot source-verify or quote the authored contribution from this turn.
```

Abstain only when:

- no identity can be resolved and clarification is required;
- no accepted relevant claims exist;
- admissibility denies all relevant claims;
- requested exact source wording cannot be opened and no paraphrase is appropriate;
- an integrity failure prevents safe use;
- the user asks for a fact that would require unsupported inference.

## Inference representation

Every inference must carry:

```json
{
  "inference_id": "turn-local:...",
  "text": "Alternate cure-line access should be part of encounter prep.",
  "supporting_claim_ids": ["assertion:tripod-role", "assertion:cure-line-dependency"],
  "reasoning_label": "prep_implication",
  "speculation": "low|medium|high",
  "canonical": false
}
```

UI wording: “Hermes inference” or “Prep implication,” not “Graph fact.”

## Conflict policy

When source and graph disagree:

1. preserve both records in the turn packet;
2. identify the claim and source explicitly;
3. do not let the model choose silently;
4. prefer current accepted graph state for “what DungeonBuddy currently treats as canon”;
5. state that the source contains contrary content;
6. offer a future correction proposal path without writing automatically.

## Consequences

### Positive

- Graph-native GM assertions become first-class.
- The product can provide useful partial answers during source-read outages.
- “Grounded” becomes claim-level and inspectable.
- Source verification is stronger and honestly labeled.
- Future write proposals have a clear boundary between current claim, source, inference, and suggestion.

### Costs

- Requires a claim ledger and answer-support mapping.
- Requires panel and trace redesign.
- Current grounding/citation schemas and tests must be replaced.
- Some derived node summaries can no longer be used casually as facts.

## Rejected alternatives

### Graph as index only

Rejected because governed identity decisions and GM-authored graph-native assertions are legitimate campaign records, and relational structure assembled from multiple sources is product value in its own right.

### All graph card fields authoritative

Rejected because derived summaries and convenience projections may be lossy or generated. Authority attaches to explicit accepted claims, not arbitrary presentation fields.

## Security and integrity constraints retained

- one coherent revision per factual turn;
- visibility/admissibility filtering before claims reach Hermes;
- no arbitrary model-selected path reads;
- source reads require admitted anchors and integrity validation;
- conversation history cannot authorize facts;
- no autonomous durable writes.
