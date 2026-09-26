---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: UI Presentation Substrate Sidequest
  - Flow: UI
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-UI-canvas-layout-convergence.md
  - Branch / PR: docs/ui-canvas-layout-convergence / #760
  - PR topology: stacked design review on #759; implementation BLOCKED

  ## Verification pointer
  - Review parent: #759 exact implementation head eb159a275f52e194a027fb3396637fde25be3370
  - External predecessor: Drakosfire/Canvas main e352c71558a0ff020ef97c63dbbe6b3a93e72528 observed at design
  - Changed paths: exact §4 allowlist only
  - Verification: adapter tests + Ladle Page story + Canvas layout-only dependency proof + typecheck/build + diff checks

  The checked-in ACTIVE handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — UI Canvas layout convergence experiment

**Created:** 2026-09-25  
**Status:** BLOCKED — UI-F4 is implemented in unmerged #759, but Canvas still lacks a clean layout-only consumer contract; no UI-F5 implementation has begun
**Canonical handoff path:** `Docs/Plans/HANDOFF-UI-canvas-layout-convergence.md`  
**Conversation/workstream:** `UI Presentation Substrate Sidequest`  
**Flow / owner:** `UI`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority base:** `335da68688630a4ea64363ddcabec8c6257518dd` — UI-F4 design head  
**Canvas design observation:** `Drakosfire/Canvas@e352c71558a0ff020ef97c63dbbe6b3a93e72528`  
**Activation gate:** UI-F4 accepted/merged; exact Canvas successor SHA is installable from a clean npm consumer, `dungeonmind-canvas/layout` resolves without a local sibling checkout, map/Konva peers are not installed for layout-only Buddy use, and one React singleton resolves under Buddy React 19  
**Dispatch base rule:** fresh current `main` containing this handoff after activation; record exact Buddy and Canvas SHAs at dispatch/review  
**PR topology:** `serial`  
**PR authorization:** once ACTIVE, open/update exactly one Buddy implementation PR for this experiment; no Canvas repair inside the Buddy PR and no successor/repair PR  
**PR title:** `UI: prove Canvas layout convergence`

**Current stacked review parent:** #759 exact head `eb159a275f52e194a027fb3396637fde25be3370`. This is a re-anchored design PR, not an ACTIVE implementation lane or write lease.

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

## §1 Mission and merge-ready invariant

**Mission:** Prove or falsify that Buddy can reuse standalone Canvas for measurement/pagination while Buddy retains authoritative document semantics and visible Page presentation.

**Merge-ready invariant:** One static representative Buddy TipTap document maps deterministically into transient Canvas layout inputs, Canvas performs measurement/pagination through the **layout subpath only**, and a Buddy-owned PageProjection renders the resulting LayoutPlan without creating a second document authority, save path, Canvas PageDocument, PHB/statblock presentation dependency, map/Konva runtime, or backend requirement.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every path proves one narrower seam: Canvas owns layout mechanics only; Buddy owns semantic adaptation and visible rendering. |
| Most likely adversarial sequence | “Use Canvas” expands into adopting `PageDocument`/CanvasPage, generated IDs, map peers, or a second save model because those APIs are convenient. |
| Will §7 detect that failure? | Yes. Source guards ban `CanvasPage`/root imports and PageDocument persistence; package lock must not gain Konva/react-konva; adapter tests require fixed identities. |
| Easiest owning boundary to under-test | Measurement context parity: visible Buddy renderer and offscreen MeasurementPortal must render the same block component under equivalent width/typography. |
| What PR topology is authorized, and why is it safe? | Serial. Package dependency + layout adapter + Page story form one bounded experiment and collide with F4 package/story files. |
| Fact that forces stop/split | Canvas cannot be consumed reproducibly from an exact artifact; layout-only install pulls map stack; duplicate React appears; neutral measurement requires Canvas source patches; or TipTap semantics cannot map without losing identity. |

## §2 Context, authority, lane, and PR topology

