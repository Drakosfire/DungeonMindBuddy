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

**Current verification anchor:** `main` at `df15db4c695240ce08b5812d43ca398cd70ff6ac` (PR #694 merged), observed 2026-09-08 after successful Stage 5A human dogfood.

### Current sequencing posture

`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` owns the current C1/C2 demo-readiness sequence. Root backlog does **not** independently sequence historical source coverage, graph-object richness/provenance, recap presentation, navigation-shell residuals, Agent-on-Ingest/cross-surface Agent work, real-material save/reopen, or the later move of durable authorities off the laptop.

PR #694 removed full-document loads among the primary React surfaces and the post-merge human dogfood was a material product win. Persistent-AppChrome Stage 5B work is therefore conditional on a concrete residual remount/restart failure rather than an automatic successor. Current steward direction is substrate-first: preserve/recover the useful prototype-era context through durable DB-backed authority and controlled DungeonMind projection before doing the deliberate fun/readable styling pass.

---

# READY

## [READY] Publish Statblock Workbench as a Build Tool capability
**Kind:** CODE  
**Owner:** Build / Surface Interaction  
**Captured:** 2026-08-11  
**Last verified:** 2026-09-08 @ `df15db4c695240ce08b5812d43ca398cd70ff6ac`  
**Depends on:** shared Tool Host merged in PR #501; native Build Surface Interaction publication merged in PR #506; shared Threat projection/lens merged in PR #512. The Threat/Statblock roadmap still explicitly leaves this capability in root backlog until sequenced elsewhere.

**Problem:** Build can natively publish/search/inspect World Graph capabilities through shared hosts, but Statblock Workbench authoring is not yet an ordinary Build Tool capability.

**Slice:** Publish the existing Workbench launcher/inventory through the active Build Surface Interaction lease. Reuse the shared Tool Host and existing Workbench; do not create Build-local tool chrome or couple Threat viewing to Workbench ownership.

**Exit proof:** From an admitted Build document, the shared Tool Host exposes the Workbench capability, opens the existing Workbench, survives surface/document lease replacement correctly, and leaves Plan behavior and graph/document authority unchanged.

**Refs:** PRs #501, #506, #512; `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`; `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`; `apps/live-control-ui/src/surfaceInteraction/`.

## [READY] Define durable source archive / restore lifecycle
**Kind:** DESIGN  
**Owner:** APP-STATE / source lifecycle  
**Captured:** 2026-08-11  
**Last verified:** 2026-09-08 @ `df15db4c695240ce08b5812d43ca398cd70ff6ac`  
**Depends on:** Stage 2A durable APP-STATE authority on `54331`; immutable `source.artifact` / `source.revision` identity and exact source-Markdown service; local editor discard remains a separate non-destructive concept.

**Problem:** Durable source removal is a server-owned lifecycle operation, but the now-real APP-STATE source authority has no explicit archive/restore contract. A local “discard my edits” action must never be confused with changing durable source visibility or identity.

**Slice:** Define archive, visibility, restore, collision, audit, confirmation, and exact-identity semantics for one APP-STATE durable source. Do not implement local-draft discard in this slice. Do not hard-delete by default without a named contract reason.

**Exit proof:** One checked-in contract/decision + bounded implementation handoff makes archive vs local discard unambiguous, defines recoverability and exact artifact/revision identity after restore, and identifies the authorized APP-STATE server write boundary.

**Refs:** `Docs/Reports/REPORT-application-state-durability-drill.md`; `Docs/Reports/REPORT-stage-2b-c1-c2-repopulation.md`; `src/application_state/source/service.py`; `Docs/Reports/DOGFOOD-POLISH-CLOSEOUT-2026-08-11.md`.

---

# BLOCKED

## [BLOCKED] Generation liveness via lease heartbeat
**Kind:** CROSS-REPO CONTRACT + CODE  
**Owner:** DungeonMind generation lifecycle → Buddy consumer  
**Captured:** 2026-07-30  
**Last verified:** 2026-09-08 @ `df15db4c695240ce08b5812d43ca398cd70ff6ac`  
**Depends on:** a first-class pollable DungeonMind generation-operation / lease-heartbeat contract that Buddy can consume without guessing provider latency.

**Problem:** A real generation can outlive Buddy's fixed client timeout, producing a false product failure while DungeonMind continues successfully.

**Slice when unblocked:** First prove/land the provider liveness contract; then change Buddy generation UX to treat a fresh lease as heartbeat and fail on stalled/dead lease plus a safety ceiling. Revise-generation liveness remains a successor unless the same contract covers it naturally.

**Unblock proof:** Pinned DungeonMind API/contract exposes exact operation identity plus truthful live/stalled/terminal status or lease freshness, with restart/timeout semantics documented.

**Refs:** Buddy DungeonMind statblock client/config; DungeonMind generation-operation/lease domain.

## [BLOCKED] Define authored-worldbuilding elevation through DungeonMind authority
**Kind:** CROSS-REPO AUTHORITY CONTRACT / DESIGN  
**Owner:** DungeonMind World write authority → Buddy Build/Graph Review consumer  
**Captured:** 2026-07-24  
**Last verified:** 2026-09-08 @ `df15db4c695240ce08b5812d43ca398cd70ff6ac`  
**Depends on:** a controlled DungeonMind write/elevation contract for authored worldbuilding. Buddy no longer owns World Graph storage, contribution replay, or graph-truth transitions after CUTOVER.

**Problem:** Reviewed authored lore still needs an explicit path to become publishable World truth when the GM chooses, but the pre-cutover READY item incorrectly assumed Buddy could choose and own that authority transition itself.

**Slice when unblocked:** Consume one DungeonMind-owned elevation contract from Buddy. Preserve source identity/evidence, require an explicit actor/confirmation boundary, define replay/idempotency and failure semantics, and keep worldbuilding draft distinct from campaign played chronology. Never silently relabel `worldbuilding_draft` as played canon.

**Unblock proof:** DungeonMind exposes a reviewed, durable contract that names the write authority, identity/evidence semantics, replay behavior, admissibility, and exact resulting World revision semantics without requiring Buddy to reconstruct or mutate graph storage directly.

**Refs:** `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; current DungeonMind CUTOVER boundary; historical `src/graph_memory/candidate_semantic_promote_matrix.py` / `worldbuilding_plumbing_profile.py` are design ancestry, not current write authority.

---

# DEFERRED

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

# IDEA

## [IDEA] Node digest from multi-session + worldbuilding context
**Kind:** DOGFOOD / PRODUCT  
**Owner:** Demo-Ready Stage 4 object-card richness; timeline when that work exists  
**Captured:** 2026-09-08  
**Last verified:** 2026-09-08 C2S25 ingest dogfood after syntactic relationship copy

Do not dispatch from this IDEA. The demo-ready roadmap owns sequencing.

Syntactic hover/card copy (`Orik is associated with Brin`, no Related-objects wrap) is an improvement and still not a useful object. Orik is a thin session-local NPC: one relationship, one recap paragraph. The next richness is not more graph chrome. It is a digest of the node when there is enough context to combine.

Good examples are campaign-lived PCs/NPCs such as Lysandra or Pippa: multiple sessions plus worldbuilding-related objects that can be read together. Imagine a loop that decides whether the node has enough material, then composes one GM-facing digest instead of listing edges. That composition touches timeline work, which is not ready; do not dispatch a digest slice against Orik. Keep the imagined shape: session chronology + worldbuilding objects → one readable node digest, only when the node is dense enough.

**Surfaces when:** Stage 4 presentation; node card digest; Lysandra; Pippa; thin vs dense graph objects; Orik is not the example; timeline; object richness; why the card still feels empty after provenance

**Refs:** C2S25 ingest dogfood; `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx`; `apps/live-control-ui/src/graphReference/nodeGlancePresentation.ts`

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

## Hygiene history

- 2026-08-16 pass 1: 74 active headings → 29; see `Docs/Reports/BACKLOG-HYGIENE-2026-08-16.md`.
- 2026-08-16 pass 2: converted root backlog from “worth doing” list to strict dispatch inventory; tracker-owned work delegated without duplicate status and READY reduced to seven bounded slices.
- 2026-09-08 pass 3: re-anchored after PR #694 and the Stage 2A/2B durability work. Status-bearing headings reduced **17 → 7** (`2 READY`, `2 BLOCKED`, `3 DEFERRED`). Demo-Ready/CON-READY/Threat-owned work moved to pointer-only delegation; pre-cutover graph-authority assumptions were corrected; broad durability umbrellas were retired after real APP-STATE/World recovery proof; browser-local statblock persistence was retired as a product durability target.