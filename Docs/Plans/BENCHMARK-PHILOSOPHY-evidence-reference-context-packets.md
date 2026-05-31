# Benchmark Philosophy and Harness Architecture — Evidence-Reference Planning Context

## Purpose

DungeonBuddy benchmarks should prove that the system can ingest campaign material, retrieve admissible evidence, preserve authority boundaries, attach route context, and construct useful planning context.

The benchmark should not primarily grade prose similarity. A plausible answer is not enough. A passing run must produce a structured, citable context packet whose claims are backed by admissible corpus evidence.

## Core Philosophy

DungeonBuddy is not trying to answer trivia from campaign notes. It is trying to assist planning from a living TTRPG corpus.

Therefore the benchmark should evaluate the pipeline:

```text
raw or played source
→ canonical recap
→ normalized recap
→ breadcrumb/routing artifact
→ session-memory records
→ activated planning corpus manifest
→ query/admission
→ enriched planning context packet
```

The target is not "did the model write the right summary?" The target is:

Can the system prove what evidence it used, why that evidence was admissible, which routes/hubs it touches, and how that evidence helps the GM plan?

## What Counts as Evidence

Evidence should be addressable and machine-checkable.

Preferred references:

- `path`
- `source_role`
- `authority`
- `session_scope`
- `unit_id` (session-memory records)
- `breadcrumb_id` (or stable span id)
- `line_start` / `line_end` when source markdown lines are cited
- `routes`
- `allowed_uses`
- `forbidden_uses`

Phrase matching is only a drift/sanity check when stable evidence IDs are unavailable.

## Authority Rules

Play facts should come from `canon_play` or `derived_memory`.

Allowed for play facts:

- canonical played recap
- normalized played recap
- breadcrumbed recap only as index back to canonical recap
- session-memory records derived from played recap

Not allowed as normal play-fact support after canonical recap exists:

- raw staged notes
- Session Prep scaffolds
- roll tables
- live observations about past sessions
- planning packets

These may be used for provenance, reconciliation, planning intent, or audit, but not as proof that an event happened in play.

## Benchmark Output Contract

PR97 benchmark runs should emit one packet per question:

```json
{
  "schema": "dmb_enriched_planning_context_packet_v1",
  "question_id": "...",
  "intent_class": "...",
  "corpus_preconditions": {},
  "activation_manifest_refs": [],
  "retrieved_evidence": [],
  "admitted_evidence": [],
  "rejected_evidence": [],
  "claims": [],
  "route_context": [],
  "planning_implications": [],
  "capability_status": {},
  "blocked_or_missing": [],
  "citation_policy": {}
}
```

Failures must stay visible. Missing capabilities and rejected evidence should be explicit.

## Harness Architecture (PR97 Target)

### Layer 1 — Corpus precondition checks

Verify required artifacts exist before query tests:

- Session 22 canonical recap
- Session 22 normalized recap
- Session 22 breadcrumbed recap
- Session 22 session-memory JSONL/meta
- Session 23 live workspace
- activated planning corpus manifest

### Layer 2 — Manifest activation checks

For each source in the activated manifest, verify:

- route/path
- `route_exists`
- `admissible`
- `source_role`
- `authority`
- `allowed_uses`
- `forbidden_uses`
- session scope

### Layer 3 — Query/admission checks

For each question:

1. Query over manifest-admissible sources.
2. Retrieve candidate evidence.
3. Admit/reject by authority and allowed/forbidden uses.
4. Preserve rejected evidence with reason codes.
5. Require admitted evidence for supported claims.

### Layer 4 — Context packet construction

Each claim should carry:

- `claim_id`
- `claim_type`
- `support_status`
- `supporting_evidence_refs`
- `route_refs`
- `planning_implication`
- `authority_notes`

### Layer 5 — Scoring

Score invariants, not prose:

- corpus preparation
- manifest activation correctness
- admissible retrieval
- authority discipline
- route enrichment
- packet completeness
- planning usefulness
- capability truthfulness

## PR97 Benchmark Requirement

PR97 is benchmarked only when the harness demonstrates:

1. activated manifest load
2. query over manifest-admissible sources
3. preserved authority metadata through retrieval
4. inadmissible-source rejection for play-fact claims
5. structured context packet emission
6. packet scoring against evidence-reference gold
7. truthful capability/unsupported-action reporting

## Non-goals

- Do not build a second ingestion system.
- Do not benchmark answer vibes.
- Do not rely on exact phrase matching as primary evidence test.
- Do not allow planning scaffolds/roll tables/staging notes to satisfy play-fact gold.
- Do not hide rejected evidence.
- Do not mutate campaign corpus during retrieval benchmark execution.

## Prototype vs PR97

The current adapter (`adapt_c2s23_dogfood_traces_to_context_packets.py`) is a
prototype bridge from dogfood traces into packet format. It is intentionally not
the final PR97 query/admission runner.

PR97 acceptance requires a true manifest-backed query/admission pass (Layer 3),
not only post-processing of prior planner traces.

## Initial PR97 File Set

```text
Docs/Plans/BENCHMARK-PHILOSOPHY-evidence-reference-context-packets.md
evals/c2_live_prep/benchmarks/c2s23_route_evidence_gold.json
evals/c2_live_prep/schemas/enriched_planning_context_packet.schema.json
evals/c2_live_prep/evaluate_c2s23_context_packets.py
evals/c2_live_prep/adapt_c2s23_dogfood_traces_to_context_packets.py
```

## Relationship to Existing Work

- Existing C2S23 seed questions remain scenario drivers.
- Existing dogfood traces remain baseline behavior evidence.
- PR97 layer should convert these into evidence-reference checks for manifest query/admission.
