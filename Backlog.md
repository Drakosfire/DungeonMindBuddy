# DungeonMindBuddy — Backlog

Project-specific ideas and independently actionable follow-ups for DungeonMindBuddy and the Eldyrwild corpus it serves. Cross-project / AI-tooling items live in `~/.cursor/learnings/Backlog.md` instead.

**Format:** see `~/.cursor/skills/capture-learning/SKILL.md`.  
**Status legend:** `IDEA` → `READY` → `DOING`. Terminal states with lasting reference value may be archived to `Backlog-DONE.md`.

Sort newest → oldest within each status; promote with `/promote`; archive with `/done` or `/drop`.

> **Backlog hygiene rule (2026-08-16):** Active implementation sequencing belongs in its owning roadmap / PR tracker, not duplicated here. In particular, `Docs/Plans/PR-TRACKER-campaign-supergraph.md` is the sole sequence authority for Campaign Supergraph work. This file is for independent product debt, dogfood findings, and follow-ups that do not already have a sequencing owner. Before dispatching an entry older than 30 days, re-verify it against current `main`; if the original architecture or owning workstream has been replaced, rewrite or drop the entry rather than executing it literally.
>
> **2026-08-16 cleanup:** The prior active file had 74 status headings spanning April–August and mixed current work with completed experiments, superseded architectures, process rules, and already-shipped fixes. This pass intentionally keeps only a smaller set of independently actionable items. See `Docs/Reports/BACKLOG-HYGIENE-2026-08-16.md` for disposition rules and examples. Removed entries remain available in Git history; they were not bulk-copied into `Backlog-DONE.md` because many were superseded research notes rather than terminal implementation tickets.

## [READY] Build Import — create a new campaign inside an existing world — retained 2026-08-16
**Context:** The earlier combined item covered both new-world and new-campaign creation. CR01B / PR #564 already established the new-world path via the managed world-container registry.
**Insight:** New campaign creation is a distinct placement/lifecycle capability and should not stay hidden inside a ticket whose new-world half is already implemented.
**Action:** Design and implement intentional campaign creation inside an admitted world, with explicit campaign identity and no implicit graph fork or duplicated world entities.
**Surfaces when:** Build Import, New Source, campaign selector, managed world-container registry, create campaign.
**Refs:** `Docs/Plans/HANDOFF-BUILD-create-new-world-from-build.md`; `Docs/Design/CONTRACT-world-container-v1.md`; `Docs/Roadmaps/ROADMAP-con-ready.md`.

## [READY] Preserve Plan Ask continuity across prep-document switches — captured 2026-08-11
**Context:** DOGFOOD-POLISH made exact prep selection, intentional creation, and same-session multi-prep normal. `documentId` scopes the Canvas work object; it must not accidentally define Hermes conversation identity.
**Insight:** Conversation continuity and document identity are separate authorities.
**Action:** Characterize current thread persistence/keying and define A → B → A prep-switch semantics. Preserve same-thread dialogue while the active document context changes; explicit new-thread behavior remains explicit.
**Surfaces when:** Plan Ask, prep selector, Create New Prep, Hermes thread storage, Surface Context, `documentId` switch.
**Refs:** `Docs/Plans/HANDOFF-BUILD-dogfood-polish-generalized-workspace-document-create.md`; `apps/live-control-ui/src/planSurface/`; `Docs/Reports/DOGFOOD-POLISH-CLOSEOUT-2026-08-11.md`.

## [READY] Shared Threat projection parity across Plan and Build — captured 2026-08-11, narrowed 2026-08-16
**Context:** Plan already opens Threat chips to the campaign-facing `ThreatSheetProjection`; Build has exact graph-reference search/insertion and `GraphNodeChipRuntimeProvider`.
**Insight:** The same exact Threat should open the same projection regardless of surface. This is separate from where Statblock Workbench launchers are published.
**Action:** Hoist/register Threat content projection surface-agnostically for Plan + Build. Falsify identical Threat chip behavior on both surfaces with no Plan ownership leak.
**Surfaces when:** Build Threat chip, `ThreatSheetProjection`, `BuildReferenceCapability`, `GraphNodeChipRuntimeProvider`.
**Refs:** `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`; `Docs/Plans/HANDOFF-STATBLOCK-ux-ui-world-object-reboot.md`.

