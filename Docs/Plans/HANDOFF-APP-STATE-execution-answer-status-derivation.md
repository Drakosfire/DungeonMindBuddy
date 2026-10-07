# HANDOFF — APP-STATE: derive execution answer context status

**Status:** ACTIVE — PRIME authorized this bounded pure-contract slice on 2026-10-07.
**Base and lane:** `main@25914c4d9e944f3f951053a7b1ac5656bc0c5ceb`; branch `codex/appstate-execution-answer-status-derivation` in managed worktree `appstate-answer-status-derivation`. One serial PR to `main`; PRIME owns independent review and merge.
**Write lease:** `src/application_state/agent_conversation/types.py`; focused owning tests in `tests/application_state/test_agent_conversation_postgres.py`; this handoff. No other paths.

## Contract

Expose `derive_execution_answer_context_status(*, context_receipt_sha256, answer_segments, citation_map, receipt, execution, producing_provider_attempt_id, claim_graph_event_ids)` as an internal pure helper. It accepts typed answer segments and citation map before the final status-bearing completion model is constructed. It validates the exact existing receipt, Plan attribution, producing response, claim/citation, and final-envelope support predicates, then returns one of the existing four answer context statuses based on the producing envelope. The helper takes no model status. Reuse the validator's existing evidence checks rather than implementing a second predicate set.

`validate_execution_completion(...)` remains APP-STATE's final independent validator: it calls the shared derivation path and rejects a mismatched supplied status with the current fixed rejection code and message. Preserve all other codes, messages, and validation behavior. Valid sufficient, complete, untruncated cited support derives `graph_grounded`; valid sufficient support that is incomplete or truncated derives `graph_grounded_partial`. Insufficient cited support remains invalid and must keep raising its existing rejection. This says nothing about whole-corpus completeness. With no Graph claims, retain the current producing-envelope rule for `plan_only_graph_unused` versus `plan_only_insufficient_evidence`.

No schema/table/public response/new status, provider/runtime operation, parser relaxation, answer retention, or bypass of final validation is authorized. This is an APP-STATE helper contract for SERVER; the helper is pure and APP-STATE retains final validation.

## Live diagnostic evidence

PRIME reported a fresh safe witness on candidate runtime `0f5c96d5` with `stage=binding` and `reason=grounded_status_mismatch`, reached after claim, citation, and producing-envelope support validation. The turn ended failed with no completion; two authorized attempts and one validated Graph operation were recorded. No raw answer was retained and no replay occurred. The safe proof is `/tmp/prime-binding-witness-inflight.json`, with before/after snapshots `/tmp/prime-binding-witness-before.json` and `/tmp/prime-binding-witness-after.json`. This confirms the observed status mismatch for that witness without changing the strict evidence predicates or authorizing another runtime/provider experiment.

## Re-anchor and coordination

Fetched `origin/main` at `78760713f0b1bd80fe4b114362f83c4302896a37`, then re-anchored to `25914c4d9e944f3f951053a7b1ac5656bc0c5ceb` before final verification. The intervening #994/#995 merges change handoff/evidence/UI files and do not change the leased validator or test paths. Open PR #939 also touches `types.py` for Plan Ask history attribution, but its hunks are in separate models outside these validator functions; this lane is not stacked on or editing PR #939. The new PR is one independent APP-STATE slice; SERVER integration follows only after PRIME reviews the helper contract.

## Acceptance evidence

- `test_execution_answer_status_derives_from_validated_producing_evidence` proves all four existing valid status literal values derive the same evidence-based graph and Plan-only statuses without passing a completion object/status to the helper; malformed status syntax remains rejected by the strict completion model. Complete, incomplete, truncated, and Plan-only sufficient/insufficient cases retain their current semantics. It also proves an invalid event binding still raises the existing safe classification.
- `test_completion_validation_codes_are_closed_safe_and_valueerror_compatible` passes alongside the new derivation test; 2 tests passed. The suite body exercises pure validator functions; no provider, runtime, or database-write operation was run.
- Ruff on both changed Python files and `git diff --check` pass.
- `validate_execution_completion(...)` still rejects wrong labels with the existing `grounded_status_mismatch` / `plan_only_status_mismatch` code and exact fixed message after shared evidence validation.

The PR description identifies the exact committed head and cumulative `main@25914c4d…` diff. PRIME owns independent review and merge.
