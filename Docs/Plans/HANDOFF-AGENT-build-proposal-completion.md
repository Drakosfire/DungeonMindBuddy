# AGENT: durable conversation completion for a prepared Build proposal

ACTIVE under PRIME's Graph collaboration goal, following ARCHITECTURE's shared-writer design. Basefd855c140905068e4fe2a61c4dfcb9948952b987; branch codex/build-proposal-completion in the existing buddy-tool-denial-delivery checkout. PRIME implements solo; ARCHITECTURE independently reviews. Serial successor to1321. No new checkout, export, dependency environment or /tmp directory.

## Outcome

A governed Build turn can complete with a typed authoring outcome referencing an already persisted proposal from the same writer attempt. The host acknowledgement is deterministic and reports only that a preview is ready; it does not claim insertion, Save, Graph publication or factual grounding. APP completion and historical reload independently bind the exact proposal reservation/origin, document basis, producing attempt/envelope and immutable proposal-result digest. Mutable action revision and insertion status do not affect that digest. An already persisted proposal may finish a missing turn completion without another provider request, subject to the existing live turn fence.

## Write lease

- This handoff and factual settlement of Docs/Plans/HANDOFF-AGENT-build-proposal-shared-writer.md.
- src/application_state/agent_conversation/types.py: distinct Build authoring completion and execution/response validation.
- src/application_state/agent_conversation/build_authoring.py (new): immutable result binding and proposal-owner record validation inside APP transactions.
- src/application_state/agent_conversation/service.py and repository.py: complete/reload validation at the owning boundary.
- src/application_state/migrations/versions/20261017_0030_build_authoring_completion.py (new): additive typed completion admission descending0029, guarded downgrade.
- apps/live_control_server/models/agent_turn.py: accept the distinct typed Build response completion.
- tests/application_state/test_build_authoring_completion.py (new): actual disposable APP proposal/completion/reload, identity/body/scope refusals, direct SQL and downgrade, recovery and mutable insertion invariance.

No edits to held MEDIA1306's proposal models/service, Harness routing or UI; no runtime activation/provider call/retained migration or World write. MEDIA's unmerged0028 must later be renumbered/rebased onto accepted migration head. Existing preview consumer remains responsible for explicit Insert and Save. This internal completion alone does not expose a new public request or select Jev in ordinary conversation.

## Acceptance and limits

Verify actual APP proposal persistence and turn completion/reload, exact shared writer attempt and envelope, origin/turn attempt/document basis/argument and result hashes, failed/unknown/missing/foreign proposals, result tampering, no arbitrary model acknowledgement, deterministic no-grounding status, idempotent completion recovery, immutable digest after reported insertion and guarded schema downgrade. Preserve older Build source/Graph completions. Independent review before merge. Ordinary writer inclusion and action selection remain a subsequent integration gate; creative suggestions and source-backed factual proposals must remain explicitly distinct.
