---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: UI Presentation Substrate Sidequest
  - Flow: UI
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-UI-world-object-showroom.md
  - Branch / PR: none while BLOCKED
  - PR topology: serial

  ## Verification pointer
  - Design authority / head: BLOCKED F1 handoff design PR #770 at f44091de
  - Changed paths: exact §4 allowlist only
  - Verification: focused ObjectSheet tests + Ladle build + typecheck + production build + diff checks

  The checked-in ACTIVE handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — UI World-object showroom

**Created:** 2026-09-25
**Status:** BLOCKED — UI-F1 implementation is not current authority after rollback; this design PR may land as blocked, but F2 implementation requires F1 to merge first
**Canonical handoff path:** `Docs/Plans/HANDOFF-UI-world-object-showroom.md`
**Conversation/workstream:** `UI Presentation Substrate Sidequest`
**Flow / owner:** `UI`
**Direction:** DESIGN → CODE → REVIEW
**Design authority base:** `f44091de` — open F1 handoff design PR #770 head
**Design PR topology:** stacked on PR #770 at `f44091de`; merge/re-anchor #769, then #770, then this one-file handoff PR. Historical PR #757 and F1 implementation PR #768 were merged but reverted and are not current authority.
**Activation gate:** F1 implementation accepted/merged after its steward-landed handoff is ACTIVE; this F2 design handoff landed on main; fresh-main re-anchor confirms the actual primitive/token/workshop API and no conflicting UI lease
**Dispatch base rule:** fresh current `main` containing this checked-in handoff after the activation gate is satisfied; record the exact implementation branch base at dispatch/review.
**PR topology:** `serial`
**PR authorization:** once ACTIVE, open/update exactly one implementation PR for this capability without asking; no successor/repair PRs
**PR title:** `UI: add World-object showroom`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

## §1 Mission and merge-ready invariant

**Mission:** A frontend developer can compare representative World-object presentations in the backend-free UI workshop so that table-first object design can be iterated against real Buddy view-model shapes before production integration.

**Merge-ready invariant:** One new ObjectSheet presentation consumes the existing `GraphObjectCardViewModel` contract without redefining graph semantics, renders the same bounded information hierarchy across sparse/rich object fixtures, and remains entirely static/workshop-owned with no production routing, authority, or persistence change.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every story is the same ObjectSheet over the same existing view-model contract; fixture variety exercises presentation pressure rather than separate capabilities. |
| Most likely adversarial sequence | Fixture needs “better data” → presentation invents fields/semantics not in `GraphObjectCardViewModel` → showroom stops representing production truth. |
| Will §7 actually detect that failure? | Yes. Fixtures are typed as `GraphObjectCardViewModel`, predecessor-field mapping is explicit, and source guards prohibit production DTO/network adapters in the showroom. |
| Easiest owning boundary to under-test | Sparse/empty-state hierarchy: rich fixtures can hide accidental assumptions about summary, role, aliases, relationships, or evidence always existing. |
| What PR topology is authorized, and why is it safe? | Serial. This slice depends on the exact F1 primitive/workshop API and should not guess it while F1 is unmerged. |
| Fact that forces stop/split | ObjectSheet requires new product semantics/fields, Threat mechanics become necessary, or the slice must modify existing production `GraphObjectCard` to be useful. |

## §2 Context, authority, lane, and PR topology

