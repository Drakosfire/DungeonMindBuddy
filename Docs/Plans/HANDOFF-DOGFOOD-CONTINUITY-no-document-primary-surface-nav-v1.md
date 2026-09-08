---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / post-STOP-2 shell repair
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW → MERGE → HUMAN DOGFOOD
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-no-document-primary-surface-nav-v1.md`
  - Branch / PR: `dogfood-continuity/no-document-primary-surface-nav-v1` / `DOGFOOD-CONTINUITY: navigate primary surfaces without document reload`

  ## Verification pointer
  - Base: `73cc35abe65eb0584b765bf6e6c553684d64401e`
  - Predecessor: PR #693 merged; STOP 2 durability witness held while assembled-product UX failed
  - Verification: §7 browser navigation/history contract + UI regression suite/build + human dogfood after merge

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and browser witness are the review contract. This body is
  transport metadata only.
---

# HANDOFF — DOGFOOD-CONTINUITY: no-document primary-surface navigation v1

**Created:** 2026-09-08  
**Status:** READY TO DISPATCH — one implementation capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-no-document-primary-surface-nav-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / post-STOP-2 assembled-product repair`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW → MERGE → HUMAN DOGFOOD  
**Base revision:** `73cc35abe65eb0584b765bf6e6c553684d64401e` — `main` after merged PR #693  
**Implementation branch:** `dogfood-continuity/no-document-primary-surface-nav-v1`  
**PR title:** `DOGFOOD-CONTINUITY: navigate primary surfaces without document reload`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

---

## §0 Accepted STOP 2 design ruling

This handoff consumes an operator-accepted design decision from STOP 2 dogfood.
The design input itself was supplied out-of-band and is not required as an
implementation authority; the accepted conclusions are encoded here.

Current exact repository truth:

```text
main                           73cc35abe65eb0584b765bf6e6c553684d64401e
PR #693                        MERGED
Stage 2B implementation        MERGED — exact bounded C1/C2 repopulation on 54331
Stage 2 / STOP 2               OPEN
C2 Session 25 reboot witness   PASS — exact source remained readable
World join                     PASS when durable 54330 was running
assembled product              FAIL — flash/reload feeling remains
open implementation PRs        none at design time
```

STOP 2 changed the roadmap ordering. The accepted direction is:

```text
Stage 3                 reconnaissance/verification first; no World-contract CODE
                        unless a healthy 54330 reproduces a contract failure

Stage 5A                THIS SLICE — no-document primary-surface navigation

HUMAN DOGFOOD           mandatory; measure which flash/reboot symptoms remain

Stage 5B                persistent AppChrome ownership/remount repair only if the
                        post-Stage-5A witness still proves it is needed

Stage 2C                additional exact historical source adoption after the
                        operator separately accepts unknown-revision-UUID semantics

Stage 4                 rich graph objects / Threat presentation + recap-local
                        session navigation on top of the accepted URL/history contract

Stage 7A                useful Agent-on-Ingest recap selection/highlight

Stage 6                 real cross-surface material + write/save/reopen

Stage 7B                full cross-surface Agent context + observability
```

This PR implements only Stage 5A. It does not close Stage 5, Stage 2, STOP 2,
or any later stage.

### §0A Backward-looking predecessor sync

The implementation PR must truthfully record facts already true before this
slice begins:

```text
PR #693                        DONE / MERGED
merge                          73cc35abe65eb0584b765bf6e6c553684d64401e
Stage 2B implementation        merged; human STOP remains open
Stage 2 / STOP 2               OPEN
STOP 2 design                  accepted — Stage 5A moves ahead of Stage 4
current implementation slice   Stage 5A no-document primary-surface navigation
```

Sync these mutable authorities inside the implementation PR:

```text
Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2b-c1-c2-repopulation-v2.md
```

The predecessor handoff may be updated only to say the implementation merged and
that Stage 2 / STOP 2 remain open. Do not mark Stage 2B as an accepted completed
stage from this PR. Do not pre-mark this Stage 5A slice DONE.

---

## §1 Mission and merge-ready invariant

**Mission:** A user can move among Index, Plan, Play, Ingest, and Build through
normal product navigation without loading a new browser document, so the shared
application providers are not destroyed merely because the primary surface
changes.

**Merge-ready invariant:**

