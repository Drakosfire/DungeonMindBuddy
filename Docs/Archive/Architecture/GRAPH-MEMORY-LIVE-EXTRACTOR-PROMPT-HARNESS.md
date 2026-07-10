# Graph Memory Live Extractor Prompt Harness v0

## Current rung

Completed rung: **Live Extractor Prompt/Harness v0**.

This document is retained as the prompt-harness design record. It is no longer the active workstream anchor.

Current operational anchor:

`Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md`

Current graph projection design target:

`Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md`

## Purpose

Render one-shot and two-shot model-ready prompts from PR189 source-spanned recap ingest run bundles and an explicit matching source recap file. The harness then supports validation of supplied Candidate Graph Preview IR-shaped JSON for benchmark review.

The important current interpretation is that extractor output should be treated as producer input for a larger graph substrate, not as the final `/plan` graph source.

## Inputs

The renderer requires both inputs before it can include source text in a prompt:

1. a live recap ingest run bundle directory with `run_manifest.json`, `source_units.json`, `source_span_index.json`, `provenance_index.json`, and `diagnostics.json`;
2. an explicit source recap file whose SHA-256 and line count match `run_manifest.source`.

The run bundle alone is intentionally insufficient because it does not store the full raw recap text.

## Prompt modes

- `one_shot` renders `one_shot_prompt.md`, which asks the model to emit complete preview-only candidate graph JSON.
- `two_shot` renders `observation_extraction_prompt.md` and `graph_assembly_prompt.md`; the harness renders prompts only and does not require model execution in CI.

## Candidate output target

The prompt target is Candidate Graph Preview IR-shaped JSON with these sections: `candidate_nodes`, `candidate_edges`, `session_beats`, `unnamed_important_concepts`, `ignored_items`, `deferred_items`, `proposed_writes`, `high_risk_claims`, and `diagnostics`.

Every positive claim must cite `source_span_ref_id` evidence. The prompt requires uncertainty preservation and treats alias binding, identity binding, inferred relationships, cliffhanger outcomes, uncertain counts, and unsupported canon promotion as high-risk.

## Relationship to the union supergraph

The prompt harness is not the final graph store.

The intended flow is now:

```text
source artifacts
→ source-spanned ingest bundles
→ extractor/materializer outputs
→ reconciliation into global graph nodes/edges
→ campaign/worldbuilding union supergraph
→ session recap projection as a focused lens
→ global node navigation
```

Extractor output should help create or update global graph assertions. It should not become a session-local projection graph by default.

The next design target is not a hand-authored Session 23 graph snapshot. The next target is a union supergraph read model where Session 23 recap pills resolve to global nodes such as `pc_caelynn`.

## Safety boundary

Still blocked unless explicitly gated elsewhere:

- canon promotion
- approved memory writes
- corpus mutation
- production retrieval changes
- Agent Interaction integration
- opaque identity merging
- treating candidate output as trusted graph truth

The harness itself does not approve proposed writes, persist review state, promote facts, promote canon, query graph memory, or change runtime behavior.

## Manual / CLI dogfood workflow

The harness can render prompts and validate supplied JSON output. Model execution may happen outside CI or through a gated dogfood CLI, but candidate output remains untrusted until validated and reconciled.

Rendered extractor output should be understood as candidate assertions that may feed the future union supergraph materializer.

## Next rung

Next active design/backend rung:

```text
graph-memory: add union supergraph projection contract v0
```

The success bar is not “a Session 23 graph exists.”

The success bar is:

```text
Session 23 Caelynn pill resolves to global pc_caelynn.
Clicking Caelynn opens all-of-Caelynn graph context.
Session 23-supported facts/edges are highlighted.
Navigation can continue across edges from campaign and worldbuilding sources.
```
