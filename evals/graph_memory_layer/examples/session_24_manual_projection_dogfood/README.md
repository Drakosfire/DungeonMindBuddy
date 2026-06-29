# Session 24 Manual Projection Dogfood

Schema: `dmb_manual_graph_projection_dogfood_benchmark_v0`

This fixture package is a manual, non-canon dogfood benchmark for graph-memory projection work.

It is intentionally **not** an extractor benchmark, runtime retrieval integration, `/plan` integration, Agent Interaction integration, approval flow, or canon-promotion artifact.

## Purpose

Given a raw Session 24 recap, a manually authored gold graph, and a graph-chip projection question set, test whether DungeonBuddy can make the GM faster and better prepared for the next session while preserving source boundaries.

The benchmark asks:

- Do recap chips resolve to useful global-style graph nodes?
- Do node views show focus-session evidence, not just generic summaries?
- Do adjacent nodes help next-session prep?
- Does the system preserve uncertainty around unresolved hooks?
- Does it avoid promoting candidate graph memory into canon?

## Files

- `session_24_raw_recap_PLACEHOLDER.md` — paste the raw Session 24 recap here before running/manual reviewing.
- `session_24_source_anchors.json` — normalized source anchors over the raw recap.
- `session_24_manual_gold_graph.json` — manually authored gold graph for Session 24 projection dogfood.
- `session_24_projection_questions.json` — GM-style projection benchmark questions and scoring rubric.
- `session_24_manual_dogfood_report_template.md` — report template for manual or future automated runs.

## Non-goals

- No corpus mutation.
- No approved memory writes.
- No production retrieval behavior changes.
- No Agent Interaction integration.
- No `/plan` runtime dependency.
- No LLM extraction requirement.
- No claim that this preview is campaign canon.

## Expected use

1. Paste the raw recap into `session_24_raw_recap_PLACEHOLDER.md`.
2. Verify the anchor spans still match the pasted source.
3. Render a recap projection using `session_24_manual_gold_graph.json`.
4. Answer the questions in `session_24_projection_questions.json`.
5. Fill out `session_24_manual_dogfood_report_template.md`.
6. Treat failures as product/design feedback for graph projection, not extraction failure.
