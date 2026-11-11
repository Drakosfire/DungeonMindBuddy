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
**Last verified:** 2026-10-24 @ `c74b5082ead867cd28fb302935dc05965dc1f4c0`
**Context:** Edge authoring dogfood: the author wants to move and resize artwork on a snapping grid, then compose images, editable text, tables and callouts intentionally on the page.

**Direction:** Keep Tiptap for writing; define shared row/column layout containers, stable section identities and durable layout representation. Preserve reading order for retrieval, citations and Markdown export. Distinguish this page-layout work from the deferred infinite spatial workspace below.

**First slice to design:** Move and resize one existing image on a visible snapping grid. Decide persistence ownership and representation before implementation; image centering is an immediate separate convenience, not completion of the grid constructor.

**Exit proof:** Ordinary controls place/resize an image; Save, reload and reopen preserve placement, undo/recovery preserve authorship, and narrow screens stack content predictably. Later slices may add adjacent editable text, tables/callouts and agent suggestion placement using stable section identities. Freeform overlap, pan/zoom and connectors require separate selection.

**Surfaces when:** Planning Build authoring, media placement, shared page layout or proposal insertion. Product sequencing remains owned by `Docs/Roadmaps/ROADMAP-demo.md`; high priority does not activate implementation or resume the paused broad goal.

**Refs:** Edge source `bba72416-9dfe-49bb-add0-21a346e9a421`; `apps/live-control-ui/src/tiptap/extensions/MediaImageNode.tsx`; `apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts`; conversation `01a0ef89-ca57-7b82-9c9c-215b02d0fc3b`.


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

# IDEA

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

**Next slice on trigger:** Pin one ordinary request and its admitted evidence. Compare controller decisions through the same existing native actions and benchmark assessment. Measure support, coverage, latency and calls. Determine whether successful traces warrant further controller research.

**Refs:** `src/application_state/agent_conversation/native_retrieval.py`; `apps/live_control_server/services/build_jev_driver.py`; `apps/live_control_server/services/plan_jev_driver.py`; `evals/buddy_benchmark/`; [original research capture](Docs/Backlog/BACKLOG-graph-exploration-system-one-controller-lab.md) as historical design input.


---

# DEFERRED

## [DEFERRED] Composable spatial workspace and selectable themes
**Owner:** Buddy presentation
**Captured:** 2026-09-26
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** The operator selects spatial composition or selectable themes for implementation.

**Current boundary:** Shared presentation components and graph canvas exist. Current source has no saved multi-object workspace arrangements or selectable theme-pack contract. The shared grid page constructor above owns the separate request for snapping page content into rows and columns.

**Next slice on trigger:** Select either saved spatial arrangements or selectable themes and bound it independently. For spatial arrangements, investigate existing canvas/projection components and define ownership of positions, sizes and camera state. For themes, investigate existing semantic tokens and define one reversible theme selection. These are separate capabilities.

**Refs:** [presentation substrate plan](Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md); `apps/live-control-ui/src/localWorld/worldGraphCanvas/`; shared grid page constructor entry above.

## [DEFERRED] Create a campaign inside an existing World
**Owner:** Buddy campaign UX + DungeonMind campaign membership
**Captured:** 2026-08-11
**Last verified:** 2026-11-10 @ Buddy `8a9ad7902`, DungeonMind `430c1a6d`
**Trigger:** An operator needs to start a new campaign in an existing World through ordinary controls.

**Current boundary:** DungeonMind's campaign ingest-context route requires an existing campaign membership. Buddy's #1860 restored two retained memberships via an offline repair. Neither provides a user-facing creation operation.

**Next slice on trigger:** Define a DungeonMind-owned membership creation operation and the minimal Buddy flow that uses it. Prove the new campaign can be selected and admit its own sources in the existing World.

**Refs:** [Campaign membership repair](Docs/Plans/HANDOFF-BUILD-elderwyld-campaign-membership.md); `src/dungeonmind/service/api.py` in DungeonMind.


---

# Delegated workstreams — pointers only, no root status

The rows below preserve discoverability for capabilities removed from root without creating a second status owner.

