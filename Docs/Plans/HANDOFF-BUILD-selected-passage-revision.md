# Reviewed replacement of selected authored text

ACTIVE serial PRIME slice, codex/build-selected-passage-revision, base
41d22cd2709530582332023180179ee3598f03e7, existing buddy-context-loop checkout.

## Capability / invariant / critique
Use the existing Build proposal route for additions and explicit selected-passage
revisions. A nonempty textual selection captures its exact end/text alongside the
existing start, complete editor/draft digests and saved source basis. The route and
writer see that target as untrusted authored context. Stage a continuously editable
review at the captured start; only Keep replaces the exact captured range, and the
normal page save remains separate. Preserve original provider output and complete
before/after recovery digests. Revisions stay pinned to their selection; additions
remain movable. Reject stale or forged range/text, cross-page/cross-tab changes,
double apply and moving a replacement. Images still insert only at a caret.

Historical reservations keep their exact serialized identities; this is one active
proposal path with two meaningful edit targets, not a legacy execution fallback.
No new character/token limits. Never infer a replacement range from model output.

## Exclusive writes / state / topology
This handoff; HANDOFF-SURFACE-hosted-conversation-frame.md; Docs/Roadmaps/ROADMAP-demo.md;
src/application_state/build_proposal/types.py and review.py;
apps/live_control_server/services/build_document_proposal.py and build_jev_driver.py;
apps/live-control-ui/src/api/buildDocumentProposalApi.ts;
apps/live-control-ui/src/buildSurface/buildComposeBridge.ts and .test.ts;
apps/live-control-ui/src/buildSurface/BuildPageProposal.tsx and .test.tsx;
apps/live-control-ui/src/documentEditing/markdownInsertion.ts and .test.ts;
tests/test_build_document_proposal.py; tests/test_build_proposal_review.py;
tests/test_agent_build_jev_ordinary_harness.py.
Serial one PR; fetched open lanes disjoint. PRIME owns API8000/UI5202; APP0060 and
native0017 unchanged. New selection is optional nested reservation metadata; existing
JSON owner schema admits it without rewriting rows. Preserve all retained work.
No live model probes while the operator writes; use synthetic SDK/disposable APP.

## Verification / delivery
Bridge/helper real-editor tests cover exact inline/block replacement, preserved
surroundings, no mutation before Keep, Undo, restore/reload selection, changed basis,
wrong selection text, stale response and duplicate application. Owner tests cover
stored target identity, writer input/instruction, pinned review placement, uncertain
apply/recovery and unchanged source. Ordinary mocked SDK confirms the existing
route can deliver a persisted revision proposal. Shared review tests prove intent,
editing/Keep/Discard behavior. Exact independent Bugbot, PRIME merge, protected
API/UI delivery and retained-state proof. Live rendered model-driven revision and
operator/full journey acceptance remain explicitly open while probes are stopped.
