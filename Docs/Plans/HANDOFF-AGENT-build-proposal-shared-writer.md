# AGENT: proposal owner shares the guarded writer dispatch

ACTIVE under PRIME's Graph collaboration goal and ARCHITECTURE's one-writer design guidance. Base70e3471a4339779a667a78b5e70f6b45013138df; branch codex/build-proposal-shared-writer, reusing buddy-tool-denial-delivery and existing dependencies. PRIME implements solo; ARCHITECTURE independently reviews. Serial prerequisite to ordinary Jev adoption. No new worktree, source export, environment or /tmp directory.

## Outcome and invariant

A trusted parent may execute an origin-bound Build proposal through the existing proposal owner's generator while requiring a second writer dispatch gate. Both owners see the same actual immutable SDK request identity and lifecycle. Either authorization or sending acknowledgement failing prevents transport. The proposal owner still constructs the exact native schema request, reserves the action, validates output, stores the result, and owns uncertainty/idempotence. This is not an API for importing arbitrary generated Markdown.

Existing compose callers keep their current behavior. The new trusted seam requires an actual Agent-origin reservation. Existing request replay returns the same stored action without invoking either gate or another provider call. A stored proposal can therefore be recovered after a missing turn completion. Readiness is derived from the persisted action, never model prose.

## Write lease

- This handoff and factual settlement of Docs/Plans/HANDOFF-AGENT-build-jev-driver-decisions.md.
- apps/live_control_server/services/build_document_proposal.py: optional trusted writer gate composed with the existing proposal gate; no request/model/schema changes.
- tests/test_build_proposal_shared_writer.py: real mocked SDK, real disposable APP action lifecycle, owner refusals, callback failure/uncertainty and no replay.

No edits to held MEDIA1306's BuildProposalService/types, ordinary Agent dispatch, public request/UI, Graph authority, migration, configuration or runtime. Open PRs checked: MEDIA1306 remains held; INGEST1235 has disjoint paths. No provider calls or retained writes.

## Proof and next adoption

Verify exact same prepared request and lifecycle identities at both gates, zero transport when either owner refuses, failure during sending/response acknowledgement, persisted output before readiness, timeout uncertainty, and completed/uncertain idempotent recovery without regeneration. Preserve existing proposal validation/route/tool tests. Independent review before merge.

This seam alone does not activate ordinary Jev. Its successor must bind the selected action/capability and outcome to a typed APP conversation completion, make the same request pass the turn writer's inclusion gate, and retain ordinary source answers in the same conversation. Proposed factual Markdown needs structured attribution to included opened-source receipts; creative suggestions must not masquerade as existing World facts. Deterministic acknowledgement avoids a second prose call. Multi-owner transactions are not atomic: partial authorization/sending/response acknowledgement remains recoverable and never licenses a replay.

## Implementation evidence

39 focused shared-writer/proposal/tool tests pass in11.83s with one inherited Starlette/AnyIO deprecation warning. Tests use the real SDK guard and disposable APP proposal/Agent-origin records, with a synthetic parent callback gate. Both callbacks see the same actual attempt/envelope; refusal or exceptions before send produce no HTTP, failed response acknowledgement retains unknown, and stored/uncertain actions return without another attempt. Existing inert Markdown validation and source-drift/tool-origin regressions pass. Scoped Ruff and diff checks pass. No ordinary turn writer inclusion/completion is claimed by the synthetic parent gate. Independent review remains required; provider calls and retained mutations are zero.
