# Agent Harness — mounted Graph expansion

Status: ACTIVE. PRIME implements solo; ARCHITECTURE independently reviews.
Base: Buddy `ed7fc8462f9531c2b47d6670fbd1f1382ff017b9`.
Branch: `codex/agent-mounted-graph-expansion`; topology: serial, one PR.

## Outcome and evidence

An ordinary Build Agent question on stable main5876 received the correct
published World revision in initial context, but both expansion calls failed:
`world_graph_authority_configuration_invalid`: mounted World Graph refuses
alternate world_root. The Harness passes its code repository as executor root;
the executor mistakes that repository for a Graph-store selector. Mounted
DungeonMind remains the sole Graph authority. Source files remain Buddy-owned.

Fix the executor's adapter calls: Graph operations use configured mounted
DungeonMind, while source reads resolve the configured artifact repository,
with the caller's repository as the default. Do not weaken the service guard,
add file-store fallback, change World/revision scope, or change ingestion gold.

## Exact write lease

- `Docs/Plans/HANDOFF-AGENT-mounted-graph-expansion.md`
- `src/graph_memory/interaction/expansion_executor.py`
- `tests/test_agent_mounted_graph_expansion.py`

No concurrent open PR owns these paths (open PRs inspected at activation).
The operational checkout is `/tmp/prime-mirathorn-governance-current`.
Serving archives, retained databases and DOGFOOD5202 are not implementation lanes.

## Verification and follow-through

Reproduce through the model-visible tool adapter with real mounted-authority
guards and a code root distinct from the Graph root. Cover search, object,
neighborhood, support and source reads; preserve World/revision pins and source
repository selection. Retired authority modes and explicit alternate Graph
roots must still fail closed. Run existing interaction/source/Harness tests,
Ruff and cumulative diff; open PR and obtain exact-head independent review.
After merge, the existing lifecycle authorizes a matched main5876 rollout and
the changed live council question. Preserve failed evidence; no unchanged model
retry, direct Graph repair or new publication is needed.

Test-adapter settlement: add `tests/test_selected_subject_initial_sources.py`
to the exact write lease. Its native-read double must accept the source
repository keyword (`repo_root`) rather than the retired Graph-root keyword;
retain all batch, rollback, receipt and claim-preservation assertions.
