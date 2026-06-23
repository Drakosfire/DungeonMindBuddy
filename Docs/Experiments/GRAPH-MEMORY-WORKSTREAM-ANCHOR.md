# Graph Memory Workstream Anchor

Date: 2026-06-22
Status: active current anchor — post-session-23-raw-recap-ingest-fixture checkpoint
Workstream: Graph Memory / Recap Ingestion / Candidate Graph Preview / Agent Interaction bridge
Branch: `experiment/ontology-taxonomy-ladder`

## Purpose

This file is the short operational anchor for future agents. It summarizes where the Graph Memory workstream currently stands, what the latest dogfood changed, and what must exist before the project can execute the next meaningful vertical slice.

The longer historical ladder remains in:

`Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md`

This file should be updated whenever the workstream meaningfully re-anchors.

## Current Re-Anchor

The workstream has crossed from **source-artifact safety proof** into **recap-to-memory product design**.

The old question was:

```text
Can source artifacts safely become projection payloads?
```

That has been answered well enough for now.

The new question is:

```text
Can a real recap become an inspectable, evidence-backed candidate graph that a GM trusts enough to approve into memory?
```

Everything next should serve that question.

## Current State

The ladder has completed the following recap-ingestion path:

```text
explicit recap artifacts
→ source artifact materializer
→ source refs and provenance
→ materializer diagnostics
→ projection-readiness checks
→ projection payload fixture
→ one real-derived explicit artifact dogfood bundle
→ human dogfood evaluation
```

The latest practical finding is that Graph Memory now has a deterministic Session 23 raw-to-normalized recap fixture using the existing recap-ingest helper spine. The fixture preserves paragraph/source-line provenance and validates source-span seed refs without LLMs, graph extraction, corpus writes, or runtime integration.

The Redacted Lantern Archive rich recap remains useful as a synthetic/control fixture. Session 23 is now the first real campaign source fixture for graph-memory gold evaluation.

The current reports count payload units and readiness states. Those are useful developer diagnostics, but they are not the product surface. The next product artifact must let the GM inspect whether the recap was understood.

## Completed Recent Rungs

Recent completed rungs:

1. Recap-Ingestion Source Ref / Provenance Linkage Hardening v0
2. Recap-Ingestion Projection Payload Fixture v0
3. Recap-Ingestion Explicit Real-Artifact Dogfood Fixture v0
4. Recap-Ingestion Dogfood Evaluation Report v0, captured as design guidance
5. Source Span Evidence Resolver Contract v0
6. Candidate Graph Preview IR v0
7. Rich Recap Dogfood Fixture v0 — synthetic/control fixture
8. Session 23 Raw Recap Ingest Fixture v0

The dogfood evaluation reframed the workstream: future work should prioritize preview graph trust, evidence resolvability, write intent, queryability, and Agent Interaction chip/deeplink readiness.

## What The Current Dogfood Proved

The current dogfood proved:

- explicit manifest loading can work without directory scanning
- five admitted recap-ingestion artifact families can survive the pipeline
- materializer output can preserve source artifacts, anchors, units, source refs, provenance, and semantic state
- projection-readiness can reach `ready`
- projection payload shape can be emitted without obvious raw text, absolute path, adapter, `/plan`, Agent Interaction, or runtime leakage

## What The Current Dogfood Did Not Prove

The current dogfood did not prove:

- that a real recap can become a useful graph
- that graph candidates are understandable to the GM
- that provenance is actionable in the UI
- that source refs can resolve to highlightable evidence spans
- that graph memory can answer useful session-recall questions
- that Agent Interaction can consume graph results
- that the current reports are GM-facing value

The dogfood evaluation's central product observation is:

```text
Nothing yet as a GM is useful here.
```

That is not a failure. It is the pivot.

## New Product Loop

The intended product loop is now:

```text
1. GM provides or imports a recap.
2. System segments the source and preserves resolvable evidence spans.
3. System performs multi-pass extraction.
4. System produces a preview-only candidate graph.
5. GM inspects the graph and evidence.
6. GM approves, rejects, or defers proposed writes.
7. Approved graph memory becomes queryable.
8. Agent Interaction uses evidence-backed graph query results.
9. Frontend renders markdown chips, deeplinks, hover cards, and source evidence.
```

The next work should move toward that loop. Do not optimize count reports unless they directly support preview graph trust.

