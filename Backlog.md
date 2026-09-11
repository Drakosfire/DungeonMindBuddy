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

## Captured UI/product goals — non-status design input

These goals preserve the 2026-09-09 fresh-eyes Buddy UI audit and the Of Conks / Hempholm prototype comparison as **design input only**. They do not own sequence and are not dispatchable from root. The Demo-Ready roadmap, CON-READY/Play authorities, Threat roadmap, and future dogfood STOP decisions own decomposition and ordering.

**Interaction language (2026-09-10):** shell regions, peek/glance grammar, steal/ignore from Mobbin + Of Conks, and the recommended first peek-not-overlay slice live in [`Docs/Design/ui-language/DESIGN-interaction-layer-language.md`](Docs/Design/ui-language/DESIGN-interaction-layer-language.md). That folder is the living UI language; `ARCHITECTURE-surface-interaction-layer.md` remains chrome **ownership**.

The forcing product question behind all of them is:

> Can a GM move through **prepare → run → capture/review → update World → resume** with less friction than a well-organized Markdown workspace, while DungeonMind/APP-STATE authority remains trustworthy but mostly invisible?

### Goal 1 — Orient Buddy around the GM journey, not subsystem taxonomy

**Outcome:** The application explains where the GM is in the campaign and what they can do next without requiring them to understand graph, run, revision, publication, or ingestion architecture.

**User stories:**

- As a GM opening DungeonBuddy, I can immediately see the current campaign/session state and resume the most likely next task.
- As a GM moving from preparation into play and then post-session review, I can follow the workflow without translating between architectural surface names and my table work.
- As a GM who wants technical detail, I can still inspect exact IDs, revisions, publication state, and evidence through an Advanced/operator path rather than losing that truth.
- As a returning GM, the home/index experience tells me what is prepared, what was last played, what needs review, and what can be resumed.

**Scope guardrail:** This is information architecture, navigation, terminology, and workflow framing. It does not change DungeonMind authority, APP-STATE ownership, or invent automatic campaign-state transitions.

### Goal 2 — Make the shared shell coherent, responsive, and context-preserving

**Outcome:** Plan, Play, Ingest, and Build feel like modes of one application rather than independently composed workbenches competing for fixed screen real estate.

**User stories:**

- As a GM on desktop or a narrow viewport, I can use the primary work area without drawers, rails, scrims, and the Agent bar overlapping or squeezing it into an unusable strip.
- As a GM opening a tool or object, I can understand what is primary content and what is temporary chrome, and dismiss secondary UI predictably.
- As a GM switching surfaces, I preserve the campaign/session/document context that should survive the switch and do not inherit stale controls from the prior surface.
- As a GM, I do not lose persistent screen space to an unavailable global feature.

**Scope guardrail:** Prefer one responsive shared drawer/pane composition and explicit mobile behavior. Do not add another fixed rail to solve an existing fixed-rail problem. Persistent AppChrome remains conditional on an observed remount failure rather than being assumed necessary.

### Goal 3 — Make native Play a table instrument, not a debugger cockpit

**Outcome:** Keep native Play's durable state model and cockpit composition, but make the current moment scan and behave like a GM handout at the table.

**User stories:**

- As a GM running a session, the current Scene/Beat gets most of the useful viewport while navigation and presence remain cheap.
- As a GM scanning the current moment, I can distinguish At the table, read-aloud, GM notes, rules, warnings, and wait/succeed/fail material without reading one undifferentiated body blob.
- As a GM making or recording a Decision, I use native durable option identity/persistence, and after selection the relevant Scene choices visibly become more or less prominent rather than relevance existing only as text below the Decision.
- As a GM, I can inspect a Scene without accidentally making it current, and I can deliberately Make Current when I am ready.
- As a GM, At a Glance shows actual nearby/openable people, places, threats, or tools instead of spending a rail on a count such as “Scenes N”.
- As a GM, current-moment material reads as a paper instrument inside dark product chrome: dark AppChrome/rails around a warm parchment Scene/Beat/object/mechanics surface.

