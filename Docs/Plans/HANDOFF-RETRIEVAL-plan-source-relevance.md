# RETRIEVAL: establish source relevance before whole-document acquisition

Status: ACTIVE. User retrieval optimization goal; backend ownership transferred by PRIME.
Base: dcc3d7b6b906c46edef31c9c942dbb2f99ee9ea6.
Branch: codex/plan-source-relevance. Topology: parallel-independent of #2214;
disjoint prompt/dispatch paths, no shared runtime execution. PRIME owns merge/delivery.

Outcome: test whether relevance-first Plan guidance reduces unrelated whole-source
acquisition without losing coverage or citations. No filtering, caps or added calls.
Historical Plan V1 and Build V2/V3 wire reconstruction remain exact. New Plan V2
is surface-bound and fenced by schema 131; no historical fallback execution.

Expected writes: this handoff; src/application_state/agent_conversation/jev_retrieval_contract.py;
apps/live_control_server/services/plan_jev_dispatch.py;
src/application_state/migrations/versions/20261108_0131_plan_source_relevance.py;
tests/test_jev_retrieval_contract.py;
tests/application_state/test_surface_native_decisions.py.

Evidence: retained source-selection-policy-audit-v1 under retrieval-answer-continuation-v1.
13/15 first offers exposed eleven full sources without sections. Existing absence-of-sections
clause is a hypothesis, not a proven cause of broad acquisition.

Validation: exact versioned wire reconstruction, surface rejection, unchanged questions,
Build behavior, durable SDK authorization/reload/replay; independent subagent review.
Then matched current-main control/candidate Q01,Q09,Q14,Q15, one observation per arm
initially through the consolidated workflow. Fixed corpus, provider settings, starting
clones and concurrency. Keep frozen historical baseline descriptive, not a causal control.
Accept only reduced unnecessary acquisition/admission latency with no source-qualified
coverage, attribution or citation regression. Reject or retain inconclusive adverse results;
no unchanged retries. Promising results require full cohort validation before adoption.

Resources: isolated evaluator PostgreSQL 55447 disposable clones only; unique capture
output directories. No primary, UI5202, API8000, APP54331 or Core54330 mutations/restarts.
No UI paths leased. Reader fence has no data transformation. No paid experiment until
implementation review and boundary checks pass.
