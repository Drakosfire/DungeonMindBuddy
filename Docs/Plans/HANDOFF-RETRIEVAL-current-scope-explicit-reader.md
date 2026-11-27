# RETRIEVAL: read explicit current-page scope decisions

ACTIVE under the user's over-retrieval goal. First serial slice: branch
`codex/current-scope-explicit-reader`, base `codex/coverage-capability-serving-base`
at live revision `5b39878f6e68a629a695b771a52479821684aba9`, checkout
`retrieval-source-window`. The open #4884 candidate was checked at
`d19e58b5f833` and does not modify this source or focused test file. No shared
runtime, model, database or production write is assigned to this reader slice.

In signed-in smoke diagnostic `1e664aa7-024a-4229-88f1-a8fad123a658`, a request
for a different named saved page was classified current-page-only and failed
before a reply. Register one more exact source-need instruction that tells the
controller to distinguish the open page from a differently named saved page.
The producer must continue emitting the historical instruction in this slice.
Keep the existing vote, tie, scope, access and current-page exclusivity checks;
do not infer user intent using title substring or host metadata heuristics.

Verify legacy and new exact questions, actual selected probabilities, invalid
instructions/options, ties, and retained selection proof reconstruction at the
owning boundary. Require independent exact-head review and applicable checks.
Deploy the dual reader before the producer emits the new instruction; once it
does, the compatible reader is the rollback floor. Re-anchor on the then-current
serving parent before publication.

Serial producer successor: emit the registered instruction, replay the exposed
named-other-page failure and independent explicit-current-page controls, and
verify in the signed-in app. This wording cannot guarantee perfect model
classification; do not claim the broader routing problem solved without evidence.
The current-page optional-skip error and unavailable-source 503 remain separate.

Write lease: this handoff,
`src/application_state/agent_conversation/build_intentional_response.py`, and
focused cases in `tests/test_native_build_work_view.py`.
