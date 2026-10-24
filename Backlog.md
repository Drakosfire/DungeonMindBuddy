# DungeonMindBuddy — Backlog

This file is the **root dispatch inventory** for independent DungeonMindBuddy work that does not already have a sequencing owner.

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
The old demo-ready roadmap and 2026-09-08 dispatch snapshot are historical.
Do not infer a current blocker or READY assignment from them.

---

# Independent ideas requiring re-verification

## [IDEA] High priority — shared grid page constructor
**Priority:** HIGH — explicitly requested by the operator.  
**Kind:** DESIGN → bounded implementation slices  
**Owner:** Build / shared Surface authoring  
**Captured:** 2026-10-24  
**Last verified:** 2026-10-24 @ `c74b5082ead867cd28fb302935dc05965dc1f4c0`  
**Context:** Edge authoring dogfood: the author wants to move and resize artwork on a snapping grid, then compose images, editable text, tables and callouts intentionally on the page.

**Direction:** Keep Tiptap for writing; define shared row/column layout containers, stable section identities and durable layout representation. Preserve reading order for retrieval, citations and Markdown export. Distinguish this page-layout work from the deferred infinite spatial workspace below.

**First slice to design:** Move and resize one existing image on a visible snapping grid. Decide persistence ownership and representation before implementation; image centering is an immediate separate convenience, not completion of the grid constructor.

**Exit proof:** Ordinary controls place/resize an image; Save, reload and reopen preserve placement, undo/recovery preserve authorship, and narrow screens stack content predictably. Later slices may add adjacent editable text, tables/callouts and agent suggestion placement using stable section identities. Freeform overlap, pan/zoom and connectors require separate selection.

**Surfaces when:** Planning Build authoring, media placement, shared page layout or proposal insertion. Product sequencing remains owned by `Docs/Roadmaps/ROADMAP-demo.md`; high priority does not activate implementation or resume the paused broad goal.

**Refs:** Edge source `bba72416-9dfe-49bb-add0-21a346e9a421`; `apps/live-control-ui/src/tiptap/extensions/MediaImageNode.tsx`; `apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts`; conversation `01a0ef89-ca57-7b82-9c9c-215b02d0fc3b`.


## [IDEA] Publish Statblock Workbench as a Build Tool capability
**Kind:** CODE  
**Owner:** Build / Surface Interaction  
**Captured:** 2026-08-11  
**Last verified:** 2026-09-08 @ `df15db4c695240ce08b5812d43ca398cd70ff6ac`  
**Depends on:** shared Tool Host merged in PR #501; native Build Surface Interaction publication merged in PR #506; shared Threat projection/lens merged in PR #512. The Threat/Statblock roadmap still explicitly leaves this capability in root backlog until sequenced elsewhere.

**Problem:** Build can natively publish/search/inspect World Graph capabilities through shared hosts, but Statblock Workbench authoring is not yet an ordinary Build Tool capability.

**Slice:** Publish the existing Workbench launcher/inventory through the active Build Surface Interaction lease. Reuse the shared Tool Host and existing Workbench; do not create Build-local tool chrome or couple Threat viewing to Workbench ownership.

**Exit proof:** From an admitted Build document, the shared Tool Host exposes the Workbench capability, opens the existing Workbench, survives surface/document lease replacement correctly, and leaves Plan behavior and graph/document authority unchanged.

**Refs:** PRs #501, #506, #512; `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`; `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`; `apps/live-control-ui/src/surfaceInteraction/`.

## [IDEA] Define independent source-artifact archive / restore lifecycle
**Kind:** DESIGN  
**Owner:** APP-STATE / source lifecycle  
**Captured:** 2026-08-11  
**Last verified:** 2026-09-08 @ `df15db4c695240ce08b5812d43ca398cd70ff6ac`  
**Depends on:** Stage 2A durable APP-STATE authority on `54331`; immutable `source.artifact` / `source.revision` identity and exact source-Markdown service; local editor discard remains a separate non-destructive concept.