| Field | Required content |
|---|---|
| Parent authority | `PLAN-ui-presentation-substrate-sidequest-v1.md`; `DESIGN-shared-markdown-canvas-surface-composition.md` |
| Design authority base | `335da68688630a4ea64363ddcabec8c6257518dd` |
| Activation gate | UI-F4 merge + exact installable Canvas layout-only artifact |
| Dispatch base rule | fresh current Buddy main containing this handoff after activation |
| Predecessor contract | Buddy TipTap JSON semantics; Canvas generic component/data-source/adapter/layout contracts |
| Exact input consumed | One fixed `JSONContent` fixture shaped exactly like `MarkdownCanvasSession.editorContent` / current TipTap schema |
| Named successor | UI-F6 — post-substrate steward re-entry decision |
| What remains false | No live MarkdownCanvasSession integration; no document save; no Flow/Board implementation; no Canvas map use |
| Explicit non-goals | TipTap replacement; Canvas PageDocument persistence; CanvasPage adoption; freeform board; map/Konva; print export; production Plan/Play route integration |
| PR topology | serial |
| Authorized PR action | open/update exactly this assigned Buddy PR only |
| Open implementation PRs in workstream at dispatch | none required; steward re-checks |
| Stack parent + merge/rebase order | not applicable |
| Branch / isolated checkout | fresh isolated implementation branch/worktree after activation |
| Parallel lanes / collision hotspots | package.json/lock and `src/ui` stories; Canvas repository is read-only from Buddy implementation |
| Runtime/state ownership | static Ladle story only; no Buddy/Canvas durable state |
| State-authority sync set after merge | sidequest plan records UI-F4 completed predecessor / UI-F5 experiment result |

### Canvas prerequisite discovered during design

At design-time `Drakosfire/Canvas@e352c71558a0ff020ef97c63dbbe6b3a93e72528` has useful generic layout APIs, but is **not yet a clean layout-only dependency for Buddy**:

- package exports point to `dist/**`; those files **are tracked at this exact commit**, correcting the original design-time assertion that they were absent;
- no install-time `prepare` build exists, though tracked `dist` makes this point non-blocking by itself;
- map peers (`konva`, `react-konva`) are declared package peers;
- local-consumer history explicitly warns about duplicate React singleton invalid-hook failures.

**2026-09-26 prerequisite audit:** Canvas `main` remains exactly
`e352c71558a0ff020ef97c63dbbe6b3a93e72528`. Its tracked tree includes
`dist/layout/index.js` and `dist/layout/index.d.ts`, but its exact
`package.json` still declares `konva` and `react-konva` as required peers.
The §2 activation condition that map/Konva peers are absent from an ordinary
layout-only Buddy install is therefore not satisfied. Do not implement this
Buddy slice by using `--omit=peer`, local links, source imports, or a copied
build. The Canvas packaging repair belongs to a separate reviewed Canvas
predecessor. This PR stays open as the existing blocked handoff; #761's human
decision gate is not advanced by an unrun convergence experiment.

Do not work around this with:

- a sibling-path dependency;
- vendored Canvas source;
- deep imports from Canvas `src/**`;
- committed generated Canvas `dist` copied into Buddy;
- npm-link/manual setup as merge evidence.

A separately reviewed Canvas packaging slice must make the exact layout subpath consumable first.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Fixed TipTap fixture | Editable schema exists only in Buddy | Pure adapter reads exact current JSON shape | Yes | Buddy adapter |
| Ordinary prose/heading | Current editor renders directly | Maps to Buddy-owned prose block data/component | Yes | adapter + registry |
| Table | TipTap standard table/tableRow/tableHeader/tableCell | Maps without flattening cell structure | Yes | adapter + Buddy renderer |
| Callout | node type `callout`, attrs kind/label, nested blocks | Preserves kind/label/content in Buddy block payload | Yes | adapter |
| Graph reference | inline `graphNodeReference` with exact `nodeId` + label | Stays inline inside Buddy-rendered prose; exact id preserved | Yes | adapter/renderer |
| Playable v2 heading | heading attrs carry kind/id/version/beatKind/sceneId | Exact identity metadata preserved; Canvas does not interpret it | Yes | adapter |
| Playable v2 option | top-level list item attrs carry option identity/edges | Exact identity/transition metadata preserved | Yes | adapter |
| Measurement | none in Buddy Page lab | Canvas MeasurementPortal measures same Buddy block renderer | Yes | Canvas layout engine |
| Pagination | none in Buddy Page lab | Canvas LayoutPlan deterministically places blocks across pages | Yes | Canvas layout engine |
| Visible page | no shared Page projection | Buddy-owned PageProjection renders LayoutPlan with UI tokens | Yes | Buddy presentation |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Same TipTap fixture → adapter twice | exact stable component/data-source IDs/order; no Date.now/random IDs | adapter test |
| Graph reference nested in paragraph | exact `nodeId` survives; no label-based identity | adapter test |
| v2 Beat/Scene/Choice/Option metadata | exact IDs/attrs survive as opaque Buddy data; Canvas never interprets Playable semantics | adapter test |
| Block taller than one page | truthful Canvas overflow/pagination result; no silent content deletion | layout story/test |
| Import dependency | only `dungeonmind-canvas/layout`; no root/map import | source guard |
| Inspect package lock/bundle | no `konva` or `react-konva` added for Buddy | lock/source check |
| Render measurement + visible page | same Buddy block renderer function used for both | source/test proof |