## [READY] Publish Statblock Workbench capability where Build needs it — split 2026-08-16
**Context:** The previous Threat-parity item also bundled shared Statblock tooling.
**Insight:** Threat projection is a content projection; Workbench is an authoring tool. They should not be one capability just because both concern Threats.
**Action:** Publish the existing Statblock tool inventory through the shared Tool Host for Build where appropriate, without recreating Plan-local chrome or coupling Threat opening to Workbench ownership.
**Surfaces when:** Build Tools, Statblock Workbench, Tool Host, surface capability publication.
**Refs:** `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`; `Docs/Plans/HANDOFF-STATBLOCK-ux-ui-world-object-reboot.md`.

## [READY] Build ready-state Reload / Discard-local actions — split 2026-08-16
**Context:** Save is owned by the shared Edit Host and conflict recovery exists in MarkdownCanvas. The old entry bundled local working-copy recovery with durable source lifecycle.
**Insight:** Discarding a local draft is not the same authority as archiving a durable source.
**Action:** Design ordinary ready-state Reload / Discard-local through existing Canvas/Edit ownership, with no Build-specific duplicate heading bar.
**Surfaces when:** Build Edit Host, Reload, Discard local, MarkdownCanvas conflict recovery.
**Refs:** `Docs/Reports/DOGFOOD-POLISH-CLOSEOUT-2026-08-11.md`; `apps/live-control-ui/src/markdownCanvas/`.

## [READY] Durable source archive / restore lifecycle — split 2026-08-16
**Context:** Durable source deletion/archive semantics were previously bundled with local draft recovery.
**Insight:** Durable source lifecycle is a server-owned destructive operation and needs its own authority/restore contract.
**Action:** Design archive/discard/restore for durable sources with explicit confirmation, auditability, and no ambiguity with local draft discard.
**Surfaces when:** source archive, source restore, Build source lifecycle, destructive source actions.
**Refs:** `Docs/Reports/DOGFOOD-POLISH-CLOSEOUT-2026-08-11.md`; Build source services and document registry.

## [READY] Threat glance should be campaign-useful, not metadata-first — captured 2026-08-04, narrowed 2026-08-16
**Context:** MAGIC-D3 proved governed Threat publication and Plan/Hermes rediscovery, but the default glance/hover still exposes engineering provenance more prominently than encounter usefulness.
**Insight:** Publication correctness is not the same as useful presentation.
**Action:** Make the compact Threat glance lead with name, role/feel, and hydrated AC/HP/CR/speed when available; move IDs/digests/provenance behind inspect/trace. Keep this slice presentation-only; Hermes progress and general latency live in separate items below.
**Surfaces when:** Threat Sheet, `glanceOnly`, hover card, `ThreatSheetProjection`, hydrated mechanics.
**Refs:** `Docs/Reports/MAGIC-MOMENT-D3-2026-08-04.md`; `Docs/Reports/MAGIC-MOMENT-D3-2026-08-05.md`; `ThreatSheetProjection.tsx`.

## [READY] Verbatim `source_phrase` grounding vs renderer snippets — captured 2026-08-01, rescoped 2026-08-03
**Context:** TL01 close left one bounded deterministic failure: development phrase-grounding fails in both lanes when the required verbatim phrase is not present in the renderer-produced cited snippet.
**Insight:** This is a renderer/evidence contract problem, not a prompt-tuning problem.
**Action:** Only when phrase-level extraction needs this path, prove one known-good smoke case grounds through both lanes before authoring new cohorts or prompts. Keep sealed cohorts/gold untouched.
**Surfaces when:** `grounding_failure`, `source_phrase`, phrase-level evidence binding, renderer snippet fidelity.
**Refs:** `Docs/Design/DECISION-tl01-temporal-prompt-calibration-close.md`; `Docs/Reports/REPORT-tl01g-v15-adv13-promotion-matrix.md`; `Docs/Reports/REPORT-tl01g-grounding-path-recovery.md`; PRs #468, #486, #500.

