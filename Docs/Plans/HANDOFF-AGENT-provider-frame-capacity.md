# AGENT: Provider authorization frame capacity

Status: ACTIVE. PRIME solo implementation; ARCHITECTURE independently reviews before merge.
Base: 00e457f16551ff85100cdad0aec07e15e00549e3. Branch: codex/agent-provider-frame-capacity.
Topology: serial successor to accepted #1238; disjoint from DOGFOOD #1235/#1237.

## Outcome and invariant
Allow the frozen Agent request budget to authorize provider bodies up to a separately named byte ceiling. The old 262144-byte generic IPC ceiling and 256000-byte host body check reject otherwise admissible requests. Synthetic reproduction proves this mechanism; the exact rejected frame from the live Float Goat failure was not captured, so causal attribution remains provisional.

The provider-only frame may exceed generic IPC capacity. All other message types retain their existing ceiling. Freeze maxProviderRequestBytes per turn (historical absent field defaults 256000); current Luna policy selects 1050000 bytes. This is a byte transport bound, independent of token estimation, not an authorization call cap. Hash, declared size, request/attempt correlation, exact evidence inclusion, APP authorization and context estimation remain authoritative.

## Exclusive write set
- This handoff
- apps/live_control_server/services/hermes_graph_agent_contract.py
- apps/live_control_server/services/hermes_graph_agent_host.py
- apps/live_control_server/services/agent_turn_service.py
- tests/test_agent_provider_frame_capacity.py
- tests/test_hermes_graph_agent_host.py

No serving port, credentials, provider call, retained database, Graph publication, UI or dependency change. Temporary synthetic evidence under /tmp. Implementation completion includes focused tests, cumulative diff inspection, pushed PR and independent review. Runtime adoption and a fresh ordinary Agent question follow accepted merge.

## Failure cases and evidence
Prove former rejection; below/at/above body boundary; JSON escaping/control/Unicode expansion; forged declared size/hash; oversized non-provider frame; frozen-budget validation; spawned worker/parent correlated authorization with a large synthetic request and denial. No real provider dispatch. Existing APP evidence/fencing remains unchanged and its owning tests must pass. Explicit size errors must be distinguishable without exposing request content. Record beginning/end refs for task experiments.
