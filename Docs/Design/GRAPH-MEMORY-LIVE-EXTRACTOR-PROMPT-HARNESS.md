# Graph Memory Live Extractor Prompt Harness v0

## Current rung

Current rung: **Live Extractor Prompt/Harness v0**.

## Purpose

Render one-shot and two-shot model-ready prompts from PR189 source-spanned recap ingest run bundles and an explicit matching source recap file. The harness then supports validation of manually supplied Candidate Graph Preview IR-shaped JSON for benchmark review.

## Inputs

The renderer requires both inputs before it can include source text in a prompt:

1. a live recap ingest run bundle directory with `run_manifest.json`, `source_units.json`, `source_span_index.json`, `provenance_index.json`, and `diagnostics.json`;
2. an explicit source recap file whose SHA-256 and line count match `run_manifest.source`.

The run bundle alone is intentionally insufficient because it does not store the full raw recap text.

## Prompt modes

- `one_shot` renders `one_shot_prompt.md`, which asks the model to emit complete preview-only candidate graph JSON.
- `two_shot` renders `observation_extraction_prompt.md` and `graph_assembly_prompt.md`; the harness renders prompts only and does not execute model calls.

## Candidate output target

The prompt target is Candidate Graph Preview IR-shaped JSON with these sections: `candidate_nodes`, `candidate_edges`, `session_beats`, `unnamed_important_concepts`, `ignored_items`, `deferred_items`, `proposed_writes`, `high_risk_claims`, and `diagnostics`.

Every positive claim must cite `source_span_ref_id` evidence. The prompt requires uncertainty preservation and treats alias binding, identity binding, inferred relationships, cliffhanger outcomes, uncertain counts, and unsupported canon promotion as high-risk.

## Safety boundary

Still blocked: graph writes, approval persistence, query execution, runtime retrieval, `/plan`, Agent Interaction, corpus scan/mutation, production extraction, and production UI.

The harness does not call a live LLM, require API keys, approve proposed writes, persist review state, promote facts, promote canon, query graph memory, or change runtime behavior.

## Manual dogfood workflow

Render prompts into the gitignored manual run directory, paste the prompt into a model manually, save untrusted JSON as `candidate_output.json`, and validate it before comparison against Session 23 gold fixtures.

## Next rung

Next rung: **gated manual live LLM dogfood run / candidate output review packet** against the Session 23 benchmark. Agent Interaction remains later, after candidate graph extraction is proven useful and approved/queryable memory contracts exist.