## [READY] Hermes authoring needs a dynamic copyable markdown artifact — captured 2026-07-30
**Context:** R0-B produced useful paste-ready prose inside a long conversational answer, but there is no dedicated copy/edit artifact interaction.
**Insight:** Copyable authoring is a product interaction, not a Markdown-fence convention.
**Action:** Define a structured markdown artifact with copy/edit affordances and separate provenance/uncertainty metadata; teach grounded authoring to emit it for paste-ready Threat/prep blocks.
**Surfaces when:** Hermes authoring, dynamic markdown, Copy markdown, ThreatDraft description, structured UI output.
**Refs:** `Docs/Reports/MAGIC-MOMENT-R0-B-2026-07-30.md`; `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`.

## [READY] Hermes composer — optimistic transcript + usable multiline input — captured 2026-07-30
**Context:** Submitted questions remain in the input until the response returns; the one-row composer is cramped for serious prep questions.
**Insight:** The composer behaves like a blocking form instead of a chat surface.
**Action:** Optimistically render the user turn, clear the input, attach truthful pending/error/retry state, and use an auto-growing multiline composer with explicit Enter/Shift+Enter behavior.
**Surfaces when:** Hermes composer, Plan Ask, pending assistant turn, multiline input, retry.
**Refs:** `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`.

## [READY] Hermes honest live-progress UX — captured 2026-07-30
**Context:** Long Hermes turns currently collapse to a generic asking state; the operator cannot distinguish active work from a stall.
**Insight:** A spinner is not enough, but fake internal stages are worse.
**Action:** Add elapsed-time + truthful in-flight/recovery UI now. Longer-term, consume real lifecycle events or a pollable operation for accepted/retrieval/source/synthesis/complete and cancel/retry.
**Surfaces when:** Hermes wait, agent liveness, elapsed time, cancel/retry, turn operation.
**Refs:** `PlanAgentInteractionBar.tsx`; `apps/live_control_server/services/hermes_graph_query.py`; `apps/live_control_server/services/hermes_graph_agent_host.py`.

## [READY] Hermes performance telemetry — operationalize existing trace data — captured 2026-07-30
**Context:** Backend responses already include tool events, per-tool duration, bounded graph/source counts, outcomes, and diagnostic codes, but the data is not a durable/queryable dogfood record.
**Insight:** Instrumentation mostly exists; operationalization does not.
**Action:** Persist a privacy-safe turn telemetry envelope and build a small trace/aggregate report for p50/p95 latency, per-tool time, bounded graph/source counts, warning/error codes, model/prompt/schema provenance, and token/cost metrics when available. Keep raw corpus text/prompts out.
**Surfaces when:** Hermes telemetry, p50/p95, tool duration, latency diagnosis, token cost.
**Refs:** `apps/live_control_server/services/hermes_graph_agent_contract.py`; `apps/live_control_server/services/hermes_graph_query.py`.

## [READY] Grounded answer → Threat seed authoring capability — captured 2026-07-30
**Context:** Hermes can produce grounded research answers that still stop one transformation short of an editable Threat description.
**Insight:** Retrieval grounding and bounded creative authoring are separate capabilities.
**Action:** Add an authoring action/skill that carries forward evidence boundaries and emits `established`, `inferred`, `creative proposal`, and `unknown`, plus a concise editable Threat description candidate without inventing canon/mechanics.
**Surfaces when:** Hermes answer, ThreatDraft handoff, grounded authoring, answer-to-artifact.
**Refs:** `Docs/Runbooks/INSTRUCTIONS-reboot-dogfood-R0A-R0B.md`; `Docs/Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md`.

## [READY] Hermes grounded graph chips in answers and queries — captured 2026-07-30
**Context:** Hermes already returns graph references/retrieval trace, but prose does not expose those nodes as reusable authoring interactions and the composer lacks explicit node-ref input.
**Insight:** Retrieved evidence context, decorative text matching, and explicit user-directed graph refs are different semantics.
**Action:** Add response-side chips restricted to retrieved nodes plus explicit query chips serialized as stable node/revision refs. Stale/unresolved refs remain visible errors; chips never create new citation authority.
**Surfaces when:** Hermes chips, graph references, query anchors, `@` graph search, response-to-query.
**Refs:** `apps/live-control-ui/src/api/types.ts`; `WorldGraphQueryContextPanel.tsx`; `hermes_graph_query.py`.

