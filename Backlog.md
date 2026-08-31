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

**Current verification anchor:** `main` at `62f7f9e856327247b8677b4c951801e4c58a826c` (merged PR #622), observed 2026-08-20.

---

# READY

## [READY] Define campaign creation inside an existing world
**Kind:** DESIGN  
**Owner:** Build / source lifecycle  
**Captured:** 2026-08-11  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`  
**Depends on:** CR01B / PR #564 new-world creation; managed world-container registry; `CONTRACT-world-container-v1`.

**Problem:** The former combined import item covered both creating a world and creating a campaign. New-world creation shipped; explicit creation of a campaign inside an admitted existing world remains undefined.

**Slice:** Produce the campaign-creation authority contract and implementation handoff only. Freeze campaign identity, world placement, persistence/reopen semantics, duplicate/collision behavior, and the rule that campaign creation never forks or duplicates World Graph identity implicitly.

**Exit proof:** One checked-in decision/contract + bounded implementation handoff resolves the success/failure matrix and names the exact implementation successor. No runtime campaign creation is claimed by this design slice.

**Refs:** `Docs/Plans/HANDOFF-BUILD-create-new-world-from-build.md`; `Docs/Design/CONTRACT-world-container-v1.md`; `Docs/Roadmaps/ROADMAP-con-ready.md`.

## [READY] Publish Statblock Workbench as a Build Tool capability
**Kind:** CODE  
**Owner:** Build / Surface Interaction  
**Captured:** 2026-08-11  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`  
**Depends on:** shared Tool Host merged in PR #501; native Build Surface Interaction publication merged in PR #506; shared Threat projection/lens merged in PR #512.

**Problem:** Build can natively publish/search/inspect World Graph capabilities through shared hosts, but Statblock Workbench authoring is not yet an ordinary Build Tool capability.

**Slice:** Publish the existing Workbench launcher/inventory through the active Build Surface Interaction lease. Reuse the shared Tool Host and existing Workbench; do not create Build-local tool chrome or couple Threat viewing to Workbench ownership.

**Exit proof:** From an admitted Build document, the shared Tool Host exposes the Workbench capability, opens the existing Workbench, survives surface/document lease replacement correctly, and leaves Plan behavior and graph/document authority unchanged.

**Refs:** PRs #501, #506, #512; `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`; `apps/live-control-ui/src/surfaceInteraction/`.

## [READY] Build ready-state Reload / Discard-local actions
**Kind:** CODE  
**Owner:** Build / Markdown Canvas  
**Captured:** 2026-08-11  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`  
**Depends on:** shared Edit Host and existing Canvas conflict/reload authority.

**Problem:** Ordinary ready-state recovery still lacks a clear operator action for abandoning the mutable local working copy without confusing that action with durable source deletion.

**Slice:** Add Reload / Discard-local through existing Canvas/Edit ownership. The action reloads the exact durable document authority, clears local dirty state, and never archives/deletes the durable source.

**Exit proof:** Dirty local edits can be discarded and reloaded through the shared Edit surface; exact durable source bytes/revision remain unchanged; no Build-specific duplicate Edit bar is introduced.

**Refs:** `Docs/Reports/DOGFOOD-POLISH-CLOSEOUT-2026-08-11.md`; `apps/live-control-ui/src/markdownCanvas/`; shared Edit Host implementation.

## [READY] Define durable source archive / restore lifecycle
**Kind:** DESIGN  
**Owner:** Build / source lifecycle  
**Captured:** 2026-08-11  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`  
**Depends on:** current durable source/document registry; local Discard semantics remain separate.

**Problem:** Durable source removal is a server-owned destructive lifecycle operation and has no explicit archive/restore authority contract.

**Slice:** Define archive, visibility, restore, collision, audit, and confirmation semantics for one durable source. Do not implement local-draft discard in this slice and do not hard-delete by default without a named contract reason.

**Exit proof:** One checked-in contract/decision + implementation handoff makes archive vs local discard unambiguous, defines recoverability and exact identity after restore, and identifies the authorized server write boundary.

**Refs:** `Docs/Reports/DOGFOOD-POLISH-CLOSEOUT-2026-08-11.md`; Build source services/document registry.

## [READY] Hermes composer — optimistic transcript + multiline input
**Kind:** CODE  
**Owner:** Hermes / Agent Interaction UI  
**Captured:** 2026-07-30  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`  
**Depends on:** existing Hermes thread submission API; no backend lifecycle redesign required.

**Problem:** Submitted questions remain in the input until the response returns and the one-row composer is cramped for serious prep work.

**Slice:** Optimistically append the user turn, clear the composer immediately, show truthful pending/error/retry state, and use an auto-growing multiline input with explicit Enter/Shift+Enter behavior.

**Exit proof:** One submit creates exactly one visible user turn and one backend request, input clears immediately, multiline keyboard behavior is tested, failure is retryable without duplicate transcript turns, and thread identity remains unchanged.

**Refs:** `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` and current Agent Interaction composer owner.

## [READY] Define worldbuilding-draft elevation authority
**Kind:** DESIGN  
**Owner:** Build / Graph Review authority  
**Captured:** 2026-07-24  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`  
**Depends on:** existing `worldbuilding_draft` extraction semantics and played-canon promotion gate.

**Problem:** Reviewable authored lore is intentionally not played canon, but there is no explicit authority transition for a GM who wants to elevate reviewed worldbuilding into publishable World Graph truth.

**Slice:** Choose and freeze exactly one elevation model: e.g. explicit operator elevation, draft authority plane, or another bounded profile-specific transition. Do not implement the chosen model in the same slice.

**Exit proof:** A checked-in decision states source authority, actor/confirmation boundary, identity/evidence preservation, replay behavior, and what remains non-canon. It explicitly forbids silently relabeling `worldbuilding_draft` as played canon and names the implementation successor.

**Refs:** `src/graph_memory/candidate_semantic_promote_matrix.py`; `src/graph_memory/extraction/worldbuilding_plumbing_profile.py`; Campaign Supergraph acceptance debt.

## [READY] Browser-local statblock draft persistence with untrusted receipt restore
**Kind:** CODE  
**Owner:** Statblock Workbench  
**Captured:** 2026-07-24  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`  
**Depends on:** immutable accepted-mechanics persistence and authoritative server validation remain unchanged.

**Problem:** Workbench draft persistence was reverted because restoring a validation receipt from mutable browser storage would falsely preserve exact-definition trust.

**Slice:** Persist only mutable working-copy/editor state (including useful undo/view state). On restore, mark the draft unvalidated and require a fresh server validation before any receipt-dependent acceptance/save action.

**Exit proof:** Hard reload restores the working copy but never restores trusted validation authority; acceptance remains blocked until a fresh matching server receipt exists; corrupt/stale local data fails safely.

**Refs:** reverted `statblockEditorDraftStore.ts`; PR #404 review history; current Workbench editor/validation owners.

---

# BLOCKED

## [BLOCKED] Generation liveness via lease heartbeat
**Kind:** CROSS-REPO CONTRACT + CODE  
**Owner:** DungeonMind generation lifecycle → Buddy consumer  
**Captured:** 2026-07-30  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`  
**Depends on:** a first-class pollable DungeonMind generation-operation / lease-heartbeat contract that Buddy can consume without guessing provider latency.

**Problem:** A real generation can outlive Buddy's fixed client timeout, producing a false product failure while DungeonMind continues successfully.

**Slice when unblocked:** First prove/land the provider liveness contract; then change Buddy generation UX to treat a fresh lease as heartbeat and fail on stalled/dead lease plus a safety ceiling. Revise-generation liveness remains a successor unless the same contract covers it naturally.

**Unblock proof:** Pinned DungeonMind API/contract exposes exact operation identity plus truthful live/stalled/terminal status or lease freshness, with restart/timeout semantics documented.

**Refs:** Buddy DungeonMind statblock client/config; DungeonMind generation-operation/lease domain.

---

# DEFERRED

## [DEFERRED] Verbatim `source_phrase` grounding vs renderer snippets
**Kind:** EVALUATION / EVIDENCE CONTRACT  
**Owner:** Temporal/grounding evaluation  
**Captured:** 2026-08-01  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`  
**Trigger:** phrase-level extraction again requires this renderer path.

**Problem:** Development phrase-grounding fails deterministically when the required verbatim phrase is not present in the renderer-produced cited snippet.

**Next slice on trigger:** Prove one known-good smoke case grounds through both lanes before touching cohorts/prompts; keep sealed cohorts/gold unchanged.

**Refs:** `Docs/Design/DECISION-tl01-temporal-prompt-calibration-close.md`; `Docs/Reports/REPORT-tl01g-grounding-path-recovery.md`; PRs #468, #486, #500.

## [DEFERRED] Ecology/resource extraction pass
**Kind:** DESIGN / EXPERIMENT  
**Owner:** Graph extraction  
**Captured:** 2026-07-18  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`  
**Trigger:** current one-shot/worldbuilding dogfood shows species/flora/fauna/resource duplication materially harms preparation or retrieval.

**Problem:** Ecology/resource concepts repeatedly blur actor/object boundaries, but current product priorities do not justify inventing a new extraction pass without fresh dogfood pressure.

**Next slice on trigger:** Reproduce the defect on current extraction architecture, then design a bounded `ecology_resource_pass` and compare it against the current pipeline before implementation.

**Refs:** `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-MANUAL-REVIEW.md`; `Docs/Plans/HANDOFF-prime-design-graph-memory-extraction-taxonomy.md`.

---

# IDEA

## [IDEA] Teach the Play chooser the Runbook → Run relationship
**Kind:** PRODUCT / COPY  
**Owner:** Play surface  
**Captured:** 2026-08-29  
**Last verified:** 2026-08-29 @ BF3B handoff scope correction  
**Depends on:** not BF3B. Do not pull this into Decision interaction.

The Play chooser currently titles the page **Choose a Run** and then offers
**Create blank Runbook** as the first empty-state action, with neighboring
**Edit Runbook** / **Start exact Run**. A new operator can reasonably think
those are the same kind of object.

Frozen vocabulary:

```text
RUNBOOK = durable Playable document / session script (immutable WorkRevisions)
RUN     = runtime instance of play; pins one exact committed Runbook WorkRevision
```

Create blank Runbook is predecessor DF0 behavior: it creates the minimum legal
committed script. It does not create a Run, start play, mutate Runtime, or
write Plan prep. The missing product work is one explanatory sentence (and
possibly chooser terminology) that teaches that relationship before asking the
operator to create either object.

**Surfaces when:** Play chooser, "Choose a Run", Create blank Runbook, Edit
Runbook, Start exact Run, empty Play, Runbook-vs-Run confusion, onboarding copy.

**Refs:** `Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md` §0.3.

## [IDEA] Durable database persistence for GM work across worktrees
**Kind:** PRODUCT / ARCHITECTURE  
**Owner:** Buddy persistence (steward sequencing)  
**Captured:** 2026-08-19  
**Last verified:** 2026-08-20 @ post-C2S27 re-anchor, `main` `62f7f9e856327247b8677b4c951801e4c58a826c`  
**Depends on:** separate domain-first proof from the Run-continuity and
Combat-durability slices; this cross-domain item is not an atomic prerequisite
and must not block either domain slice.

C2 Session 27 table dogfood, operator rank 1. Plan export dropped playable
blocks and styling; workspace drafts are checkout-local, so jumping worktrees
lost authored work. The affected domains include Plan documents, Playable
blocks/styling, Combat board, Threat drafts, and Run/workspace registries, but
that list is too broad to define one implementation slice. First let the
domain owners prove their own durability invariants; only then extract a
bounded shared persistence seam if both domains demonstrate one.

**Surfaces when:** Plan export, worktree switch, Combat state save, persistence/database, "don't lose work".

**Refs:** `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`; `Docs/Plans/HANDOFF-PLAY-SURFACE-c2s27-reanchor-and-workspace-cleanup.md`.

## [IDEA] Finish Combat Tracker — durable board, easy roster loading
**Kind:** PRODUCT  
**Owner:** Combat / Play  
**Captured:** 2026-08-19  
**Last verified:** 2026-08-20 @ post-C2S27 re-anchor  
**Depends on:** disposition of the retained `agent/play-command-board-disk-saves`
worktree (mine/adopt/commit or discard its uncommitted Combat disk-save work);
then a bounded Lane B handoff. The P4 exact Threat→Combat design
(`Docs/Plans/HANDOFF-PLAY-SURFACE-add-to-combat.md`) is preserved but deferred until
this durable Combat re-anchor.

Operator rank 2. The HTML Combat Tracker was the surface actually used at
C2S27. Loading players, NPCs, and threats with sheets attached must be easy,
and live HP/initiative/notes must persist in a Combat-owned durable authority —
not only browser `localStorage` plus export JSON. Post-re-anchor Lane B is a
domain-first durable Combat slice, but it cannot dispatch until the retained
uncommitted Combat-save worktree is mined/adopted/committed or discarded.

**Surfaces when:** Combat add-from-pool, live HP tracking, browser reload, worktree switch.

**Refs:** `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`; `evals/c2_live_prep/mireward-prep/combat.html` (prototype evidence, PR #623 branch).

## [IDEA] First-class statblock and roll-table display across surfaces
**Kind:** PRODUCT  
**Owner:** Surface Interaction / Statblock Workbench  
**Captured:** 2026-08-19  
**Last verified:** 2026-08-20 @ post-C2S27 re-anchor  
**Depends on:** none for viewing; modification flows depend on existing Workbench/mechanics authority.

Operator rank 3. Load, view, and modify a statblock from any surface (Plan, Play, Combat, Workbench) without a dead path or HTML-only preview. Roll tables have the same gap. Statblock/roll-table opening remains a first-class table need.

**Surfaces when:** statblock click/preview, roll table, Threat sheet, Combat roster sheet.

**Refs:** `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`; `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`.

## [IDEA] Native Play board usability — Beat-first current-moment stage
**Kind:** PRODUCT / DESIGN  
**Owner:** Play surface  
**Captured:** 2026-08-19  
**Last verified:** 2026-08-20 @ post-C2S27 re-anchor  
**Depends on:** Lane A (active-Run continuity) and Lane B (durable Combat)
domain slices, plus the reviewed Beat/Scene/Decision + Plan→Playable design
task and its P1/P2 structure/serialization/manifest/current-position/
migration-rebase redesign. Do not treat the D4 table-stage chrome (PR #623,
closed unmerged) as the close of Play usability.

Operator rank 4. The native Play board was abandoned almost immediately at C2S27. Beat is the larger useful hierarchy over Scenes; Decisions carry consequences and reshape which Scenes remain possible/relevant. No new native Play table implementation starts until that model is reviewed.

**Surfaces when:** `/play` Table, current Beat, Scene navigation, decision/branch visibility.

**Refs:** `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`; `Docs/Design/DESIGN-play-surface-projection.md`.

## [IDEA] Move durable Buddy runtime state out of checkout-local `out/`
**Kind:** ARCHITECTURE SPIKE  
**Owner:** Buddy persistence  
**Captured:** 2026-07-24  
**Last verified:** 2026-08-20 @ C2 Session 27 dogfood (Plan export + worktree loss)

Worktree dogfood shows that checkout-local World Graph/run registries/Threat
drafts/candidate caches do not compose cleanly with parallel worktrees. C2S27
table dogfood made cross-domain durability the operator's rank-1 residual:
authored Plan blocks/styling and live Combat state do not follow the GM across
worktrees. This remains an architecture spike, not a dispatchable shared
database slice. After Lane A and Lane B each prove their domain invariant,
inventory the actual shared consumers and bind one bounded migration target
only if a common persistence seam is evidenced. Keep auditable source Markdown
separate from runtime-state storage.

## [IDEA] Hermes prompt/configuration quality pass
**Kind:** DOGFOOD / CONFIGURATION  
**Owner:** Hermes  
**Captured:** 2026-07-30  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`

Dogfood has shown occasional system-meta narration and uneven co-GM voice. Before promotion, define a small falsifiable quality set covering campaign-facing voice, uncertainty, no system-meta narration, and tool-selection quality, then inventory which prompt/config boundary actually owns each failure.

## [IDEA] Revision-aware evidence deduplication across Hermes turns
**Kind:** DESIGN / TELEMETRY  
**Owner:** Hermes evidence continuity  
**Captured:** 2026-07-16  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`

Stable object identity does not imply stable factual state. Before promotion, characterize whether repeated evidence is currently a measurable product/latency problem and define cross-turn identity around revision-aware evidence without making prior-turn context current authority.

---

# Delegated workstreams — pointers only, no root status

The rows below preserve discoverability for capabilities removed from root without creating a second status owner.

| Capability / residual | Status owner | Root disposition / owner health |
|---|---|---|
| Plan/Hermes continuity across document/surface switches | `Docs/Roadmaps/ROADMAP-cross-surface-statblock-demo.md` — DEMO-02 | Delegated. Re-verify the roadmap before dispatch because its status snapshot predates the August Playable/CUTOVER work. |
| Exact-run Graph Review presentation + inspectable evidence failures | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` — `exact-run-candidate-review-projection` | Delegated. Campaign tracker is the sole sequence owner; CUTOVER state-sync is currently being advanced separately in PR #598 and implementation PR #602. |
| Ingest primary-path simplification | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` — PR380E | Delegated. The tracker, not root backlog, owns whether it is BLOCKED/READY. |
| World-anchor insertion for world-fed known entities (E1b) | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` — PR380F extraction/identity hardening | Delegated as the concrete dogfood defect to preserve when PR380F is dispatched. |
| Hermes copyable authoring artifact | `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md` — `AUTHORING-ARTIFACT` | Delegated; tracker re-anchored 2026-08-16 and owns READY status. |
| Grounded answer → Threat authoring | same tracker — `AOW01` / `AOW02` | Delegated; owner marks this DECOMPOSE before dispatch. |
| Hermes response/query graph chips | same tracker — `GRAPH-CHIPS` | Delegated; owner requires separate response-side and query-anchor slices. |
| Workbench Revise-with-AI UX | same tracker — `REVISE-UX` | Delegated; tracker owns READY status. |
| Dedicated statblock mechanic editor expansion | same tracker — `EDITOR-EXPANSION` | Delegated; tracker requires one mechanic family per slice. |
| Hermes live-progress UX | same tracker — `HERMES-LIVENESS` | Delegated; tracker owns the bounded immediate liveness slice. |
| Hermes durable performance telemetry | same tracker — `HERMES-TELEMETRY` | Delegated; tracker requires capture and reporting to be split before READY. |
| Statblock presentation/media evolution | same tracker — `SBW16–18` | Delegated as DEFERRED domain work rather than a root IDEA. |
| Build/Plan shared Threat projection + campaign-useful glance | merged PR #512 | Removed from active backlog as implemented; regressions should be filed as new current defects. |
| Abandoned `/surface` / `SurfaceShell` cleanup | current source tree | Removed from active backlog after current-tree search found no `SurfaceShell` owner to dispatch; resurrect only from a concrete current consumer. |

## Hygiene history

- 2026-08-16 pass 1: 74 active headings → 29; see `Docs/Reports/BACKLOG-HYGIENE-2026-08-16.md`.
- 2026-08-16 pass 2: convert root backlog from “worth doing” list to strict dispatch inventory; status-bearing entries reduced to 13, tracker-owned work delegated without duplicate status, READY reduced to seven bounded slices, and the Threat/Statblock owner tracker/roadmap re-anchored to current merged evidence.
