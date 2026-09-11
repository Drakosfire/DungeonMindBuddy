---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: UI language design series / DOGFOOD-CONTINUITY
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui01-ingest-shared-peek-v1.md`
  - Branch: `dogfood-continuity/ui01-ingest-shared-peek-v1`

  ## Verification pointer
  - Base: `514823701246879d88085857e5f23258fd0b763e`
  - Changed paths: must remain inside HANDOFF §4 / bounded discovery
  - Verification: HANDOFF §7; exact-head automated evidence + C2S25 desktop/narrow browser witness required

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — DOGFOOD-CONTINUITY: UI-01 Ingest shared peek composition

**Created:** 2026-09-10
**Status:** ACTIVE — implementation complete; awaiting independent review
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui01-ingest-shared-peek-v1.md`
**Conversation/workstream:** UI language design series / C1-C2 demo-readiness
**Flow / owner:** `DOGFOOD-CONTINUITY` / Surface Interaction + AppChrome layout
**Direction:** DESIGN → CODE → REVIEW
**Base revision:** `514823701246879d88085857e5f23258fd0b763e`
**Implementation branch:** `dogfood-continuity/ui01-ingest-shared-peek-v1`
**PR title:** `DOGFOOD-CONTINUITY: compose Ingest around one shared peek`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). UI language: [`Docs/Design/ui-language/DESIGN-interaction-layer-language.md`](../Design/ui-language/DESIGN-interaction-layer-language.md). Shell ownership: [`Docs/Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

## §1 Mission and merge-ready invariant

**Mission:** A GM reviewing a loaded historical recap in Ingest can open Tools, a tool projection, or a World object as secondary context without losing, covering, navigating away from, or remounting the recap.

**Merge-ready invariant:** **On Ingest only, the exact loaded historical recap remains the stable CENTER while secondary inspection uses one real PEEK layout region. At most one peek is visible at a time; the existing semantic owner of each participant keeps its own state/lifecycle; a temporary higher-priority peek does not destroy lower-priority context; Nav remains visible; and participating Ingest peeks do not depend on fixed viewport overlays or guessed `--app-chrome-*` offsets. Non-Ingest surfaces retain their current presentation behavior.**

The one accepted grammar for this slice is:

```text
NAV — cheap, never covered
CENTER — expensive loaded recap; remains mounted
PEEK — one secondary column: projection > Tools > opened World object

wide viewport: CENTER | PEEK
narrow viewport: CENTER then PEEK in normal layout flow
```

The priority order is presentation arbitration only:

```text
projection > tools > world-object
```

It is not World priority, retrieval relevance, persistence, or product authority.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every changed path is about composing already-existing Ingest secondary UI into one layout region while preserving the recap and existing owner state. |
| Most likely adversarial sequence | Load C2S25 → open Karsemine → reveal local relationship state → open Tools → launch Diagnostics projection → close projection → Karsemine returns **without a second complete-object read** and without recap remount/scroll reset. |
| Will §7 actually detect that failure? | Yes: shared-peek arbitration tests retain mounted lower-priority content; Ingest integration proves complete-object request count remains one; browser witness proves geometry, recap continuity, and narrow layout. |
| Easiest owning boundary to under-test | DOM/layout composition: unit tests can prove portal/arbitration state but not that desktop/narrow geometry is actually usable. Exact-head browser dogfood is therefore a merge requirement. |
| Fact that forces stop/split | Needing to change Agent behavior, SurfaceInteraction publication schemas, World/generic-lens semantics, Load/Unload/edit-lock semantics, durable state, server APIs, or non-Ingest surface behavior beyond compatibility regression. |

---

## §2 Context, authority, and lane

### Re-anchor truth at dispatch

```text
main                         514823701246879d88085857e5f23258fd0b763e
open PRs                     none at design/dispatch time
#698                         MERGED — compact opened World objects are A/E-good enough
#699                         MERGED — b1153423f04dd220e3b53d305e8627146a8afb7e
#699 accepted head           99420b0b248aea4d037ae08c1c58b836c8acabe5
#699 lesson                  chrome-band offsets are stabilization, not target architecture
UI language design pickup    accepted: Ingest-first implementation; Play remains visual grammar north star
7A1                          DESIGN READY / QUEUED; must remain undispatched during UI-01
Stage 4                      NOT DONE
```

| Field | Required content |
|---|---|
| Parent authority | `DESIGN-interaction-layer-language.md`; `ARCHITECTURE-surface-interaction-layer.md`; Demo-Ready Stage 4/5 STOP findings; `HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md` |
| Base revision | `514823701246879d88085857e5f23258fd0b763e` |
| Predecessor contract | PR #699 merge `b1153423f04dd220e3b53d305e8627146a8afb7e`, accepted head `99420b0b248aea4d037ae08c1c58b836c8acabe5`; PR #698 complete compact object inspection underneath |
| Exact input consumed | Existing `AppChrome`; `surfaceInteractionPublication.surfaceId`; ToolHost open state; ProjectionHost `active`; Ingest `GraphReviewHistoricalRecapProjection.activeNodeId` + complete-object state. No new server input. |
| Named successor | **UI-02 Agent dock / absence when unavailable.** Agent presentation remains exactly #699-level in UI-01. |
| What remains false | Token-anchored glance, Play parchment/current-moment paint, cross-surface Peek adoption, Load-bar lock/Unload semantics, 7A1 contextual Ask, generic-lens repair, Combat integration. |
| Explicit non-goals | No whole-app shell rewrite; no Of Conks branch merge; no recap parchment paint; no Agent redesign; no graph/search/retrieval changes; no APP-STATE/World writes. |
| Branch / isolated checkout | `dogfood-continuity/ui01-ingest-shared-peek-v1` from exact base above; worker uses isolated worktree/equivalent. |
| Parallel lanes / collision hotspots | No open PRs at dispatch. Remote 7A1 design branch exists but is **queued/inactive**; do not implement it in parallel because it will touch Ingest/Agent seams. `App.tsx`, `AppChrome.tsx`, `styles.css`, ToolHost, ProjectionHost are central collision paths. |
| Runtime/state ownership | Frontend composition only. Dogfood may read World `54330` and APP-STATE `54331`; no writes. Do not start/use disposable `54329`. UI/API `5173/8000` may be used for the exact-head browser witness. |
| State-authority sync set after merge | In this implementation PR, backward-looking only: `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`, `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`, `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md`, and this HANDOFF. Record #698/#699 + accepted Ingest-first decomposition and that UI-01 is the active implementation slice. **Do not mark UI-01 complete or advance UI-02/7A1.** |

Read the exact current ToolHost, ProjectionHost/adapter, AppChrome composition, historical recap object projection, and their tests before changing code. If current `main`, authority, predecessor shape, active lanes, or invariant differs materially, stop and report the consequence.

### Design decision: shared primitive, first consumer only

UI-01 may create a reusable layout/portal primitive under Surface Interaction, but **Ingest is the only surface allowed to adopt it in this PR**.

This is deliberate characterization:

```text
shared Peek primitive
    ↓
first proving consumer = Ingest Graph Review / C2S25

Plan / Build / Play
    retain current presentation behavior in UI-01
```

Do not “finish the abstraction” by migrating every surface.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Ingest loaded recap, no secondary context | Recap fills its current reader layout; global fixed hosts exist outside AppChrome | CENTER renders normally; empty PEEK consumes no second-column space | Yes | AppChrome / Peek layout |
| Click Karsemine or another recap object | Ingest creates a local `recap-graph-object-panel` beside the reader | Existing complete object renders in shared PEEK; recap component remains mounted | Yes | GraphReview historical projection + Peek host |
| Close opened object | Object state has no shared Peek close grammar | X closes object peek by clearing only local object/relationship selection; recap stays | Yes | GraphReview historical projection |
| Open Tools while object is open | Global fixed Tool drawer overlays/squeezes around chrome-band offsets | Tools occupies the **same PEEK** and temporarily hides the object without clearing its local state | Yes | ToolHost + Peek host |
| Launch Ingest Diagnostics from Tools | ProjectionHost opens another fixed drawer; ToolHost closes on successful projection launch | Projection occupies the same PEEK. Existing ToolHost activation semantics remain. Object state remains underneath. | Yes | ProjectionHost / adapter + Peek host |
| Close Diagnostics | Projection closes; previous layout depends on independent drawers | Projection closes and the still-selected World object becomes visible in PEEK without a new complete-object request | Yes | ProjectionHost + Peek arbitration |
| Surface identity/route changes while an Ingest peek is open | Existing host cleanup is lease/state-specific | Ingest claims clean up on unmount/identity change; no stale Ingest peek leaks into Plan/Build/Play | Yes | Peek provider + existing owners |
| Narrow viewport | #699 fixed drawers use conservative viewport offsets | CENTER and active PEEK stack in normal layout flow; Nav stays visible; no horizontal overflow or viewport-cover drawer | Yes | AppChrome / CSS |
| Plan / Build / Play Tool/Projection behavior | Existing legacy fixed/drawer presentation | **Unchanged in UI-01** except any inert provider/slot DOM needed for shared composition | Yes | Compatibility regression |
| Ask DungeonBuddy unavailable sheet | #699 bottom sheet / chrome-band reservation | **Unchanged.** UI-01 neither fixes nor regresses it. | Yes | Regression only; Agent is not a UI-01 owner |

### Adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| C2S25 → Karsemine → Show all → Tools → Diagnostics → Close | Recap never remounts; relationship disclosure state and selected object survive; object returns; complete-object API request count remains one | Ingest integration + Peek arbitration + browser witness |
| Object open → Tools open → Tools close | Same object reappears immediately; no refetch/reset | Peek provider + Ingest integration |
| Object open → switch to Plan | Ingest claim disappears; Plan receives no stale object/tool peek and retains its legacy presentation | provider cleanup + compatibility test |
| Ingest Tools open → publication identity changes/empties | Existing ToolHost close behavior remains; stale Tools claim is removed | ToolHost regression |
| Ingest projection open → Escape/X | Existing ProjectionHost close semantics work; lower-priority object may reappear | ProjectionHost test + browser witness |
| Desktop witness → resize / load at ~390×844 | Peek stacks rather than covering/squeezing CENTER into an unusable strip; no nav coverage | manual browser witness |

A path that requires changing Agent semantics, World retrieval, durable source/object state, or Load semantics is outside this invariant and must stop/split.

---

## §4 Files in scope — write lease

Every expected change must stay inside this lease or the bounded discovery exception.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live-control-ui/src/surfaceInteraction/peekHost/PeekRegionProvider.tsx` | Layout-only transient Peek target + deterministic claim arbitration; no surface/domain authority |
| Create | `apps/live-control-ui/src/surfaceInteraction/peekHost/PeekRegionProvider.test.tsx` | Prove one-visible-claim, priority, lower-claim retention, cleanup, and remount behavior |
| Create | `apps/live-control-ui/src/surfaceInteraction/peekHost/index.ts` | Narrow exports for the shared layout primitive |
| Modify | `apps/live-control-ui/src/App.tsx` | Mount the Peek provider around AppChrome + existing app-level hosts; no routing/Agent/World semantic change |
| Modify | `apps/live-control-ui/src/chrome/AppChrome.tsx` | Compose CENTER + physical Peek slot as layout only; AppChrome does not become Tool/Projection/object semantic owner |
| Create or Modify | `apps/live-control-ui/src/chrome/AppChrome.test.tsx` | Prove empty Peek collapses and populated Peek composes beside CENTER without moving Nav ownership |
| Modify | `apps/live-control-ui/src/styles.css` | Shared CENTER/PEEK wide + narrow layout; Ingest peek styling; preserve legacy non-Ingest drawer rules and #699 Agent stabilization |
| Modify | `apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHost.tsx` | On active **Ingest** publication only, render existing Tools panel into shared Peek; preserve ToolHost state/focus/activation ownership and legacy presentation elsewhere |
| Modify | `apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHost.test.tsx` | Prove Ingest Peek adoption + existing identity/inventory/focus semantics + non-Ingest legacy behavior |
| Modify | `apps/live-control-ui/src/surfaceInteraction/projection/ProjectionHost.tsx` | Support an explicit Peek placement while retaining current controlled projection lifecycle; do not redefine projection semantics |
| Modify | `apps/live-control-ui/src/surfaceInteraction/projection/ProjectionHost.test.tsx` | Prove Peek placement has no modal backdrop/fixed takeover and legacy placement still works |
| Modify | `apps/live-control-ui/src/surfaceInteraction/projection/projectionHost.css` | Peek presentation styles alongside retained legacy overlay styles |
| Modify | `apps/live-control-ui/src/planSurface/projection/LegacyProjectionHostAdapter.tsx` | Select Peek placement only for the Ingest legacy policy; Plan/native Build remain current behavior |
| Modify | `apps/live-control-ui/src/planSurface/projection/LegacyProjectionHostAdapter.test.tsx` | Prove exact Ingest-vs-Plan/Build placement choice without changing projection resolution contracts |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.tsx` | Move existing complete-object panel into the shared Peek and add explicit close; retain exact complete-object request semantics |
| Create or Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.test.tsx` | Focused lower-priority object retention / no-refetch proof; create if clearer than growing the workbench integration file |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx` | Preserve exact C2S25 wrapper/integration behavior if the focused proof must traverse the workbench |
| Modify | `apps/live-control-ui/src/planSurface/planSurface.css` | Remove historical-Ingest local two-column/object-panel layout assumptions superseded by shared Peek; **do not touch Agent paint/behavior** |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Backward-looking sync: #698/#699/UI-series selection; UI-01 active, Stage 4 still NOT DONE |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Replace stale #697/Stage4A forcing-function text with truthful predecessor + UI-01 active slice; do not advance successor |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md` | Record accepted decomposition: Ingest-first, Agent dock split, UI-01 leased |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui01-ingest-shared-peek-v1.md` | Review evidence, exact head, findings/handback |

**Bounded discovery exception:**

```text
Directory:
  apps/live-control-ui/src/surfaceInteraction/peekHost/
  and test files adjacent to already-leased frontend components

Maximum additional paths: 2

Allowed path kinds:
  - one small layout-only helper required to keep Peek provider/portal code cohesive
  - one focused frontend test file required to prove the §1 invariant at the owning boundary

Decision rule:
  No SurfaceInteraction publication/type/schema changes.
  No server/API files.
  No Agent files.
  No new durable/browser persistence.
  No new surface adoption beyond Ingest.
```

A required path outside the lease/exception is a stop report. Do not edit first and rely on Git conflict review later.

---

## §5 Explicitly out of scope / collision boundary

| Path / capability | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/agentInteraction/**` | UI-02 / Stage 7 owns Agent dock/usefulness. #699 unavailable-sheet behavior remains baseline. |
| `apps/live-control-ui/src/surfaceInteraction/types.ts` and publication schemas | Peek is layout composition, not a new surface/domain publication contract. If schema change seems necessary, stop. |
| `apps/live-control-ui/src/graphLens/**` | Standing `?campaign=` generic-lens mismatch is a separate successor. |
| `apps/live-control-ui/src/modules/IngestionModule*` | Load-bar lock/Unload/paste-new-recap empty state is a separate Ingest workflow capability. |
| `apps/live-control-ui/src/playSurface/**` | Play is visual grammar north star, not UI-01 implementation consumer. Parchment/current-moment paint follows later. |
| `apps/live-control-ui/src/buildSurface/**` | No Build adoption in first proving slice. |
| `apps/live-control-ui/src/statblocks/**` | Threat/parchment presentation is unchanged. |
| `apps/live_control_server/**`, `src/application_state/**` | No server, durable source, APP-STATE, or runtime contract changes. |
| DungeonMind / World contracts | Read-only dogfood only; no graph truth/retrieval/write changes. |
| `dogfood/of-conks-*`, `evals/of_conks_end_to_end_dogfood/packet/**` | Evidence only. Do not merge/copy adventure bridges, packet product surfaces, or licensed fixtures. |
| Global removal of `--app-chrome-top` / `--app-chrome-bottom` | #699 offsets still protect legacy non-Ingest consumers and Agent. UI-01 removes **participating Ingest Peek content** from dependence on them; global demolition is a later shared-shell adoption. |
| Token-anchored hover glance | Independently useful interaction state; later UI slice. |
| 7A1 contextual Ask | Queued behind UI series; must not be dispatched/absorbed here. |

---

## §6 Implementation contract

### Layout/ownership contract

```text
Input:
  AppChrome current route/content
  existing SurfaceInteraction publication identity + surfaceId
  existing ToolHost open/close/activation state
  existing ProjectionHost active projection + close/expand callbacks
  existing Ingest activeNodeId / selectedRelationshipId / complete-object hook

Output:
  one physical Peek region composed by AppChrome
  layout-only Peek provider/portal/arbitration primitive
  Ingest ToolHost content rendered there while open
  Ingest ProjectionHost content rendered there while active
  Ingest complete World object rendered there while selected

Invariant:
  the exact loaded recap remains mounted as CENTER;
  exactly one highest-priority Ingest Peek is visible;
  lower-priority owner state is retained while hidden;
  Nav remains visible;
  non-Ingest presentation stays baseline.

Failure behavior:
  claim closes/unmounts → next eligible lower-priority claim becomes visible or Peek collapses
  Ingest surface unmount/identity replacement → Ingest claims clean up; no stale Peek
  object complete read loading/missing/error → object Peek remains the owner and shows the existing truthful state; do not silently fall back to a different object
  legacy non-Ingest host → retain current drawer/overlay path

Replay / idempotency:
  same open claim → no duplicate visible Peek and no CENTER remount
  changed object under world-object claim → owner updates its content using existing exact node identity
  higher-priority temporary claim opens/closes → lower claim survives without re-fetch/reinitialization when its owner remained mounted

Trust boundary:
  Verifies: transient UI claim ownership/priority + active Ingest surface placement
  Records/trusts without proving: existing World object correctness, Tool capability semantics, projection resolver semantics, recap source identity
```

### Peek claim contract

The exact API shape is implementation-owned, but the behavior must be equivalent to:

```text
claim kind        rank        semantic owner
---------------------------------------------
world-object      low         GraphReviewHistoricalRecapProjection
tools             medium      ToolHost
projection        high        ProjectionHost
```

Rules:

1. The Peek primitive owns **only layout target + visibility arbitration**.
2. Participant components remain mounted when hidden behind a higher-priority claim unless their existing owner semantics already close them.
3. The primitive does not copy participant state into a new store.
4. It does not persist claims.
5. It does not infer campaign/session/object identity.
6. Owner close handlers remain authoritative.
7. A route/surface unmount naturally removes its claims.
8. Do not use arbitrary z-index/viewport offsets to arbitrate claims.

### State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| Empty Peek | provider/slot mounted, no claim | CENTER takes available width | same | same | same | route cleanup | deterministic |
| World-object Peek | existing complete-object loading copy | existing #698 card | existing missing/error copy | existing truthful error | existing partial warning / error | owner/object change replaces exact content | higher-priority hide/show must not itself re-request |
| Tools Peek | current ToolHost inventory | existing enabled/disabled tool groups | zero tools → no claim | existing disabled reason | existing ToolHost behavior | identity change closes | reopen uses owner state |
| Projection Peek | existing projection resolution | existing body | existing unknown/unavailable copy | existing behavior | existing behavior | active projection/identity cleanup | close/open deterministic |
| Narrow layout | same data states | CENTER then PEEK in flow | same | same | same | same | resize does not mutate owner state |
| Non-Ingest | current baseline | current baseline | current baseline | current baseline | current baseline | current baseline | current baseline |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Peek claim identity | Stable **UI-local** claim key scoped to mounted owner; never a World/source identity | duplicate same-owner registration must settle deterministically or fail test; no two visible copies | No semantic fallback |
| World object | Existing exact `activeNodeId` remains owner identity; Peek never relabels/resolves it | existing complete-object behavior | No |
| Surface | Existing SurfaceInteraction identity/publication determines whether ToolHost is Ingest | stale/unmounted publication cleans claim | No guessed surface |
| Projection | Existing controlled `active` projection remains identity/lifecycle source | existing resolver unavailable state | No |

### Persistence / replay

**Not applicable — UI-01 introduces no durable or browser persistence.** Refresh/reload rebuilds transient Peek state from existing owners. World and APP-STATE remain read-only during dogfood.

### Predecessor → consumer mapping

**Grounding source:** PR #699 exact accepted head + current `main` component contracts.

| Predecessor field/outcome | Real shape/optionality | UI-01 consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| #699 `--app-chrome-*` stabilization | root CSS vars used by legacy fixed hosts | Ingest Peek participants stop relying on fixed drawer geometry; vars remain for untouched paths | layout region replaces Ingest overlay placement only | browser witness + CSS/component tests |
| ToolHost `isOpen` + identity cleanup | transient local owner state | content targets Peek only when active surface is Ingest | presentation only | ToolHost tests |
| ProjectionHost `active` / callbacks | controlled props | optional explicit Peek placement | presentation only | ProjectionHost + adapter tests |
| Historical recap `activeNodeId` | exact node selection | object body portals/renders in Peek; close clears local selection only | presentation only | Ingest focused test |
| #698 complete-object hook | one exact request per selected object; local relationship disclosure | hidden lower-priority object remains mounted/stateful | no payload change | API mock call-count + disclosure state regression |

---

## §7 Evidence required to merge

Every material invariant clause requires evidence at its owning boundary.

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Exactly one visible Peek; priority is projection > tools > object; lower claim survives | Peek provider | adversarial component test | focused `PeekRegionProvider.test.tsx` | deterministic arbitration; hidden participant not remounted merely by visibility change; cleanup exposes next claim | multiple visible peeks, lost lower state, unstable priority |
| Empty Peek does not reserve a second column; Nav remains outside CENTER/PEEK competition | AppChrome layout | component/regression | `AppChrome.test.tsx` or equivalent owning-boundary test | empty slot collapsed; populated slot composes; nav remains rendered once | permanent empty rail or nav enters peek/content layout incorrectly |
| Ingest Tools uses Peek but keeps existing identity/inventory/focus behavior | ToolHost | regression | `ToolHost.test.tsx` | Ingest panel targets Peek; identity/inventory close still pass; non-Ingest legacy assertions pass | behavior migration to other surfaces or focus regression |
| Ingest projection uses Peek; Plan/Build remain baseline | ProjectionHost + legacy adapter | regression | `ProjectionHost.test.tsx` + `LegacyProjectionHostAdapter.test.tsx` | explicit Ingest placement, no backdrop/fixed takeover in Peek mode; legacy placement unchanged | global ProjectionSize/placement change |
| Opened World object remains complete and stateful beneath temporary peeks | historical recap projection | integration/adversarial | focused historical projection/workbench test | object opens; Show all/local state can be set; higher claim hides it; after close object returns; complete-object request count remains **1** | second read caused solely by Tools/projection; recap remount; object selection cleared |
| Existing #698 compact/Advanced/relationship behavior survives | Ingest wrapper | regression | existing GraphReview workbench focused suite | current #698 assertions remain green | disclosure/provenance/partial-warning regression |
| Wide/narrow composition is actually usable | assembled product | **manual exact-head dogfood** | C2S25 scenario below at desktop and ~390×844 | no recap overlay/remount, nav visible, one Peek, no horizontal overflow, narrow stack works | visual overlap/squeeze/viewport takeover |
| #699 unavailable Ask behavior is not accidentally changed | assembled product / regression | smoke/manual or existing focused test if touched indirectly | Open/Close Ask on Ingest after C2S25 load | same #699 bottom-sheet behavior; UI-01 makes no Agent claim | Agent behavior changed without rebrief |
| Non-Ingest surfaces are not silently migrated | compatibility | focused tests | Plan/Build Tool/Projection tests | current legacy behavior still asserted | first slice expands to global adoption |
| State-authority docs tell the truth | roadmap/anchor/design handoff | review | inspect cumulative diff | #698/#699 + accepted Ingest-first decomposition recorded; UI-01 not pre-marked complete | successor/status overclaim |

### Exact verification commands

From `apps/live-control-ui`:

```bash
npx vitest run \
  src/surfaceInteraction/peekHost/PeekRegionProvider.test.tsx \
  src/chrome/AppChrome.test.tsx \
  src/surfaceInteraction/toolHost/ToolHost.test.tsx \
  src/surfaceInteraction/projection/ProjectionHost.test.tsx \
  src/planSurface/projection/LegacyProjectionHostAdapter.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx \
  --testTimeout 15000
```

If one of the two optional new test files is not created because equivalent owning-boundary evidence is placed in an already-leased test, adjust the command truthfully and explain the substitution in the handback.

Also run:

```bash
npm run build
```

Repository root:

```bash
git diff --check
git diff --name-only 514823701246879d88085857e5f23258fd0b763e...HEAD
```

### Minimal live / dogfood proof — REQUIRED

Use the exact implementation PR head, not `main` and not a retired worktree.

Runtime:

```text
UI          http://127.0.0.1:5173/
API         http://127.0.0.1:8000/health
World       54330 read-only
APP-STATE   54331 read-only
54329       DO NOT START
```

Canonical path:

```text
/ingest?campaign=longmont-c2&session=session-25
```

#### Desktop witness

1. Hard refresh the canonical path and load C2S25.
2. Note a recognizable reading position in the recap without pasting source prose into the handback.
3. Click **Karsemine**.
4. Confirm:
   - recap remains CENTER;
   - Karsemine is in the right PEEK;
   - Nav is fully visible;
   - no modal/backdrop covers the recap.
5. Exercise one local #698 state, preferably **Show all relationships**.
6. Open **Tools**.
   - Tools replaces the visible Peek content.
   - recap does not remount or jump.
7. Launch **Diagnostics** from Tools.
   - Projection occupies the same Peek.
   - no second drawer appears.
8. Close Diagnostics.
   - Karsemine returns in Peek.
   - prior local disclosure state remains when applicable.
9. Close Karsemine.
   - Peek collapses and CENTER uses the available width.
10. Record whether any complete-object reloading spinner/network-visible delay occurred solely because Tools/Diagnostics temporarily covered the object. It should not.

#### Narrow witness

Repeat the important path at approximately `390×844`:

```text
loaded recap → Karsemine → Tools → Diagnostics → Close
```

Required observation:

- Nav remains visible.
- CENTER remains readable.
- Active Peek enters normal stacked layout flow rather than a fixed viewport drawer.
- No horizontal overflow / unusable sliver.
- Closing Peek content restores the recap naturally.

#### Compatibility smoke

- Open Ingest Ask **Open/Close** once. It may still be the #699 bottom sheet; UI-01 must not redesign it.
- Run the focused Plan/Build Tool/Projection regressions. Manual Plan/Build restyling is **not** part of this proof.

### Baseline failure handling

The frontend production build has had an inherited baseline failure around `ThreatPublicationPanel.tsx` / `Cannot find namespace 'JSX'` in the recent Stage 4 lane. UI-01 does not own that failure.

If `npm run build` fails:

1. run the exact same command on base `514823701246879d88085857e5f23258fd0b763e`;
2. record base/head output and whether the failing blob/config is unchanged;
3. accept it as baseline debt only if head adds **no new build failure** and reviewer confirms the comparison;
4. otherwise stop — UI-01 does not get a blanket build waiver.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. §1 mission/invariant disposition;
3. §7 required vs produced evidence + provenance (author-local, independent rerun, CI, manual dogfood separately);
4. nano-commit/fix story;
5. base/head and actual changed paths vs §4;
6. build baseline comparison/waiver if applicable;
7. paths outside §4 (`none` or stop report);
8. exact desktop + narrow C2S25 dogfood observations;
9. whether Karsemine complete-object request count stayed one across temporary higher-priority peeks;
10. whether non-Ingest presentation behavior remained baseline;
11. named successor **UI-02 Agent dock / absence when unavailable** remains false;
12. 7A1 remains queued and undispatched;
13. prior finding ledger on re-review.

---

## §9 Acceptance rubric

### Implementation handback — ready for Review Cycle 1

- PR: `#700`; branch: `dogfood-continuity/ui01-ingest-shared-peek-v1`; implementation code head: `0ff26d4806519cf139af2b907996078e67d977e2`.
- Mission disposition: implemented one Ingest-only shared Peek layout region with deterministic `projection > tools > world-object` arbitration. Lower-priority claims remain mounted while hidden.
- Automated evidence (author-local): six focused files passed, 80 tests total. The owning Graph Review workbench regression proves the complete Karsemine sequence, retained 15-row disclosure state, and exactly one complete-object request; it was kept in the existing leased integration file rather than creating the optional focused wrapper file. Existing React `act(...)` and intentional error-path stderr remained warnings only.
- Production build (author-local): passed at the implementation code head. Vite emitted only its existing large-chunk advisory.
- Repository checks: actual changed paths are all inside §4; paths outside the write lease: `none`. `git diff --check` is clean after normalizing pre-existing handoff line endings.
- Nano/fix story: the first exact-head desktop witness exposed that the portaled Tools drawer no longer matched its former ancestor-qualified Peek selector and rendered beyond the viewport. Commit `0ff26d48` anchors the drawer through its actual `data-peek-claim="tools"` portal owner and adds a DOM-containment assertion. The witness was then repeated successfully.
- Desktop C2S25 dogfood: recap stayed mounted in CENTER; Karsemine occupied PEEK with no backdrop; Show all persisted as Show fewer; Tools replaced World; Diagnostics replaced Tools in the same region; closing Diagnostics restored Karsemine without a loading delay; Nav stayed visible; no horizontal overflow appeared.
- Narrow C2S25 dogfood at `390×844`: CENTER and PEEK stacked in normal flow (`position: static`, Peek below CENTER); the same World → Tools → Diagnostics → World sequence passed; Nav remained visible and there was no horizontal overflow.
- Complete-object request count: stayed at one in the owning integration regression. The browser witness showed no reload spinner or visible delay during arbitration.
- Compatibility: focused Tool/Projection tests preserve non-Ingest legacy placement; Plan/Build/Play were not migrated. Ingest Ask retained the #699 fixed bottom-sheet behavior and passed Open/Close smoke.
- Successors remain false: UI-02 Agent dock/absence is unimplemented; 7A1 remains queued and undispatched; Stage 4 remains not done.
- Review Cycle 1 has not yet occurred. No independent-review or CI provenance is claimed here.

- [x] One capability only: Ingest secondary context composes through one shared Peek while the loaded recap remains CENTER.
- [x] Peek is a real layout region, not another `position: fixed` drawer or z-index exception.
- [x] Exactly one Peek is visible; arbitration is deterministic (`projection > tools > world-object`).
- [x] Lower-priority object context survives temporary Tools/Projection visibility without a new complete-object read caused by Peek arbitration.
- [x] C2S25 recap remains mounted/preserved through the canonical adversarial path.
- [x] World object close is explicit and local; no recap navigation/remount occurs.
- [x] Nav is never covered.
- [x] Narrow viewport stacks CENTER/PEEK in usable normal flow.
- [x] ToolHost and ProjectionHost remain semantic/lifecycle owners; AppChrome/Peek own layout only.
- [x] SurfaceInteraction publication/types and server contracts are unchanged.
- [x] Plan / Build / Play are not silently migrated to Peek presentation.
- [x] #699 Agent behavior is not redesigned in this slice.
- [x] #698 object disclosure/provenance/partial behavior remains green.
- [x] State-authority sync is backward-looking and truthful; Stage 4 remains NOT DONE.
- [x] Actual changed paths stay inside §4 / bounded discovery.
- [x] Exact-head desktop + narrow browser witness passes.
- [x] Build/test provenance and any inherited baseline failure are recorded truthfully.
- [x] UI-02, Play parchment paint, Load-bar lock, generic-lens repair, token glance, Combat, and 7A1 remain unimplemented/unclaimed.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- Peek requires changing `SurfaceInteractionPublication`, `surfaceInteraction/types.ts`, or another public/durable contract;
- implementation requires moving Tool/Projection/Agent semantic ownership into AppChrome/Peek;
- preserving the recap requires changing APP-STATE, World, source/revision, or server APIs;
- a second independently useful capability appears (Agent dock, Load lock, hover glance, parchment paint, global surface migration);
- non-Ingest Tool/Projection presentation must change materially to make Ingest work;
- Ingest object selection cannot remain exact without changing World/generic-lens retrieval policy;
- a path outside §4 / bounded discovery is required;
- another lane begins touching a leased central file before this slice merges;
- exact-head dogfood still produces overlapping fixed UI and the only proposed fix is another offset/z-index exception;
- baseline/head build comparison shows a new UI-01 failure;
- owning-boundary tests cannot prove lower-priority state retention / no-refetch behavior.

Report:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```
