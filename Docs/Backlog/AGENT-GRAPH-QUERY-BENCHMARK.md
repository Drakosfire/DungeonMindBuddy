# Agent Graph-Query Benchmark — backlog capture

**Captured:** 2026-09-14  
**Revised:** 2026-09-15 after accepted-World dogfood STOP  
**Status:** active evaluation authority; sequencing follows `Docs/Design/ACCEPTANCE-dogfood-readiness.md` and the CON-READY steward anchor  
**Origin:** review of the current Agent surface against `evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md`

## Forcing question

> Given a product-loadable World Graph, can the current DungeonBuddy Agent recover and synthesize campaign memory well enough to answer the 16 Campaign 1 Sessions 1–10 GM questions using only its real product context and tools?

The useful distinction is not simply “did the Agent answer correctly?” We need to separate whether:

1. the published World can actually be opened through normal product reads;
2. the graph contains and exposes enough authority-correct information;
3. the Agent successfully investigates and synthesizes that information.

## Dogfood readiness prerequisite

This benchmark is subordinate to the repository acceptance law in:

`Docs/Design/ACCEPTANCE-dogfood-readiness.md`

> **If the operator cannot dogfood the World through the normal product, it is not ready.**

Structural publication/continuity PASS is not sufficient to begin interpreting Agent benchmark scores as product readiness.

Before the 16-question result is treated as a semantic/Agent decision signal, require:

```text
accepted World/revision is reachable
published object IDs round-trip through product reads
projection/search/object/complete-object/evidence agree on object identity
operator can mount/select the intended World/campaign/revision through normal product context
```

A raw publication payload or database row does not rescue a product read miss.

## Current accepted-World observation

The first gauntlet against the structurally accepted current-corpus World returned:

```text
dogfood_ready       = false
oracle answerable   = 4 / 16
Agent FULL          = 0 / 16
Agent tool calls    = 0 on the four oracle-answerable questions
```

Observed primary blocker classes:

- published-object read continuity: an admitted Mireward identity was present in publication material but ordinary product search/object/complete-object/evidence could not open it;
- graph coverage: 12 questions were not oracle-answerable at the C1S10 revision;
- Agent orchestration: Q01, Q02, Q07, and Q13 were oracle-answerable but Hermes abstained without using graph tools;
- product mounting/context: default UI World and C1+C2 campaign-lens behavior do not yet make the accepted World an ordinary operator path.

These findings do **not** invalidate structural acceptance. They narrow its claim and set sequencing: repair the earliest product-loadability boundary before semantic tuning or Agent tuning.

## Current capability observation

The current Agent surface is sufficiently real and sufficiently constrained to make this benchmark useful once product loadability is established:

- the turn is pinned to exact World / campaign / revision / admissibility context;
- the initial retrieval packet is bounded rather than a graph dump;
- the model can iteratively expand a shared `GraphRetrievalSession` using search/object/neighborhood/support and read graph-admitted source anchors;
- neighborhood depth is bounded to 1–2 per call, so longer paths require iterative tool use;
- arbitrary corpus/Markdown fallback is not an acceptable way to hide a graph miss;
- current model-visible graph expansion does not expose first-class `path`, `timeline`, `compare`, or `coverage` operations.

Therefore the primitives are enough to *attempt* the whole benchmark, but the harder questions distinguish product loadability, graph/retrieval quality, and Agent orchestration quality.

## Expected stress areas

- Direct lookup and one-hop questions should be strong if the graph has the fact and the published identity is product-readable.
- Multi-session joins and continuity questions should be plausible but depend on identity quality and iterative retrieval.
- Long ordered path reconstruction is brittle without a path primitive.
- Learned encounter/mechanics questions require the observations to exist as discoverable claims/evidence, not merely as entity nodes.
- Temporal identity questions such as Sprite/fey-familiar continuity test reconciliation and state accumulation.
- Planning-vs-played questions test retained source authority, not just proposition extraction.
- Broad end-of-window synthesis tests whether the Agent can investigate enough of the campaign and know when it has sufficient coverage.
- Continuity-warning questions are currently query-time capabilities; automatic Plan linting/proactive contradiction interruption is a separate future interaction capability.

## Evaluation design

Run the 16-question suite at two scored layers against the same exact benchmark revision, after product-loadability readiness is green.

### Layer 0 — product loadability

Before scoring oracle or Agent behavior, prove representative admitted identities can round-trip through the normal product read contracts.

Question:

> Can the operator/product open what publication says exists?

A failure here is `dogfood_ready = false` and blocks downstream readiness interpretation.

### Layer 1 — oracle retrieval

For each question, manually/script the sensible bounded retrieval sequence using the same production graph/retrieval contracts, but do not require the Agent to choose the sequence.

Question:

> Does the graph plus current retrieval API contain enough reachable, authority-correct information to construct the gold answer?

This establishes an **oracle-answerable** score.

Do not rescue a miss with direct database inspection or arbitrary corpus/Markdown search.

### Layer 2 — real Agent

Run the exact natural-language questions through the current Agent surface with:

- the same exact World revision;
- the real `GraphRetrievalSession`;
- the real current model-visible tools;
- normal surface/conversation context only;
- no benchmark hints, gold answers, must-include fields, or evaluator-only source synthesis.

This establishes an **Agent-answerable** score.

Each benchmark question should start independently unless the benchmark explicitly tests conversational continuity.

## Failure taxonomy

Classify every miss into one primary bucket:

1. **Graph coverage failure** — required fact never entered World.
2. **Graph connectivity/identity failure** — facts exist but are split, misidentified, insufficiently related, or a published identity cannot round-trip through product reads.
3. **Retrieval API failure** — the graph contains the answer but bounded tools cannot expose it reasonably.
4. **Agent orchestration failure** — the tools could retrieve it, but the Agent chose an insufficient investigation or never invoked the tools.
5. **Source/authority failure** — proposition was retrieved but played truth, planning, inference, ambiguity, or temporal authority cannot be distinguished correctly.
6. **Synthesis failure** — the right evidence was retrieved and the Agent still formed the wrong answer.

A loadability failure may be recorded separately as a readiness blocker even when a more specific B/C classification describes the technical cause.

## Decision signal

First ask:

```text
PRODUCT LOADABILITY = PASS ?
```

Only then compare **oracle answerable vs Agent answerable** rather than treating the benchmark as one scalar.

Examples:

- Oracle 14/16, Agent 8/16 → stop tuning ingestion; next work belongs in Agent retrieval/orchestration.
- Oracle 7/16, Agent 6/16 → Agent is using available memory reasonably; graph construction/publication is still the bottleneck.

A suspiciously perfect 16/16 result should be checked for evaluator leakage before being celebrated.

The current first-run result is not permission to tune Hermes yet: the accepted World is still product-loadability `NOT_READY`. Repair that earliest boundary, then rerun the same benchmark contract before choosing the next downstream slice.

## References

- `Docs/Design/ACCEPTANCE-dogfood-readiness.md`
- `evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md`
- `src/graph_memory/interaction/session.py`
- `src/graph_memory/interaction/expansion_executor.py`
- `apps/live_control_server/services/hermes_graph_interaction_tools.py`
- `apps/live_control_server/services/agent_context_assembler.py`
- `Docs/Design/ANCHOR-hermes-campaign-sensemaking-goal.md`
- `Docs/Design/ARCHITECTURE-hermes-campaign-authoring-foundation.md`
- `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md`
- PR #714 / Stage 4L chronological C1 rehearsal
