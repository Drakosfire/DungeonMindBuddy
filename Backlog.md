# DungeonMindBuddy — Backlog

This file is the **root dispatch inventory** for independent DungeonMindBuddy work that does not already have a sequencing owner.

See the [Maintenance queue](Docs/Backlog/MAINTENANCE.md) for technical follow-ups, the [release rehearsal checklist](Docs/Runbooks/RELEASE-REHEARSAL-buddy-checklist.md) for deployment evidence, and [Backlog-DONE.md](Backlog-DONE.md) for retained implementation history.

Cross-project / AI-tooling items live in `~/.cursor/learnings/Backlog.md` instead. Completed and superseded history remains in Git history and, when intentionally archived as a terminal implementation record, `Backlog-DONE.md`.

## Status contract

| Status | Meaning |
|---|---|
| `READY` | Dependencies are satisfied, one bounded slice is known, and a handoff can be authored/dispatched now. |
| `DOING` | One active branch/PR owns the capability. |
| `BLOCKED` | The bounded capability is understood but a named dependency or acceptance gate is unsatisfied. |
| `DEFERRED` | Intentionally not worth pulling now, or only becomes relevant when a named trigger occurs. |
| `IDEA` | Worth preserving, but not yet bounded enough to dispatch. |

Terminal work leaves this file rather than accumulating under `DONE` / `DROPPED` headings.

## Ownership and promotion rules

1. **One status owner.** If an active roadmap, PR tracker, or implementation plan owns sequencing for a capability, that document owns its status. Root backlog keeps at most a non-status pointer in **Delegated workstreams** below.
2. **READY is an execution state, not a synonym for “good idea.”** Every READY entry must contain `Kind`, `Owner`, `Captured`, `Last verified`, `Depends on`, one bounded `Slice`, and an observable `Exit proof`.
3. **Promotion rewrites the entry.** Moving `IDEA` / `DEFERRED` / `BLOCKED` to `READY` means converting capture prose into the execution shape below, not merely changing the heading label.
4. **Captured is immutable.** Re-scoping does not make an old problem newly discovered. Freshness is recorded only in `Last verified`.
5. **Re-verify before dispatch.** More than 30 days after `Last verified`, READY is stale for dispatch until checked against current `main`. If the owning architecture/workstream changed, rewrite, delegate, or drop it.
6. **One slice, one independently useful capability.** “Design and implement,” immediate UX plus future architecture, or multiple authority boundaries must be split before READY.
7. **No shadow sequencing.** Root backlog never overrides a tracker/roadmap because its note happens to be newer.

**Audit anchor:** remote `main@fcaab28ab1db7ce2c024152d15ca844e4c3bb3ef`, 2026-10-19.
This is a document reconciliation anchor, not fresh acceptance of every retained idea.

### Current sequencing posture