| Capability / residual | Status owner | Root disposition / owner health |
|---|---|---|
| Remaining C1/C2 source coverage and the authoring, preparation and Play journey | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) | The [DEMO steward handoff](Docs/Plans/STEWARDS-HANDOFF-demo.md) describes the mandate. The [old Demo-Ready ladder](Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md) and [CON-READY anchor](Docs/Plans/STEWARDS-ANCHOR-con-ready.md) are historical evidence. |
| Build ready-state Reload / Discard-local actions | Demo-Ready Stage 6 / current Markdown Canvas ownership | Removed from root READY on 2026-09-08. It belongs with the real-material edit/save/reopen dogfood rather than an independent pre-Stage-6 dispatch. |
| Hermes optimistic transcript + multiline composer | Demo-Ready Stage 7 Agent work | Removed from root READY on 2026-09-08. Useful UX remains, but Agent-on-Ingest/context/observability sequencing owns when it should ship. |
| Hermes prompt/configuration quality + revision-aware cross-turn evidence deduplication | Demo-Ready Stage 7 / Agent observability | Removed from root IDEA on 2026-09-08. Reproduce against the assembled cross-surface Agent before creating an independent slice. |
| First-class statblock and roll-table display across surfaces | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) and owning Threat/Play contracts | Assess remaining cross-surface behavior there; the Build Workbench launcher is already delivered. |
| Durable Combat board / easy roster loading | CON-READY / Play + Combat authorities | Removed from root IDEA. Combat remains a real product need, but it is later than current Demo-Ready continuity and must be re-anchored when Play/Combat resumes. |
| Native Play board usability / Beat-first current moment | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) and owning Play design | Re-anchor with DEMO when Play work resumes. |
| Rich Threat authoring, statblock presentation/media, and related conversation behavior | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) and current owning handoffs | The [Threat roadmap](Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md) retains historical design and acceptance wording. |
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

- 2026-11-10: reverified the next four entries. Retained the distinct residuals, removed already-shipped portions, and replaced the proposed controller environment with a comparison through existing native retrieval and evaluation.

- 2026-11-10: audited the four oldest active entries against Buddy main `8a9ad7902` and DungeonMind main `430c1a6d`. Archived two retired proposals and reverified two deferred lifecycle gaps.

- 2026-11-10: checked delivery through Buddy main `b0585f6d9`; archived the Build Statblock Workbench launcher, recorded completed image authoring slices, and corrected superseded roadmap pointers.

- 2026-08-16 pass 1: 74 active headings → 29; see `Docs/Reports/BACKLOG-HYGIENE-2026-08-16.md`.
- 2026-08-16 pass 2: converted root backlog from “worth doing” list to strict dispatch inventory; tracker-owned work delegated without duplicate status and READY reduced to seven bounded slices.
- 2026-09-08 pass 3: re-anchored after PR #694 and the Stage 2A/2B durability work. Status-bearing headings reduced **17 → 7** (`2 READY`, `2 BLOCKED`, `3 DEFERRED`). Demo-Ready/CON-READY/Threat-owned work moved to pointer-only delegation; pre-cutover graph-authority assumptions were corrected; broad durability umbrellas were retired after real APP-STATE/World recovery proof; browser-local statblock persistence was retired as a product durability target.


## [DEFERRED] Propose edits to an existing related page from the current workspace
**Owner:** Build authoring
**Captured:** 2026-10-16
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** The operator asks to revise an existing related page while retaining the current workspace.

**Current boundary:** Related saved-page context, connected-page creation and saved-source relationship reviews have shipped. Build text proposals still capture one page as their mutation target. A request for a different page returns a destination mismatch or requires handoff. The broad original ticket's connected-page and relationship portions are already covered.

**Next slice on trigger:** Capture an explicit existing destination document and passage, show an editable proposal through the shared review host, and preserve the originating workspace. After saving, reuse the existing source and reviewed publication flow for any proposed Graph changes.

**Refs:** `apps/live_control_server/services/build_document_proposal.py`; `src/application_state/agent_conversation/collaboration.py`; `src/application_state/agent_conversation/relationship_review.py`; #2127, #2129, #2273.
