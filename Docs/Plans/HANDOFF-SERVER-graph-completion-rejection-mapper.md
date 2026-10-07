# HANDOFF — SERVER: safe Graph completion rejection mapper

**Status:** READY FOR PRIME REVIEW — PRIME authorized the SERVER consumer after accepting APP-STATE [#992](https://github.com/Drakosfire/DungeonMindBuddy/pull/992), merged at `04b4bee5dda0951a707bf26dc1be74f45d355e98`.
**Base:** that exact merge commit on `main`. This branch changes only the SERVER consumer, its owning test file, and this handoff. PRIME owns independent review and merge.

## Primary question

Can SERVER report APP-STATE's closed, non-content-bearing completion rejection code at the existing `binding` diagnostic boundary while preserving the strict parser, validator, generic fallback, and safe log content?

## Lease and boundary

Write only `apps/live_control_server/services/agent_turn_service.py`, `tests/test_agent_turn_service.py`, and this handoff. APP-STATE owns `GraphCompletionValidationError.rejection_code` and the closed `GraphCompletionRejectionCode` enum in `src/application_state/agent_conversation/types.py`; this PR consumes that accepted internal contract without copying predicates or matching exception messages. SERVER emits an enum value only for that typed exception at the completion-binding stage. An ordinary or malformed `ValueError` remains `completion_binding`.

No answer text, provider body, exception message, user content, or raw Graph data enters the diagnostic reason. Do not change APP-STATE validators, answer schema, prompts, retries, persistence, public API, UI, native Graph, source artifacts, runtime checkout, or any live turn. The failed witness `013fda69-296e-4202-bee1-9543faba6454` remains fixed evidence. This slice authorizes no provider call or new Ask.

## Acceptance and stop conditions

Owning tests must prove a typed Graph status mismatch maps to its fixed code, a Plan-only mismatch reaches the full service warning with no provider content, and an unclassified validator error keeps the generic reason. The rest of the SERVER test file and changed-file Ruff must pass. Inspect the exact cumulative `04b4bee5`→head diff for only leased paths and unchanged rejection behavior. Stop if the mapping needs a new APP-STATE code, copied validator logic, a public contract, or answer-content inspection; return that to PRIME for an owner decision.

**Read-only diagnosis limit:** the failed live completion was not persisted. Its `completion_binding` log proves only that strict parsing and preliminary support passed before APP-STATE validation. Offline synthetic completions against its frozen receipt and ledger show supported `graph_grounded` and `plan_only_graph_unused` controls pass, while their mismatched status variants fail. These are boundary examples, not a claim about the unretained live answer.

## Implementation evidence

The source-and-test implementation commit is `772adbea990a19051ec98f343e09b184f5459b9e`. It changes only the two leased Python files. SERVER reads `GraphCompletionValidationError.rejection_code` only when the exception arose at the binding stage and the value is an actual member of the closed enum. Other exceptions, including an unclassified `ValueError` or a malformed typed code, keep `completion_binding`. The API failure code, failure persistence, parser shape, and validator predicates remain unchanged.

On the exact merged APP-STATE base, `tests/test_agent_turn_service.py` passed **51** tests; changed-file Ruff and `git diff --check` passed. The adjacent APP-STATE classifier seam, SERVER route, and Hermes Graph contract batch returned **49 passed, 5 failed**. Running the identical batch on clean base `04b4bee5` returned the same 49/5, with the same failures: one route fixture lacks `maxProviderAttempts`, two full-route imports lack `dungeonmind.application.vnext`, and two Hermes contract tests fail at the continuity/provider gate. Those failures are not introduced by this mapper. No live Ask, provider, runtime, or database write was used in verification.

The cumulative diff against exact `04b4bee5` must contain only the two Python files and this handoff. PRIME will review the exact PR head and decide acceptance; this handoff does not claim the failed live answer's unknown subtype or authorize a new witness.
