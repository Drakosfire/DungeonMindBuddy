# AGENT: Recover from an unavailable observation selection

ACTIVE; PRIME solo implementation, ARCHITECTURE independent review. Base80dd7a2a54a2677953c1fa8443df156717d04861. Branch codex/agent-recoverable-observation-selection. Serial successor to #1240; disjoint DOGFOOD UI leases.

## One capability
Preserve the existing native read-only selected_observation_unavailable422 as a recoverable tool denial, so the Agent can choose the correct owner without aborting the turn. No assertion is admitted by a denial. Do not treat arbitrary native failures or persistence/integrity errors as recoverable.

Read-only current-revision diagnostics show requesting FloatGoat assertion4d8... on Mirathorn/Bubbles returns this deterministic refusal; requesting it on Elderwyld succeeds. Latest ordinary UI trial c6cf8f87 stopped20.2s with unexpected native_retrieval → graph_operation_indeterminate. Failed call arguments were not retained, so exact causal attribution is provisional. No new provider run until local owning regression passes.

## Exclusive write set
- This handoff
- apps/live_control_server/services/agent_turn_service.py
- tests/test_agent_build_governed_graph.py

No runtime/state/provider/Graph publication/dependency/UI change during implementation. Only recognize the exact owned error class+code+422 in native_retrieval stage before durable Graph append; all other exceptions preserve existing failure handling. Existing denied-payload correlation and worker4xx handling must remain intact. Verify a real disposable APP turn includes the exact denial, subsequently admits a corrected read, and completes with evidence; unrelated native integrity failure stays terminal. Complete to pushed PR and independent review before adoption. Preserve task beginning/end refs.
