# HERMES host latency experiment — ACTIVE

Authority: operator's request on 2026-10-01 for a provisional Hermes-tuning subagent to iterate on response quality, speed, and Graph use with evidence check-ins to PRIME. Buddy PR #840 was independently reviewed and merged at `92d5ff9c35778a97527546aa9aa15ca8fb7290af`; it established a synthetic prose/Graph baseline. This successor starts from that exact `origin/main` revision. It does not appoint a permanent steward or change production inference policy.

## One bounded question

How much of the observed Hermes wall-time residual belongs to the product's process-isolated host and its cold versus reused worker path? The #840 `run_pair.py` called the inner `run_hermes_graph_agent_turn` directly, so its residual does not measure the production `HermesGraphAgentHost` lifecycle/IPC. This slice produces reproducible timing evidence, not a runtime optimization.

Use the same fully synthetic evidence, question, current policy-resolved GPT-6 Luna model, and conversation-only capability as #840. Run the actual `HermesGraphAgentHost` path with one measured cold turn and at least four measured subsequent turns on the same host, interleaving direct Responses controls where feasible. Record each outer wall time, observed model-call duration and count, unallocated residual, worker PID/reuse or restart, token/cost/tool counts, and answer hard-gate result. Measure host start/ready time separately if the public host API permits it without production edits. First useful visible text remains unknown unless this route actually streams it. Do not attribute an uninstrumented residual to a specific phase.

Compare the cold turn with the warm distribution descriptively; five turns do not establish a stable latency distribution or a production speedup. A useful outcome is either a repeated worker-reuse signal or a falsified warm-up hypothesis with clear next instrumentation. Report exact commands, effective provider/model, all samples, failures, and limitations to PRIME. Check in after the first valid cold/warm pair before finishing the run.

## Lease and gates

Topology: parallel-independent from Buddy open #836/#839 and paused #826. Branch `codex/hermes-host-latency` from merged Buddy main above, in the isolated Hermes worktree. Exclusive expected write set: this handoff and `evals/hermes_tuning/**`. Product runtime, routes, UI, model policy, Graph authority, and user-facing Plan state are read-only. No live service/Graph or private corpus is part of this slice. Prior automatic approval review rejected exporting a private C2 Session 23 packet to OpenAI; do not retry or reroute it without specific approval. Synthetic provider calls with the already configured key are authorized for this experiment; never emit credentials.

Verify the harness at its host/process boundary, inspect cumulative base→head diff and generated artifacts, commit/push, and open one Buddy PR. Do not merge. PRIME reviews the evidence and decides whether to allocate a runtime instrumentation/optimization slice, a Graph witness, or a model/prose challenger. Continue the provisional experimental loop only under a newly pinned bounded handoff after each review.
