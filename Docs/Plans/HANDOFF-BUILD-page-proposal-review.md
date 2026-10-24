# Page proposal review

ACTIVE serial PRIME slice on codex/build-page-proposal-review at
15919026f23a66848a2083fe70c2b342e88ef901, existing buddy-context-loop checkout.
Operator-authorized page-centered authoring; no overlapping open write lease.
PRIME implements and delivers; independent Bugbot reviews the cumulative head.
Owned API8000/UI5202; retained user tabs, sources, drafts and corpus protected.

## One capability
An anchored Build suggestion is reviewed on the page, outside accepted document
content, with editable Markdown, Keep and Discard. Shared Surface placement and
review controls own presentation; Build APP review owns durable review state;
existing editor owns the actual draft transaction and its existing Save/autosave.
Immutable generated proposal/provider evidence remains unchanged. Review edits,
dismissal and exact reviewed insertion receipt have their own revisioned owner
record. Keep binds reviewed bytes and original anchor to one prepared insertion;
unknown outcomes are checked, not blindly applied again. Unaccepted suggestions
must never enter editor JSON, saved Markdown, undo history or autosave.

## Failure critique
Reload/caret movement must preserve target; intervening page edits make target
stale rather than relocate it. Scope/visibility/conversation drift, concurrent
review revisions, failed review writes, lost insertion acknowledgment and invalid
Markdown cannot overwrite authored work or regenerate provider output. An apply
reservation survives uncertainty with exact before/after editor digests; explicit
recovery recognizes the after snapshot without reinsertion or resumes only the
exact before snapshot. Historical proposals without anchors stay readable only.
Draft review typing is retained locally while unsaved; conflicting persisted
review revisions remain explicit. Discard changes review state, never the page.
This slice does not implement floating conversation geometry, revisions replacing
existing text, media review, or claim full J1–J6 completion.

## Exclusive writes
- This handoff; HANDOFF-BUILD-original-proposal-anchor.md; Docs/Roadmaps/ROADMAP-demo.md.
- src/application_state/build_proposal/review.py; new APP0059 migration.
- apps/live_control_server/routes/build_proposal_reviews.py; agent.py router inclusion.
- apps/live-control-ui/src/api/buildProposalReviewApi.ts and .test.ts.
- api/liveApi.ts: exact new review route authentication classification, including
  existing cookie/CSRF, memory-only bearer and loopback destination protection.
- apps/live-control-ui/src/surface/SurfacePageProposal.tsx and .css/tests.
- apps/live-control-ui/src/buildSurface/BuildPageProposal.tsx and tests.
- buildComposeBridge.ts/tests; documentEditing/markdownInsertion.ts/tests.
- planSurface/components/BuildComposeProposal.tsx/tests and WorldPlanAgentConversation.tsx.
- buildSurface/BuildCompose.integration.test.tsx; focused APP/API review tests.
- media/PreparedBuildImage.test.tsx: await existing asynchronous capability admission
  before clicking Generate; no media runtime behavior changes.

## Gates
APP CAS/isolation/terminal transitions/immutable original provider result; authenticated
routes reject foreign selectors. Real editor mounted preview is absent from JSON
and Markdown; reviewed edit/Keep at original location, Discard unchanged; reload,
unknown apply acknowledgment without duplicate insertion, source drift and one
Undo. Typecheck/build and exact independent Bugbot. Migration/delivery protects
all old APP/native/product/corpus state. Ordinary synthetic rendered rehearsal
through Keep/Discard/reload, preserving real user page. Settle predecessor from
its exact merged/delivered evidence; keep full goal outstanding.