**Scope guardrail:** Preserve native Decision CAS/persistence, Inspect vs Make Current, exact object identity, collapsible rails, and Scene-centered current-moment semantics. Do **not** merge or revive `ofConks*` adventure code, prep-HTML hosting, branch enums, hardcoded media maps, or packet-specific product surfaces.

### Goal 4 — Present World objects for table use first and inspection second

**Outcome:** A complete surface-neutral World object remains exact underneath, while the default Play/object presentation leads with what helps the GM use it now.

**User stories:**

- As a GM clicking Karsemine, Nar Granitetooth, or another World object, I first see a readable sheet with type, title, an At-the-table summary, relevant hooks/rules/source material, and connected objects as openable chips.
- As a GM hovering an object, I get one useful glance line rather than taxonomy, graph adjacency, and provenance diagnostics.
- As a GM following a connected object, I click a chip and remain in the table flow rather than entering a graph-browser row/list experience.
- As a GM who needs provenance, I can expand Advanced to inspect node ID, World revision, evidence counts/anchors, raw relationship detail, and other diagnostic identity.
- As a GM opening a Threat, the same parchment hierarchy can expose exact mechanics and a clear Add to Combat action.

**Scope guardrail:** Presentation must consume the complete admitted object rather than reinterpreting or truncating graph truth. Current-state/timeline reduction, media asset contracts, and map-pin resolution are later capabilities unless separately dispatched. IDs move under Advanced; they are not removed.

### Goal 5 — Turn Ingest into a GM memory-review workflow

**Outcome:** Normal Ingest usage answers “what did DungeonBuddy learn from this session, and what needs my decision?” while exact pipeline state remains available for diagnosis.

**User stories:**

- As a GM reviewing Session 25, I can see a concise summary such as proposed updates, accepted-looking updates, decisions needed, and unresolved identities before opening technical details.
- As a GM reviewing proposed memory, I can approve, reject, or resolve the material that needs judgment and understand what publication will change.
- As a GM, publishing approved changes is an explicit action; merely inspecting historical source material never mutates World truth.
- As an operator debugging a problem, I can still inspect exact run identity, lifecycle state, proposal/receipt bindings, and validation diagnostics under Advanced.

**Scope guardrail:** This is a presentation/workflow reframe over the governed write path. Do not weaken exact-run binding, explicit confirmation, stale-fail-closed behavior, or DungeonMind write authority to make the UI simpler.

### Goal 6 — Give Build an obvious authoring job

**Outcome:** Build communicates what the GM is creating, why they are creating it, and how that authored material relates to the campaign without presenting a mostly empty generic source canvas.

**User stories:**

- As a GM entering Build, I understand that I am authoring reusable world/campaign source material and can choose a meaningful starting intent instead of confronting an unexplained “New source”.
- As a GM creating an NPC, location, faction, encounter idea, or other worldbuilding source, I can work in a calm document-first canvas and use World references without needing to understand graph storage.
- As a GM, I can save, leave, reopen, and continue the same durable authored material.
- As a GM, I can distinguish “I wrote this source” from “this is now published World truth”; authoring does not silently elevate canon.

**Scope guardrail:** Exact creation templates/categories should be proved by real authoring demand rather than pre-building a taxonomy of forms. World elevation remains a separate governed DungeonMind authority capability.

### Goal 7 — Integrate Combat into Play instead of maintaining a parallel product model

**Outcome:** Combat remains a recognizable tabletop tool but becomes an ordinary Play mode with durable application state and contextual entry/exit.

**User stories:**

- As a GM looking at a relevant Threat or Beat, I can add/open combat through a real table-facing control without rebuilding the creature or roster manually.
- As a GM entering Combat, I can load the relevant roster quickly, operate initiative/HP/turn state, and return to the current Scene without losing where I was.
- As a GM who closes or restarts the application, I can trust the documented durability semantics of active combat rather than discovering that this one major workflow only lived in browser-local state.
- As a GM in Combat, I see combat-relevant tools; unrelated ingestion/operator controls do not appear merely because they share old toolbox infrastructure.

