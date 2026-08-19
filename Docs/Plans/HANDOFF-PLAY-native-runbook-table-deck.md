# HANDOFF — project one durable Runbook as a native Play table deck

> **MERGED / HISTORICAL (2026-08-19):** PR **#618** merged as
> `03252d51c8e13ff0322204bacdc605d3fc3a1201` after **3 review cycles**.
> Reviewed head `a907e623c3e53113688c2a55161e0c7ad4c4d53b`;
> implementation/evidence head `196144bb59281f15931305ecc70b252d69f5670d`.
> P3A proved native `/play` over one exact Run + sealed manifest + committed Runbook.
> Immediate consuming successor: `Docs/Plans/HANDOFF-PLAY-start-run-from-runbook.md`
> (Start Run dogfood bridge). P3B remains designed but deferred behind that sequence.

**Created:** 2026-08-17
**Status:** MERGED / HISTORICAL — PR #618 / main `03252d51c8e13ff0322204bacdc605d3fc3a1201` after **3 formal review cycles**. Implementation/evidence head `196144bb59281f15931305ecc70b252d69f5670d`; final reviewed head `a907e623c3e53113688c2a55161e0c7ad4c4d53b`. This file is not current dispatch authority.
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md`
**Workstream:** `Playable Architecture Graduation / P3A`
**Flow / owner:** `PLAY`
**Direction:** DESIGN → CODE → REVIEW
**Implementation base:** `93ad974d2f9690e5f8f552059d2fb71f5181b9b9`
**Base revision:** `93ad974d2f9690e5f8f552059d2fb71f5181b9b9`
**Suggested branch:** `agent/play-native-runbook-table-deck`
**PR title:** `PLAY: project native Runbook table deck`

> Repository law: `AGENTS.md`.
> Playable authority: `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`.
> Play product design: `Docs/Design/DESIGN-play-surface-projection.md`.
> Shared-host authority: `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`.
> Graph authority: `Docs/Design/ARCHITECTURE-campaign-supergraph.md`.
> Living sequence: `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.
>
> Do **not** dispatch from PR #615, PR #616, or the pre-review version of `HANDOFF-PLAY-exact-graph-reference-open.md`. PR #617 made that design explicitly non-dispatchable.

## 0. Re-anchor and correction of course

Current repository truth at dispatch:

```text
main:
  93ad974d2f9690e5f8f552059d2fb71f5181b9b9
  merge of PR #617

P2:
  COMPLETE

P2C / PR #612:
  merge:                  a2c88d95397d972ad86834912b00a244edcdba17
  implementation/evidence 0299d6a610566eebbad83b1786d72aa567826258
  final reviewed head:    13b09b7a52e573082857d09dc0413e1b29e39774
  formal review cycles:   2

P3C / PR #608:
  merge:                  53aaf9a566cfd40dd09f1a4c9723276cefa2a98a
  implementation/evidence 9b6918d66643094c06821f354f9afb80322f39ac
  final reviewed head:    6b0b177f08a09c2b1f8c8ff9a1eb71b450b57087
  status:                 merged early, partial P3 capability

PR #615:
  accidentally merged design
  exact-reference handoff now NON-DISPATCHABLE

PR #616:
  exact-reference implementation CLOSED / UNMERGED
  useful design evidence only

PR #617:
  repaired #615 repository state
  explicitly leaves P3 next implementation capability unselected

current native Play product:
  no /play route
  no mounted PlaySurfacePage
  no native Runbook table deck
  playSurface/reference contains early P3C object/mechanics composition
```

The failed #615/#616 sequence exposed the missing prerequisite: exact reference opening cannot truthfully be called a **Play surface capability** until a native Play surface exists.

A prior P3A design at `b47c66c6a780308ceb2d8720de2f3086aad33cfc` identified that prerequisite correctly. This handoff rebriefs that design against current `main`; the old branch itself is not dispatch authority.

### Capability decomposition