## [READY] Workbench Revise-with-AI UX cleanup — captured 2026-07-30
**Context:** Revise orchestration exists, but the default UI exposes recovery IDs and transport choreography instead of a simple GM revision flow.
**Insight:** Tested orchestration is not product-ready interaction.
**Action:** Provide one primary “Revise from working copy” flow with a plain instruction box; hide recovery controls under Advanced unless needed; show a clear new-proposal outcome before re-adding revise to the R0-A hard gate.
**Surfaces when:** `ReviseWithAiPanel`, proposal history, R0-A revise, SBW06 polish.
**Refs:** `apps/live-control-ui/src/statblocks/revision/StatblockRevisePanels.tsx`; `StatblockWorkbenchModule.tsx`.

## [READY] Expand Workbench dedicated mechanic editing — captured 2026-07-30
**Context:** Dedicated controls cover name, abilities, primary AC, one HP scalar, and rule-element name/prose, but not several mechanics operators reasonably expect to edit directly.
**Insight:** Dogfood claims should match the actual editor surface.
**Action:** Add dedicated controls in bounded order: walk speed; attack `to_hit` + one damage formula; save DC on save-effect mechanics. Keep protected fallback for everything else.
**Surfaces when:** `StatblockDefinitionEditor`, speed, attack bonus, damage, save DC.
**Refs:** `apps/live-control-ui/src/statblocks/editor/StatblockDefinitionEditor.tsx`.

## [READY] Generation liveness via lease heartbeat, not one wall-clock timeout — captured 2026-07-30
**Context:** A real DMS generation completed after Buddy's shorter client timeout, producing a false failure while the server continued successfully.
**Insight:** Fixed request timeouts guess model latency; the durable generation lease is the liveness signal the system actually owns.
**Action:** Make generation operation-status/lease renewal pollable and let Buddy/UI treat a fresh lease as heartbeat. Fail on stalled/dead lease plus a safety ceiling, not on a single predicted generation duration. Start with generate, then revise if warranted.
**Surfaces when:** `downstream_timeout`, generation lease, async generate, Workbench generating state.
**Refs:** Buddy DungeonMind statblock client/config; DMS `CandidateGenerationOperationV1` / generation application service.

## [READY] Delete abandoned Live Control `/surface` board — captured 2026-07-29
**Context:** Product entry is root → Plan/Ingest/Build/Combat; `/surface` and `/live-control` are leftover module-layout UI and have repeatedly leaked back into dogfood instructions.
**Insight:** Dead routes create false product doors and maintenance debt.
**Action:** Audit remaining consumers, update any still-current runbooks, then delete/quarantine `SurfaceShell` and obsolete layout APIs/tests once no named consumer remains.
**Surfaces when:** `/surface`, `/live-control`, `SurfaceShell`, launcher/product navigation.
**Refs:** `apps/live-control-ui/src/App.tsx`; `apps/live-control-ui/src/surface/SurfaceShell.tsx`.

## [READY] Worldbuilding draft elevation contract — captured 2026-07-24
**Context:** Worldbuilding extraction correctly stamps `worldbuilding_draft`; promote requires played-canon authority. BLD-07 therefore narrowed to inspect-only rather than lying about publication.
**Insight:** Reviewable draft lore is not played truth. Elevation needs an explicit authority transition.
**Action:** Decide/implement how a reviewed `worldbuilding_draft` becomes publishable: draft graph/overlay, explicit operator elevation, or another profile-specific authority transition that does not silently relabel draft as played canon.
**Surfaces when:** Build Extract → Graph Review → merge, `worldbuilding_draft`, `not_promote_eligible`, BLD-08+.
**Refs:** `src/graph_memory/candidate_semantic_promote_matrix.py`; `src/graph_memory/extraction/worldbuilding_plumbing_profile.py`; Campaign Supergraph acceptance debt.