**Scope guardrail:** Combat is a Play mode/lens, not a peer graph or new authority system. Durable Combat state and roster-loading are later CON-READY/Play capabilities and must be re-anchored before dispatch.

### Goal 8 — Make the Agent contextual where it exists

**Outcome:** The Agent feels like an interaction capability of the current work rather than a permanently visible global promise that often says to open another surface.

**User stories:**

- As a GM asking about the object, prose selection, Scene, or document I am already looking at, the Agent receives that current context without requiring me to paste or restate it.
- As a GM on a surface where Agent interaction is not yet useful, I do not lose persistent space to a disabled bar advertising unavailable functionality.
- As a GM moving between supported surfaces, I can tell what context the Agent currently has and avoid accidentally asking against stale campaign/session/object state.
- As an advanced user debugging an answer, I can inspect model, token, cost, timing, retrieval, graph/source context, and tool-step traces without making that telemetry the default conversation UI.

**Scope guardrail:** Agent context consumes the same selected World object and surface/document context as the product. It must not invent a parallel graph interpretation or use chat history as campaign truth.

### Supporting UI engineering constraint — make redesign cheaper than preservation

This is not a GM-facing capability and should not be dispatched as one giant refactor. It is a constraint on slices implementing the goals above:

- stop growing multi-thousand-line production components and giant route-specific stylesheets when a touched seam can be extracted cleanly;
- converge on reusable layout, typography, spacing, parchment, and dark-chrome tokens instead of adding one-off paint;
- eliminate overlapping fixed-position composition rather than compensating with more z-index/responsive exceptions (see `Docs/Design/ui-language/DESIGN-interaction-layer-language.md`);
- keep one trustworthy fast frontend verification path so visual/product work does not rely only on narrow handoff-specific tests;
- require each cleanup to be justified by a product slice or a separately bounded maintainability defect, not by a broad rewrite program.

### Of Conks design-evidence locator

Read these as visual/interaction evidence only; **do not merge the dogfood branches wholesale**.

| Evidence | Locator |
|---|---|
| Table-ready prototype / PR #578 | `dogfood/of-conks-hempholm-table-ready` @ `88e4d65e7ed69afe262008749194e2b948ce4c43` |
| Prototype paint | `apps/live-control-ui/src/playSurface/beats/beats.css`; `graphReference/playObjectSheetProjection.css`; `PlayObjectSheetProjection.tsx` on that branch |
| End-to-end follow-on | `dogfood/of-conks-end-to-end` @ `b40d893f` — UI-hardening dogfood, **not** the Hempholm parchment prototype |
| Packet visual hierarchy | Play Object Sheet CSS/TSX on the table-ready tip; there is no `of-conks-packet.css` on `88e4d65e` |
| Native Play composition | `apps/live-control-ui/src/playSurface/playSurface.css`; `PlayGraphObjectSheet.tsx`; current Play cockpit/design authorities on `main` |
| Parchment survivor on main | `apps/live-control-ui/src/statblocks/projection/threatSheetProjection.css` and Threat glance/sheet presentation |

Design synthesis: **keep native state/persistence/composition; steal prototype table hierarchy and visual grammar.** Navigation/presence should be cheap; the current card should be expensive. Dark room chrome and warm paper instruments are complementary parts of one product, not competing themes.

## Hygiene history

- 2026-08-16 pass 1: 74 active headings → 29; see `Docs/Reports/BACKLOG-HYGIENE-2026-08-16.md`.
- 2026-08-16 pass 2: converted root backlog from “worth doing” list to strict dispatch inventory; tracker-owned work delegated without duplicate status and READY reduced to seven bounded slices.
- 2026-09-08 pass 3: re-anchored after PR #694 and the Stage 2A/2B durability work. Status-bearing headings reduced **17 → 7** (`2 READY`, `2 BLOCKED`, `3 DEFERRED`). Demo-Ready/CON-READY/Threat-owned work moved to pointer-only delegation; pre-cutover graph-authority assumptions were corrected; broad durability umbrellas were retired after real APP-STATE/World recovery proof; browser-local statblock persistence was retired as a product durability target.
