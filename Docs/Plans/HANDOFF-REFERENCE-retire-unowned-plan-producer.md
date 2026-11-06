# Retire the unowned non-World Plan proposal producer

Status: ACTIVE. Owner/designer: PRIME. Authority: active reference integration
and adoption/demolition goal. Base: remote main
b1a89a7b8a610c021e004146b50cd28a0b0c56c9 (merged #2103). Branch:
codex/retire-unowned-plan-edit-producer, existing buddy-context-loop checkout.

Topology: parallel-independent implementation relative to #2103's UI slice;
delivery is serial after #2103 and its ordinary dogfood. This slice must not delay
that delivery or enter the already reviewed delivery candidate. No runtime lease,
port, database, provider or corpus mutations are allocated here.

## Outcome and critique

Remove the non-World /plan-document-edit/propose endpoint, its uncalled UI API
wrapper, standalone server request/response models, generator, private prompt
projection and campaign/session authority check. Static production caller tracing
finds only the exported wrapper; no mounted UI invokes it. The live historical
clarification caller invokes /world-plan-edit/propose instead.

The World service still uses model selection and the shared insertion prompt;
retain those exercised dependencies and their policy tests. Preserve World
proposal/clarification execution, native proposal execution, historical Actions,
review, Save, drafts and all retained data. Removing a non-durable inert producer
needs no APP migration or row rewrite. Do not replace the removed endpoint with
an alias, redirect, deprecated executor or fallback.

Failure cases: accidental removal of a World-shared helper, stale import/model
reference, disappearance of the World route, or retained client-only codec code
being mistaken for evidence of a live producer. Backend/client symbol search,
mounted HTTP/OpenAPI checks, real World service tests and TypeScript verification
must prove the boundary. The old client-only non-World capture/admission helpers
remain an explicitly open caller-audit disposition; this slice removes server
execution, not all remaining Plan legacy code.

## Exclusive expected write lease

- apps/live_control_server/routes/live.py: only removed endpoint and its imports.
- apps/live_control_server/services/plan_document_edit_proposal.py: only unowned
  producer/authority/prompt projection and imports made unused by their removal.
- apps/live_control_server/models/plan_document_edit_proposal.py: standalone
  non-World request/response; shared and World models remain.
- apps/live-control-ui/src/api/liveApi.ts: only the uncalled wrapper and its imports;
  preserve live ingestion additions and all World/native wrappers.
- tests/test_plan_document_edit_proposal.py: keep exercised shared World model-policy
  checks; retire deleted producer expectations; verify mounted endpoint absence.
- .github/workflows/world-ownership-core.yml: query/authoring suite selectors for
  the retirement check and retained World producer tests, without changing other
  owners' suites or limits.
- This handoff. No #2103 handoff/status edits; that lane retains its write set.

## Gates

Run mounted retirement/policy and retained World proposal/clarification tests with
synthetic provider transport, TypeScript compilation, no-new-lint and cumulative
diff checks. Obtain independent review, commit/push/open a separate small PR and
satisfy CI. Merge/deliver only after #2103's priority delivery and re-anchoring.
The full Plan/Play/Build reference goal and per-surface acceptance remain open.

## Verification discovery and split

The full retained World suite exposed two untouched historical fixture failures:
a downgrade to0032 across an intentional forward-only reader fence, and an old
sourced clarification fixture whose heading locator is correctly unreadable.
Its fake reader cannot grant source admission. An exploratory canonical paragraph
locator also remained unadmitted; do not weaken or spoof authority. That larger
fixture/native-adoption task is separate. All exploratory World/helper test edits
were restored; failure traces and the investigation patch are retained privately.

Reproduce both failures on the exact fetched base before attributing a regression.
The bounded deletion's current World producer, shared policy/prompt, models and
route must remain structurally identical; verify their exercised exact-context,
idempotent replay and shared grammar cases. CI adds those concrete boundaries and
the mounted endpoint-removal test, not a waiver or blanket skip of old failures.
The full reference goal still requires resolving each remaining legacy execution
and historical-reader disposition; this PR does not claim that completion.

Baseline confirmation: both untouched historical failures reproduce on exact
remote main 0e35332a7ddde40a0e4b16755ac36dd0448a55e1 (two failures,
no provider calls). The deletion's mounted retirement/policy and concrete retained
World checks pass 12 cases; TypeScript passes. Current source is rebased onto
merged #2103 b1a89a7b8a610c021e004146b50cd28a0b0c56c9; its delivery
remains the priority and excludes this deletion until separately reviewed/gated.