## §4 Files in scope — write lease

Exact Canvas dependency syntax/SHA is determined at activation from the accepted packaging predecessor.

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/package.json` | Exact Canvas layout package dependency |
| Modify | `apps/live-control-ui/package-lock.json` | Exact npm lock |
| Create | `apps/live-control-ui/src/ui/fixtures/runbookPage.ts` | Fixed current-schema TipTap JSON fixture |
| Create | `apps/live-control-ui/src/ui/canvas/tiptapToCanvasLayout.ts` | Pure Buddy semantic adapter → transient Canvas layout inputs |
| Create | `apps/live-control-ui/src/ui/canvas/RunbookBlock.tsx` | Buddy-owned renderer for semantic block payloads |
| Create | `apps/live-control-ui/src/ui/canvas/RunbookPageProjection.tsx` | Canvas layout/measurement orchestration + Buddy visible page renderer |
| Create | `apps/live-control-ui/src/ui/canvas/RunbookPageProjection.css` | Page presentation through UI tokens |
| Create | `apps/live-control-ui/src/ui/canvas/RunbookPageProjection.stories.tsx` | Backend-free Page witness |
| Create | `apps/live-control-ui/src/ui/canvas/tiptapToCanvasLayout.test.ts` | Exact semantic/identity mapping proof |
| Create | `apps/live-control-ui/src/ui/canvas/RunbookPageProjection.test.tsx` | Layout/render boundary proof |
| Create | `Docs/Reports/REPORT-UI-canvas-layout-convergence.md` | Record YES / NARROWER / NO evidence/result |
| Modify | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` | Backward-looking predecessor/result sync |

**Bounded discovery exception:**
```text
Directory: apps/live-control-ui/src/ui/canvas/
Maximum additional paths: 2
Allowed path kinds: one pure type module and/or one Buddy-only block renderer helper
Decision rule: only to keep adapter/render ownership explicit; no Canvas wrapper framework or second document model
```

## §5 Explicitly out of scope / collision boundary