**Problem:** Build/Plan/Play now have recoverable Trash (#1445–#1447). Reproduce any remaining need to independently archive source artifacts/revisions before designing another lifecycle. Document Trash, editor draft discard and underlying evidence retention have different meanings; the old missing-delete claim is obsolete.

**Slice:** Define archive, visibility, restore, collision, audit, confirmation, and exact-identity semantics for one APP-STATE durable source. Do not implement local-draft discard in this slice. Do not hard-delete by default without a named contract reason.

**Exit proof:** One checked-in contract/decision + bounded implementation handoff makes archive vs local discard unambiguous, defines recoverability and exact artifact/revision identity after restore, and identifies the authorized APP-STATE server write boundary.

**Refs:** `Docs/Reports/REPORT-application-state-durability-drill.md`; `Docs/Reports/REPORT-stage-2b-c1-c2-repopulation.md`; `src/application_state/source/service.py`; `Docs/Reports/DOGFOOD-POLISH-CLOSEOUT-2026-08-11.md`.

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

# IDEA

## [IDEA] Background suggestions for missing World graph relationships — captured 2026-10-13
**Context:** Mirathorn context-loop dogfooding: the loaded graph has a disconnected Sara node and no Frank node-name match, while corpus recaps describe their operator roles and connections to Mirathorn, Lysandra, and the rockie-talkie network.
**Insight:** Buddy should suggest additional evidence-backed edges. A low-cost background decision loop could identify candidate relationships in admitted sources, assess whether they are already represented and useful, and surface them only when user review or a decision is needed.
**Action:** Design bounded candidate generation and triage: preserve source references and proposed endpoints/predicates; deduplicate existing or previously reviewed candidates; distinguish explicit source facts from inference; decide when to stay quiet versus request review. Retain an inspectable record of why a candidate was suppressed or surfaced. Automatic publication is not decided by this idea. Buddy owns suggestions and review UX; canonical relationship publication requires the owning World graph contract.
**Surfaces when:** Iterating Buddy's conversation context loop, investigating sparse subject neighbourhoods, improving relationship extraction, or designing proactive graph review.
**Refs:** Mirathorn context-loop discussion and loaded Elderwyld graph inspection, 2026-10-13; `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/sara_mirathorn_operator_character_dossier.md`.

## [IDEA] Graph exploration controller lab — oracle traces to System One policy
**Kind:** RESEARCH / EVALUATION / AGENT RETRIEVAL  
**Owner:** Agent retrieval / DungeonMind graph-read consumer  
**Captured:** 2026-09-26  
**Last verified:** 2026-09-26 after review of current Agent graph-query benchmark  
**Depends on:** the existing Agent graph-query benchmark and a normally product-readable pinned World/revision. This does not own sequencing and must re-anchor against the post-CUTOVER DungeonMind/Buddy read boundary before promotion.

**Problem:** The existing graph-query benchmark already distinguishes product loadability, oracle retrieval, and real-Agent orchestration, but its oracle layer is manual/scripted. DungeonBuddy has enough real corpus and challenging gold to turn that layer into a constrained graph-navigation game. A strong code agent can play the game using only legal bounded graph actions; its trajectories and failures can reveal the smallest reusable action algebra needed for difficult retrieval. Those state/action traces can later benchmark cheaper policies, including a System One / Jev-style controller.

**Research direction:** Start with a deliberately tiny read-only action set such as resolve, expand, follow, open evidence, and supported/insufficient stop. Record every legal alternative, chosen action, observation, evidence admitted, budget, and termination. Classify failures before adding actions. New actions must be general graph operations, not benchmark-specific semantic shortcuts. Retrieval quality is scored separately from final answer synthesis.

**Critical constraints:** No arbitrary repository/corpus search by the explorer; no raw storage/SQL bypass; no visibility/admissibility bypass; no parallel graph authority; no hidden full LLM behind one giant search action; Jev is a later controller experiment, not the first implementation dependency.

**Promotion trigger:** The current graph-query benchmark can run against one pinned, product-readable revision and there is a clean seam for exposing legal bounded actions without creating another retrieval backend.

**Likely first slice on promotion:** Build only the bounded read-only graph-exploration environment and deterministic trace contract. Code-agent oracle automation, action-set discovery, and Jev/System One comparison remain successors.

**Detailed capture:** Docs/Backlog/BACKLOG-graph-exploration-system-one-controller-lab.md  
**Parent benchmark:** Docs/Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md

---

# DEFERRED

## [DEFERRED] Composable spatial workspace + instant theme packs
**Kind:** PRODUCT DESIGN / FRONTEND ARCHITECTURE / RESEARCH  
**Owner:** Buddy presentation layer / future spatial workspace  
**Captured:** 2026-09-26  
**Last verified:** 2026-09-26 @ `24e0565145ad578783c3b9ed3b0b672d9f6b3f30` after UI-F1–F4 substrate work merged/reviewed  
**Trigger:** a basic demo-ready Buddy presentation is accepted and the product can afford exploratory spatial/composable UI work without delaying the demo.

**Problem:** The long-term presentation dream is a fast, composable workspace where the GM can arrange reusable Buddy components freely on a large/infinite spatial surface, save different workspace arrangements, zoom between overview and detail, and swap pre-baked visual themes (for example D&D/fantasy → sci-fi) instantly without changing component semantics, data, or layout ownership. This is intentionally **not** the current demo-readiness priority.

**Design direction to preserve:**

```text
Buddy domain / durable state
        ↓
presentation model
        ↓
Buddy component registry
        ↓
presentation engine
  ├─ Flow
  ├─ Page / Print
  └─ Spatial / infinite workspace

theme pack is orthogonal:
  component + layout stay the same
  semantic CSS/theme tokens repaint the workspace
```

Keep these concerns independent:

- **component meaning:** World object, Scene, Runbook, ToolHost, Agent, Combat, note, map, etc.;
- **spatial layout:** x/y/size/z/collapse/group/camera/workspace preset only;
- **theme:** semantic paint/typography/radius/border/shadow/icon treatment only;
- **durable authority:** remains in Buddy/DungeonMind/APP-STATE; the spatial layer references objects and must not copy their bodies into a second truth store.

Performance is a first-class requirement because the ordinary development/client machine may be weak. A future spatial engine should therefore prefer viewport culling, cheap pan/zoom, level-of-detail rendering, stable component identity, and avoiding full expensive component renders when zoomed far out.

**Next slice on trigger:** Design/research only. Re-anchor against the then-current presentation substrate and compare at least:

1. a library-backed spatial engine (tldraw is a current candidate, not a decision);
2. a deliberately small Buddy-owned spatial engine;
3. whether the existing `Drakosfire/Canvas` package should remain Page/Print-only rather than serving spatial work.

Freeze a minimal `SpatialWorkspacePort` / spatial-item contract and a theme-pack token contract before implementation. Explicitly decide persistence ownership for workspace arrangement and camera state. Do **not** start by building freeform interaction mechanics, merging Page and Spatial canvas concerns, or coupling themes to domain components.

**Desired eventual experience:** the same ObjectSheet/Scene/Runbook/etc. can be moved around a saved infinite workspace, switch between workspace presets such as “At the Table” and “Worldbuilding,” and instantly change visual language (fantasy, sci-fi, clean, etc.) by swapping theme tokens without rebuilding or reauthoring the components.

**Refs:** `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md`; `Docs/Design/ui-language/DESIGN-interaction-layer-language.md`; F1–F4 presentation-substrate work; `Drakosfire/Canvas` as Page/Print-layout research ancestry only.


## [DEFERRED] Define campaign creation inside an existing World
**Kind:** DESIGN / CROSS-BOUNDARY AUTHORITY  
**Owner:** Buddy campaign lifecycle + DungeonMind campaign scope  
**Captured:** 2026-08-11  
**Last verified:** 2026-09-08 @ `df15db4c695240ce08b5812d43ca398cd70ff6ac`  
**Trigger:** creating a genuinely new campaign becomes an immediate product/dogfood need.

**Problem:** The old READY item predates the completed DungeonMind cutover and assumed a world-container model that no longer describes authority correctly. One World now has one authoritative World Supergraph; campaign is assertion/evidence/chronology/visibility scope, while Buddy owns application/source/work state.

**Next slice on trigger:** Re-decompose campaign creation into its actual authority boundaries before writing a contract: Buddy campaign/application identity and source/work bindings vs DungeonMind campaign-scoped assertion semantics. Freeze only the independently useful first contract; do not fork or duplicate World identity implicitly.

**Refs:** `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Design/CONTRACT-world-container-v1.md` as historical design evidence; `Docs/Roadmaps/ROADMAP-con-ready.md`.

## [DEFERRED] Verbatim `source_phrase` grounding vs renderer snippets
**Kind:** EVALUATION / EVIDENCE CONTRACT  
**Owner:** Temporal/grounding evaluation  
**Captured:** 2026-08-01  
**Last verified:** 2026-09-08 @ `df15db4c695240ce08b5812d43ca398cd70ff6ac`; no current demo-readiness trigger observed  
**Trigger:** phrase-level extraction again requires this renderer path.

**Problem:** Development phrase-grounding fails deterministically when the required verbatim phrase is not present in the renderer-produced cited snippet.

**Next slice on trigger:** Prove one known-good smoke case grounds through both lanes before touching cohorts/prompts; keep sealed cohorts/gold unchanged.

**Refs:** `Docs/Design/DECISION-tl01-temporal-prompt-calibration-close.md`; `Docs/Reports/REPORT-tl01g-grounding-path-recovery.md`; PRs #468, #486, #500.

## [DEFERRED] Ecology/resource extraction pass
**Kind:** DESIGN / EXPERIMENT  
**Owner:** Graph extraction  
**Captured:** 2026-07-18  
**Last verified:** 2026-09-08 @ `df15db4c695240ce08b5812d43ca398cd70ff6ac`; no current demo-readiness trigger observed  
**Trigger:** current extraction dogfood shows species/flora/fauna/resource duplication materially harms preparation or retrieval.

**Problem:** Ecology/resource concepts repeatedly blur actor/object boundaries, but current product priorities do not justify inventing a new extraction pass without fresh dogfood pressure.

**Next slice on trigger:** Reproduce the defect on the current DungeonMind/Buddy extraction boundary, then design a bounded `ecology_resource_pass` and compare it against the current path before implementation.

**Refs:** `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-MANUAL-REVIEW.md`; `Docs/Plans/HANDOFF-prime-design-graph-memory-extraction-taxonomy.md`.

---

# Delegated workstreams — pointers only, no root status

The rows below preserve discoverability for capabilities removed from root without creating a second status owner.

| Capability / residual | Status owner | Root disposition / owner health |
|---|---|---|
| C1/C2 historical source coverage, durable provenance, rich recap/object/Threat experience, session navigation, shell residuals, real-material save/reopen, Agent-on-Ingest/cross-surface Agent, observability, off-laptop durable authorities | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` + `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Delegated. This is the current execution program; root backlog must not shadow its STOP-driven sequencing. |
| Build ready-state Reload / Discard-local actions | Demo-Ready Stage 6 / current Markdown Canvas ownership | Removed from root READY on 2026-09-08. It belongs with the real-material edit/save/reopen dogfood rather than an independent pre-Stage-6 dispatch. |
| Hermes optimistic transcript + multiline composer | Demo-Ready Stage 7 Agent work | Removed from root READY on 2026-09-08. Useful UX remains, but Agent-on-Ingest/context/observability sequencing owns when it should ship. |
| Hermes prompt/configuration quality + revision-aware cross-turn evidence deduplication | Demo-Ready Stage 7 / Agent observability | Removed from root IDEA on 2026-09-08. Reproduce against the assembled cross-surface Agent before creating an independent slice. |
| First-class statblock and roll-table display across surfaces | Demo-Ready Stage 4 + `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md` | Removed from root IDEA. Rich-object/Threat dogfood and the Threat owner decide the split; do not build a second cross-surface status lane here. |
| Durable Combat board / easy roster loading | CON-READY / Play + Combat authorities | Removed from root IDEA. Combat remains a real product need, but it is later than current Demo-Ready continuity and must be re-anchored when Play/Combat resumes. |
| Native Play board usability / Beat-first current moment | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` + current Play design authorities | Removed from root IDEA. BF3B and further Play work remain parked behind the current continuity program. |
| Hermes copyable authoring artifact, grounded-answer→Threat authoring, graph chips, Revise UX, mechanic-editor expansion, liveness UX, durable telemetry, statblock presentation/media evolution | `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md` / Threat roadmap | Delegated; that owner remains the status authority for these domain capabilities. |
| Historical Campaign-Supergraph residual labels such as PR380E/PR380F and exact-run review sequencing | current Demo-Ready/CUTOVER-era authorities, not the old tracker by default | Historical design ancestry only. Do not dispatch directly from stale PR380 labels without re-anchoring against the post-cutover DungeonMind boundary. |
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

## Hygiene history

- 2026-08-16 pass 1: 74 active headings → 29; see `Docs/Reports/BACKLOG-HYGIENE-2026-08-16.md`.
- 2026-08-16 pass 2: converted root backlog from “worth doing” list to strict dispatch inventory; tracker-owned work delegated without duplicate status and READY reduced to seven bounded slices.
- 2026-09-08 pass 3: re-anchored after PR #694 and the Stage 2A/2B durability work. Status-bearing headings reduced **17 → 7** (`2 READY`, `2 BLOCKED`, `3 DEFERRED`). Demo-Ready/CON-READY/Threat-owned work moved to pointer-only delegation; pre-cutover graph-authority assumptions were corrected; broad durability umbrellas were retired after real APP-STATE/World recovery proof; browser-local statblock persistence was retired as a product durability target.


## [IDEA] Route authored facts to their subject's document and Graph provenance — captured 2026-10-16
**Context:** Operator writing Edge in Build while discussing facts about Mirathorn with the Agent.
**Insight:** The open document is the current workspace; each new fact may belong to a different subject and source document. The operator wants facts to produce useful nodes and relationships with openable links to their actual source passages.
**Action:** Design a reviewable authoring proposal that names the destination document/passage and proposed nodes/relationships together. A Mirathorn addition discussed while Edge is open should target the appropriate Mirathorn document, preserve the originating conversation reference, and ask when the subject/destination is ambiguous. Distinguish new authored lore from retrieval of already established facts. Commit source text before deriving admitted Graph knowledge; never silently treat conversation prose as canon or edit the wrong page.
**Surfaces when:** Build Agent authoring, cross-document edit proposals, selection annotations, and authored-source Graph ingestion.
**Refs:** Operator Build dogfood, Edge document `6e0e35c4-41d7-48a6-9f57-6adbca2a0c19`; `Docs/Plans/HANDOFF-AGENT-full-prompt-inspection.md` (predecessor only).
