---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: UI language design series / DOGFOOD-CONTINUITY
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui02-agent-dock-presence-v1.md`
  - Branch: `dogfood-continuity/ui02-agent-dock-presence-v1`

  ## Verification pointer
  - Base: `5810a253239a53d731da831a9ac4ccd2548f10d9`
  - Changed paths: must remain inside HANDOFF §4 / bounded discovery
  - Verification: HANDOFF §7; exact-head Plan + unavailable-surface browser witness required

  Post-#700 dogfood was submitted to design and the product owner explicitly dispatched
  UI-02 unchanged. The checked-in handoff and exact-head evidence are the review contract.
---

# HANDOFF — DOGFOOD-CONTINUITY: UI-02 truthful Agent dock presence

**Created:** 2026-09-11
**Status:** ACTIVE — implementation complete; awaiting independent review
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui02-agent-dock-presence-v1.md`
**Conversation/workstream:** UI language design series / C1-C2 demo-readiness
**Flow / owner:** `DOGFOOD-CONTINUITY` / Agent Interaction chrome presentation
**Direction:** DESIGN → CODE → REVIEW
**Base revision:** `5810a253239a53d731da831a9ac4ccd2548f10d9` — PR #700 merge
**Design branch:** `dogfood-continuity/ui02-agent-dock-presence-v1`
**Suggested PR title if dispatched:** `DOGFOOD-CONTINUITY: make Agent presence cheap and truthful`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). UI language: [`Docs/Design/ui-language/DESIGN-interaction-layer-language.md`](../Design/ui-language/DESIGN-interaction-layer-language.md). Shell ownership: [`Docs/Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md).

## 0. Dispatch gate

PR #700 is merged at `5810a253239a53d731da831a9ac4ccd2548f10d9`. The product owner is dogfooding that change now.

This handoff is intentionally prepared **before** that dogfood finishes so implementation can start quickly if UI-02 survives the STOP. It is not permission to preempt the STOP.

Before coding, the steward must record one of:

```text
[x] DISPATCH UI-02 unchanged — product owner confirmed dogfood notes were submitted to design and explicitly authorized implementation on 2026-09-11
[ ] REBRIEF UI-02 from #700 dogfood findings
[ ] DEFER UI-02; different UI/product defect outranks it
```

If the operator reports a #700 regression, a more important composition defect, or a reason Agent presence should not be the next slice, **do not implement this handoff as written**.

---

## §1 Mission and merge-ready invariant

**Mission:** DungeonBuddy only advertises Agent interaction where a real Ask plugin is registered, and when Ask is real but collapsed it appears as cheap compact chrome rather than a persistent full-width bottom band.

**Merge-ready invariant:** **Visible Agent presence is derived only from the existing Ask-plugin registration contract. When no Ask plugin is registered, Agent chrome contributes no visible DOM, no focusable “Open” affordance, and no reserved bottom layout band. When a plugin is registered and the pane is closed, exactly one compact Agent dock is available without becoming a full-width rail. When the real Ask pane is opened, existing Plan Ask behavior, thread/context state, citations/trace behavior, and provider ownership remain unchanged. Hiding unavailable chrome must not mutate Agent thread or pane state merely to make the UI disappear.**

UI-02 changes **presence grammar**, not Agent capability.

```text
Ask unavailable
→ no Agent chrome
→ no disabled “Open Plan” bar
→ no empty Ask sheet
→ no bottom-space reservation

Ask available + closed
→ one small dock / pill
→ truthful surface + thread label
→ Open remains accessible

Ask available + open
→ existing Plan Ask behavior for this slice
```

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | **Yes.** The slice is strictly about whether Agent chrome exists and how much collapsed space it consumes. |
| Most likely adversarial sequence | Plan with a real thread → close Ask → navigate to Ingest/Build → Agent disappears and layout budget is released → navigate back to Plan → real Ask presence returns with thread/pane state preserved. |
| Will §7 detect that failure? | Yes. Agent chrome component tests own availability/continuity; chrome-band CSS regression owns layout reservation; exact-head browser witness proves the absence is physical, not only hidden text. |
| Easiest boundary to under-test | Global layout budget. Rendering `null` can look correct while `--app-chrome-bottom` / `.app-wrap` still reserve the old band. |
| Fact that forces stop/split | Need to add Ask on Ingest/Build/Play, move open Ask into Peek, change Agent provider/thread semantics, alter request/context schemas, or redesign Plan Ask internals. |

---

## §2 Context, authority, and lane

### Re-anchor truth

```text
main                         5810a253239a53d731da831a9ac4ccd2548f10d9
#700                         MERGED — UI-01 Ingest shared Peek
#700 accepted head           d6091ee9e053ab3c2eb889d77ad3ec432836e1f8
open implementation PRs      none at handoff creation
UI-01                        MERGED in #700; post-merge dogfood submitted
UI-02                        ACTIVE / DISPATCHED unchanged
7A1                          DESIGN READY / QUEUED; do not dispatch here
Stage 4                      NOT DONE
```

Current Agent truth on this base:

- `AgentInteractionChrome` always renders a bottom shell even when `askPluginPresent === false`.
- unavailable surfaces get a disabled-feeling bar that says Open Plan to enable Ask;
- clicking it opens an honest-but-useless empty sheet;
- `AskPluginSlot` already has the exact semantic signal UI-02 needs: `askPluginPresent`;
- Plan registers real Ask presence through `useRegisterAskPluginPresence(true)`;
- UI-02 does not need a new surface whitelist or route heuristic;
- #699 still leaves global bottom chrome reservation even when Ask is unavailable;
- UI-01 deliberately left Agent behavior untouched.

| Field | Required content |
|---|---|
| Parent authority | `DESIGN-interaction-layer-language.md` §0/§2/§6/§7; root UI Goal 8; UI-series handoff; #700 predecessor |
| Base revision | `5810a253239a53d731da831a9ac4ccd2548f10d9` |
| Predecessor contract | PR #700 shared Peek is merged and must remain unchanged by UI-02 except ordinary CSS compatibility |
| Exact input consumed | `AskPluginSlot.askPluginPresent`; `AgentInteractionProvider.paneState`, `activeThread`, `activeSurfaceContext`; existing Plan Ask registration |
| Named successor | **Useful Ask composition** (right Peek or center-mode decision) remains a later UI slice; 7A1 remains queued separately for contextual Ask on loaded Ingest recap |
| What remains false | Ask on Ingest/Build/Play; 7A1 context envelope; open Ask-as-Peek; chip glance; parchment paint; Load lock; generic-lens repair; Combat integration |
| Explicit non-goals | No new Agent capability; no Plan Ask model/retrieval changes; no thread schema/storage changes; no request/context contract changes; no World/APP-STATE writes; no new route heuristics |
| Branch / isolated checkout | if dispatched, implementation continues on `dogfood-continuity/ui02-agent-dock-presence-v1` or a fresh branch from the then-current main after re-anchor |
| Parallel lanes / collision hotspots | Agent chrome, `styles.css`, `planSurface.css`, and chrome-band tests are collision paths. 7A1 must remain inactive while UI-02 touches Agent/Ingest chrome seams. |
| Runtime/state ownership | frontend presentation only. Normal Plan/Ingest dogfood may read existing authorities; UI-02 performs no durable writes itself. |
| State-authority sync after implementation merge | backward-looking only: UI-series handoff, demo-ready roadmap, steward anchor, this handoff. Do not advance 7A1 or mark Stage 4 complete. |

If the post-#700 dogfood changes the forcing function, stop before opening an implementation PR.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owner |
|---|---|---|---:|---|
| Ingest with no Ask plugin | Persistent `Ask DungeonBuddy · Ingest` bottom bar; Open launches empty “Open Plan” sheet | No Agent shell/bar/button in rendered UI; no unavailable sheet path; no global Agent bottom reservation | Yes | AgentInteractionChrome + shell CSS |
| Build with no Ask plugin | Same disabled/persistent chrome pattern | Same absence rule as Ingest | Yes | AgentInteractionChrome |
| Play with no Ask plugin | If surface publishes context, global Agent shell still exists without useful Ask | No visible Agent chrome until a real Ask plugin exists | Yes | AgentInteractionChrome |
| No active surface / launcher | “Open Plan to enable graph-grounded ask” bar can still occupy bottom | No Agent chrome because no real Ask plugin is registered | Yes | AgentInteractionChrome |
| Plan with Ask plugin, pane closed | Full-width persistent bottom bar | Compact intrinsic-width dock/pill; truthful thread/surface context; one Open action | Yes | AgentInteractionChrome + CSS |
| Plan with Ask plugin, pane open | Existing Plan Ask host/pane | **Behavior unchanged in UI-02.** Existing plugin content, close, thread, citations, trace, query semantics continue | Yes | Regression only |
| Plan closed dock → Ingest → Plan | bar remains on Ingest today | Agent absent on Ingest; returns on Plan. Existing thread state survives navigation according to current provider semantics. | Yes | AskPluginSlot + AgentInteractionProvider regression |
| Plan pane open → navigate to unavailable surface → return | global pane/chrome can remain available-looking | Chrome is absent while plugin is absent; UI-02 does **not** forcibly destroy thread/pane state. On re-registration, current provider state is reflected truthfully. | Yes | AgentInteractionChrome regression |
| Narrow viewport | full-width bottom bar consumes significant viewport | compact dock remains usable and does not force a permanent bottom rail or horizontal overflow | Yes | CSS + browser witness |
| Graph glance placement | closed Agent shell is treated as a bottom obstacle | If dock exists, current obstacle logic remains valid enough; if Agent is absent, no phantom obstacle exists because no shell is rendered | Yes | compatibility regression |
| UI-01 Ingest Peek | Agent unavailable bottom bar/sheet coexists underneath | Peek behavior remains unchanged; absence of Agent releases space rather than changing Peek arbitration | Yes | UI-01 regression |

### Required adversarial sequences

| Sequence | Required safe outcome | Proof |
|---|---|---|
| Plan real Ask closed → Ingest | Agent DOM disappears; no focusable Open; center/peek gets normal bottom space | component + browser |
| Ingest → Plan | compact dock appears from real plugin registration; no route heuristic needed | component + browser |
| Plan with existing thread → Ingest → Plan | thread title/identity remains intact under existing provider semantics | component/integration |
| Plan Ask open → close → inspect collapsed state | compact dock appears; no stale full-width bar dimensions | browser |
| Ingest C2S25 object open → Tools → Diagnostics | UI-01 remains unchanged with no Agent band competing for bottom space | focused regression + smoke |
| 390×844 Plan dock → Ingest | Plan dock is compact; Ingest has no phantom blank bottom band; no horizontal overflow | manual exact-head |

A path that requires creating Ask capability on a new surface is **not** UI-02.

---

## §4 Files in scope — write lease

Expected implementation paths:

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.tsx` | derive visible chrome strictly from `askPluginPresent`; remove unavailable empty-bar/sheet presentation; keep real Ask host/pane behavior |
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.test.tsx` | replace old “honest empty Ask” expectations with absence + real-plugin dock/continuity tests |
| Modify | `apps/live-control-ui/src/styles.css` | remove default collapsed-Agent bottom reservation; preserve bottom inset only where a real **open** Ask pane genuinely needs it; ensure app-wrap does not reserve phantom space |
| Modify | `apps/live-control-ui/src/planSurface/planSurface.css` | style the available collapsed Agent as compact dock; delete/retire unavailable-open-sheet CSS that becomes unreachable; leave real open Plan Ask behavior unchanged |
| Modify | `apps/live-control-ui/src/chrome/chromeBand.test.ts` | retire #699 unavailable-Ask assertions and prove no default bottom Agent band while open real Ask can still reserve its existing space |
| Modify if needed for regression only | `apps/live-control-ui/src/graphReference/glancePlacement.test.ts` | update/strengthen absent-vs-available Agent obstacle characterization; no new placement algorithm |
| Modify if needed for regression only | `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.test.tsx` | prove registered Plan Ask still mounts/opens through existing plugin host; no behavior change |
| Modify after implementation review evidence | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui02-agent-dock-presence-v1.md` | exact head, evidence, findings |
| Modify after implementation only if steward dispatches | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md` | record UI-02 dispatch/result without preselecting later slice |
| Modify after implementation only if steward dispatches | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | backward-looking current-slice truth only |
| Modify after implementation only if steward dispatches | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | current forcing function / predecessor truth |

### Bounded discovery exception

```text
Directory:
  apps/live-control-ui/src/agentInteraction/
Maximum additional production paths:
  1
Allowed path kinds:
  an existing chrome/presence helper only
Decision rule:
  only if AgentInteractionChrome already delegates availability/presence there on the implementation base
```

A required change to `AgentInteractionProvider`, storage, API types, request builders, server routes, or surface publication contracts is a **stop report**, not discovery.

---

## §5 Explicitly out of scope / collision boundary

| Path / concern | Why UI-02 must not touch it |
|---|---|
| `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx` | provider/thread/pane semantics are predecessor authority; UI-02 is presentation-only |
| `apps/live-control-ui/src/agentInteraction/agentSurfaceContextRequest.ts` and request types | contextual Ask belongs to 7A1 / Agent capability, not dock presence |
| `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` production | real Plan Ask behavior is not being redesigned; test-only characterization is allowed |
| Ingest Agent implementation | 7A1 remains queued |
| `surfaceInteraction/types.ts` / publication contracts | no new bar ownership or public contract |
| World / generic-lens code | separate successor |
| UI-01 Peek provider / arbitration | merged predecessor; no Agent claim is added to Peek in UI-02 |
| Of Conks parchment / Play Scene styling | later paint slice |
| Load/Unload lock semantics | separate capability |
| Combat | separate Play integration |

Do not create a new `surfaceId === "plan"` visibility rule. **Real Ask registration is the capability signal.**

---

## §6 Implementation contract

```text
Input:
  askPluginPresent: boolean from AskPluginSlot
  paneState.isOpen from AgentInteractionProvider
  activeThread / activeSurfaceContext from existing provider

Output:
  askPluginPresent = false
    → no visible AgentInteractionChrome DOM
    → no focusable Open action
    → no Agent-specific bottom layout reservation

  askPluginPresent = true, pane closed
    → exactly one compact Agent dock
    → truthful surface/thread copy
    → Open action

  askPluginPresent = true, pane open
    → existing Ask host/pane semantics

Invariant:
  visibility follows registered capability, not surface/URL inference;
  presentation changes do not mutate thread/request/persistence semantics.

Failure behavior:
  plugin unregisters
    → chrome becomes absent
    → provider state is not rewritten solely for presentation

  plugin re-registers
    → chrome reflects current provider state

Replay / navigation:
  same plugin registration → deterministic presence
  navigation to surface with no plugin → absence
  navigation back → current real plugin presence restored

Trust boundary:
  UI-02 trusts AskPluginSlot registration as the statement “Ask exists here.”
  UI-02 does not independently prove campaign context, World health, or model readiness.
```

### Availability / state matrix

| Ask plugin | Pane state | Required chrome | Layout reservation | Capability change? |
|---|---|---|---|---|
| absent | closed | none | none beyond ordinary page padding | No |
| absent | open in provider state | none while unavailable | none | No; do not forcibly reset state |
| present | closed | compact dock | no full-width bottom band | No |
| present | open | existing real Ask pane | existing open-pane space contract may remain | No |

### Important CSS rule

The implementation must not “hide” unavailable Agent while leaving #699’s layout tax behind.

At minimum, the resulting CSS semantics must be equivalent to:

```text
default / unavailable:
  --app-chrome-bottom = no Agent reservation

real Ask open:
  --app-chrome-bottom = existing open Ask requirement

real Ask collapsed:
  compact localized dock; not a page-wide reserved band
```

Do not replace `4.75rem` with another guessed collapsed-dock height in `--app-chrome-bottom`.

---

## §7 Evidence required to merge

| Guarantee | Owner | Evidence | Required proof | Stop condition |
|---|---|---|---|---|
| unavailable Ask renders no Agent chrome | AgentInteractionChrome | component | Build/Ingest/no-plugin harness: no chrome, no Open button, no Plan-link empty pane | disabled chrome remains reachable |
| availability is registration-driven | AgentInteractionChrome / AskPluginSlot | component | same surface context with and without registered plugin changes presence solely by plugin registration | URL/surface whitelist introduced |
| real Plan Ask still opens | Agent chrome + Plan plugin | regression | registered plugin → compact dock → Open → plugin host/pane renders → Close works | Plan Ask behavior broken |
| thread/context continuity survives unavailable navigation | provider/chrome integration | adversarial component/integration | real thread → unregister plugin → register again → same thread label/provider state | UI-02 clears semantic state |
| no phantom bottom band | global shell CSS | structural + browser | default `--app-chrome-bottom` no longer reserves collapsed/unavailable Agent space; Ingest content physically reaches normal bottom padding | invisible 4.75/6.5rem gap remains |
| collapsed available Agent is cheap | Agent chrome CSS | browser | intrinsic/compact width at desktop; not full-width; one Open action | full-width rail remains |
| narrow layout remains usable | assembled UI | manual | 390×844 Plan dock + Ingest absence; no horizontal overflow; content not squeezed by reserved band | mobile rail/blank band |
| UI-01 remains intact | Ingest | regression/manual | C2S25 recap → object → Tools → Diagnostics → object; no Agent band competes underneath | Peek regression |
| glance has no phantom obstacle when Agent absent | graph glance | focused regression/manual if relevant | absent Agent shell yields no bottom obstacle; available dock remains detectable enough | invisible shell still affects placement |
| successors remain false | review | diff inspection | no 7A1, no Ask-on-Ingest, no open-Ask Peek migration | scope expansion |

### Exact automated verification

From `apps/live-control-ui`:

```bash
npx vitest run \
  src/agentInteraction/AgentInteractionChrome.test.tsx \
  src/chrome/chromeBand.test.ts \
  src/graphReference/glancePlacement.test.ts \
  src/planSurface/components/PlanAgentInteractionBar.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx \
  --testTimeout 15000

npm run build
```

If a listed regression file is not touched and is demonstrably unrelated on the dispatch base, the implementation handback may adjust the command, but it must explain the substitution. Do not drop the Ingest UI-01 regression entirely.

Repository root:

```bash
git diff --check
git diff --name-only <dispatch-base>...HEAD
```

### Minimal exact-head browser witness — REQUIRED

Use the exact implementation PR head.

#### A. Ingest — unavailable means absent

Open:

```text
/ingest?campaign=longmont-c2&session=session-25
```

1. Load C2S25.
2. Confirm no persistent Agent bar/dock is visible because no Ingest Ask plugin exists yet.
3. Confirm there is no “Open Plan to enable Ask” action or unavailable empty sheet path.
4. Confirm the page does not retain a suspicious blank bottom band where the old collapsed Agent bar lived.
5. Open Karsemine → Tools → Diagnostics → Close.
6. Confirm UI-01 behaves as before and the released Agent band does not create new overlap.

#### B. Plan — useful Ask gets a compact dock

Open a Plan state where the existing Ask plugin is genuinely registered.

1. With Ask closed, confirm one compact Agent dock/pill is visible.
2. It must be materially narrower/cheaper than the old page-wide bar at desktop.
3. Confirm truthful thread/surface labeling remains.
4. Open Ask.
5. Exercise an existing non-destructive Ask interaction far enough to prove the real Plan plugin is mounted; UI-02 does not need new answer-quality evidence.
6. Close Ask; compact dock returns.

#### C. Navigation continuity

```text
Plan (dock visible)
→ Ingest (Agent absent)
→ Plan (dock returns)
```

If an existing thread exists, verify the thread label is not silently reset by the hide/show cycle.

#### D. Narrow viewport

At approximately `390×844`:

- Plan: compact dock is usable and does not become a wide reserved rail.
- Ingest: Agent is absent and no phantom bottom gap remains.
- no horizontal overflow.
- Nav remains usable.

### Baseline failure handling

UI-02 owns frontend presentation only. If the production build fails, compare the same command on the exact dispatch base. No blanket baseline waiver.

---

## §8 Required review handback

Record:

1. Review Cycle number and exact PR/head;
2. post-#700 dogfood dispatch disposition that authorized UI-02;
3. §1 invariant disposition;
4. exact availability behavior on Ingest/Build/Play/no-surface vs Plan;
5. whether `--app-chrome-bottom` still reserves unavailable/collapsed Agent space;
6. thread/pane continuity behavior across plugin unregister/re-register;
7. Plan real Ask regression evidence;
8. UI-01 C2S25 regression evidence;
9. desktop + 390×844 browser observations;
10. actual paths vs §4;
11. build/test provenance;
12. successor ledger: useful-open-Ask composition false, 7A1 false, parchment false, Load lock false;
13. prior review findings on re-review.

---

## §9 Acceptance rubric

### Implementation handback — ready for Review Cycle 1

- Authorization: after #700 dogfood notes were submitted to design, the product owner explicitly said “Proceed and implement”; UI-02 was dispatched unchanged.
- Implementation code head: `9c158c8852daa5575666c14388fbc482409eb70c`; branch `dogfood-continuity/ui02-agent-dock-presence-v1`.
- Invariant disposition: `AgentInteractionChrome` returns no DOM unless `askPluginPresent` is true. A registered closed Ask renders one compact fixed dock; opening it retains the existing full Plan Ask host/pane. No route or surface whitelist was added.
- State continuity: the focused component regression opens the pane, unregisters the plugin, confirms chrome absence, re-registers it, and confirms the provider-owned open state returns unchanged.
- Layout contract: default and narrow `--app-chrome-bottom` are `0rem`; only `.plan-agent-shell.open` activates `--app-ask-open-height`. The retired unavailable sheet CSS was deleted. Ordinary `.app-wrap` bottom padding computes to 16px on Ingest.
- Author-local automated evidence: the exact §7 five-file command passed, 47 tests total. Production build passed with only the existing Vite large-chunk advisory.
- Desktop browser evidence on the code head: Ingest had no Agent chrome, no Open action, `--app-chrome-bottom: 0rem`, 16px content bottom padding, visible Nav, and no horizontal overflow. UI-01 Karsemine → Tools → Diagnostics → Karsemine remained intact. Plan’s closed dock measured 448px in a 1280px viewport (35% width), exposed one Open action and truthful Plan/thread context; open Ask mounted the real Plan pane with Question and Close controls, then returned to the compact dock.
- Navigation browser evidence: Plan → Ingest → Plan removed and restored chrome solely with plugin registration; the dock label remained identical across the round trip.
- Narrow browser evidence at `390×844`: Plan dock measured 358px without horizontal overflow; Ingest had no Agent DOM, zero bottom reservation, 16px ordinary padding, visible Nav, and no horizontal overflow.
- Actual production/test paths are exactly the five expected §4 paths. State-authority sync is backward-looking for #700 and marks UI-02 active, never complete.
- Successors remain false: useful open-Ask composition/UI-03, Ask-on-Ingest/7A1, parchment paint, Load lock, generic-lens repair, and Combat are unimplemented/unclaimed.
- Review Cycle 1 has not occurred; no independent-review or CI provenance is claimed.

- [x] Post-#700 dogfood explicitly dispatches UI-02; handoff was not implemented speculatively.
- [x] No Ask plugin → no Agent chrome DOM and no focusable Open action.
- [x] No Ask plugin → no Agent-specific persistent bottom-space reservation.
- [x] Real Ask plugin + closed → compact dock, not full-width bar.
- [x] Real Ask plugin + open → existing Plan Ask behavior remains intact.
- [x] Visibility is driven by Ask-plugin registration, not route/surface heuristics.
- [x] UI-02 does not clear or rewrite Agent semantic state merely because capability is temporarily unavailable.
- [x] Ingest/Build/Play do not gain Ask capability.
- [x] UI-01 Peek remains intact.
- [x] Narrow viewport has no phantom bottom band or horizontal overflow.
- [x] No new public/durable/API contract.
- [x] Actual changes remain inside §4 / bounded discovery.
- [x] UI-03/open-Ask composition, 7A1, parchment paint, Load lock, generic-lens, Combat remain unimplemented/unclaimed.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- #700 dogfood changes the next-product priority;
- removing unavailable chrome requires changing Agent provider/thread/storage semantics;
- implementation needs a route/surface whitelist instead of AskPluginSlot registration;
- worker starts adding Ask capability to Ingest/Build/Play;
- worker moves useful open Ask into Peek/center mode in this PR;
- worker changes model/retrieval/context request behavior;
- compact dock can only be made safe by restoring a full-width reserved band or adding another guessed global offset;
- UI-01 Peek regresses and repair requires changing its arbitration contract;
- required production path falls outside §4/bounded discovery;
- baseline/head build comparison shows a new UI-02 failure.

Report:

```text
Stop condition:
Invariant clause affected:
Why UI-02 cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Recommended rebrief / successor:
State-authority update needed:
```