> A normal unmodified primary navigation click among `/`, `/plan`, `/play`,
> `/ingest`, and `/build` updates browser history and the rendered route inside
> the current document; browser back/forward replays that route state; direct
> hard reload at each URL still boots the correct surface; the top-level Agent
> and World provider roots are not replaced by primary route navigation; native
> link behavior remains available for modified/new-tab navigation; `/combat`
> remains a normal document navigation target; and existing Play query-string
> history such as `/play?run=<id>` continues to work without being rewritten or
> discarded by the application router.

This is intentionally narrower than full DFC-NAV1. It removes the guaranteed
full-document reload from primary product navigation. It does **not** promise
that every `AppChrome` instance remains mounted or that every post-load visual
flash is solved.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. All changed behavior is browser URL/history → route rendering while preserving one document and the existing provider root. |
| Most likely adversarial sequence | User is on a real Play run with `?run=…` → uses primary nav → browser back → returns to `/play?run=…` → route renders Play without losing the query or forcing a new document. |
| Will §7 detect that failure? | Yes. Route/history integration tests plus a browser same-document witness and an explicit Play query regression are required. |
| Easiest owning boundary to under-test | Native anchor semantics. A helper-only test can pass while Ctrl/Cmd-click, new-tab, Combat, back/forward, or hard reload behavior regresses. |
| Fact that forces stop/split | If same-document routing requires moving/re-owning Agent or World providers, redesigning surface state persistence, changing backend routing, or absorbing AppChrome remount repair. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `ROADMAP-demo-ready-c1-c2-to-of-conks.md` Stage 5 + accepted STOP 2 reorder in §0 |
| Base revision | `73cc35abe65eb0584b765bf6e6c553684d64401e` |
| Predecessor contract | PR #693 merged; durable APP-STATE/World join exists; assembled-product shell still performs document navigation |
| Exact input consumed | `APP_NAV_ITEMS`, `window.location.pathname/search`, existing `App()` route switch, existing Play History API behavior |
| Named successor | `Stage 5B — persistent AppChrome ownership / remaining post-load remount repair` if dogfood still demonstrates it |
| What remains false | Stage 5/STOP 5; AppChrome never-remount; session-selection persistence rules; rich node cards; Agent Ask on Ingest; Stage 2/STOP 2; auto-start of 54331/54330 |
| Explicit non-goals | See §5; especially no Agent provider ownership, no World provider ownership, no backend/API/state changes |
| Branch / isolated checkout | `dogfood-continuity/no-document-primary-surface-nav-v1` + isolated worktree/equivalent |
| Parallel lanes / collision hotspots | No open PR at design time. `App.tsx`, `AppChrome.tsx`, route/history, and active roadmap/anchor are exclusive to this lane while active. Do not run a simultaneous Agent-provider/navigation-shell lane. |
| Runtime/state ownership | Browser URL/history is writable by this lane. `54331` and `54330` are read-only normal product dependencies for manual dogfood; `54329` untouched/off. |
| State-authority sync set | Roadmap + steward anchor + predecessor Stage 2B handoff, as §0A |

### Existing implementation seam

At the base revision:

```text
AppChrome primary nav
  APP_NAV_ITEMS
  → <a href="/plan"> / <a href="/play"> / <a href="/ingest"> / <a href="/build">
  → browser document navigation

App
  currentRoute()
  → reads window.location.pathname once per render
  → route content chosen below the shared Agent / World providers

Play
  already uses window.history.pushState / replaceState
  + PopStateEvent for ?run= / ?choose= routing
```

The top-level provider placement is already favorable:

```text
AgentInteractionProvider
  AskPluginSlotProvider
    WorldGraphLensProvider
      WorldGraphLensProjectionProvider
        SurfaceContextProvider
          routed content
          ToolHost
          LegacyProjectionHostAdapter
          AgentInteractionChrome
```

The slice should make location/history reactive **without moving that ownership**.

### Primary vs non-primary routes

For this slice the in-document primary route set is exactly:

```text
/
/plan
/play
/ingest
/build
```

