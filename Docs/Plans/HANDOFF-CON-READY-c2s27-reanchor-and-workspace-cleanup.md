---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CON-READY / post-C2S27 steward re-anchor
  - Flow: CON-READY
  - Direction: steward-authorized documentation-only state synchronization (explicit exception)
  - Handoff: Docs/Plans/HANDOFF-CON-READY-c2s27-reanchor-and-workspace-cleanup.md
  - Branch / PR: con-ready/c2s27-reanchor-workspace-cleanup / `CON-READY: re-anchor C2S27 dogfood and clean steward workspace`

  ## Verification pointer
  - Base: `62f7f9e856327247b8677b4c951801e4c58a826c` (merge of PR #622)
  - Changed paths: HANDOFF §4 write lease only; no production/runtime code
  - Verification: HANDOFF §8 — stale-claim sweep, mirror byte-identity, worktree before/after inventory

  The checked-in handoff, cumulative diff, and independently rerun verification
  are the review contract. The PR description is transport metadata only.
---

# HANDOFF — re-anchor C2S27 dogfood and clean steward workspace

**Created:** 2026-08-20  
**Status:** ACTIVE — one exceptional documentation-only synchronization PR plus local steward workspace cleanup; becomes MERGED / HISTORICAL at merge.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CON-READY-c2s27-reanchor-and-workspace-cleanup.md`  
**Workstream:** `CON-READY`  
**Flow / owner:** `CON-READY` (steward)  
**Direction:** operator-authorized state-authority sync → REVIEW → MERGE  
**Implementation base:** `62f7f9e856327247b8677b4c951801e4c58a826c`  
**Suggested branch:** `con-ready/c2s27-reanchor-workspace-cleanup`  
**PR title:** `CON-READY: re-anchor C2S27 dogfood and clean steward workspace`

> Repository law: `AGENTS.md`.
> Workstream anchor: `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`.
> Product roadmap: `Docs/Roadmaps/ROADMAP-con-ready.md`.
> Living Playable sequence: `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.
> Final dogfood report: `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`.

---

## 0. Explicit doc-sync exception

This is deliberately **not** a `DOCUMENTS` flow PR; the owning workstream is **CON-READY**.

`AGENTS.md` invariant 10 makes documentation-only PRs exceptional. The operator has **explicitly authorized** this exceptional documentation-only synchronization. The exception belongs to this handoff and the PR record. `AGENTS.md` is **not** modified; the general rule is not weakened.

## 1. Mission

Establish one clean post-C2S27 steward baseline from which implementation can safely resume.

After this PR, current repository authorities must agree on:

- what is actually merged (D2 / PR #622 at `62f7f9e856327247b8677b4c951801e4c58a826c`);
- what C2S27 dogfood proved;
- what parts of PR #623 were rejected;
- the revised Playable hierarchy and product direction;
- the new implementation sequence;
- the fact that P3B/P4 are deferred rather than current dispatch authority.

The local coding workspace must also contain only intentionally retained worktrees so stale development lanes no longer interfere with new dispatch.

## 2. Merge-ready invariant

At one exact `main` base, all mutable CON-READY / Playable state authorities, canonical Playable design documents, sequencing handoffs, backlog entries, and design-agent export mirrors describe the same post-C2S27 truth:

- D2 / PR #622 is complete;
- PR #623 is non-mergeable dogfood/mining evidence;
- native Play is not product-ready;
- active-Run continuity, durable Combat, durable mutable state, Beat-first Playable structure, and direct Plan→Playable authoring precede another Play-table implementation;
- P3B and P4 remain deferred.

No production/runtime code changes in this PR. The operator-authorized workspace cleanup removes only safely classified stale local worktrees and preserves any unmerged or dirty work before removal.

## 3. Authority facts to record

- `main` is pinned at `62f7f9e856327247b8677b4c951801e4c58a826c`, merge of PR #622.
- D2's handoff is stale on `main` and still calls itself ACTIVE even though #622 merged.
- PR #623 (`agent/play-current-beat-table-stage`, head `aa6d1119343c6ec4a65fcf3792251d62c466861d`) is evidence/mining, not an implementation candidate. Its useful evidence includes the Session 27 dogfood, the persistence findings, and the prototype comparison. Its Table implementation, hidden Scenes prose parsing, Combat localStorage changes, and bundled multi-capability code are **not** to be merged.
- The expanded C2S27 dogfood result is recorded as **BLOCKED / PLAY NOT READY**, not the branch report's interim `NOT RUN`. The branch report recorded that exact Run admission worked while the native table experience did not. The subsequent operator observations to record:
  - Leaving Play and returning forced Run selection again.
  - Ordinary re-entry encouraged creation of duplicate Runs.
  - The chooser rapidly accumulated useless duplicate UUIDs.
  - Native Play did not meaningfully reproduce the useful prototype interaction/design.
  - Decision loading / branch visibility was unclear.
  - Plan ideas did not enter Play with sufficient semantic fidelity.
  - Beat appears to be the larger useful hierarchy over Scenes.
  - Decisions should carry consequences and reshape which Scenes remain possible/relevant.
  - Combat Tracker was materially more useful than native Play.
  - Combat state must become durable and independent of browser/worktree.
  - Statblock and roll-table opening remain first-class table needs.

## 4. Repository write lease

| Action | Path | Required sync |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-CON-READY-c2s27-reanchor-and-workspace-cleanup.md` | This explicit exception/reset authority |
| Create | `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md` | Mine #623 report, update to final current dogfood truth |
| Modify | `Backlog.md` | Replace one broad persistence/Play idea with bounded residuals and dependencies |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` | Re-anchor CR-U11/U13–U17 and new delivery priority |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | Record D2 merge, C2S27 falsification, retire D4 as current sequence |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Current-state re-anchor and current false user stories |
| Modify | `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md` | Replace fixed Runbook → Scene → Beat assumption; activate Combat-linked runtime need |
| Modify | `Docs/Design/DESIGN-play-surface-projection.md` | Beat-first table hierarchy, Run continuity, Scenes/Decisions beneath current Beat |
| Modify | `Docs/Design/DESIGN-playable-authoring-and-adoption.md` | Plan authors/adopts the exact Playable material rather than exporting a lossy derivative |
| Modify | `Docs/Design/ANCHOR-runbook-lantern.md` | Update mnemonic hierarchy and current-table language |
| Modify | `Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md` | Mark D2/#622 merged/historical with evidence/review truth |
| Modify | `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md` | Keep P3B designed/non-dispatchable behind new roadmap |
| Modify | `Docs/Plans/HANDOFF-PLAY-add-to-combat.md` | Preserve useful design, remove "directly dispatchable when selected" posture until durable Combat re-anchor |
| Modify | `Docs/Design/INDEX-design-agent-source-set.md` | Refresh repository authority basis; add current Playable roadmap to the mirrored set |
| Modify | `Docs/Sources/design-agent/README.md` | Refresh export basis only |
| Mirror | corresponding `Docs/Sources/design-agent/ACTIVE_AUTHORITY/**` / `ACTIVE_REFERENCE/**` copies | Byte-identical copies of every changed canonical authority/reference, including the newly added Playable roadmap copy |

The **Project Sources snapshot date must not advance** merely because repository mirrors are refreshed; the source-set contract reserves that date for an actual operator refresh of the user-managed sources.

### Explicitly not in this PR

- `Docs/Design/DESIGN-play-native-current-moment-deck.md` from #623 does **not** come onto `main`. Its central Scene-first hierarchy has been superseded by the newer dogfood conclusion.
- Session 27 campaign prose/statblocks and other unique #623 artifacts (Session 27 Prep, `mireward_latchling.md`, the C2S27 runbook artifact, dogfood scripts/tests, D3/D4 handoffs, dogfood brief/operator runbook) stay out of this authority PR unless independently classified as accepted canonical content. They remain safely recoverable from the remote PR branch at `aa6d1119343c6ec4a65fcf3792251d62c466861d`.
- No product source, backend, frontend, schema, corpus, generated statblock, package, lockfile, or runtime-state file may change.

## 5. Playable design decisions this sync is allowed to make

The architecture no longer states that `Runbook → Scene → Beat` is the fixed first-class organization. Instead:

```text
Runbook
  → Beats

Beat
  → table objective / pressure / phase
  → Scenes
  → Choices/Decisions
  → consequences
  → references/tools

Scene
  → concrete playable situation inside a Beat

Choice/Decision
  → Options
  → consequences
  → authored transitions affecting later Scene/Beat relevance
```

Exact wire grammar is **not** designed in this PR.

Keep existing stable Choice / Option identity as the first candidate storage primitive for Decisions.

Runtime remains separate and conceptually becomes:

```text
Run
  currentBeat?
  currentScene?
  resolvedBeats
  selections
  notes
  linkedCombatRuntime?
```

Combat is now a real live consumer, so `linkedRuntimeObjects` is no longer purely hypothetical. The architecture activates the need without freezing its eventual wire shape.

## 6. Workspace cleanup contract

This is local steward work performed during the PR, not a repository feature.

The branch inventory shows a very large collection of historical `agent/*` branches, including the whole Play progression. The cleanup target is **local worktrees**, not mass remote-branch deletion.

Classify every worktree before removal:

```text
KEEP
- primary main checkout
- this sync PR checkout
- intentionally active/open PR checkout
- any dirty/untracked checkout until its work is preserved
- any branch with unique commits that are not safely recoverable remotely

REMOVE
- clean worktree for a merged PR
- clean worktree for an explicitly abandoned/closed PR after confirming its head exists remotely
- obsolete detached/stale checkout after confirming no unique work

NEVER
- rm -rf a Git-managed worktree
- remove a dirty worktree merely because its PR is old
- delete remote branches as part of this cleanup
- delete #623's worktree before all wanted dogfood evidence is captured
```

Use normal Git worktree operations, then prune stale registrations.

For #623 specifically: first mine the report/current design evidence into this sync PR and confirm `aa6d1119343c6ec4a65fcf3792251d62c466861d` remains remotely recoverable. Then close #623 without merge and remove its local worktree. The remote branch remains for historical recovery until a later explicit remote-branch hygiene pass.

## 7. Lane / collision review

- This lane's write lease is §4. No other active lane may write those paths while this PR is open.
- Open PRs at dispatch: #623 (being closed by this reset), #607 (`documents/process-exact-state-sync-set`, disjoint process-docs lane), #578 (historical dogfood/mining branch). No write-lease collision.
- Dirty/local-only worktrees (`play/s27` primary checkout, `agent/play-command-board-disk-saves`, `agent/hermes-selected-recap-context`, `cutover/post-dnd34-adoption-proof-state-sync`) are classified KEEP and are not touched.

## 8. Verification

The review proves three different things.

### 8.1 Repository authority

Search the synchronized authority set for stale claims such as:

- D2 being ACTIVE;
- P3B/P4 being next;
- fixed `Runbook → Scene → Beat`;
- D4 being current dispatch authority.

No current state-bearing document may retain those claims. Historical/merged handoffs and evidence reports keep their historical wording.

### 8.2 Mirror integrity

Every changed canonical design/source-set document and its export copy must be byte-identical:

```bash
diff Docs/Design/ARCHITECTURE-playable-material-and-runtime.md Docs/Sources/design-agent/ACTIVE_AUTHORITY/ARCHITECTURE-playable-material-and-runtime.md
diff Docs/Roadmaps/ROADMAP-con-ready.md Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md
diff Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-playable-hoist-dungeonmind-kernel.md
diff Docs/Plans/STEWARDS-ANCHOR-con-ready.md Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md
diff Docs/Design/DESIGN-play-surface-projection.md Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-projection.md
diff Docs/Design/DESIGN-playable-authoring-and-adoption.md Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-playable-authoring-and-adoption.md
diff Docs/Design/ANCHOR-runbook-lantern.md Docs/Sources/design-agent/ACTIVE_REFERENCE/ANCHOR-runbook-lantern.md
diff Docs/Design/INDEX-design-agent-source-set.md Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-design-agent-source-set.md
```

Every command must produce no output.

### 8.3 Workspace integrity

Capture `git worktree list --porcelain` before and after. Every removed worktree must have a recorded safe classification (§6). Final output contains only the primary checkout, this sync lane, and explicitly retained active lanes. No dirty work is lost.

## 9. Post-merge state

The next dependent dispatches are:

```text
Lane A   Active Run continuity / Resume vs Start New
Lane B   Durable Combat state / database-backed tracker authority
```

Those can proceed in parallel after a fresh re-anchor.

The next design task is the Beat/Scene/Decision + Plan→Playable model, but no native Play table implementation starts until that model is reviewed.

This reset protects what P1/P2/P3A/D1/D2 proved, stops investing in the hierarchy C2S27 rejected, makes the useful runtime surfaces durable, and then reconstructs Play around how the GM actually prepares and runs the game.