## [READY] Generalize exact-run Graph Review presentation — captured 2026-07-24
**Context:** Exact ExtractionRun handoff reused promote plumbing but not the richer recap review presentation; source/assertion/evidence interaction feels like a stub beside the recap workbench.
**Insight:** Exact-run candidate authority should not imply a second review product.
**Action:** Use one Graph Review presentation for exact runs: source-prose selection/highlight, first-class assertion rail, and prepare/confirm in the same chrome when promotable. Preserve Kernel semantics.
**Surfaces when:** exact-run candidate review, `GraphReviewExactRunProjection`, Build → Graph Review handoff.
**Refs:** `GraphReviewWorkbenchModule.tsx`; `GraphReviewExactRunProjection.tsx`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md` exact-run candidate review sequence.

## [READY] Inspect exact-run evidence failures without weakening promotion gates — captured 2026-07-24
**Context:** A run may be extraction-reviewable while strict review-package construction rejects a false/misaligned anchor quote, leaving the operator with only an error string.
**Insight:** Inspectability and promotability are distinct states.
**Action:** Return an inspectable package with source prose, assertions, and structured evidence issues even when promotion is blocked; keep Prepare/Confirm hard-blocked until issues are resolved.
**Surfaces when:** `false_anchor_quote`, `run_not_promotable`, exact-run evidence inspection.
**Refs:** `apps/live_control_server/services/extract_promote.py`; `GraphReviewExactRunProjection.tsx`.

## [READY] Browser-local statblock draft persistence with honest receipt trust — captured 2026-07-24
**Context:** Local persistence was reverted because restoring a validation receipt from mutable storage would falsely preserve exact-definition trust.
**Insight:** Working-copy persistence is safe; receipt authority is not automatically portable through mutable browser storage.
**Action:** Persist working copy/undo/view state, but restore as unvalidated and require fresh server validation. Only restore receipts later if they gain explicit tamper/freshness binding.
**Surfaces when:** tab reopen, localStorage editor draft, validation receipt restore.
**Refs:** reverted `statblockEditorDraftStore.ts`; PR #404 review history.

## [READY] Ingest Recap primary-path simplification — captured 2026-07-13, consolidated 2026-08-16
**Context:** The current wizard exposes too many peer controls and multiple operator-facing session/source identities. Earlier dogfood also found the promote CTA hard to discover.
**Insight:** Most confusion comes from presenting mechanical pipeline stages as choices rather than background progression and from having more than one apparent “working session.”
**Action:** Collapse to one primary path (paste/load → generate → review/merge), keep readiness as the single status surface, move mechanical satisfied steps into background progression, synchronize the working session/source identity, and make the transition to Graph Review explicit. Keep force/recovery controls under Advanced.
**Surfaces when:** `IngestionModule.tsx`, ingest readiness, Load prior ingestion, Review & merge, session identity.
**Refs:** `apps/live-control-ui/src/modules/ingestReadiness.ts`; `apps/live-control-ui/src/modules/IngestionModule.tsx`; `Docs/Design/DESIGN-extract-promote-graph-review-bridge.md`.

## [READY] World-anchor insertion for world-fed known entities (E1b) — captured 2026-08-08
**Context:** World-fed suppression reused known identities but reduced gold recall because world-known nodes were suppressed without inserting canonical anchors; party anchoring already demonstrates the substitution pattern.
**Insight:** Suppression is subtraction; anchoring is substitution. Owned canonical IDs must remain in the candidate graph so edges and review can bind to them.
**Action:** Insert canonical world-anchor nodes for mentioned world entities, analogous to party anchors; rerun the existing S23/S25 Luna experiment and require no regression against the control recall bar before graduation.
**Surfaces when:** recap graph extraction, known-entity registry, world-head context, edge endpoint binding.
**Refs:** `evals/graph_memory_layer/run_world_fed_registry_experiment.py`; `src/graph_memory/extraction/known_entity_registry.py`; `src/graph_memory/session_graph_context.py`.

## [READY] Ecology/resource as its own extraction pass — captured 2026-07-18
**Context:** Named session creatures belong in actor extraction; species/flora/fauna/products/habitat pressure has repeatedly produced cross-class actor/object duplication.
**Insight:** Ecology/resource concepts are neither individual actors nor generic objects.
**Action:** Design an `ecology_resource_pass` with bounded species/resource/region semantics and tighten object extraction against commodity/species explosion. Keep session-recap use lighter than worldbuilding use.
**Surfaces when:** fauna/flora taxonomy, products/resources, Float Goat species vs individual creature, worldbuilding extraction.
**Refs:** `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-MANUAL-REVIEW.md`; `Docs/Plans/HANDOFF-prime-design-graph-memory-extraction-taxonomy.md`.

## [IDEA] Expand statblock presentation to styling + images without mutating mechanics identity — captured 2026-08-06
**Context:** The product direction includes styled cards and media while the domain already separates immutable mechanics revision, presentation, and image refs.
**Insight:** A GM-facing statblock card is a composed projection, not one stored blob.
**Action:** Design presentation/media composition after core glance UX: parchment/PHB styling plus portrait/token/thumbnail refs, with tests proving style/image changes never mutate `definition_digest` or silently rebind mechanics revision.
**Surfaces when:** statblock styling, portrait/token art, image refs, `StatblockRenderer`.
**Refs:** `Docs/Design/DESIGN-authored-threat-statblock-domain-contract.md`; `Docs/Plans/HANDOFF-STATBLOCK-ux-ui-world-object-reboot.md`.

## [IDEA] Move durable Buddy runtime state out of checkout-local `out/` — captured 2026-07-24
**Context:** Worktree dogfood exposed that World Graph/run registries/Threat drafts/candidate cache under gitignored `out/` do not compose cleanly with parallel worktrees and path-containment safety.
**Insight:** Checkout-local JSON trees are a poor long-term durability boundary for shared runtime state.
**Action:** Open a design spike for a shared DB/store service, starting with the highest-pain durable `out/` consumers. Keep auditable source Markdown where it belongs; do not conflate source storage with runtime state.
**Surfaces when:** multi-worktree dogfood, world graph root, graph-ingest run registry, ThreatDraft store, statblock candidate cache.
**Refs:** `apps/live_control_server/config.py`; `graph_ingest_run_registry.py`; `threat_draft_store.py`; `statblock_candidate_cache.py`.

## [IDEA] Hermes prompt/configuration quality pass — consolidated 2026-08-16
**Context:** Dogfood has shown occasional system-meta narration and uneven co-GM voice; prompts, tool descriptions, capability policy, answer-scope rules, and model/host settings have not received the same systematic audit as graph contracts.
**Insight:** Thread isolation and host mechanics are invariants Hermes should obey, not narrate by default.
**Action:** Inventory Hermes prompt/config end-to-end and run a small falsifiable dogfood set, including “no system-meta narration,” campaign-facing voice, uncertainty behavior, and tool-selection quality. Keep this separate from retrieval authority changes.
**Surfaces when:** Hermes answer quality, prompt edits, capability policy, model policy.
**Refs:** `apps/live_control_server/services/hermes_graph_query.py`; `Docs/Design/ARCHITECTURE-hermes-campaign-authoring-foundation.md`; `Docs/Design/UX-STORIES-hermes-campaign-authoring-foundation.md`.

## [IDEA] Revision-aware evidence deduplication across Hermes turns — captured 2026-07-16
**Context:** Turn-local claims are keyed within a retrieval session, but there is no explicit cross-turn reuse/dedup telemetry keyed by conceptual identity plus revision.
**Insight:** Stable object identity does not mean stable factual state; same-object evidence at a new graph revision must remain distinguishable.
**Action:** Design cross-turn evidence identity/reuse around `(object_id, revision_id)` where appropriate, exposing bounded new/reused/changed-revision decisions without turning prior-turn context into current authority.
**Surfaces when:** Hermes continuity, evidence reuse, graph revision tracking, freshness telemetry.
**Refs:** `apps/live_control_server/services/hermes_graph_query.py`; `src/graph_memory/interaction/session.py`; `src/graph_memory/kernel/world_retrieval.py`.
