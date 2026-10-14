# AGENT: batch source-read evidence

Status ACTIVE; PRIME solo under Mirathorn lifecycle. Exact base
38d4539281f6d665aa51a2ab7e5e6e5123e012d9; isolated /tmp branch
codex/agent-batch-source-read-evidence, serial successor of accepted source-time
policy. Open MIND/source diagnostic lanes disjoint. No serving/native lease.

Exclusive five paths:
- this handoff
- apps/live_control_server/services/agent_source_read_telemetry.py
- apps/live_control_server/services/hermes_graph_agent.py
- apps/live_control_server/services/pydantic_ai_agent_runtime.py
- tests/test_agent_batch_source_read_evidence.py

Confirmed gap: model batch read calls return reads arrays, while the shared safe
summary recognizes only single anchorId/sourceAnchors. The completion therefore
loses selected source IDs/outcomes. No transcript is returned for these ephemeral
turns; previous actual both-source-read acceptance remains unproven.

Outcome: bounded metadata-only batch telemetry for both existing harness adapters.
Record requested anchor IDs, actual per-read anchor/source/span/revision/outcome,
truncation, returned character count and computed returned-content SHA256. Reuse
existing bounded_ids nested scalar maps; no new required wire/public schema,
corpus bodies, paths, prompts, credentials, source text or model-visible changes.
Limit to8 reads and report telemetry truncation honestly. Recognize only existing
V1/V2 source batch schemas; preserve current single-read behavior. Nested errors
remain identified as such; metadata presence is not successful opening or semantic
acceptance. Never promote claims, change Graph tools/retrieval/budgets, or alter
aggregate acceptance from logging. Source citations/rendering are excluded.

Verify actual collector callbacks and IPC roundtrip, both wrappers, V1/V2 success/
mixed/error, malformed/unknown packets, limits and secret/body exclusion. Synthetic
owning callbacks plus saved exact batch responses suffice before review. After
independent exact-head review, a changed-observability ordinary Agent gold run can
identify unavailable/omitted/truncated/not-read/read-and-ignored evidence. Existing
standing provider approval applies; no unchanged/uncertain replay. New evidence
and worker homes /tmp, declared original source/credential stores read-only;
disposable native DB only. Cleanup rejection is not bypassed.

Finish tests, exact cumulative diff, commit/push/PR and ARCHITECTURE review. No
full transcript, semantic gold, current-state or retained publication acceptance
follows from telemetry. Preserve earlier results and local estimate versus unknown
observed billing. Shared source-time policy is already merged; do not modify it.
