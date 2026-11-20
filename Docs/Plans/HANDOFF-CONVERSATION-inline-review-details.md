# Conversation preview and Details

Status: ACTIVE. Operator explicitly requested this UI fix after reviewing the Corrupted Edge dogfood trace. The broader goal loop remains paused.

Authority/base: `origin/main` at `dcc3d7b6b906c46edef31c9c942dbb2f99ee9ea6`. Branch `codex/conversation-inline-review-details`, reused context-loop checkout. PRIME owns design, implementation and merge/delivery; independent review is required. Topology: parallel-independent of ADVERSARY's backend routing/admission work and the local World foundation stack. No dependency on either; no overlapping backend or localWorld writes.

## Outcome and boundary

Useful generated page suggestions are readable inline, and their existing page-owned review action remains directly available through receipt/detail loading and refresh. One per-reply Details disclosure owns advanced source/receipt/trace inspection. Inline citations and useful authoring actions remain outside it. Preserve all receipt/digest, owner/pointer, revision and insertion checks; a genuinely invalid detail response must remain rejected without hiding saved text or valid independently owned proposals.

Do not change routing, prompts, providers, generation, ingestion or Graph authority. Preserve saved pages, drafts, retained failures and proposals. Do not retry generation while investigating. A page suggestion remains a proposal until the user reviews/applies it through the existing page editor; rendering it inline never inserts or saves it.

## Expected write lease

- This handoff.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx` and its existing history/integration tests.
- `apps/live-control-ui/src/planSurface/components/BuildComposeProposal.tsx`, `.css`, and `.test.tsx`.
- `apps/live-control-ui/src/planSurface/components/ConversationDetailsButton.tsx`, or its replacement shared reply-details component and focused tests/styles.
- `apps/live-control-ui/src/planSurface/components/BuddyActivity.tsx`, its styles/tests, only to direct advanced inspection into the same reply Details owner.
- Existing Build proposal presentation/tests if needed for stable review; no edit/apply contract changes.

If diagnosis requires backend or shared protocol changes, stop that part and coordinate ownership with ADVERSARY before expanding this lease.

## Owning presentation correction

The built-browser check showed that `WorldConversationPresentation.css` still hides the entire old turn-debug/evidence wrapper behind ConversationDock's Technical details checkbox. Keeping that gate would make the new single Details view inaccessible in normal use. This is the same requested outcome, not a new capability. Extend the lease to `apps/live-control-ui/src/agentInteraction/WorldConversationPresentation.css` and `apps/live-control-ui/src/ui/ConversationDock.tsx`, its `.css` and `.test.tsx`: retire the redundant visibility flag/checkbox/styles; keep technical answer metadata inside reply Details and direct citation/review controls outside. Verify the shared menu still preserves context controls and drafts.

## Validation and delivery

Use the retained latest Corrupted Edge detail/trace as private read-only evidence, not checked-in corpus or a tailored answer. Add provider-free regressions for the actual rejected envelope shape, invalid/cross-owner detail rejection, delayed/failed detail reads, preview/action stability across hydration/refresh, and single advanced disclosure. Verify current Build/Plan/Play presentation and direct citations with owner tests, typecheck/build, independent cumulative review and CI. Use a nonlive UI for browser verification; no live page mutation or provider rerun. Commit/push/open one PR; merge and deliver only after satisfied gates and coordinated local runtime ownership.

## Investigation and verification record

The retained latest native Build authoring reply's receipt/provenance digests, shared native completion shape, and exact lightweight-message identity all pass current validation. A false checksum diagnosis is not established; invalid detail responses remain rejected. The UI previously positioned proposal sidecars using hydrated full turns, so detail hydration could change their placement. Proposals now attach directly to their recorded durable originating turn in the lightweight or hydrated transcript; failed or unanchored historical proposals retain their previous inspection path.

Generated text is labeled as a suggestion, not a supported answer or saved page content. Saved author-reviewed text and superseded placement receipts remain separately inspectable under the same Details owner. Nothing renders by inserting or saving it. The operator's currently discarded review disposition is preserved; active-review browser testing uses an explicitly labeled isolated replay with writes blocked.

Provider-free owning verification before independent review: complete history/activity/proposal/disclosure suite 353/353; native Build proposal and delayed valid/invalid detail plus recovery contrast checks 6/6; ordinary Plan committed-basis/editable proposal/reload checks 8/8; typecheck and production build passed. New shared-dock gate verification and final exact-head qualification follow the same boundary. Broad cross-surface run had 83 failures, of which 80 also reproduce on unchanged main `dcc3d7b6`; the three candidate-only cases were corrected and pass targeted recheck. Full baseline/candidate failures and commands remain in the private runtime-evidence location. These are not a claim that the unrelated broad suite is green.

No inference, source ingestion, Graph publication, model changes, backend contracts, schema revisions or primary/runtime writes are part of this slice. No actual receipt acceptance check was removed. Independent exact-head review, CI and coordinated delivery remain gates; operator product acceptance is not inferred from these tests.

Final local owner run: 376/376 across history, activity, proposals, reply Details and shared dock. Two additional direct-source tab regressions pass after preserving source-tab selection on citation clicks; eight ordinary Plan-host checks pass. The built isolated active-review replay confirmed: preview and enabled review action before and during a delayed exact detail read; identical preview text and button DOM node after hydration; one Details entry with no retired Sources/actions or Debug controls; direct page-review region; reload restoration; no receipt alerts; unchanged editor-model hash. The replay intercepted static assets only in its own browser and answered review commands with an in-memory fixture because the real review is discarded. It sent no generation, save, apply, discard or publication command to the product. Temporary authentication was revoked and the nonlive preview process was stopped. This is presentation verification, not a claim that the discarded review was reopened or that routing is fixed.
