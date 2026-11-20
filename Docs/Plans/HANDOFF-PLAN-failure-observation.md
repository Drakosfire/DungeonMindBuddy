# PLAN: preserve failure observations

Status: ACTIVE. PRIME owns this operator-authorized bug fix. Base1a19895fd3978fcb00900bb3fc0b328d32b6781e; branch codex/plan-failure-observation; reuse buddy-context-loop checkout. Parallel-independent from2258 UI/statblock and2260/2261 execution-owner work. No live resource lease or provider calls.

Outcome: Plan records its safe failure code and phase before settling the turn, so the existing timeline/export explain why it stopped. Preserve the original exception when observation or cleanup also fails. Never rewrite the retained Old Bath House attempt.

Critique: the captured request correctly selected different_destination; Plan explicitly refuses it. Durable failure is plan_authoring_destination_unavailable, but no trace failure observation was emitted. This slice repairs observation only. It does not enable connected-page generation. A serial successor must adopt the existing reviewed connected-page capability for Plan without bypassing source, creation or publication guards.

Expected writes: this handoff; apps/live_control_server/services/plan_jev_harness.py; tests/test_plan_jev_failure_observation.py; tests/test_plan_jev_authoring.py. No API/schema/UI/configuration changes.

Validation: provider-free orchestration tests for known/generic codes, observation failure isolation and cleanup preserving the original error; existing disposable-APP native authoring refusal tests for matching durable/captured failures and no writer/page action. Independent Bugbot, owning CI and cumulative diff before delivery.
