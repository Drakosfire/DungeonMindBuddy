# Original Build proposal anchor

ACTIVE serial PRIME slice, base af77b2984f1c9444bdd4322d4156eeacfad86fec,
branch codex/build-original-proposal-anchor; reuse buddy-context-loop. The operator
has authorized page-centered authoring. PRIME owns implementation and delivery;
independent Bugbot reviews the exact cumulative head. Relevant open PRs do not
lease these paths. API8000/UI5202 are PRIME-owned; user pages/drafts stay intact.

## Capability and contract
Keep a generated Build proposal attached to its originally captured insertion
position after caret movement and reload. Capture a SHA-256 of the exact editor
JSON alongside the existing saved-source/draft/caret basis. Persist it in the
existing immutable proposal reservation. Recover only against identical current
editor JSON, draft, World/document/revision/hash/visibility and a valid original
position. Never reinterpret the current caret as the original target. Historical
records without the editor digest remain readable but require a new request to
insert; they do not acquire fabricated anchor authority.

This is the anchor prerequisite for on-page proposal staging. Editable review,
persistent discard, on-page preview and the floating conversation host remain
required by the full goal and are not claimed by this slice.

## Failure critique
Current selection may move without moving the intended target. Actual document,
saved revision, visibility, editor replacement during asynchronous recovery, or
World/conversation drift must prevent mutation. Validate the whole resulting
Markdown before one undoable editor transaction. Preserve strict current-caret
semantics for existing explicit media placement. A recovered original target
never maps itself through edits, even if the text appears nearby. Unknown provider
requests are read/recovered, never replayed by this capability.

## Exclusive expected writes
- This handoff; HANDOFF-BUILD-explicit-placement-failure.md; Docs/Roadmaps/ROADMAP-demo.md.
- src/application_state/build_proposal/types.py and focused proposal/input tests.
- apps/live-control-ui/src/api/buildDocumentProposalApi.ts.
- apps/live-control-ui/src/buildSurface/buildComposeBridge.ts and .test.ts.
- apps/live-control-ui/src/documentEditing/markdownInsertion.ts and .test.ts.
- apps/live-control-ui/src/planSurface/components/BuildComposeProposal.tsx and .test.tsx.
- apps/live-control-ui/src/buildSurface/BuildCompose.integration.test.tsx.

## Gates
Exact reservation digest survives persistence; malformed digests rejected;
retained records readable. Real editor recovery at original position after caret
movement/recreation; drift and async editor changes rejected without mutation;
one Undo restores original document. Mounted proposal reload uses recovery and
no generation. Typecheck/build and independent Bugbot. Protected API/UI adoption
preserves retained stores. Ordinary synthetic proposal reopen/insertion/Undo
proof without changing the operator's page. Settle predecessor only from actual
merged and live evidence.