| Candidate outcome                                   | Decision                                      |
| --------------------------------------------------- | --------------------------------------------- |
| Native `/play` route over one explicit durable Run  | **Include**                                   |
| Exact Run + manifest + bound Runbook admission      | **Include**                                   |
| Scene / Beat / Choice / Option table projection     | **Include**                                   |
| Existing P2 Runtime progress controls               | **Include**                                   |
| Run chooser without implicit first/latest selection | **Include**                                   |
| Exact graph-reference opening                       | **Exclude — P3B successor**                   |
| Generic graph-object sheet workflow                 | **Exclude — P3B successor**                   |
| P3C Threat mechanics changes                        | **Exclude — already landed; regression only** |
| Add Threat to Combat                                | **Exclude — P4**                              |
| Run rebase UI                                       | **Exclude — separate lifecycle workflow**     |
| Automatic consequence execution                     | **Exclude**                                   |
| New Playable grammar                                | **Exclude**                                   |
| New Runtime persistence format                      | **Exclude**                                   |
| Historical Runbook archive                          | **Exclude**                                   |
| New Projection host / provider                      | **Prohibited**                                |
| DungeonMind / DungeonMindDnD contract change        | **Prohibited**                                |

---

## §1 Mission and merge-ready invariant

**Mission:** A GM can open one explicit durable Run in native `/play`, see the exact Run-bound Runbook as a Scene/Beat/Choice table deck, and update its existing P2 Runtime progress without campaign-specific bridge data or a second authority store.

**Merge-ready invariant:**

> Native Play becomes usable only from one coherent exact authority set: the persisted Run, its sealed reference manifest, and the committed workspace Runbook snapshot whose document ID, revision, and content digest exactly match the Run binding. Scene/Beat/Choice/Option identity and authored content come from that admitted Runbook; current/resolved/selection/note state comes only from the P2 Run under `run_revision` CAS. Missing, malformed, recovery-pending, stale, mismatched, or structurally contradictory inputs fail closed before Play presents editable Runtime controls. Play never overlays old Runtime on newer Runbook prose, silently rebases, auto-selects another Run, falls back to #578 campaign data, opens graph references, creates a second Projection host, or mutates World/Source/Mechanics/Combat authority.

### Pre-dispatch critique

| Question                                                | Answer                                                                                                                                                                                  |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Can one invariant govern every changed observable path? | **Yes.** Route entry, chooser, exact admission, rendering, and Runtime mutations all operate on one Run-bound authority set.                                                            |
| Most dangerous adversarial sequence                     | Run N is bound to Runbook R → Runbook R+1 is committed elsewhere → Play reloads and accidentally displays R+1 prose with N's Runtime progress.                                          |
| Required safe result                                    | Block the deck as `rebase required`; render no authored body under the stale Run binding and expose no progress mutation controls.                                                      |
| Does §7 detect it?                                      | **Yes.** Owning integration/component proof supplies mismatched workspace revision/SHA and proves no ready deck or mutation path exists.                                                |
| Easiest boundary to under-test                          | Client P1 structure vs sealed P2B1 manifest parity. Both understand Playable IDs independently; disagreement must be integrity failure, not normalization.                              |
| Stop/split trigger                                      | Need for historical Runbook retrieval, grammar changes, graph-reference opening, graph-object composition, rebase UI, new backend projection schema, or a generic work-object contract. |

---

## §2 Context, authority, and predecessor contracts

Read before changing code, in this order:

1. `AGENTS.md`
2. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
3. `Docs/Design/DESIGN-play-surface-projection.md`
4. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
5. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
6. `Docs/Plans/HANDOFF-PLAY-run-rebase.md`
7. P1 identity/index implementation
8. P2 Run authority
9. Workspace authority
10. Shared surface host
11. P3C only as an already-landed sibling

PR #578 may be inspected for **interaction evidence only**. Do not copy `ofConks*`, campaign dictionaries, branch enums, separate run state, or injected legacy Play globals into permanent P3A.

### Exact predecessor

P2 supplies Run identity, sealed P2B1 manifest, and full-progress CAS under `run_revision`. P2C recovery-pending must fail closed. TypeScript may mirror route payloads; it must not invent approximately equivalent vocabulary.

### State-authority sync

```text
PREDECESSOR DOC SYNC REQUIRED: none
```

