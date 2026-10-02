# HERMES tuning experiment — ACTIVE

Authority: operator request on 2026-10-01 to examine `Tuning Hermes for DungeonMindBuddy.md`, move it into Buddy docs, run a provisional subagent experiment on prose, latency, and graph crawling, and report evidence to PRIME. Base: Buddy `origin/main@012ff01acc4e490601f4993644903689af2708c4`. This is a product research lane, not an adopted model policy or a standing steward appointment.

## First bounded slice

Build a reproducible Hermes tuning baseline using existing Buddy graph/Agent benchmarks and corpus questions. Compare the current Luna/Hermes path against a same-model, same-evidence minimal call where feasible; then test one small prose-oriented prompt or context variation. Measure answer quality, grounding, graph traversal behavior, model/tool call counts, elapsed time, and time to first useful visible text where the transport permits. Record the actual effective model/provider and request controls. Unknown telemetry stays unknown. Run the first loop now and report a compact evidence packet to PRIME before selecting the next variation.

The moved research note at `Docs/Experiments/RESEARCH-Tuning-Hermes-for-DungeonMindBuddy.md` is a hypothesis source, not authority. Reverify mutable model availability/prices/provider controls before any model comparison. Start with GPT-6 Luna as the control. Do not expand to other models merely because the note names them; ask PRIME to allocate a named challenger after the controlled baseline.

## Ownership and collisions

Topology: parallel-independent research relative to open Buddy PRs #836 (managed World/native Graph binding), #839 (Plan source diagnostics), and paused #826 (KnowledgeSpace binding). This lane owns only this handoff, the moved research note, and `evals/hermes_tuning/**` in its first slice. The existing runtime, routes, UI, model policy, Graph authority, and user-facing Plan state are read-only until PRIME reviews the baseline and explicitly assigns a second bounded implementation slice. Use an isolated checkout/branch. Do not use or mutate the live :5202 UI, :7866 API, Graph, personal corpus, or managed World records for an experiment without a separately identified witness.

The first evaluation cohort should cover: direct NPC fact, multi-hop relationship, NPC-specific knowledge, Mireward Reach context, absent Session 28 admission, capability question, and co-GM prep synthesis. Prefer existing `evals/hermes_spike/questions.jsonl`, graph benchmark gold, and Plan Agent witnesses; distinguish fixture authority from live native Graph. For each answer, score usefulness/prose separately from hard correctness. Preserve evidence provenance and source scope. Avoid benchmark contamination by keeping expected answers out of model input.

## Review loop and handback

After each bounded variation, send PRIME: exact branch/head, corpus/fixture IDs, prompts and effective provider settings, sample paired answers, raw measurement paths, quality and correctness results, latency breakdown, costs if known, and failures. State what changed from the control and what remains unproved. PRIME reviews the packet and either authorizes the next variation, hands the result to DEMO/another owner, or ends the experiment. Do not claim native Graph crawling from a fixture-only run.

Finish the authorized first slice through cumulative diff review, verification, commit, push, and a Buddy PR. Do not merge. If a new runtime write set is justified, propose a second handoff/PR with exact paths and collision check rather than broadening this lease silently. PRIME decides whether the provisional role should become a formal steward after evidence of repeatable improvement.
