# PR45 Retrieval Context Quality Report

## Topline
Approved with caveat: benchmark rows pass, but LLM-facing packets are often bloated and weakly prioritized.

## High-level findings
- Across all three modes, benchmark row pass rate and required-group recall are perfect (3/3 rows per mode).
- This masks packet quality issues: admitted context is often large, dominated by session-memory entries, and only loosely lane-typed.
- Q5 support evidence is present but commonly buried behind many prior-memory rows.

## Q1 analysis (NPC morning-after prep)
- Retrieval includes relevant Stone Bridge and NPC references (Pippa/Bubbles/Grishna/River's Edge), but also broad unrelated historical recap snippets.
- Admission tends to include large prior-memory swaths because `budgeted_v1` can fill available budget with rank-valid but weakly relevant rows.
- Planner usability: moderate (score 3/5) — enough facts exist, but answer quality risk remains due to distraction from stale context.

## Q3 analysis (route and known-gap safety)
- Known-gap expectations are satisfied in benchmark scoring.
- Render/readability risk remains where broader prior memory competes with route-specific safety context.
- Planner usability: moderate (3/5), with caution that route questions need stronger route/worldbuilding lane prioritization.

## Q5 analysis (Hempholm tree support)
- Hempholm support appears in candidate context (first required support around candidate rank 27 in prior_only artifact), and is admitted under larger budgets.
- Even when admitted, support can be buried after many prior-memory records.
- Planner usability: low-to-moderate (2–3/5) despite benchmark pass; packet may require model scavenging.

## Retrieval vs admission vs rendering critique
### Retrieval quality
- Positive: expected evidence is usually retrievable.
- Weakness: candidate lists include high noise density from broad session memory and meta-summary rows.

### Admission quality
- Positive: required groups are retained.
- Weakness: flat budget behavior over-admits prior memory; lane balance is weak.

### Rendering quality
- Positive: rendered packet and provenance structure exist and are inspectable.
- Weakness: rendered payload can be verbose; critical support can lose prominence.

## What current design gets right
- End-to-end retriever → admission → rendered packet path is operational.
- Benchmark catches hard failures on required/forbidden/known-gap constraints.

## What current design gets wrong (for planner usability)
- Pass/fail signal is too permissive for packet quality.
- Noisy prior memory crowds support and query-specific context.
- Fallback semantics from missing lane/source metadata limit deliberate rendering.

## Recommended next PRs (priority order)
1. Query-sensitive deterministic lane routing and lane budgets.
2. Section-aware compression/summarization for long prior-memory blocks.
3. Upstream normalization of `source_kind` and `presentation_lane` metadata.
4. Add packet quality metrics (burial depth, relevance density, section token share).

## Caveats
- This analysis intentionally does not modify retrieval/admission/rendering/gold behavior.
- Some row-level rendered-section details are best inspected via emitted canvas payload and sample packets.