This PR **does** own selecting P3A as the active P3 implementation in the living roadmap and adding its implementation/evidence ledger disposition before final review. It must not claim P3A merged or P3B active before those facts become true.

---

## §3 Observable paths and adversarial sequences

### Route behavior

`/play` shows the durable Run chooser: list from the existing P2 Run endpoint; no first-run auto-selection; no "latest" heuristic; no campaign-name/label matching as identity; choosing one Run navigates to its exact canonical UUID.

`/play?run=<run UUID>` loads only that Run. Malformed or missing identity produces a truthful error/miss state; it never chooses another Run.

### Exact admission pipeline

For one explicit Run: load exact persisted Run, exact sealed reference manifest, and current committed workspace snapshot for `run.playable_artifact_id`. Prove document ID, admitted Runbook kind, revision, and content SHA match the Run binding. Parse that exact Markdown through existing P1 admission, derive the P1 structure index, verify structure/reference membership against the sealed manifest, and only then enter READY.

No later/current workspace bytes are accepted merely because they share the document ID.

### Ready table deck

Present Run identity/title, Scene navigation, Beat navigation, focused authored table content, Choice/Option content, resolved state, current Scene/Beat, selection state, and notes. Keep table-first presentation calm. Do not turn P3A into a graph/evidence dashboard.

If Runtime has no current Scene, the UI may visually preview the first authored Scene, but it must not write `current_scene_id` until the GM explicitly chooses/set-current.

### Runtime mutation

All Runtime mutations reuse the existing P2 full-progress operation and sole `run_revision` CAS. No local durable progress store. No second concurrency token. Prefer server-authoritative UI: submit exact current snapshot + expected `run_revision` → server success → replace local Run snapshot with returned authoritative state.

On `409` CAS conflict: do not silently retry, merge, or preserve the attempted local result as truth; refetch exact Run; show truthful conflict/reload state.

On timeout/network/unknown outcome: do not assume success or failure; refetch exact Run before further mutation.

### Required failure matrix

| Condition                                       | Required behavior                              |
| ------------------------------------------------ | ---------------------------------------------- |
| `/play` with no run                             | chooser; no auto-selection                     |
| Run not found                                   | explicit miss                                  |
| Run GET unavailable                             | unavailable/error; no fabricated deck          |
| P2C recovery pending                            | blocked/recovery state; no mutation            |
| Manifest missing                                | integrity failure                              |
| Manifest malformed/mismatched                   | integrity failure                              |
| Workspace document missing                      | unavailable/miss                               |
| Workspace revision differs from Run             | `rebase required`                              |
| Workspace SHA differs from Run                  | `rebase required` / integrity block            |
| Client structure disagrees with sealed manifest | integrity failure                              |
| Workspace discarded / uncommitted / missing target | integrity failure; no READY deck           |
| READY coherent authority set                    | native table deck                              |
| Progress PUT succeeds                           | adopt returned authoritative Run               |
| CAS 409 same Playable binding                   | conflict + exact Run reload; no implicit retry |
| CAS 409 / unknown outcome with changed Playable binding | re-admit; never overlay new Run on old scenes |
| Unknown write outcome                           | reconcile by exact Run reload                  |
| Route changes to another Run during async load  | stale completion discarded                     |
| Component unmounts / surface lease changes      | stale completion cannot repopulate Play        |

### Identity rules

Run identity is exact canonical `run_id` only. Playable work object is exact `playable_artifact_id`. Playable revision is the exact revision + content SHA pair. Scene/Beat/Choice/Option use exact existing P1 stable IDs. Display titles are presentation only. Label/alias normalization is never an identity fallback. Graph nodes are not opened in this slice.

---

## §4 Files in scope — exclusive write lease