## Required Foundations Before Runtime Work

The team needs these foundations before any runtime or `/plan` integration:

1. Source Span / Evidence Resolver Contract
2. Candidate Graph Preview IR
3. Rich Recap Dogfood Fixture
4. Session 23 Raw Recap Ingest Fixture
5. Session 23 Hand-authored Candidate Graph Gold Fixture
6. Multi-pass Extraction Contract
7. Eval-only LLM Extractor Harness
8. Preview Graph UX Design Spec
9. Static Preview Graph UI Prototype
10. Query Vocabulary Fixture
11. Agent Interaction Chip Payload Contract
12. Preview Approval / Write Intent Contract

Runtime/shadow experiments should come only after those contracts exist.

## Immediate Next Backend PR

Recommended next backend PR:

```text
graph-memory: add session 23 hand-authored candidate graph gold fixture v0
```

Mission:

Add a hand-authored gold candidate graph preview for Session 23, using Candidate Graph Preview IR v0, Source Span Evidence Resolver Contract v0, and the Session 23 raw-to-normalized recap ingest fixture. The Redacted Lantern Archive rich recap remains useful as a synthetic/control fixture, while Session 23 is now the first real campaign source fixture for graph-memory gold evaluation. This fixture does not contain extracted graph output.

Completed rung:

```text
Rich Recap Dogfood Fixture v0
Session 23 Raw Recap Ingest Fixture v0
```

No extraction, graph writes, approval, query execution, `/plan` integration, Agent Interaction integration, fact promotion, or canon promotion should be added by the next gold fixture PR.

## Immediate Next Frontend/Design PR

Recommended frontend/design PR:

```text
frontend-design: add graph memory recap preview UX handoff
```

Suggested file:

```text
Docs/Design/GRAPH-MEMORY-RECAP-PREVIEW-UX-HANDOFF.md
```

Mission:

Design the GM trust surface for recap-derived candidate graph previews.

The design should cover:

- graph/timeline split view
- node detail panel
- edge detail panel
- evidence drawer
- proposed write diff
- ignored/deferred drawer
- state chips
- future Agent Interaction entity/evidence chips
- visible versus advanced/internal fields
- backend fields required for v0

Do not implement React components yet unless explicitly requested.

## Candidate Graph Preview Concepts

The candidate graph preview should include:

- named entity nodes
- unnamed-but-important nodes
- session beat nodes or beat records
- relationship edges
- unresolved thread nodes
- ignored or deferred items
- evidence refs on every meaningful node, edge, beat, or fact
- semantic state envelopes
- proposed write intent

Important: do not restrict graph memory to named entities. TTRPG memory depends on unnamed important concepts such as warnings, motives, debts, clues, mysteries, promises, unresolved threads, and suspicious events.

## Source Evidence Requirements

`source_ref_id` is a machine key, not a human-facing trust surface.

The UI should not show raw source-ref IDs by default. Its job is to resolve them:

```text
click evidence
→ open source recap
→ scroll to relevant location
→ highlight exact span or structured field
```

The next backend contracts must support that flow.

Every evidence-backed graph candidate must have resolvable evidence. If evidence is missing or unresolvable, the preview must show a warning.

## Preview-Only Write Policy

The first graph-ingestion loop must be preview-only.

Default write policy:

```text
Recap goes in.
Candidate graph is generated.
GM inspects preview.
Writes happen only after approval.
```

Approval is not the same as canon promotion. Approval may mean:

- store candidate
- store played canon
- store unresolved thread
- store ignored detail
- store diagnostic restraint

Do not collapse all approval into `make canon`.

## Query Vocabulary Target

Graph memory is only valuable if it becomes queryable.

Initial constrained query operations should include:

```text
list_named_characters(session_id)
outline_sessions(scope)
recent_events(limit, scope)
entity_interactions(entity_id_or_name, filters)
```

Query results must return evidence, not just answer text.

Future Agent Interaction should consume structured graph query results and render entity/evidence chips, source deeplinks, and hover cards.

## Frontend Trust Surface

The frontend should be designed as a GM trust surface, not a generic graph viewer.

The primary user question is:

```text
Did the system understand my recap, and can I safely approve this memory?
```

The likely preview layout:

