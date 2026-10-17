# AGENT: retain correlated sanitized turn traces

Status: ACTIVE. Operator refreshed PRIME goal explicitly requires implementation,
independent ARCHITECTURE review, merge and coordinated adoption.
Base: origin/main@4144e98ece3e14f5b3470e77b40a513cf0698f3b.
Branch: codex/agent-trace-retention. Reuse buddy-context-loop checkout/dependencies.
Topology: serial Buddy telemetry slice; DOGFOOD owns separate Ingest paths.

Contract: retain existing sanitized timing/usage in the private service journal,
explicitly enable only dmb.agent.turn_trace at application lifespan startup.
No broad logging, new sink/service/environment/database, provider dispatch,
Graph authority, timing optimization or context-event schema change. Preserve
client turn_id; bind optional durable turn/conversation/attempt from existing
validated records only. Missing joins and postdispatch accounting stay unknown.
Use existing route finalization; at most one emission attempt per request, not
acknowledged durable delivery. Sink failure cannot change request behavior.
Explicit log metadata allowlist and bounded UTF-8 records; truncation reported.
Host journal rotation/persistence is inherited, not guaranteed indefinite.

Exact lease:
- this handoff
- apps/live_control_server/main.py
- apps/live_control_server/services/agent_turn_trace.py
- apps/live_control_server/services/agent_turn_service.py
- tests/test_agent_turn_trace.py
- tests/test_agent_turn_route.py
- tests/test_agent_turn_service.py

Verify existing Uvicorn config + startup logger, repeated setup, privacy/size,
success/error/replay and durable joins with deterministic stubs; run owning
suites, scoped Ruff and cumulative diff check. Review exact head independently.
PRIME owns merge and existing API8000 restart; preserve5202/drafts/DB/artwork.
After adoption, MIND reads naturally occurring Build records joined explicitly;
no artificial model call is required. Full goal and Mirathorn acceptance remain.

Input: private MIND HANDOFF-Buddy-existing-turn-trace-retention.md and
DOGFOOD-TRACE-ANALYSIS-20261017.md under established Projects scratch. Historical
cohort is not an A/B benchmark. Core#136 merge9088e5d is not runtime adoption.