| Action | Path                                                                           | Purpose                                                                 |
| ------ | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| Create | `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md`                         | checked-in implementation authority                                     |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`                   | select P3A + current evidence ledger/disposition; do not pre-mark merge |
| Modify | `apps/live-control-ui/src/App.tsx`                                             | native `/play` route + launcher composition                             |
| Modify | `apps/live-control-ui/src/App.test.tsx`                                        | owning route tests                                                      |
| Modify | `apps/live-control-ui/src/chrome/appChromeConfig.ts`                           | Play route/nav label through shared AppChrome                           |
| Modify | `apps/live-control-ui/src/test/combatTrackerProductNav.test.ts`                | preserve Combat product-nav correspondence with `APP_NAV_ITEMS`         |
| Modify | `evals/c2_live_prep/mireward-prep/assets/prep.js`                              | add Play to Combat `PRODUCT_NAV` to match AppChrome                     |
| Modify | `apps/live-control-ui/src/api/types.ts`                                        | exact frontend mirrors of existing P2 Run/manifest contracts            |
| Modify | `apps/live-control-ui/src/api/liveApi.ts`                                      | thin clients over existing Run/manifest/progress endpoints              |
| Create | `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`                     | chooser, admission lifecycle, Play surface publication                  |
| Create | `apps/live-control-ui/src/playSurface/playSurface.css`                         | Play-owned table-deck presentation                                      |
| Create | `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts`      | pure exact admission/projection derivation                              |
| Create | `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts` | revision/SHA/manifest/P1 parity proof                                   |
| Create | `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx`            | Scene/Beat/Choice deck + P2 Runtime controls                            |
| Create | `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.test.tsx`       | component + CAS/failure behavior                                        |
| Create | `apps/live-control-ui/src/playSurface/runbook/index.ts`                        | Play-local exports only                                                 |

### Bounded discovery exception

Maximum **two** additional paths, only under `apps/live-control-ui/src/playSurface/`. Allowed kinds: test helper, test fixture, small Play-local presentational component. Use only when splitting such a file makes the exact same §1 invariant easier to test or review. No existing shared/P1/P2/P3C file may enter through this exception.

---

## §5 Explicitly out of scope

Do not modify or claim:

```text
apps/live-control-ui/src/playSurface/reference/**
apps/live-control-ui/src/graphReference/**
apps/live-control-ui/src/agentInteraction/** host ownership
apps/live-control-ui/src/surfaceInteraction/** host implementation
apps/live_control_server/**
src/graph_memory/**
DungeonMind / DungeonMindDnD packages
Combat mutation/state
Run rebase implementation
Playable Markdown grammar
World Graph identity/projection semantics
source/evidence authority
statblock/mechanics authority
```

Specifically forbidden: resurrecting #616's `PlayExactGraphReference`; opening graph chips; wiring `PlayGraphObjectSheet` into the new route; corpus fallback; `ofConks*` bridge data; auto-rebase; historical Runbook storage; Add to Combat; another Projection host/provider; localStorage Runtime authority.

---

## §6 Implementation contract

```text
Input:
  exact Run UUID
  exact persisted P2 Run
  exact sealed P2B1 manifest
  exact current committed workspace snapshot
  existing P1 Markdown/Playable identity/index contracts

Output:
  native /play surface
  reconstructable Runbook table projection
  existing P2 Runtime progress mutations

Invariant:
  §1 merge-ready invariant

Trust boundary:
  Play verifies exact cross-authority identity/revision/digest/manifest agreement.
  It trusts each predecessor only for the authority that predecessor owns.

Durable writes:
  existing P2 Runtime progress only

New durable representation:
  none

Graph/Source/Mechanics writes:
  none
```

Play is a surface publisher (`surfaceId = play`). It does **not** mount its own AgentInteractionProvider, Projection host, or Tool/Edit/AppChrome bar implementations.

---

## §7 Evidence required to merge

Focused UI proof from `apps/live-control-ui`:

```bash
pnpm exec vitest run \
  src/playSurface/runbook/nativeRunbookProjection.test.ts \
  src/playSurface/runbook/RunbookTableDeck.test.tsx \
  src/App.test.tsx \
  src/test/combatTrackerProductNav.test.ts \
  src/tiptap/playable/playableStructureIndex.test.ts \
  src/tiptap/markdown/markdownToTiptap.test.ts
```

Must prove at least: `/play` exists and uses shared AppChrome; `/play` does not auto-select a Run; `/play?run=<uuid>` loads that exact Run; matching Run + manifest + workspace revision/SHA reaches READY; revision mismatch blocks; digest mismatch blocks; discarded/uncommitted/missing-target workspace blocks; manifest mismatch blocks; client P1 structure/manifest disagreement blocks; recovery-pending Run blocks; current Scene/Beat overlay comes from Runtime; current-null may preview without hidden write; resolved Beat update uses exact `run_revision`; Choice selection changes only the named selection; note mutation changes only the named element note; 409 does not silently retry/merge; unknown mutation outcome reconciles via exact Run reload; concurrent rebase 409 does not overlay the new Run on the old admitted scenes; stale async completion after Run/surface change cannot attach; blocked Play publishes surface identity without admitted campaign/document authority; Combat product nav matches `APP_NAV_ITEMS`; no `ofConks*` data is used; no graph-reference opening is introduced.

P2 owning regression proof from repository root, plus `pnpm run typecheck` / `pnpm run build`, steward preflight, and static search that new P3A paths contain no `ofConks`, corpus fallback, `PlayGraphObjectSheet`, `PlayThreatMechanicsSection`, `AgentInteractionProvider`, or `ProjectionHost`.

---

## §8 Roadmap review requirement

Before final passing review, add the P3A implementation/evidence head to the living roadmap ledger and answer exactly one of `ROADMAP_REVIEW — NO DESIGN CHANGE` or `ROADMAP_REVIEW — UPDATED`. Do not mark P3A merged or invent its future merge SHA/review count in this PR.

Expected default absent contrary evidence:

```text
P3A_HOIST_OBSERVATION:
  Native Runbook projection remains Play-owned.
  P1 stable element identity remains Play-owned.
  P2 Runtime remains Play-owned.
  shared AppChrome/Projection host remains reused rather than forked.
  WorkObjectElementRef remains not yet justified by an independent non-Play consumer.
  WorkObjectRevisionRef remains not yet justified.
  DungeonMind relevance discovered: none.
```

---

## §9 Required review handback

The coding agent returns the §9 checklist from the dispatch: PR URL, branch, head SHA, §1 mission and invariant verbatim, base SHA, nano-commits, changed paths, focused diff stat, every §7 command result, evidence provenance, stale-Runbook / manifest-P1 / CAS results, roadmap disposition, paths outside §4, baseline failures, operator waivers, stop conditions, and confirmation that P3B/reference-open, P3C changes, P4 Combat, rebase UI, and new durable contracts remain false.

---

## §10 Acceptance rubric

Merge only when native `/play` is a real mounted product route; one explicit Run UUID is the only Run selection identity; no automatic first/latest Run selection exists; READY requires exact Run + manifest + committed Runbook revision/SHA coherence; P1/manifest disagreement and P2C recovery-pending fail closed; Scene/Beat/Choice content comes from the admitted exact Runbook; Runtime overlay comes only from the admitted P2 Run under `run_revision` CAS; CAS conflict and unknown outcomes are reconciled truthfully; browser reload reconstructs table position from durable authority; stale async completions cannot attach; shared AppChrome/Agent/Projection ownership remains singular; P3C files are unchanged except regression execution; no graph reference opens; no `ofConks*` data exists in the new path; no historical Runbook archive, new backend schema, local Runtime store, or generic work-object contract was introduced; every changed path is inside §4 or its bounded exception; roadmap disposition is recorded from actual evidence; P3B remains the first graph-object/reference-open successor; P4 remains the first Combat mutation.

---

## Stop conditions

Stop and report rather than expanding if implementation discovers that the exact bound Runbook revision cannot be obtained without historical Runbook storage; current P2 APIs do not expose enough information to prove the Run/manifest/workspace authority tuple; P1 client structure cannot be compared with the sealed manifest without changing the Playable grammar; native Play requires a new backend projection schema; progress mutation requires a second concurrency token or client persistence format; graph-reference opening is required merely to make the table deck useful; P3C mechanics require modification to mount `/play`; another active lane owns a §4 path; a second Projection host/provider appears necessary; any path outside §4/bounded discovery is required; or evidence shows the P3A invariant actually decomposes into independently useful capabilities.