| Field | Required content |
|---|---|
| Parent authority | `PLAN-ui-presentation-substrate-sidequest-v1.md`; UI language Goal 4 table-first World objects |
| Design authority base | `f44091de` — BLOCKED F1 handoff design PR #770 |
| Activation gate | F1 implementation merged; this F2 handoff landed on main; steward re-anchors and verifies no conflicting UI lease |
| Dispatch base rule | fresh current main containing this handoff after activation |
| Predecessor contract | `apps/live-control-ui/src/graphObjectCard/types.ts` `GraphObjectCardViewModel`; F1 tokens/primitives/workshop |
| Exact input consumed | Static values conforming exactly to `GraphObjectCardViewModel` |
| Named successor | UI-F3 — separate one mature production host/controller from replaceable presentation |
| What remains false | Existing `GraphObjectCard` unchanged; no production ObjectSheet adoption; no Threat/statblock redesign; no screenshot regression suite |
| Explicit non-goals | graph DTO changes; World read logic; new object fields; evidence admission; relationship semantics; Threat mechanics; production Peek integration |
| PR topology | serial |
| Authorized PR action | open/update exactly this assigned PR without asking; no additional PRs |
| Open implementation PRs in workstream at dispatch | none required; steward re-checks |
| Stack parent + merge/rebase order | not applicable |
| Branch / isolated checkout | none while BLOCKED; fresh implementation branch/worktree after activation |
| Parallel lanes / collision hotspots | graphObjectCard production files are read-only evidence; UI-F2 writes only new `src/ui` files plus plan sync |
| Runtime/state ownership | static workshop only; no backend/runtime state |
| State-authority sync set after merge | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` records UI-F1 completed predecessor / UI-F2 current |

Read before implementation:

1. `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md`
2. active UI-F1 implementation/result
3. `apps/live-control-ui/src/graphObjectCard/types.ts`
4. `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx`
5. `apps/live-control-ui/src/graphObjectCard/graphObjectDisplay.ts`
6. `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.test.tsx`
7. `Docs/Design/ui-language/DESIGN-interaction-layer-language.md`

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Sparse NPC fixture | No isolated canonical object fixture | ObjectSheet remains useful with label/type and little else | Yes | ObjectSheet |
| Rich NPC fixture | Production-only path | Summary, aliases, relationships, source/evidence hierarchy remains table-first | Yes | ObjectSheet |
| Location fixture | Production-only path | Same component hierarchy; no location-specific branch required | Yes | ObjectSheet |
| Faction fixture | Production-only path often reads like graph dump | Presentation emphasizes campaign information over graph diagnostics | Yes | ObjectSheet |
| Relationship-heavy fixture | Current card caps/discloses rows | ObjectSheet remains scannable and bounded; no giant graph dump | Yes | ObjectSheet + existing pure helpers |
| Narrow workshop viewport | No canonical object comparison | Sheet remains readable without adding route-specific responsive state | Yes | ObjectSheet CSS |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Render sparse object with empty optional arrays/fields | Useful identity shell; no fake placeholders or exceptions | focused component test |
| Render 15+ relationships → expand/collapse | Bounded default rows and deterministic disclosure; fixture remains static | focused component test |
| Fixture contains evidence/debug IDs | Ordinary sheet keeps technical identity secondary; no raw IDs promoted into primary hierarchy | component test/story review |
| Change fixture kind from NPC to Faction without shape change | Same component contract; no type-specific domain branching needed | story comparison |

## §4 Files in scope — write lease

Assumes UI-F1 created `apps/live-control-ui/src/ui/`. Re-anchor exact paths at activation without changing mission.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live-control-ui/src/ui/fixtures/worldObjects.ts` | Typed static `GraphObjectCardViewModel` fixtures |
| Create | `apps/live-control-ui/src/ui/ObjectSheet.tsx` | First real Buddy presentation pattern |
| Create | `apps/live-control-ui/src/ui/ObjectSheet.css` | Pattern styling through F1 semantic tokens/primitives |
| Create | `apps/live-control-ui/src/ui/ObjectSheet.stories.tsx` | Sparse/rich NPC, Location, Faction, relationship-heavy stories |
| Create | `apps/live-control-ui/src/ui/ObjectSheet.test.tsx` | Information-hierarchy and sparse/relationship behavior proof |
| Modify | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` | Backward-looking predecessor sync |

**Bounded discovery exception:**
```text
Directory: apps/live-control-ui/src/ui/
Maximum additional paths: 1
Allowed path kinds: one pure helper module only
Decision rule: only if ObjectSheet needs a reusable presentation-only helper that cannot live readably in ObjectSheet.tsx; no new public/domain contract
```

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx` | Production adoption is intentionally later |
| `apps/live-control-ui/src/graphObjectCard/types.ts` | Existing view-model is predecessor authority; do not widen it for design convenience |
| `apps/live-control-ui/src/graphObjectCard/graphObjectDisplay.ts` | Pure helpers may be consumed, not rewritten |
| `apps/live-control-ui/src/planSurface/planSurface.css` | Do not migrate existing production paint yet |
| `apps/live-control-ui/src/statblocks/**` | Threat/statblock presentation remains its own mature path |
| `apps/live-control-ui/src/surfaceInteraction/**` | No host behavior change |
| `apps/live-control-ui/src/api/**` | No DTO/network changes |

## §6 Implementation contract

```text
Input:
  GraphObjectCardViewModel static fixture

Output:
  ObjectSheet React presentation suitable for isolated workshop comparison

Invariant:
  same as §1

Failure behavior:
  absent optional field → omit that region truthfully
  empty relationships/evidence → no empty diagnostic chrome
  long relationship set → bounded default + disclosure
  unsupported mechanics (e.g. full Threat statblock) → not represented/invented

Replay / idempotency:
  same fixture → deterministic presentation
  changed fixture → presentation changes only from typed input
  no persistence/retry state

Trust boundary:
  Verifies: presentation uses existing view-model meaning
  Records/trusts without proving: correctness/completeness of upstream graph projection
```

