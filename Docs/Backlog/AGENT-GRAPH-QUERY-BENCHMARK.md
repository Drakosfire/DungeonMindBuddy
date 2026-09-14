# Agent Graph-Query Benchmark — backlog capture

**Captured:** 2026-09-14  
**Status:** non-status design/evaluation input; sequencing remains with Demo-Ready continuity/Agent work  
**Origin:** review of the current Agent surface against `evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md`

## Forcing question

> Given an excellent World Graph, can the current DungeonBuddy Agent recover and synthesize campaign memory well enough to answer the 16 Campaign 1 Sessions 1–10 GM questions using only its real product context and tools?

The useful distinction is not simply “did the Agent answer correctly?” We need to separate whether the graph contains and exposes the answer from whether the Agent successfully investigates it.

## Current capability observation

The current Agent surface is sufficiently real and sufficiently constrained to make this benchmark useful:

- the turn is pinned to exact World / campaign / revision / admissibility context;
- the initial retrieval packet is bounded rather than a graph dump;
- the model can iteratively expand a shared `GraphRetrievalSession` using search/object/neighborhood/support and read graph-admitted source anchors;
- neighborhood depth is bounded to 1–2 per call, so longer paths require iterative tool use;
- arbitrary corpus/Markdown fallback is not an acceptable way to hide a graph miss;
- current model-visible graph expansion does not expose first-class `path`, `timeline`, `compare`, or `coverage` operations.

Therefore the primitives are enough to *attempt* the whole benchmark, but the harder questions can distinguish graph/retrieval quality from Agent orchestration quality.

## Expected stress areas

- Direct lookup and one-hop questions should be strong if the graph has the fact.
- Multi-session joins and continuity questions should be plausible but depend on identity quality and iterative retrieval.
- Long ordered path reconstruction is brittle without a path primitive.
- Learned encounter/mechanics questions require the observations to exist as discoverable claims/evidence, not merely as entity nodes.
- Temporal identity questions such as Sprite/fey-familiar continuity test reconciliation and state accumulation.
- Planning-vs-played questions test retained source authority, not just proposition extraction.
- Broad end-of-window synthesis tests whether the Agent can investigate enough of the campaign and know when it has sufficient coverage.
- Continuity-warning questions are currently query-time capabilities; automatic Plan linting/proactive contradiction interruption is a separate future interaction capability.

## Evaluation design

Run the 16-question suite at two layers against the same exact rehearsal revision.

### Layer 1 — oracle retrieval

For each question, manually/script the sensible bounded retrieval sequence using the same production graph/retrieval contracts, but do not require the Agent to choose the sequence.

Question:

> Does the graph plus current retrieval API contain enough reachable, authority-correct information to construct the gold answer?

This establishes an **oracle-answerable** score.

### Layer 2 — real Agent

Run the exact natural-language questions through the current Agent surface with:

- the same exact World revision;
- the real `GraphRetrievalSession`;
- the real current model-visible tools;
- normal surface/conversation context only;
- no benchmark hints, gold answers, must-include fields, or evaluator-only source synthesis.

This establishes an **Agent-answerable** score.

## Failure taxonomy

Classify every miss into one primary bucket:

1. **Graph coverage failure** — required fact never entered World.
2. **Graph connectivity/identity failure** — facts exist but are split, misidentified, or insufficiently related.
3. **Retrieval API failure** — the graph contains the answer but bounded tools cannot expose it reasonably.
4. **Agent orchestration failure** — the tools could retrieve it, but the Agent chose an insufficient investigation.
5. **Source/authority failure** — proposition was retrieved but played truth, planning, inference, ambiguity, or temporal authority cannot be distinguished correctly.
6. **Synthesis failure** — the right evidence was retrieved and the Agent still formed the wrong answer.

## Decision signal

Compare **oracle answerable vs Agent answerable** rather than treating the benchmark as one scalar.

Examples:

- Oracle 14/16, Agent 8/16 → stop tuning ingestion; next work belongs in Agent retrieval/orchestration.
- Oracle 7/16, Agent 6/16 → Agent is using available memory reasonably; graph construction/publication is still the bottleneck.

The benchmark should become a handoff gate after a C1 S1–S10 rehearsal head is good enough to make relationship/path retrieval meaningful. A suspiciously perfect 16/16 result should be checked for evaluator leakage before being celebrated.

## References

- `evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md`
- `src/graph_memory/interaction/session.py`
- `src/graph_memory/interaction/expansion_executor.py`
- `apps/live_control_server/services/hermes_graph_interaction_tools.py`
- `apps/live_control_server/services/agent_context_assembler.py`
- `Docs/Design/ANCHOR-hermes-campaign-sensemaking-goal.md`
- `Docs/Design/ARCHITECTURE-hermes-campaign-authoring-foundation.md`
- PR #714 / Stage 4L chronological C1 rehearsal