`/combat` remains a real document link to the mature Combat product surface.
`/surface` and `/tiptap-callout-spike` remain directly URL-reachable but are not
required to become primary in-document navigation targets in this slice.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| AppChrome Plan/Play/Ingest/Build/Index click | Native `<a href>` loads a new document | Unmodified same-tab click pushes/replaces application history as appropriate and renders target route in the same document | Yes | AppChrome + browser-history adapter + App route subscription |
| Index launcher → Plan/Play/Ingest/Build | Native document navigation | Same-document primary navigation | Yes | `App.tsx` launcher + navigation adapter |
| Browser Back/Forward | New documents/history entries from native navigation | Popstate updates rendered primary route without new document | Yes | App route subscription |
| Direct hard reload `/plan`, `/play`, `/ingest`, `/build` | Boots route from pathname | Still boots exact route directly | Yes | App route resolver + dev/prod server fallback contract already in product |
| Ctrl/Cmd/Shift/Alt-click or non-primary mouse button | Native browser behavior | Remains native; application must not hijack | Yes | navigation click filter |
| Combat Tracker link | Native document navigation | Remains native document navigation | Yes | AppChrome / launcher link classification |
| Active primary link clicked again | Reloads document today | Prefer truthful no-op rather than duplicate same-location history; must not reload document | Yes | navigation adapter |
| `/play?run=<id>` internal Play navigation | Play pushes/replaces history and emits popstate | Existing behavior remains; App may re-evaluate location but must keep the Play route/query semantics intact | Yes | App route subscription + Play regression |
| Browser back to `/play?run=<id>` after visiting another surface | Browser restores prior document today | Same document returns to Play and the run query remains available to Play | Yes | App + Play integration |
| Unknown/non-primary URL | Existing route fallback behavior | Preserve existing behavior; do not invent a new 404/router contract | Yes | App route resolver |

### Adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| `/ingest` → click Plan → click Build → browser Back → browser Back | URL and rendered route traverse Build → Plan → Ingest with one document and no provider-root replacement | route integration test + browser witness |
| `/play?run=<real-id>` → Ingest → Back | Back returns to `/play?run=<real-id>`; Play sees the same query; no full document load | Play-history regression + browser witness |
| Ctrl/Cmd-click Ingest from Plan | Browser retains native new-tab/open behavior; current document is not programmatically rerouted | click-filter test |
| Click Combat from any primary surface | Browser follows native `/combat` document navigation; React router helper does not intercept | AppChrome/launcher test |
| Hard reload while URL is `/build` | New document boots Build directly; same-document mechanism is not required across an intentional hard reload | browser smoke + existing App route test |
| Click already-active `/ingest` link | No duplicate history entry and no document reload | navigation adapter test |
| Rapid Plan → Ingest → Build clicks | Latest browser history state and rendered route remain consistent; no stale async router state is introduced | route integration test |

---

## §4 Files in scope — write lease

Expected cumulative changed paths:

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-no-document-primary-surface-nav-v1.md` | Slice authority |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Backward-sync #693 + record accepted STOP 2 reorder + Stage 5A CURRENT without closing Stage 2/STOP 2 |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Re-anchor to #693 merge and this accepted current slice |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2b-c1-c2-repopulation-v2.md` | Backward-looking predecessor status only: implementation merged, human STOP remains open |
| Create | `apps/live-control-ui/src/chrome/appNavigation.ts` | Own primary-route recognition, browser-location subscription/snapshot, same-document navigation, and safe click-interception rules |
| Modify | `apps/live-control-ui/src/App.tsx` | Make route selection reactive to browser history and use same-document navigation from the Index launcher for primary surfaces |
| Modify | `apps/live-control-ui/src/chrome/AppChrome.tsx` | Preserve real anchors while intercepting only eligible primary same-tab clicks |
| Create | `apps/live-control-ui/src/test/appNavigation.test.tsx` | Owning regression coverage for same-document route/history/native-link behavior |

**Bounded discovery exception:**

```text
Directory: apps/live-control-ui/src/test/
Maximum additional paths: 2
Allowed path kinds: existing App/AppChrome/Play route-history tests only
Decision rule: modify an existing test only when it is the owning regression
boundary for §3 and avoids duplicating the same browser contract in the new test.
```

A required production path outside this lease is a stop report. In particular,
`appChromeConfig.ts` should remain unchanged unless the current `APP_NAV_ITEMS`
shape proves insufficient to classify primary vs Combat links. If it is needed,
stop and explain why the existing `route?: AppRouteKey` distinction cannot serve
the invariant before editing it.

---

## §5 Explicitly out of scope / collision boundary