| Path/capability | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/markdownCanvas/**` | Authoritative document/session code stays unchanged |
| `apps/live-control-ui/src/tiptap/**` | Existing semantic schema stays source authority |
| production Plan/Play/Build routes | Lab-only convergence proof |
| Canvas repository | Any required Canvas repair is a separately reviewed prerequisite |
| `CanvasPage` | Current component emits PHB/statblock-era visible classes; Buddy owns visible Page presentation |
| `buildPageDocument()` / durable `PageDocument` | Avoid generated IDs/timestamps and second document authority |
| Canvas root or `/map` imports | Layout-only seam |
| Map/freeform/snap UI | Later decision only |
| HTML/PDF export | Not required to prove pagination seam |

## §6 Implementation contract

### Candidate seam

```text
fixed current-schema TipTap JSON
        ↓
Buddy tiptapToCanvasLayout()
        ↓
{
  componentInstances,
  dataSources,
  componentRegistry,
  template,
  adapters,
  Canvas config
}
        ↓
dungeonmind-canvas/layout
  CanvasLayoutProvider
  useCanvasLayout
  MeasurementPortal
        ↓
LayoutPlan
        ↓
Buddy RunbookPageProjection
~~ visible Page/Print-like presentation ~~
```

The same `RunbookBlock` renderer must be used in measurement and visible rendering.

### Semantic mapping

| Buddy TipTap source | Required transient Buddy/Canvas representation | Identity rule |
|---|---|---|
| paragraph / ordinary heading | `dmb.prose` block payload preserving TipTap subtree | deterministic path-based block id |
| standard table subtree | `dmb.table` payload preserving row/header/cell JSON | deterministic path-based block id |
| `callout` | `dmb.callout` payload with exact `kind`, optional `label`, nested content | deterministic path-based block id |
| inline `graphNodeReference` | stays inside containing Buddy semantic payload with exact `nodeId` + label | `nodeId` remains exact durable reference; label display-only |
| playable v2 heading | Buddy block payload carries exact validated playable attrs | playable ID preserved exactly, not used as Canvas authority |
| playable v2 option list item | Buddy block payload carries exact option ID/activates/suppresses | exact IDs/edge strings preserved |

Canvas component type strings are Buddy-owned adapter vocabulary. They do **not**
become TipTap schema or product ontology.

### Determinism

Do not use `buildPageDocument()`, `Date.now()`, random UUIDs, or mutable current time.

Fixture and projection IDs are fixed or derived deterministically from document tree paths / exact playable IDs.

### Layout configuration

Start with exactly one page mode:

- locked page mode;
- one column;
- fixed print-like page dimensions/margins;
- snapping disabled;
- fixed Buddy-owned portal class names through Canvas frame config;
- no map/freeform mode.

### Terminal result

The implementation report must record one of:

```text
YES
  Canvas layout subpath cleanly owns measurement/pagination; Buddy Page projection is viable.

NARROWER
  A smaller named Canvas primitive is useful, but full proposed seam has a specific bounded mismatch.

NO
  Canvas cannot serve this layer without violating dependency, authority, performance,
  identity, or presentation boundaries.
```

Do not convert NO into more glue inside the same PR.

### A. State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| static Page story | measurement skeleton allowed | LayoutPlan + Buddy pages render | unsupported TipTap node fails test/adapter explicitly | package import/build fails → stop | malformed semantic attrs fail adapter/test | n/a static fixture | deterministic rerender |
| layout overflow | measurement/pagination | explicit pages/overflow warning | n/a | n/a | content disappearance = fail | n/a | deterministic |

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| TipTap tree block | deterministic tree-path id unless exact semantic id exists | duplicate generated path impossible in valid tree | No random id |
| Playable id | preserve exact Buddy id as payload metadata | invalid attrs fail adapter/test | No regeneration |
| graph node ref | exact `nodeId`; label display-only | blank/missing id is malformed fixture/schema | No label lookup |
| Canvas component id | transient deterministic projection id | n/a | Never durable Buddy identity |
| Canvas data source id | transient deterministic fixed id | n/a | Never document identity |

### C. Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| TipTap fixture | source-controlled JSON | exact source fixture | deterministic adapter | current schema only | revert source |
| Canvas projection | none; transient | no alternate save path | recompute freely | none | unmount/delete |
| LayoutPlan | none | derived only | deterministic for same measurement inputs | none | recompute |

### D. Predecessor → consumer mapping

**Grounding sources:** current Buddy TipTap extensions and exact accepted Canvas layout contracts at activation.

| Predecessor field/outcome | Real shape/optionality | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| Callout node | `type=callout`, attrs `kind`, optional `label`, block+ content | dedicated Buddy page block | pure shape-preserving adapter | mapping test |
| Graph node reference | `type=graphNodeReference`, attrs `nodeId`, `label` | inline reference rendering in containing block | preserve exact attrs | mapping test |
| Tables | TipTap Table/Row/Header/Cell subtree | table block renderer | preserve subtree | mapping test |
| Playable heading attrs | exact validator-owned kind/id/version/beat/scene attrs | preserve opaque semantic metadata | no Canvas interpretation | mapping test |
| Playable option attrs | exact option id/version/activates/suppresses | preserve opaque semantic metadata | no Canvas interpretation | mapping test |
| Canvas `ComponentInstance` / data source | generic application-owned contracts | transient target for Buddy adapter | deterministic construction | type/test |
| Canvas LayoutPlan | pages/columns/entries | Buddy-owned visible page loop | read only | render test/story |

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command/scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Canvas package is reproducible | package boundary | contract | clean `npm ci` from Buddy + dependency inspection | exact SHA/artifact installs; layout import works | local path/manual link required |
| Layout-only really means layout-only | package lock/source | performance/boundary | search lock/imports | no `konva` / `react-konva`; no root/map import | map stack installed/imported |
| One React singleton | npm dependency tree | integrity | `npm --prefix apps/live-control-ui ls react react-dom` | Buddy React resolves without Canvas-private duplicate | invalid hook/duplicate React |
| Semantic adapter deterministic | pure adapter | contract/adversarial | focused tests; call adapter twice | deep-equal IDs/order/data; exact semantic attrs preserved | time/random/generated drift |
| Existing TipTap semantics not widened | adapter boundary | contract | source guard + mapping tests | no tiptap source modifications | any schema change |
| Measurement/render parity | Page projection | contract | component test/story | same RunbookBlock renderer feeds MeasurementPortal + visible pages | separate approximating renderer |
| Pagination is real/useful | Canvas layout | manual/regression | Ladle story with enough content for >1 page | bounded multi-page output; no silent dropped block | infinite loop/MAX_PAGES/content loss |
| UI lab remains backend-free | workshop | manual | backend services off → Page story | renders/paginates | network/backend requirement |
| Production app unaffected | frontend | regression | test/typecheck/build | no new failures | new failure |
| Visual contract can cover Page story | F4 infrastructure | regression | explicit selected visual case only if stable | optional addition within <=10 total, or report why not stable | F4 contract weakened |
| Exact lease | Git | contract | diff checks | only §4/bounded helper paths | unexpected path |

Expected commands:

```bash
npm --prefix apps/live-control-ui ci
npm --prefix apps/live-control-ui ls react react-dom
npm --prefix apps/live-control-ui run test -- src/ui/canvas/tiptapToCanvasLayout.test.ts src/ui/canvas/RunbookPageProjection.test.tsx
npm --prefix apps/live-control-ui run ui:build
npm --prefix apps/live-control-ui run typecheck
npm --prefix apps/live-control-ui run build
git diff --check
git diff --name-only <dispatch-base>...HEAD
```

### Minimal live / dogfood proof

```text
Existing surface: Ladle only
Smallest realistic scenario: open representative multi-page Runbook Page story on target laptop with all backend services off
Expected observation: ordinary prose + table + callout + graph reference + playable identities render through one Buddy Page treatment; pagination is stable and interaction stays responsive
Evidence captured: page count, overflow warnings, dependency/bundle notes, manual responsiveness, YES/NARROWER/NO verdict
```

### Baseline failure handling

A Canvas package prerequisite failure is a stop, not a Buddy baseline waiver. Buddy test/build failures use exact dispatch-base/head comparison.

## §8 Required review handback

Record:

1. Buddy dispatch base/head and Canvas exact dependency SHA/artifact;
2. Canvas packaging predecessor review/merge evidence;
3. dependency tree and proof no map peers/duplicate React;
4. exact TipTap fixture semantic node inventory;
5. actual adapter mapping table;
6. whether `CanvasPage` / `PageDocument` / root/map imports are absent;
7. page count + overflow result;
8. focused tests, Ladle build, production build/typecheck;
9. target-laptop manual observation;
10. report path and exact YES / NARROWER / NO disposition;
11. any stop condition;
12. confirmation UI-F6 remains a decision gate, not pre-authorized implementation.

## §9 Acceptance rubric

- [ ] UI-F4 predecessor merged.
- [ ] Exact Canvas artifact is reproducibly installable.
- [ ] Buddy imports `dungeonmind-canvas/layout` only.
- [ ] No Konva/react-konva dependency lands in Buddy for this experiment.
- [ ] One React singleton is proven.
- [ ] No Canvas PageDocument or alternate save path exists.
- [ ] No CanvasPage visible presentation is adopted.
- [ ] Adapter IDs are deterministic.
- [ ] Callout/table/graph-reference/playable semantics are preserved.
- [ ] Same Buddy block renderer is used for measurement and visible rendering.
- [ ] Backend-free Page story produces stable useful pagination or records a truthful stop.
- [ ] Report records YES / NARROWER / NO.
- [ ] UI-F6 remains unimplemented.

## Stop conditions

Stop and return to steward if:

- exact Canvas consumption still depends on local sibling/link/vendor setup;
- layout-only dependency installs map/Konva peers;
- duplicate React singleton appears;
- Canvas source must change to make the Buddy PR work;
- Canvas PageDocument becomes necessary;
- CanvasPage/PHB classes become necessary for visible presentation;
- Buddy TipTap schema must change;
- semantic nodes must be flattened/lost to paginate;
- measurement requires a second approximating renderer;
- the page story needs a backend;
- performance on the target laptop makes isolated UI iteration materially worse.