```text
left: session beat timeline
center: graph canvas
right: selected node/edge/evidence drawer
bottom or tab: proposed write diff and ignored/deferred items
```

Timeline may be more important than graph canvas for first comprehension because a recap is temporal.

## Non-Negotiable Blocks

Until explicitly gated in later PRs, do not implement:

- directory scanning
- canonical corpus scanning
- corpus mutation
- `/plan` integration
- Agent Interaction integration
- graph retrieval
- shadow retrieval
- runtime UI behavior
- production adapter
- entity extraction in production
- alias resolution
- identity merge
- relationship inference into committed graph memory
- fact promotion
- canon promotion
- prompt changes that affect production behavior
- LLM extraction over campaign text outside eval harnesses

## Revised Roadmap From Here

Recommended sequence:

1. Source Span Evidence Resolver Contract v0 — done
2. Candidate Graph Preview IR v0 — done
3. Rich Recap Dogfood Fixture v0 — done, synthetic/control fixture
4. Session 23 Raw Recap Ingest Fixture v0 — done
5. Session 23 Hand-Authored Candidate Graph Gold Fixture v0 — next
6. Multi-Pass Extraction Contract v0
7. Eval-Only LLM Extractor Harness v0
8. Candidate Graph Comparison / Scoring v0
9. Preview Graph UX Design Spec v0
10. Static Preview Graph UI Prototype v0
11. Query Vocabulary Fixture v0
12. Agent Interaction Chip Payload Contract v0
13. Preview Approval / Write Intent Contract v0
14. Shadow runtime experiments only after explicit gates

## Success Bar

The next time this workstream claims progress, the success bar should be human-recognizable:

```text
Alan can look at the preview and say:

That is recognizably my recap.
Those nodes make sense.
Those relationships are reasonable.
The unresolved things are correctly not promoted.
I can click evidence and verify it.
I can imagine approving this into memory.
```

If the work only produces more tables that say `ready`, it is not enough.

## Current Anchor In One Sentence

We are building toward a preview-only, evidence-backed candidate graph that turns a real recap into inspectable, approvable, queryable graph memory for future Agent Interaction — without allowing the graph to affect runtime, `/plan`, retrieval, corpus, or canon until later gates explicitly permit it.

## Post-Session-23-Raw-Recap-Ingest-Fixture Checkpoint

Current checkpoint: post-session-23-raw-recap-ingest-fixture checkpoint.

Completed recent rungs:

5. Source Span Evidence Resolver Contract v0
6. Candidate Graph Preview IR v0
7. Rich Recap Dogfood Fixture v0 — synthetic/control fixture
8. Session 23 Raw Recap Ingest Fixture v0

The Redacted Lantern Archive rich recap remains useful as a synthetic/control fixture. Session 23 is now the first real campaign source fixture for graph-memory gold evaluation.

Next backend PR: graph-memory: add session 23 hand-authored candidate graph gold fixture v0.

## post-session-23-raw-recap-ingest-fixture checkpoint

Completed rung: Session 23 Raw Recap Ingest Fixture v0.

The workstream now has a deterministic Session 23 raw-to-normalized recap fixture using the existing recap-ingest helper spine. The fixture preserves paragraph/source-line provenance and validates source-span seed refs without LLMs, graph extraction, corpus writes, or runtime integration. The next backend rung should hand-author the expected Session 23 Candidate Graph Preview gold fixture against this normalized/source-span surface.

The Redacted Lantern Archive rich recap remains useful as a synthetic control fixture. Session 23 is now the first real campaign source fixture for graph-memory gold evaluation.

Revised workstream sequence:

1. Source Span Evidence Resolver Contract v0 — done
2. Candidate Graph Preview IR v0 — done
3. Rich Recap Dogfood Fixture v0 — done, synthetic/control fixture
4. Session 23 Raw Recap Ingest Fixture v0 — done
5. Session 23 Hand-Authored Candidate Graph Gold Fixture v0 — next
6. Multi-Pass Extraction Contract v0
7. Eval-Only LLM Extractor Harness v0
8. Candidate Graph Comparison / Scoring v0
9. Preview Graph UX Design Spec v0
10. Static Preview Graph UI Prototype v0
11. Query Vocabulary Fixture v0
12. Agent Interaction Chip Payload Contract v0
13. Preview Approval / Write Intent Contract v0
14. Shadow runtime experiments only after explicit gates