[ROADMAP-demo.md](Docs/Roadmaps/ROADMAP-demo.md) is the sole Buddy product
sequencing owner. It records the delivered local authoring/Play baseline,
remaining acceptance and candidates currently under operator discussion.
The next product goal is [streaming Buddy’s reply text](Docs/Roadmaps/ROADMAP-demo.md#next-product-goal--stream-buddys-reply-text),
tracked in [#3838](https://github.com/Drakosfire/DungeonMindBuddy/issues/3838).
The old demo-ready roadmap and 2026-09-08 dispatch snapshot are historical.
Do not infer a current blocker or READY assignment from them.

---
## Product ideas at a glance

One row per product idea. These rows are pointers, not separate status records. The referenced notes own their scope; the product roadmap owns sequencing.

| Idea | Next useful slice or decision |
| --- | --- |
| [Simple bulk selection and deletion](#idea-simple-bulk-selection-and-deletion--captured-2026-11-25) | Make multi-item selection and deletion consistent across Buddy, including a real purge for deleted conversations. |
| [Delightful Buddy landing page](#idea-delightful-buddy-landing-page--captured-2026-11-16) | [Home implementation #3965](https://github.com/Drakosfire/DungeonMindBuddy/pull/3965) merged; assess actual hosted sign-in and any remaining acceptance. |
| [Inviting canvases with no graph loaded](#idea-inviting-canvases-with-no-graph-loaded--captured-2026-11-16) | Loaded-empty Graph guidance shipped. Audit setup, unavailable, and optional-Graph states across surfaces. |
| [Shared page composer residuals](#idea-high-priority--shared-grid-page-constructor) | Manual foundation merged; physical print and ordinary chat-directed layout remain separate acceptance work. |
| [Shared agent actions across surfaces](#idea-shared-agent-actions-across-surfaces) | Prove one inline text edit in Build and Plan through their native saves; then test a sourced Graph relationship. |
| [Agent page-formatting benchmarks](#idea-agent-page-formatting-benchmarks) | Compare Buddy on repeatable Build formatting tasks; preserve content and prove the saved rendered result. |
| [Report a bug from Buddy](#idea-report-a-bug-from-buddy) | One page and agent entry flow, with screenshot drop and a link to the filed issue. |
| [Layered map editor](Docs/Backlog/IDEA-layered-map-editor.md) | One durable map with editable overlays. Share coordinates where justified, not a single UI with page layout. |
| [App-wide theming](#idea-app-wide-theme-system) | One shared design system, selectable and customizable themes, with reviewed agent proposals. |
| [Composable spatial workspace](#deferred-composable-spatial-workspace) | Saved canvas arrangements; not page composition or a separate theme system. |
| [Standalone Elderwyld demo World and timeline](#idea-standalone-elderwyld-demo-world-and-timeline) | Author a populated, shareable setting history for signed-out Buddy without using collaborative campaign material. |
| [Connected campaign arcs](Docs/Backlog/IDEA-connected-campaign-arcs.md) | Explore the source-backed Wandering Forest arc across sessions; use unrelated material as a negative control. |
| [Show what Buddy is doing while it works](#idea-show-what-buddy-is-doing-while-it-works--captured-2026-11-20) | Use actual tool and action events to give concise live progress updates. |
| [Syrinscape cues in Plan and Play](#idea-explore-syrinscape-in-plan-and-play--captured-2026-11-24) | Prove user authorization and one cue in an existing library. |
| [Locally generated audio for Plan and Play](#idea-explore-local-audio-generation-for-plan-and-play--captured-2026-11-24) | Audition short effects and music loops, then compare ways to catalog and serve approved files. |
| [Step through Buddy's work](Docs/Backlog/IDEA-conversation-search-replay.md) | Merged local replay mechanisms; retain hosted and broader trace acceptance gaps. |
| [AW workflow capabilities](Docs/Backlog/IDEA-aw-workflow-capabilities.md) | Draft/variant/link/Combat mechanisms merged; ordinary live qualification remains open. |
| [Campaign recap contributor](Docs/Backlog/IDEA-recap-contributor.md) | One campaign, two accounts, GM publication, and a spoiler-isolation witness. |
| [Delete the current Build page](#idea-delete-the-current-build-page--captured-2026-11-19) | Verify the existing direct deletion controls on hosted Build. |
| [Deeper Build document hierarchy](Docs/Backlog/IDEA-build-document-hierarchy.md) | Retain only if dogfood shows a navigation gap after the merged picker and recap browser. |
| [Independent source archive and restore](#deferred-define-independent-source-artifact-archive-and-restore) | Define what discovery and old citations do before designing controls. |
| [Background relationship suggestions](#deferred-background-suggestions-for-missing-world-graph-relationships) | One opt-in, source-backed suggested relationship with duplicate suppression. |
| [Create a campaign inside an existing World](#deferred-create-a-campaign-inside-an-existing-world) | Define membership ownership and prove ordinary scoped creation. |
| [Propose edits to a related page](#deferred-propose-edits-to-an-existing-related-page-from-the-current-workspace) | Target one existing passage without leaving or corrupting the current draft. |

## [IDEA] Simple bulk selection and deletion — captured 2026-11-25

**Context:** Dogfooding conversation history: deleting old conversations one at a time is cumbersome, and Move to Trash currently leaves their stored records in place. The conversation loader is working; it is not part of this issue.
**Insight:** Across Buddy, people should be able to select multiple items and delete them as easily and consistently as they can delete one. Deletion must be honest about recovery and actual storage removal.
**Action:** Audit applicable collections and provide a consistent, accessible bulk-selection and deletion flow, with clear scope, confirmation and partial-failure handling. Start with conversations: make deletion register and execute a real purge of conversation data, preserve independently saved pages, and handle active work, retries, permissions and restore/purge races. Define the recovery period and explain backup or other retained copies before promising permanent removal; do not silently schedule existing trashed conversations. Current conversation trash uses pointer-revision-guarded commands and retained references, so a safe batch and purge need an explicit storage contract rather than a naive cascade.
**Surfaces when:** Building collection management, conversation history, trash, retention, data deletion or bulk actions in Buddy.
**Refs:** `apps/live-control-ui/src/agentInteraction/ConversationLibrary.tsx`, `src/application_state/agent_conversation/service.py`, `tests/application_state/test_conversation_trash.py`.

## [IDEA] Delete the current Build page — captured 2026-11-19

**Context:** Current source provides direct controls to trash a saved Build page and delete a saved statblock from Build. Hosted behavior still needs a direct witness.

**Action:** On a disposable hosted World, check the direct controls from the open item and confirm the return to Build after deletion.

**Exit proof:** Open a saved page and a saved statblock in Build, then delete each directly from its navbar without opening the picker. Verify the correct item is removed and check page restoration through World Trash. Record statblock deletion behavior separately.

## [IDEA] Delightful Buddy landing page — captured 2026-11-16

**Context:** Hosted Buddy sign-in dogfood surfaced the need for a welcoming first view.
**Action:** [#3965](https://github.com/Drakosfire/DungeonMindBuddy/pull/3965) merged the first view and entry points, including synthetic local browser witnesses. Actual hosted sign-in and deployment remain unverified; assess those and retain any remaining first-visit or return-visit gap.
**Surfaces when:** Revisiting Buddy Home, hosted entry, or onboarding.

## [IDEA] Inviting canvases with no graph loaded — captured 2026-11-16

**Context:** Hosted dogfood reached Buddy with no graph available to load.
**Shipped:** [#4626](https://github.com/Drakosfire/DungeonMindBuddy/pull/4626) added permission-aware guidance after an empty Graph loads. Both permission states passed tests on the deployed source. Hosted smoke checks distinguished an unavailable Graph from Pilot’s filtered one-object Graph. A disposable hosted World with a loaded-empty Graph is still needed for direct browser verification.
**Remaining:** Audit Home, Graph, Plan, Play, Ingest, Build, and Combat Tracker before Graph publication or when a graph cannot load. Give each surface an available next action and let users start working wherever Graph is optional. Keep loading, setup, access denial, and failure distinct. In managed Graph, check whether the unavailable view can offer the selected World’s Build workspace alongside retry.
**Surfaces when:** Reviewing shared navigation, World selection, or empty states across Buddy.

## Dated evidence pointers — 2026-11-17

- Hosted signed-in presenter demo World: [#3837](https://github.com/Drakosfire/DungeonMindBuddy/issues/3837) owns scope and acceptance. This is not the signed-out demo or full cross-surface demo [#410](https://github.com/Drakosfire/DungeonMindBuddy/issues/410).
- Hosted incremental ordinary reply text: [#3838](https://github.com/Drakosfire/DungeonMindBuddy/issues/3838) owns scope and acceptance. Build construction SSE and status updates are not that witness.
- Design input: [#3683](https://github.com/Drakosfire/DungeonMindBuddy/pull/3683) captures shared themes, spatial workspace, signed-out original Elderwyld content, shared agent actions, formatting benchmarks and bug-report ideas. This is design context, not authorization to implement or a change to roadmap sequencing.
- Maintenance: the 2026-11-17 audit was a historical snapshot. On 2026-11-18, six of the 20 Buddy issue-linked rows in [the queue](Docs/Backlog/MAINTENANCE.md) had closed with distinct dispositions; [#4012](https://github.com/Drakosfire/DungeonMindBuddy/pull/4012) reconciled those rows while retaining open residuals. Broader demo [#410](https://github.com/Drakosfire/DungeonMindBuddy/issues/410) and source-anchor acceptance [#783](https://github.com/Drakosfire/DungeonMindBuddy/issues/783) remain open, not closed by nearby implementation.

## Research held for evidence or selection

- [Answer-citation experiments](#idea-resume-answer-citation-experiments-after-fundamentals-settle--captured-2026-11-10) remain parked, distinct from retrieval-only work.
- [Retrieval controller comparison](#deferred-compare-retrieval-controllers-using-existing-native-actions): use existing native actions and the ordinary benchmark harness if independent evaluation identifies a controller bottleneck. Keep 70/72 as the existing regression reference, not a fresh holdout or a release claim. Use fresh questions and keep the writer out of retrieval experiments.
- [Frozen TL01 verbatim grounding](#deferred-verbatim-source-phrase-grounding-in-the-frozen-tl01-evaluation) resumes only when a real product consumer selects it.
- **Party hubs in recap Graph preview:** Decide if inferred party hubs belong in author review and how they remain distinct from reviewed facts; [prior evidence and owner](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L105).

# Retained scope and dispatch conditions
## [IDEA] Resume answer-citation experiments after fundamentals settle — captured 2026-11-10
**Kind:** RESEARCH / RESPONSE ASSESSMENT
**Owner:** Buddy response composition
**Captured:** 2026-11-10
**Last verified:** 2026-11-10
**Context:** The operator selected ingestion delivery reconciliation and completion of older fundamentals, explicitly parking citation work. Voice design is separately deferred to the operator; the tighter prompt is a fixed control.
**Insight:** The citation-first Q15 pilot reached the actual provider wire and all eight response segments used structured citation handles before prose. Selected citations passed review, but coverage fell9/9→8/9 by omitting the approximate Abyssal-like scroll clue. No adoption or retry is justified by that one result.
**Action:** Preserve the failed pilot and baseline. Do not resume answer-citation optimization, schema-order experiments, additional citation judges or prompt layers during fundamentals closeout. Existing source-integrity and citation checks remain in force; this is no waiver of them.
**Surfaces when:** Ingestion delivery, QA fundamentals, bounded worldbuilding and real collaborative follow-through have settled and the operator explicitly selects citation work again. This entry grants no implementation or provider authority.
**Refs:** `Docs/Plans/HANDOFF-COMPOSITION-citation-first-experiment.md`; PR2357; retained `out/response-writing-contract-v1/citation-first-experiment-v1/`.


## [IDEA] High priority — shared grid page constructor
**Priority:** HIGH — explicitly requested by the operator.
**Kind:** DESIGN → bounded implementation slices
**Owner:** Build / shared Surface authoring
**Captured:** 2026-10-24
**Last verified:** 2026-11-17 @ `28f4cab85a6a7eebabc4e89ce24166b86e198380`.
**Delivered foundation:** Manual mixed-content rows, revision-bound presentation, row controls, image/text composition and contextual disclosure are merged through [#3689](https://github.com/Drakosfire/DungeonMindBuddy/pull/3689), [#3690](https://github.com/Drakosfire/DungeonMindBuddy/pull/3690), [#3697](https://github.com/Drakosfire/DungeonMindBuddy/pull/3697), [#3711](https://github.com/Drakosfire/DungeonMindBuddy/pull/3711) and [#3774](https://github.com/Drakosfire/DungeonMindBuddy/pull/3774). Do not dispatch “build the first image grid” again. Local composer checks cover native editing/Undo, narrow layout, explicit Save/cold reopen and unchanged semantic Markdown for presentation-only edits; these are not physical print or every hosted-path acceptance.

**Residuals:** Physical sticker-sheet/print sizing, pagination and cutout proof remain separate. Ordinary chat-directed movement of an existing image is also separate: the local executor experiment is not normal-chat routing or model/held-out qualification, and is not a merged capability. Keep content/citation/asset identity, semantic reading order, stale rejection and explicit Save acceptance as gates. Shared agent actions and broader unscheduled design ambitions are not complete.

**Historical design context:** Edge authoring requested intentional text/art/table/callout placement in Tiptap rather than a freeform map. The [composer design](Docs/Backlog/DESIGN-build-page-composer.md) retains the specification and broader proposals; it does not create an implementation assignment or replace roadmap priorities.

**Surfaces when:** Planning remaining Build composition acceptance or agent layout. Product sequencing remains owned by `Docs/Roadmaps/ROADMAP-demo.md`; this reconciliation activates no new slice.

**Original design context:** Edge authoring dogfood began with the need to place artwork intentionally. The subsequent product discussion selected a shared page composer as the design target, not a standalone image-grid feature. It did not authorize implementation.

**Design direction:** Keep Tiptap as the editor. Add opt-in, content-height rows with independent resizable slots for ordinary paragraphs, images, tables and callouts. Tables remain semantic blocks inside slots, not a layout primitive. Keep normal documents and spatial/map work separate.

**Proposal:** [Build page composer](Docs/Backlog/DESIGN-build-page-composer.md) defines row guides, minimum heights, reading order, revision and draft recovery, and the separate sticker-sheet print test.

**Original first-slice design:** Author a real two-column Build section with editable text and an image, then prove that the same grid can place a table and a callout without special layout primitives. Insert or move an existing block, snap column boundaries, and change block order only through an explicit move. Decide revision ownership and serialization before coding. Reuse existing node editing/resize behavior where applicable without confusing image width with column placement.

**Design acceptance:** Save, reload and reopen the same layout and content. Undo/redo preserves both. Narrow screens stack content in a stable reading order; semantic Markdown, retrieval and exact citation references preserve that order and content for the saved revision. Layout-only changes must not silently reorder or alter semantic text. Preserve keyboard access, ordinary editing, and unsaved/recovered drafts. Do not require nested grids, overlap, arbitrary positioning, or map-coordinate machinery for this slice.


**Refs:** Edge source `bba72416-9dfe-49bb-add0-21a346e9a421`; `apps/live-control-ui/src/tiptap/extensions/MediaImageNode.tsx`; `apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts`; conversation `01a0ef89-ca57-7b82-9c9c-215b02d0fc3b`.

## [IDEA] Standalone Elderwyld demo World and timeline

**Goal:** Create a populated Elderwyld demo World with its own chronology, separate from the played campaigns. Write original setting history and demo material rather than copying, paraphrasing, or anonymizing jointly authored recaps. The demo should feel like a lived-in World without sharing prose Alan does not solely own.

**First slice:** Author one coherent arc with dated Events and connected people, places, and objects. Give it a few original, citable sources, a Build handout, and a Plan scene that can be run in Play. Bundle those records with the demo Graph and Conversation evidence so one story carries across the surfaces.

**Release boundary:** Use a standalone demo World and independently review its sources, citations, assets, and any conversation or trace captures before public use. Exclude live campaign records and player contributions; use only original demo material or assets cleared for this use. Signed-out edits and Play progress stay temporary, with no database writes or link to the live World. This item is content groundwork, not approval to publish or implement the guest runtime.

---

## [IDEA] Shared agent actions across surfaces

**Goal:** Enable Buddy to act wherever it makes sense in the product, without duplicating each surface's editor or giving the agent a generic write path.

**Current boundary:** Build and Plan already share the inline proposal and review UI. Build saves authored Pages and their revision-bound presentation; Plan saves native prep with playable structure. Ordinary Markdown proposals do not carry layout operations. See `apps/live-control-ui/src/surface/SurfacePageProposal.tsx` and `apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts`.

**Shared contract to test:** The surface exposes authorized operations for the current object. Buddy proposes a typed change against an exact target and revision. The user reviews the actual effect; the domain owner validates and commits it through its existing write path, then returns a durable receipt. Keep chat answers, proposed changes, and saved effects distinct. Retry must reconcile the receipt, not apply twice.

**First proof:** Run “Rewrite this paragraph without changing the facts or citations” in Build and Plan. Use the shared inline review and each native save path. Reopen and verify the edit and citations, unchanged Plan scene/table boundaries, cancellation with no durable write, and stale-proposal rejection when the user types while Buddy works. Then test one source-backed Graph relationship through its native review and write path to see whether the contract travels beyond text. Layout capabilities remain separate until the target supports them safely.

---

## [IDEA] Agent page-formatting benchmarks
**Owner:** Build authoring + Buddy benchmark harness
**Captured:** 2026-11-15
**Goal:** Give the agent a repeatable improvement loop for turning existing Build content into useful, readable pages. Score formatting separately from drafting or retrieval.

**First benchmark:** Freeze representative input Pages, a plain-language layout brief per task, and the current normal Buddy agent/action path as the baseline. Start with existing composer actions: place artwork beside prose, arrange a real table and callout, and revise the layout on a saved page. Evaluate the actual saved revision and a cold browser reopen at desktop and narrow widths, not the chat response or screenshots alone. Add text over art and sticker/print cases only once the corresponding tools exist.

**Scoring and guardrails:** Hard fail on lost or rewritten content, incorrect reading order, broken source citations, lost asset references, or a claimed save that cannot reopen. For passing runs, grade whether the layout follows the brief and is readable, then compare retries, tool calls, and time. Use structural assertions plus a small blind visual rubric; don't require pixel-perfect matches. Tune on a development set, keep a sealed holdout, and repeat baseline/candidate runs to separate improvements from variance. No benchmark run or tooling activation is implied by this entry.

## [IDEA] Report a bug from Buddy
**Owner:** Shared Surface authoring + Buddy agent
**Captured:** 2026-11-15
**Goal:** Let someone report a problem where it happens, either through a **Report a bug** page action or by asking Buddy in conversation. Both open the same reviewable draft, not separate intake systems.

**First slice:** Reuse the PDF extractor's screenshot drop/file-picker behavior (and paste where supported). Preview and allow removal of the image, capture a short title and what happened, and optionally show a reviewed page/build label. Buddy can draft the same fields, but the user sees the exact issue body, attachment, tracker, and visibility before pressing Submit. File one issue in the configured GitHub repository (or the configured equivalent ticket tracker) from the service, and return its link in the originating page or conversation.

**Acceptance:** Prove both entry points create the same kind of linked ticket. Cancel sends nothing. A retry does not file duplicates, and a failed submit keeps the report editable. Keep screenshots private by default; if the tracker or attachment would be public, make that visible and require explicit approval of the exact content or use a private intake. Don't auto-attach World content, conversation, logs, cookies, or secrets. Reuse the upload interaction, not the PDF-extraction pipeline. This entry does not authorize implementation or ticket submission.

## [DEFERRED] Define independent source-artifact archive and restore
**Owner:** APP-STATE / source lifecycle
**Captured:** 2026-08-11
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** An operator needs to withdraw or restore an independently admitted source, such as a recap, while preserving exact historical evidence.

**Current boundary:** Workspace Trash handles Build and Plan documents and Play sessions. The source service persists immutable artifact and revision identities and serves their Markdown, metadata and scope. It exposes no independent archive or restore operation.

**Next slice on trigger:** Define what source archive changes for discovery, what historical citations can still open, and what exact identity restore preserves. Then identify the owning mutation before adding any UI.

**Refs:** `src/application_state/source/service.py`; `apps/live_control_server/routes/workspace_lifecycle.py`; #1445–#1447.


---

# Cross-owner questions — not implementation blockers by default

- **Generation liveness:** reproduce any false timeout against the current
  GenerationEngine/SERVER path before assigning an owner or designing heartbeat
  machinery. The old claim that DungeonMind owns provider generation is stale.
  OverMind's open backlog-consolidation proposal (#22) is reference, not activation.
- **Authored lore publication:** current governed ingestion/review/publication
  supersedes the pre-cutover missing-elevation premise. Remaining source fidelity,
  semantic richness and fresh-World acceptance belong to the product roadmap and
  the owning knowledge contracts, not a duplicate root BLOCKED item.


## [DEFERRED] Background suggestions for missing World graph relationships
**Owner:** Buddy suggestions and review
**Captured:** 2026-10-13
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** The operator selects proactive source-backed suggestions as a product capability.

**Current boundary:** Agent-requested saved-source relationship review already exists (#1751, #1753). It validates exact supporting quotes and requires confirmation before publication. No background candidate scheduler or cross-run suppression workflow was found in current callers. The original Sara/Frank example requires fresh verification before it can serve as a defect.

**Next slice on trigger:** Reuse the existing candidate/review/publication owners for one opt-in suggestion flow. Define when a suggestion is useful, how prior review suppresses repeats, and when to ask the author.

**Refs:** `src/application_state/agent_conversation/relationship_review.py`; `tests/application_state/test_relationship_review_postgres.py`; #1751, #1753.

## [DEFERRED] Compare retrieval controllers using existing native actions
**Owner:** Retrieval evaluation
**Captured:** 2026-09-26
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** Independent evaluation identifies controller choice as a measured retrieval bottleneck and the operator selects a comparison.

**Current boundary:** Native retrieval, Jev decision drivers, trace capture and independent benchmark assessment already exist. The old proposal's first step of constructing a new exploration environment must be re-scoped around those owners.

**Concrete deferred candidate:** [#3845](https://github.com/Drakosfire/DungeonMindBuddy/issues/3845) records local typed-decision-model comparison. It does not change the trigger above or select a production controller.

**Next slice on trigger:** Pin one ordinary request and its admitted evidence. Compare controller decisions through the same existing native actions and benchmark assessment. Measure support, coverage, latency and calls. Determine whether successful traces warrant further controller research.

**Refs:** `src/application_state/agent_conversation/native_retrieval.py`; `apps/live_control_server/services/build_jev_driver.py`; `apps/live_control_server/services/plan_jev_driver.py`; `evals/buddy_benchmark/`; [original research capture](Docs/Backlog/BACKLOG-graph-exploration-system-one-controller-lab.md) as historical design input.


---


## [IDEA] App-wide theme system

**Owner:** Buddy shared presentation and surface owners
**Captured:** 2026-09-26 (theme ambition; clarified in the 2026-11-14 product discussion)
**Trigger:** Operator selects coherent, selectable styling as a product capability.

Use one shared vocabulary of semantic color, typography, spacing, focus and interaction tokens and consistent components across surfaces. Ship a selectable default and alternate theme before expanding to customization. Users and the agent should target the same bounded, typed theme settings; agent changes are reviewable and reversible, not arbitrary CSS or an independent styling path. Keep the existing palette as the default until selected otherwise. Reuse the [presentation substrate](Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md). A single surface can prove the shared contract, but do not create a Graph-only theme fork.

<a id="deferred-composable-spatial-workspace-and-selectable-themes"></a>

## [DEFERRED] Composable spatial workspace

**Owner:** Buddy presentation
**Captured:** 2026-09-26
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** The operator selects saved spatial composition for implementation.

**Current boundary:** Shared presentation components and graph canvas exist; saved multi-object workspace arrangements are not established by this backlog. The page composer handles ordered document layout. [App-wide theming](#idea-app-wide-theme-system) owns styling.

**Next slice on trigger:** Investigate existing canvas/projection components and define one saved arrangement with clear ownership of positions, sizes and camera state. Preserve low-cost pan/zoom and do not conflate coordinate mutation with theme or semantic document truth.

**Refs:** [presentation substrate plan](Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md); `apps/live-control-ui/src/localWorld/worldGraphCanvas/`.


## [DEFERRED] Create a campaign inside an existing World
**Owner:** Buddy campaign UX + DungeonMind campaign membership
**Captured:** 2026-08-11
**Last verified:** 2026-11-10 @ Buddy `8a9ad7902`, DungeonMind `430c1a6d`
**Trigger:** An operator needs to start a new campaign in an existing World through ordinary controls.

**Current boundary:** DungeonMind's campaign ingest-context route requires an existing campaign membership. Buddy's #1860 restored two retained memberships via an offline repair. Neither provides a user-facing creation operation.

**Next slice on trigger:** Define a DungeonMind-owned membership creation operation and the minimal Buddy flow that uses it. Prove the new campaign can be selected and admit its own sources in the existing World.

**Refs:** [Campaign membership repair](Docs/Plans/HANDOFF-BUILD-elderwyld-campaign-membership.md); `src/dungeonmind/service/api.py` in DungeonMind.


## [DEFERRED] Verbatim source phrase grounding in the frozen TL01 evaluation
**Owner:** Temporal grounding evaluation
**Captured:** 2026-08-01
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** A real product use case selects a temporal capability that consumes this renderer, as required by the TL01 close decision.

**Current boundary:** The original renderer check still fails when its cited snippet lacks the requested verbatim phrase. TL01 evaluation remains frozen. Current recap ingestion and source reads use exact stored spans (#1941, #1965), but those changes do not resolve this separate evaluation defect.

**Next slice on trigger:** Reproduce the retained failure through the selected consumer, then prove a known-good phrase grounds through both relevant lanes before revising cohorts or prompts.

**Refs:** [TL01 close decision](Docs/Design/DECISION-tl01-temporal-prompt-calibration-close.md), section 7; `evals/graph_memory_layer/temporal_shadow_grounding_path.py`; #1941, #1965.


---

## [DEFERRED] Propose edits to an existing related page from the current workspace
**Owner:** Build authoring
**Captured:** 2026-10-16
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** The operator asks to revise an existing related page while retaining the current workspace.

**Current boundary:** Related saved-page context, connected-page creation and saved-source relationship reviews have shipped. Build text proposals still capture one page as their mutation target. A request for a different page returns a destination mismatch or requires handoff. The broad original ticket's connected-page and relationship portions are already covered.

**Next slice on trigger:** Capture an explicit existing destination document and passage, show an editable proposal through the shared review host, and preserve the originating workspace. After saving, reuse the existing source and reviewed publication flow for any proposed Graph changes.

**Refs:** `apps/live_control_server/services/build_document_proposal.py`; `src/application_state/agent_conversation/collaboration.py`; `src/application_state/agent_conversation/relationship_review.py`; #2127, #2129, #2273.

---

# Delegated workstreams — pointers only, no root status

The rows below preserve discoverability for capabilities removed from root without creating a second status owner.

| Capability / residual | Status owner | Root disposition / owner health |
|---|---|---|
| Remaining C1/C2 source coverage and the authoring, preparation and Play journey | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) | The [DEMO bounded assignment](Docs/Plans/STEWARDS-HANDOFF-demo.md) describes the mandate. The [old Demo-Ready ladder](Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md) and [CON-READY anchor](Docs/Plans/STEWARDS-ANCHOR-con-ready.md) are historical evidence. |
| Build ready-state Reload / Discard-local actions | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) / Markdown Canvas ownership | Removed from root READY on 2026-09-08. It belongs with the real-material edit/save/reopen dogfood rather than an independent pre-Stage-6 dispatch. |
| Hermes optimistic transcript + multiline composer | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) / Agent interaction | Removed from root READY on 2026-09-08. Useful UX remains, but Agent-on-Ingest/context/observability sequencing owns when it should ship. |
| Hermes prompt/configuration quality + revision-aware cross-turn evidence deduplication | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) / Agent observability | Removed from root IDEA on 2026-09-08. Reproduce against the assembled cross-surface Agent before creating an independent slice. |
| First-class statblock and roll-table display across surfaces | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) and owning Threat/Play contracts | Assess remaining cross-surface behavior there; the Build Workbench launcher is already delivered. |
| Durable Combat board / easy roster loading | CON-READY / Play + Combat authorities | Removed from root IDEA. Combat remains a real product need, but it is later than current Demo-Ready continuity and must be re-anchored when Play/Combat resumes. |
| Native Play board usability / Beat-first current moment | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) and owning Play design | Re-anchor with DEMO when Play work resumes. |
| Rich Threat authoring, statblock presentation/media, and related conversation behavior | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) and current owning handoffs | The [Threat roadmap](Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md) retains historical design and acceptance wording. |
| Historical Campaign-Supergraph residual labels such as PR380E/PR380F and exact-run review sequencing | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) and current owning contracts | Historical design ancestry only. Do not dispatch directly from stale PR380 labels without re-anchoring against the post-cutover DungeonMind boundary. |
| Broad “durable database persistence for GM work across worktrees” umbrella | Stage 2A/2B proof + domain-specific successors | Retired as a root umbrella on 2026-09-08. Durable APP-STATE on `54331` and durable DungeonMind World on `54330` now exist and have recovery proof; remaining Combat/statblock/source-coverage/off-laptop work has narrower owners. History remains in Git. |
| Broad “move durable Buddy runtime state out of checkout-local `out/`” umbrella | Stage 2A/2B + Demo-Ready Stage 2C/8 + domain owners | Retired as a root umbrella on 2026-09-08. Checkout-local `out/` is no longer accepted product authority for the recovered core state; surviving residuals must be named by domain rather than reopening the umbrella. |
| Browser-local statblock draft persistence with untrusted receipt restore | Statblock Workbench / future durable draft owner if dogfood requires it | Retired from root READY on 2026-09-08. Browser-only storage is no longer an acceptable durability target. The safety insight survives: restoring mutable draft bytes must never restore a trusted validation receipt; any successor should use a domain-owned durable authority plus fresh validation. |
| Build/Plan shared Threat projection + campaign-useful glance | merged PR #512 | Implemented; regressions should be filed as current defects rather than reviving the old capability ticket. |
| Abandoned `/surface` / `SurfaceShell` cleanup | current source tree | Removed from active backlog after current-tree search found no owner to dispatch; resurrect only from a concrete current consumer. |

## Retained UI/product design input

The earlier detailed nine-goal inventory is in Git at the audit anchor. Keep the
following pressures without treating them as nine parallel implementation plans:

- GM-oriented navigation and a compact shared shell, preserving context/drafts.
- Playable content and usable World objects before technical/debug metadata.
- Ingest as source-faithful memory review; Build as ordinary authoring.
- Combat and roll tools integrated into the session, with owned runtime state.
- Contextual optional Agent help and low-cost presentation iteration.
- Cards' purpose, capacity, editing, boundaries and linked detail; see the current
  roadmap and OverMind's captured operator design request.

Recent navigation, notes, shared toolbar, recovery, media and session-evidence
work is already recorded in the roadmap. Reproduce a residual before dispatching
an old UI repair. Of Conks and other prototype evidence remain reference material;
a prototype is not a new durable authority.



## Consolidation record

- **2026-11-14 (operator local date):** Moved release checks and maintenance follow-ups out of the root inventory, retaining each owner's open gates and [the pinned original root evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md). Historical hygiene notes remain at [the transfer base](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L295-L354).
- Preserved [layered maps](https://github.com/Drakosfire/DungeonMindBuddy/pull/2383), [campaign arcs](https://github.com/Drakosfire/DungeonMindBuddy/pull/3328), [search replay](https://github.com/Drakosfire/DungeonMindBuddy/pull/3640), and [recap contributor](https://github.com/Drakosfire/DungeonMindBuddy/pull/3655) as separate, unscheduled captures. Split [#2389](https://github.com/Drakosfire/DungeonMindBuddy/pull/2389) into delivered Build browsing, the residual hierarchy question, and the existing extraction fix lane.
- Adopted the historical evaluation corrections from [#3186](https://github.com/Drakosfire/DungeonMindBuddy/pull/3186), preserving the current native-action controller trigger and the frozen benchmark evidence. This changes backlog ownership/discoverability only, not implementation or acceptance.

## [IDEA] Distinguish the document title from page content — captured 2026-11-27

**Context:** The document title looks like a heading in the authored page.
**Action:** Present the document title in a visually distinct header outside the editable page canvas. Keep authored headings in the page easy to recognize and edit.
**Verification:** Open a saved document with its own first heading. The document title and the first authored heading should be easy to tell apart at desktop and narrow widths.
**Surfaces when:** Document headers or page presentation work begins.

## [IDEA] Edit earlier Buddy messages and fork conversations — captured 2026-11-19

**Context:** The operator wants to revise an earlier message or explore a different direction from a prior point.
**Action:** Add edit and fork actions at a saved turn. Preserve the original conversation and its downstream turns. Reopen each branch from the picker with its own subsequent messages and the appropriate saved context.
**Surfaces when:** Conversation history, message actions, or branching work begins.

## [IDEA] Audit saved Buddy conversation loading end to end — captured 2026-11-19

**Context:** The operator reports that conversation loading seems broken.
**Action:** Reproduce with existing saved conversations on hosted Buddy. Audit the picker, active conversation selection, history pagination, refresh and surface changes, and recovery of interrupted or failed turns. Trace failures from browser to durable storage, then add regressions for the confirmed cases.
**Surfaces when:** Saved conversation loading, history display, or recovery work begins.

## [IDEA] Stop a Buddy turn and exclude it from future context — captured 2026-11-19

**Context:** The operator wants to interrupt a message at any point and prevent it from participating in future history.
**Action:** Add Stop from preparation through reply streaming. Record cancellation durably, exclude the stopped user message and any partial reply from future model context, and prevent late responses, reloads, or retries from restoring the canceled turn. Show a stopped state so the user can tell what happened.
**Surfaces when:** Conversation cancellation, turn lifecycle, or history assembly work begins.

## [IDEA] Optimize Buddy trace collection and presentation — captured 2026-11-19

**Context:** Hosted Buddy traces are valuable for debugging, but the request setup is noisy and critical-path timing still has gaps.
**Action:** Profile trace capture, persistence, reads, and rendering under realistic hosted turns. Remove duplicate events and synchronous work where evidence permits. Present each Luna or Jev call as one expandable step with the composed prompt, call configuration, timing, outcome, and retries. Make the pre-dispatch critical path and unmeasured gaps explicit, and keep the details panel stable during refresh. Preserve authorization, redaction, and the durable evidence needed to diagnose failures and verify dispatch fencing.
**Verification:** Compare trace write volume, added Send-to-first-dispatch latency, and trace open time before and after. Inspect successful, failed, retried, and historical turns on hosted Buddy.
**Surfaces when:** Trace performance, execution Details, or conversation diagnostics work begins.

## [IDEA] Cut document and page loading latency across Buddy — captured 2026-11-19

**Context:** Opening a saved document and navigating between Buddy surfaces can take several seconds. Corrupted Edge is a known hosted example.
**Action:** Profile cold entry, warm navigation, and document opens from the picker and deep links across Build, Plan, Play, Graph, and Ingest. Correlate browser navigation to usable content with server timing for authentication, document snapshots, and World data. Remove duplicate reads and request waterfalls, reuse valid World and document data across surfaces, and keep the shared navigation mounted during in-app transitions.
**Verification:** Compare p50 and p95 time to usable content before and after on hosted Buddy. Cover cold and warm loads, World changes, stale revisions, and load failures so a faster shell does not hide delayed content.
**Surfaces when:** Document navigation, page loading, or hosted performance work begins.

## [IDEA] Benchmark page element targeting in Buddy — captured 2026-11-19

**Context:** Using a saved page image through normal Send still requires selecting nearby text. Users should be able to refer to page elements naturally.
**Action:** Build a benchmark suite with saved pages containing images, passages, headings, tables, and statblocks. Label the intended element or the expected clarification for requests that refer to position, captions, names, prior context, or the current selection. Include requests with no selection, duplicate labels, nested layouts, ambiguous targets, and missing targets.
**Verification:** Report correct target selection, unnecessary clarifications, confident wrong-target choices, and latency. Check that Buddy can use the intended element through normal Send and that a missing or ambiguous target cannot silently become an edit to a different element.
**Surfaces when:** Build or shared page-context selection, image references, or agent authoring benchmarks begin.

## [IDEA] Hide provisional World state from users — captured 2026-11-20

**Context:** Buddy Cloud Pilot could save Build and Plan documents while Graph, Play, and Combat Tracker exposed internal Graph provisioning and publication states.
**Insight:** Provisional state is useful for backend lifecycle management and provenance. A user should see a World and the actions available in it. An empty World should feel ready to start.
**Shipped:** [#4631](https://github.com/Drakosfire/DungeonMindBuddy/pull/4631) renamed the shared Build and Plan fieldset to “Review GM facts.” Hosted Pilot verified the visible and accessible label and reached confirmation with a saved supporting excerpt.
**Remaining:** Audit World creation, navigation, extraction, and first-Graph setup for internal lifecycle labels. Start with Build’s source admission status and retry controls. Describe what the user can do or when to retry. Keep lifecycle state and provenance in backend records and operator diagnostics.
**Verification:** Open a new World before and after its first Graph publication. Check that user-facing surfaces show an inviting empty state or actionable feedback and that operators can still inspect the underlying state and provenance.
**Surfaces when:** World onboarding, first Graph publication, or empty states across Buddy are being changed.

## [IDEA] Show what Buddy is doing while it works — captured 2026-11-20

**Context:** Buddy’s Thinking text can stay on “Getting Things Ready” while several different operations are underway.

**Action:** Drive short, user-facing progress messages from real tool and action events. Show what Buddy is doing when it checks the saved page, searches the World, reads a source, or prepares a suggestion. Use a distinct status when Buddy is waiting on a tool. Coalesce repeated activity to keep the text steady, and keep technical detail in the trace.

**First slice:** Test one ordinary Build request that reads a source and prepares an answer. Compare each visible status with the actual event sequence, including a slow or failed tool call.

**Surfaces when:** Updating conversation progress, profiling pre-reply latency, or consolidating the trace.

## [IDEA] Explore Syrinscape in Plan and Play — captured 2026-11-24

**Context:** The operator already owns Syrinscape content and wants to cue it during sessions.

**Action:** Evaluate user sign-in and account authorization, on-demand lookup in the existing library, and an embedded player versus an external launch. Prove that a GM can reference one cue in Plan and explicitly start and stop it in Play, with Syrinscape handling playback. Record credential handling and whether players can join the same session.

**Refs:** [Syrinscape JavaScript player](https://docs.syrinscape.com/javascript-player/) and [HTTP API](https://docs.syrinscape.com/http-reference/).

## [IDEA] Explore local audio generation for Plan and Play — captured 2026-11-24

**Context:** The operator wants to generate original audio on their workstation and reuse approved tracks across sessions.

**Action:** Generate and audition a small set of music beds, looping ambience, and short effects on the workstation. Record quality, generation time, curation effort, licensing, and provenance. Sketch a searchable catalog with stable asset references, compare cloud object storage with the operator's media server for direct browser playback, and demonstrate how Plan could reference one approved cue for manual playback in Play.

**Surfaces when:** Selecting an audio generation experiment or designing a reusable audio catalog.