### A. State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| Static ObjectSheet | n/a | renders typed fixture | absent optional data omitted | n/a | TypeScript/test failure | n/a | deterministic rerender |

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Exact object id | Preserve in model but do not promote to primary display | n/a | No label substitution for identity semantics |
| Label | Display only | n/a | Yes as display text only |
| Relationship target id | Passed through existing model/callback shape; story is static | n/a | No inference |
| Alias | Display alias only | n/a | Never canonical identity |

### C. Persistence / replay matrix

Not applicable — stories/fixtures are source code, not product persisted state.

### D. Predecessor → consumer mapping

**Grounding source:** `apps/live-control-ui/src/graphObjectCard/types.ts`

| Predecessor field/outcome | Real shape/optionality | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| `label`, `typeBadgeLabel` | required strings | primary identity hierarchy | none | ObjectSheet tests |
| `secondaryRoleLabel`, `aliases` | optional | secondary identity copy when present | none | sparse/rich tests |
| `gameSummary ?? summary` | optional | table-first summary | same precedence as current card | tests |
| `relationships[]` | optional | related campaign information | reuse existing pure row selection/humanization helpers where suitable | 15-row test |
| `evidence[]`, `details` | optional | source/provenance remains secondary | no new semantics | tests |
| `campaignLabel` | optional | compact scope badge | none | fixture story |
| `actions[]` | optional | not required in F2 pattern; may be omitted from stories | no transformation | explicit non-goal |

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| ObjectSheet accepts exact predecessor model | TypeScript/component | contract | `npm --prefix apps/live-control-ui run test -- src/ui/ObjectSheet.test.tsx` | PASS | new field/type widening required |
| Sparse/rich hierarchy remains truthful | component | adversarial | focused tests | no fake placeholder regions; primary/secondary hierarchy stable | sparse object unusable |
| Large relationships stay bounded | component | regression | focused 15-row test | cap/disclosure behavior | full graph dump/default overflow |
| Workshop stories compile | Ladle | regression | `npm --prefix apps/live-control-ui run ui:build` | PASS | story build failure |
| Existing production untouched | Git/source | contract | diff path check + static search | no graphObjectCard/api/surfaceInteraction production modifications | any production adoption |
| Project still typechecks/builds | frontend | regression | typecheck + production build | no new failures | new failure |
| Visual comparison is useful | workshop | manual | compare sparse NPC, rich NPC, Location, Faction, relationship-heavy at desktop + narrow widths | differences reveal hierarchy pressure without backend | fixtures require live product to judge |
| Lease exact | Git | contract | diff checks | only §4/bounded helper path | unexpected path |

Exact commands:

```bash
npm --prefix apps/live-control-ui run test -- src/ui/ObjectSheet.test.tsx
npm --prefix apps/live-control-ui run ui:build
npm --prefix apps/live-control-ui run typecheck
npm --prefix apps/live-control-ui run build
git diff --check
git diff --name-only <dispatch-base>...HEAD
```

### Minimal live / dogfood proof

```text
Existing surface: Ladle workshop
Smallest realistic scenario: compare all World-object stories at desktop and narrow widths
Expected observation: one pattern handles sparse/rich/type variation without backend and without looking like raw graph diagnostics
Evidence captured: screenshots optional; reviewer records qualitative hierarchy failures explicitly
```

### Baseline failure handling

Same-command base/head comparison for any required failure. No new UI failure accepted.

## §8 Required review handback

Record exact head/base/topology, F1 predecessor version consumed, actual fixture list, changed paths, test/build results, workshop comparison notes, and whether any new view-model field was requested. Any requested field widening is a stop rather than an implementation convenience.

## §9 Acceptance rubric

- [ ] UI-F1 predecessor is merged and exact API recorded.
- [ ] Exactly one ObjectSheet pattern is delivered.
- [ ] Fixtures are typed with the existing `GraphObjectCardViewModel`.
- [ ] No production `GraphObjectCard` or graph DTO is modified.
- [ ] Sparse/rich/location/faction/relationship-heavy stories compile.
- [ ] Relationship-heavy default remains bounded.
- [ ] Technical identity/evidence stays secondary.
- [ ] Threat/statblock mechanics are not absorbed.
- [ ] Workshop remains backend-free.
- [ ] UI-F3 remains false.

## Stop conditions

Stop and report if:

- UI-F1 is not merged/activated as assumed;
- existing view-model cannot express the desired object hierarchy without new semantics;
- Threat mechanics become necessary to prove generic ObjectSheet;
- production GraphObjectCard must change;
- API/graph/surface provider is required;
- a second pattern/fixture framework is proposed;
- fixture content starts carrying hidden canonical product state beyond the typed view-model contract.
