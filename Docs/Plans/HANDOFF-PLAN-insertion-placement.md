# PLAN — resolve requested insertion placement before writing

Status: DESIGN APPROVED AND MERGED through PR1832 at 30a380438c1edd01de5ed9a969e5dbd7431ba189. Independent design review approved exact head7a7d8879b56e0e90367e0d86568cfd0cb7362100; both hosted checks passed. The serial implementation lease is HANDOFF-PLAN-requested-placement-runtime.md. Historical design activation: PRIME-selected bounded successor at base ce35ef2e7eb8c50020f789958ef682aec97adc7a, branch codex/plan-insertion-placement-contract, existing buddy-context-loop checkout. This PR defines the owning contract only. It grants no runtime implementation lease until independent review resolves its gates. The operator’s ongoing authoring/bug-fix authority selects the work; no new per-PR permission gate is introduced. Serial topology: settle this contract, then one bounded implementation PR before any unrelated authoring capability.

## Current witness and misunderstanding

Fresh Sheep B authoring requests twice named a location after the Preparation objective and before its Beat. Both generated insertions were staged at the document start. Manual Move corrected them; ordinary Save/reload then preserved the intended order and all playable IDs. The latest next-session briefing also needed human checkpoint links. That separate citation/output-policy defect is not included in this slice.

Current source anchors:
- WorldPlanAgentConversation.tsx Send captures editBridge.capture before requested-work routing.
- planAgentEditProposal.ts captureWorldPlanEditTarget treats every collapsed selection, including the untouched default, as insert_at_caret.
- plan_authoring.py PlanRequestedWorkInputV1 carries the capture digest and availability, but no location alternatives. Its decision selects discuss/clarify/write_current_page/different_destination.
- plan_jev_graph_packet.py sends focused_edit_target.kind to the writer, without insertion-location context.
- PlanJevHarness reserves the Plan action against that capture before writing. PlanPageProposal and existing review operations own human Move/Save/recovery.

The request’s writing intent was understood. The host incorrectly treated an incidental caret as the requested destination. Adding a prompt hint, selecting the first matching heading, defaulting to document start, or appending another fallback would preserve that misunderstanding.

## Invariant

The author requests an outcome and a destination. Capture the current page once; resolve insertion placement within that exact captured page before reserving its writing action. A model may select a host-offered location, never author offsets, rewrite the document, mint identities, choose another World/page or grant Save/publication authority. The Plan owner remains the sole resolver of actual editor positions and the sole Save owner.

Discussion and factual questions must still work without a writing target. Replacement of an explicit selection or selected playable body keeps its current exact bounds; this slice does not infer broader replacement authority. Genuine uncertainty about which location the author means stays inline in conversation and preserves the original requested work. No draft at an arbitrary substitute location.

## Required contract shape

1. Preserve the original captured editor JSON, directional selection, draft/basis digests, World/document identity and conversation owner. Keep the original capture inspectable; do not overwrite it with a model-selected position.
2. Derive a finite placement catalog from the same editor snapshot using the owning editor’s structure. Existing current caret/explicit selection and top-level section boundaries can be offered. Distinguish before-heading, after-section and end-of-page. A label is navigation data, never identity. Duplicate headings retain distinct snapshot-bound identities; do not silently pick the first. Named-table caption/table pairs are indivisible and are not ordinary section boundaries. Protected playable identities and typed objects retain their owners.
3. Catalog keys are snapshot-local selectors, derived/bound to the captured page and exact root boundary. They are not durable World nodes or a new provenance registry. Do not persist copied source authority or rely on free-form model positions. No arbitrary character/token/anchor caps.
4. Resolve intent and placement through decision capabilities, not the prose writer. Prefer one decision dispatch if the offered schema can express dependent choices without permitting writing when the placement is unresolved. Otherwise a separate bounded placement decision must have explicit actual-call telemetry and authorization; do not add an unobserved model call. Return an exact offered selector or an explicit clarification/unavailable result. Judge a named placement against the captured page and distinguish it from an incidental default caret. Never let missing placement relabel a writing request as ordinary discussion.
5. The accepted placement resolution must bind original capture/catalog digests, actual producing decision, offered selector, World/document and conversation owner. Reuse existing turn/action producer proof and review ownership. It is a location selection, not another evidence/claim authority. The exact wire/event design must be named in the implementation handoff before activation; do not tuck the decision into assistant prose or overload an unrelated field.
6. The Plan owner resolves the selected catalog entry back to the original snapshot, then captures/reseals its concrete application target through the existing editor/placement bridge. Action reservation, generation, initial on-page staging, review and Save must all bind that resolved target. An inserted fragment is inert until ordinary human Save. Human Move may still replace the proposed placement explicitly through existing review operations.
7. If the live page/selection/World/conversation differs before dispatch or application, use the existing stale/recovery boundary: preserve request, original capture and newest draft, expose the specific obstacle, and require explicit placement selection/rebase. No silent recapture, automatic replay, double insertion or cross-tab overwrite. A server that cannot resolve a browser-local anchor must request the owning client’s bounded resolution rather than duplicating ProseMirror offsets/UTF-16 semantics in Python.
8. Retained old proposals and interrupted requests remain inspectable/recoverable under their recorded immutable contracts. Current execution uses one admitted placement path. Do not add heuristic/backwards-compatibility execution fallbacks. Any unavoidable historical read handling must be narrowly justified by retained-data preservation rather than disguised as current authority.

## Boundaries and exclusions

Buddy owns client capture/position resolution, APP action/review joins, and broker decision authorization. The configured decision provider only selects offered locations. GenerationEngine owns its transport, not page semantics; no GE change is expected. Reuse shared Surface review/Move components. Put any necessary location choice in existing Surface navigation or the inline clarification object, not a new random floating toolbar.

Excluded: authored paraphrase/session-citation contract changes; automatic creation of playable IDs; Graph writes; external recap publication; image upload; new page routing; work-plan capability changes/held1764; hosted deployment1828; source/data repair; model/gold tuning; broad UI redesign. No new worktree, environment, source export or runtime restart for this design PR. API8000/UI5202 remain at their protected delivered pins until a reviewed implementation is ready.

## Activation and verification gates

Before implementation: independently critique this contract against current capture/action code; pin exact expected write paths and exact wire/event choices in a consuming handoff. Check active PRs/leases. Resolve the original-capture versus resolved-target fingerprint joins and the browser-local position owner explicitly. Do not activate an implementation with those joins implicit.

Implementation must prove:
- The captured Sheep-like request inserts after the uniquely named objective, before the Beat, without manual Move. Verify generated review location, edited Save, reload and unchanged outside-target bodies/IDs.
- Exact caret/selection requests, current-page revisions, discussion and genuine inline clarification remain distinct. No deferred work executes while clarifying.
- Duplicate/missing headings, contradictory before/after constraints and stale anchors do not choose an arbitrary target or run the writer before clarification/resolution.
- Caption/table adjacency, protected structures, UTF-16 text, nested/typed components, changed draft generations, cross-tab races, cancellation, interrupted decisions and uncertain Save outcomes preserve current ownership and recovery.
- Provider-free tests exercise actual decision authorization/selection and action reservation boundaries, client capture/application and rendered placement—not only a helper or prompt string. Retain original failure. Then independent exact-head Bugbot, cumulative diff/checks, protected delivery and ordinary same-page dogfood. No full J1–J6/operator acceptance claim from tests or deployment.