| Path / capability | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/agentInteraction/**` | Agent-on-Ingest and provider ownership are separate Stage 7A/7B contracts; navigation-shell + Agent ownership is an unsafe pairing |
| `apps/live-control-ui/src/graphLens/**` | World provider/query ownership must remain unchanged; Stage 3 is reconnaissance unless a healthy authority reproduces a contract failure |
| `apps/live-control-ui/src/ingestSurface/**` | Do not repair recap loading, Agent Ask, session navigation, or thin nodes while changing app navigation |
| `apps/live-control-ui/src/planSurface/**` | Do not absorb Plan Agent/edit state retention into this slice |
| `apps/live-control-ui/src/buildSurface/**` | Build persistence/editor state is Stage 6 / later continuity work |
| `apps/live-control-ui/src/playSurface/**` | Existing Play History API behavior is a protected consumer; change only if a concrete regression proves the App seam cannot preserve it, then stop/rebrief |
| `src/application_state/**` | No APP-STATE schema/persistence change |
| `apps/live_control_server/**` | No backend/router/API work expected |
| DungeonMind repository / graph writes | Buddy remains query-only; World head must not move |
| `compose*.yml`, runbooks, Docker restart policy | Authority auto-start after reboot is a separate ops capability |
| Rich object-card/provenance/Threat UI | Stage 4 / graph-object usefulness successor |
| Additional historical recap source adoption | Stage 2C successor; missing Session 10 is not repaired here |
| AppChrome persistent ownership/remount elimination | Named Stage 5B successor; only same-document routing is delivered here |
| Generic router dependency addition | Do not add React Router or another routing framework merely to solve this bounded contract unless the current seam is proven insufficient and steward rebriefs |

### Forbidden repairs

- no re-ingest of C1/C2;
- no silent lifecycle upgrade to `reviewable`;
- no Buddy graph writes or World-head advancement;
- no `down -v` / volume destruction against live `54331`;
- no treating shared Agent chrome as proof of Agent capability;
- no full Stage 5 refactor hidden behind a navigation helper;
- no replacing real anchors with inaccessible `<button>` navigation.

---

## §6 Implementation contract

```text
Input:
  APP_NAV_ITEMS primary routes
  current browser location (pathname + search + hash as applicable)
  native anchor click event
  browser popstate events

Output:
  reactive App route selection
  same-document history transitions for eligible primary navigation
  preserved native anchors / hrefs

Invariant:
  same as §1

Failure behavior:
  non-primary or modified/native link gesture
    → do not intercept; browser owns navigation

  same primary location
    → no document reload; no duplicate history entry

  browser back/forward
    → render route implied by browser location

  hard reload/direct URL
    → initial route resolves from current browser location

Replay / idempotency:
  same primary navigation target while already there
    → stable no-op

  repeated popstate for unchanged location
    → no semantic route change

  Play pushState/replaceState + popstate
    → App observes location without stripping query state

Trust boundary:
  Verifies:
    eligible click gesture
    primary in-app href classification
    browser location snapshot

  Records/trusts without proving:
    surface-internal async load state
    campaign/session selection retention
    provider-internal data freshness
```

### Navigation click contract

Only intercept when all are true:

```text
- event was not already prevented
- ordinary primary-button same-tab activation
- no Meta / Ctrl / Shift / Alt modifier requesting native behavior
- target href belongs to the primary in-app route set
- link does not explicitly request another target/download behavior
```

Preserve an actual `href` on product links. Copy-link, open-in-new-tab, browser
status text, keyboard activation, and intentional hard navigation must remain
meaningful.

### Browser location contract

A small app-owned adapter may use the existing project pattern:

```text
window.history.pushState / replaceState
window.addEventListener("popstate", ...)
window.dispatchEvent(new PopStateEvent("popstate"))
```

or an equivalent narrowly owned event contract. Do not create two competing
location authorities. `window.location` remains source-of-truth; React observes
it.

If `useSyncExternalStore` is used, the snapshot must be a stable primitive such
as `pathname + search + hash`, not a freshly allocated object that rerenders
forever.

### Route identity / query matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| `/`, `/plan`, `/play`, `/ingest`, `/build` | Recognize exact pathname as primary App route | None | No alternate title-based lookup |
| `/play?run=<id>` | Route identity is Play; query remains owned by Play | Preserve exact search string | No query stripping |
| `/combat` | Not primary React navigation for this slice | Native browser navigation | Yes — browser owns it |
| `/surface`, `/tiptap-callout-spike` | Preserve current direct-route handling | Do not promote to main nav | Existing behavior only |
| Unknown pathname | Preserve base behavior | Do not invent new router/404 semantics | Existing fallback only |

### Persistence / replay matrix

Not applicable to server data. Browser history is transient application state,
not a new durable product authority.

| Operation | Representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback/reversion |
|---|---|---|---|---|---|
| primary route push | browser History entry + URL | Back/forward returns same pathname/search | same-target click is no-op | direct URL reload remains valid | removing interception restores old native document navigation |
| Play run query push/replace | existing Play History behavior | existing Play back/forward semantics remain | existing contract | must not be rewritten by new app adapter | unchanged Play code preferred |

---

## §7 Evidence required to merge

Every material invariant clause needs owning-boundary proof.

| Guarantee / invariant clause | Owning boundary | Evidence class | Command / scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Primary AppChrome click changes URL/route without native document navigation | AppChrome + navigation adapter + App | integration regression | new `appNavigation.test.tsx` | click keeps anchor semantics, invokes history path, and rendered route/location changes | test can only prove helper in isolation |
| Index launcher primary cards use same contract | `App.tsx` | integration regression | same focused test | Plan/Play/Ingest/Build launcher links are same-document eligible; Combat is not | launcher still causes native document load |
| Modified click/native behavior is preserved | click filter | adversarial regression | focused test | Meta/Ctrl/Shift/Alt/non-primary/target/download cases are not intercepted | app hijacks native browser intent |
| Back/forward updates App route | App location subscription | route regression | focused test using push/popstate/back-forward equivalent | rendered route follows browser location | URL changes but App content stays stale |
| Hard reload/direct URL contract remains | App initial route resolver | regression/manual | focused test + live browser hard reload | direct `/plan`,`/play`,`/ingest`,`/build` each boot correct surface | any direct route needs manual redirect or launcher |
| Shared provider roots survive primary route navigation | browser document boundary | manual owning witness + optional component sentinel test | §7A | same `window` witness remains across primary nav; provider root is not recreated by document load | witness resets on normal primary click |
| Combat remains document navigation | AppChrome + launcher | regression/manual | focused test + live click | helper does not intercept `/combat` | Combat becomes trapped in React route fallback |
| Existing Play `?run=` history survives | App + Play consumer | regression | existing Play route/history test if present or bounded test discovery | `/play?run=…` remains intact across App observation/back navigation | search is stripped or Play remount contract changes unexpectedly |
| No backend/durable-state side effect | diff/runtime boundary | scope proof | `git diff --name-only` + manual DB observation unnecessary unless changed | no backend/migration/compose paths | production path escapes §4 |

### Exact verification commands

```bash
npm --prefix apps/live-control-ui run test -- \
  src/test/appNavigation.test.tsx \
  src/test/combatTrackerProductNav.test.ts

npm run test:ui
npm run build

git diff --check
git diff --name-only 73cc35abe65eb0584b765bf6e6c553684d64401e...HEAD
```

If an existing Play history test is found under the bounded discovery exception,
include it in the focused command and record its exact path/result. If no such
test exists, add the minimal Play-query regression to `appNavigation.test.tsx`
without editing Play production code.

### §7A Minimal live browser witness before review handback

Use the assembled application with normal C1/C2 services available. This is not
an APP-STATE mutation test.

1. Start/open DungeonBuddy normally at one primary surface.
2. In browser devtools set:

```js
window.__DMB_DOCUMENT_WITNESS__ = crypto.randomUUID()
```

3. Record the value.
4. Navigate using ordinary product links through at least:

```text
Ingest → Plan → Build → Play → Index → Ingest
```

5. After each transition verify:

```text
window.__DMB_DOCUMENT_WITNESS__
```

is unchanged.
6. Use browser Back/Forward through at least three of those entries and verify
   URL + visible surface agree and the witness remains unchanged.
7. If a real Play run is available, open it so the URL contains `?run=<id>`,
   navigate to Ingest, then browser Back. Verify the exact `?run=<id>` URL and
   Play state return without a document reload.
8. Ctrl/Cmd-click a primary link and confirm native new-tab behavior is retained.
9. Click Combat Tracker and confirm it still performs its normal document
   navigation.
10. Hard reload a primary URL such as `/ingest`; verify it boots Ingest directly.
    The window witness resetting after this **intentional hard reload** is
    expected and demonstrates that the witness would have detected a document
    replacement during normal primary navigation.

Capture the human-visible observation separately:

> Did the specific STOP 2 feeling “everything still flashes on surface change”
> materially improve once full document loads were removed? What, if anything,
> still appears to reboot after the target surface has loaded?

That final feeling is **not** a requirement to repair inside this PR. It is the
input to the mandatory post-merge STOP and possible Stage 5B design.

### Baseline failure handling

On the base revision, ordinary AppChrome primary navigation is expected to
replace the browser document. The implementation worker does not need to add
instrumentation to the base branch, but the review handback must state this as
the known baseline behavior and show that the head browser witness changes it.

If the required UI suite/build already fails on base, record the exact base/head
commands and prove the head does not add failures; do not silently waive them.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. §1 mission/invariant disposition;
3. §7 required vs produced evidence with provenance separated into author-local,
   independently rerun, CI, browser/manual, and operator dogfood;
4. nano-commit/fix story;
5. exact base/head and actual changed paths vs §4;
6. whether the bounded discovery exception was used and why;
7. baseline failures/waivers;
8. browser witness values/route sequence without leaking unrelated local data;
9. confirmation that `/combat` and modified-link native behavior remain native;
10. confirmation that Play query/history behavior remained unchanged;
11. paths outside §4 (`none` or stop report);
12. named successor Stage 5B still false;
13. Stage 2 / STOP 2, Stage 4, Stage 7A remain false;
14. prior finding ledger on re-review.

---

## §9 Acceptance rubric

- [ ] Exactly one capability is delivered: primary product navigation no longer replaces the browser document.
- [ ] Normal Index/Plan/Play/Ingest/Build navigation updates URL and rendered route through browser history.
- [ ] Back/Forward replays the correct visible route.
- [ ] Direct hard reload on each primary URL still works.
- [ ] The shared Agent/World provider ownership in `App.tsx` was not moved or redesigned.
- [ ] The live window witness survives ordinary primary navigation and resets only on intentional hard/document navigation.
- [ ] Modified/new-tab link behavior remains native and accessible anchors retain meaningful `href`s.
- [ ] Combat remains native document navigation.
- [ ] Existing Play `?run=` / `?choose=` behavior remains intact.
- [ ] Stage 5B persistent-AppChrome/remount repair remains unimplemented/unclaimed.
- [ ] Stage 2 / STOP 2 remain OPEN.
- [ ] No Agent-on-Ingest, rich-node, source-adoption, auto-start, backend, APP-STATE, or World-write work entered the PR.
- [ ] Actual changed paths stay inside §4 / bounded discovery.
- [ ] Focused tests, full UI tests, build, diff-check, and browser witness are recorded against the exact head.

### Mandatory post-merge human STOP

After this PR merges, do **not** automatically dispatch Stage 5B, Stage 4, or
Agent-on-Ingest.

The operator must dogfood the assembled product again and answer:

```text
1. Did ordinary primary-surface navigation stop feeling like a page reboot?
2. Does any flash/reboot still happen after the target surface content loads?
3. If yes, is it:
   - AppChrome/component remount,
   - provider/lens transition,
   - StrictMode/dev-only behavior,
   - actual second document reload,
   - or another observable mechanism?
4. Does the accepted next slice remain Stage 5B, or did this fix remove enough
   shell pain that graph-object usefulness / Stage 4 should become next?
```

Do not pre-author that successor handoff before this STOP is accepted.

---

## Stop conditions

Stop and report instead of expanding when any of these appears:

- preserving same-document navigation requires changing Agent provider ownership;
- preserving same-document navigation requires changing World provider ownership;
- a backend/server rewrite is required for direct primary URLs;
- Play query/history cannot remain intact without editing Play production code;
- `appChromeConfig.ts` must become a new routing authority rather than remaining
  route metadata;
- surface selection/save state must be redesigned merely to navigate;
- AppChrome persistent mounting becomes necessary to satisfy the narrower
  same-document invariant;
- a routing library/dependency is proposed as a new framework-level contract;
- a production path outside §4 is required;
- another active lane claims App/AppChrome/route ownership;
- test evidence can prove only a helper and not the browser-route integration;
- the implementation starts repairing Session 10 sources, node richness,
  Agent-on-Ingest, Docker auto-start, or World availability.

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
