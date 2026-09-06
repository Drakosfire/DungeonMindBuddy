# REPORT — C1/C2 demo readiness survey (DFC-3)

**Created:** 2026-09-06  
**RC1 repair:** 2026-09-06 (review `5126289112` on PR #687 @ `7dc57df4…`) — material library URI+digest ledger; Agent readiness downgraded  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-c1-c2-demo-readiness-survey-v1.md`  
**Library:** `Docs/Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md`  
**Product `main` surveyed:** `678e9c276ad58505c53ce61d5a659ea8c792ca31`  
**Acceptance corpus:** Longmont Campaign 1 / Campaign 2. Of Conks and Cons is prior UI/design evidence only.

This report is reconnaissance. It does not repair UX, adopt material, mutate leftover APP-STATE, re-ingest history, or change product code.

---

## Authority coordinates (sanitized)

| Field | Value | Provenance |
| --- | --- | --- |
| Survey checkout | isolated worktree of current `main` | `git rev-parse HEAD` at survey start = `678e9c276ad58505c53ce61d5a659ea8c792ca31` |
| Leftover APP-STATE | PostgreSQL `dungeonbuddy_application_state` @ `127.0.0.1:54329` | `LIVE-READ` |
| Schema | `20260902_0005` at head | `LIVE-READ` |
| Isolated write DSN | not used | no disposable write this pass |
| Product UI | Vite `127.0.0.1:5173` against this worktree | assembled browser |
| Product API | uvicorn `127.0.0.1:8000` against this worktree | assembled HTTP |
| DungeonMind | Buddy-facing `POST /api/live/world-graph/projection` | `LIVE-READ` 503 |
| Ingest identity digest | `59508725ad56789bc333af3cea9f311dda55b8eac1b89aa4639c49278b40f5f1` | before and after survey |

DSN passwords and `.env` contents are omitted.

---

## Leftover APP-STATE counts (LIVE-READ)

| Kind | Count |
| --- | --- |
| `ingest.run` | **53** (C1=24, C2=29) |
| ingest status `validated` | 36 |
| ingest status `prepared` | 17 |
| ingest status `reviewable` | **0** |
| Plan WorkObjects | **0** |
| Runbooks | **0** |
| Play Runs | **0** |
| workspace documents (HTTP registry) | **0** |

HTTP catalog: `GET /api/live/graph-preview/extraction-runs` → `dmb_extraction_run_catalog_v1`, **53** rows.

DFC-2c recovered **catalog rows**, not review packages. Operator leftover apply after PR #686 merge is survey observation, not a new DFC-2c product claim. DFC-2a Plan `80630cc2-…` is **not** in this leftover DB (Postgres tmpfs recreate after that recovery).

No new ExtractionRun identity appeared during this survey.

---

## Compact readiness scorecard

Readiness labels: `READY` / `USABLE_WITH_GAPS` / `DISCOVERABLE_NOT_USABLE` / `NOT_CONNECTED` / `BLOCKED_BY_MISSING_MATERIAL` / `UNKNOWN`.

Do not treat `CODE-ONLY` as `READY`.

| Demo element | Readiness | Live evidence | Existing implementation | Existing C1/C2 material | Primary blocker | Likely repair shape |
| --- | --- | --- | --- | --- | --- | --- |
| 1. campaign/session discovery | USABLE_WITH_GAPS | `/ingest` Load recap lists Longmont C1/C2 sessions with `· history`; `/plan` `/build` `/play` do not present APP-STATE historical C1/C2 choosers | Ingest catalog + session tabs | 17 ingested sessions; git-tracked recaps beyond catalog | Plan/Build/Play have no leftover C1/C2 WorkObjects | Keep Ingest discovery; later Plan/Build/Play adoption only where exact bytes exist |
| 2. rich historical recap reading | DISCOVERABLE_NOT_USABLE | C1S10 / C2S23 / C2S25 exact runs bind as `validated`; recap prose never appears; banners: not exact-reviewable / not reviewable for promotion | Graph Review Load recap + exact-run projection | Git-tracked recap files; leftover ingest.run pointers | First user-visible failure: after Load, the workbench shows status banners and **no recap body** | Inspect-without-promote for `validated`/`prepared` history; serve SourceArtifact prose even when not reviewable |
| 3. session-to-session recap navigation | USABLE_WITH_GAPS | Load-dialog session tabs move among ingested sessions without typing IDs; no previous/next on the bound workbench; chrome nav drops `?session=&campaign=&run=` | Load recap dialog | Ingested sessions only | First failure: leaving Ingest to Plan loses the bound run | Preserve ingest selection across shell; optional workbench prev/next among catalog sessions |
| 4. entity pills and node/object interaction | NOT_CONNECTED | Bound exact runs render no pills; catalog live projection is retired | `GraphNodeHoverToken` + markdown-link lanes exist; exact-run path is plain `<pre>` | Candidate graphs/span indexes on `primary-checkout` for 32/53 runs with explicit URI+digest in library §2.3; 0 on this checkout | First failure: no entity-linked terms in the recap view | Attach pills to readable prose **after** prose is shown; do not re-ingest |
| 5. Threat/statblock projection | NOT_CONNECTED | No Threat glance or statblock sheet on the bound historical runs | `ThreatCampaignGlance` / `ThreatSheetProjection` exist; Graph Review inspect uses `GraphObjectCard` | Historical Threat objects in World/artifacts, not opened here | First failure: nothing Threat-specific appears after Load | Reconnect Threat/statblock only on a live object-open path |
| 6. historical Ingest inspection/review | DISCOVERABLE_NOT_USABLE | 53 catalog rows; review-package HTTP `422 run_not_promotable` for C1S10/C2S23/C2S25 | Exact-review statuses = `{reviewable}` only | 53 leftover runs; 0 reviewable | First failure: Graph Review refuses `validated` as not exact-reviewable | Separate inspect vs promote; do not remap historical `validated` into `reviewable` silently |
| 7. Plan historical open/edit/save | BLOCKED_BY_MISSING_MATERIAL | `/plan` opens a blank/local-draft shell; chooser shows `local-plan:c917bba1-…` “C2 Session 23 Prep (no longer listed as active)”; leftover `list_plans()` = 0 | Blank-shell + APP-STATE prepare/commit (`CODE-ONLY` / predecessor `TEST-PROVEN`) | DFC-2a exact Plan bytes stranded after leftover DB recreate | First failure: no historical APP-STATE Plan is choosable | Re-adopt surviving exact Plan bytes into leftover if still intact; DFC-2p for missing-byte identities |
| 8. Build historical open/edit/save | BLOCKED_BY_MISSING_MATERIAL | `/build` chooser disabled; “Choose or create a source above.” | New/Import chrome present | DFC-1 four identities all `NEEDS_ADAPTER` | First failure: empty Build chooser | DFC-2b only if a safe write payload appears |
| 9. Play/Runbook historical open/edit/run/resume | BLOCKED_BY_MISSING_MATERIAL | “No durable Runs” / “No active Runbooks”; create/start disabled until campaign filled | Play APP-STATE seams exist | DFC-1 admitted 0 Runbooks/Runs | First failure: Play has nothing historical to open | Do not invent C1/C2 playable material |
| 10. World context across surfaces | DISCOVERABLE_NOT_USABLE | Chrome: `World · Needs attention · DungeonMind authority is unavailable. (authority_unavailable)` on Ingest/Plan/Play after load | `AppChromeWorldGraphStatus` + lens `POST /api/live/world-graph/projection` | Cutover complete; remote authority 503 | First failure: World chip error on every primary surface | Restore DungeonMind Buddy-facing availability; no Buddy graph ownership |
| 11. persistent no-reload application shell | NOT_CONNECTED | `AppChrome` uses `<a href>`; `App.tsx` pathname switch remounts pages; World chip remounts Loading → unavailable; ingest query does not survive `/plan` | DFC-NAV1 is documented successor, unbuilt | n/a | First failure: surface change is a full document navigation, not an in-app shell | DFC-NAV1 |
| 12. Agent on Plan | NOT_CONNECTED | Agent region present; no historical Plan object; ask bar not exercised (`CODE-ONLY`) | Shared `AgentInteractionProvider` + Plan ask bar in shell | No recovered APP-STATE Plan | First failure: shared chrome is visible but there is no usable Plan object or exercised ask flow | Bind after Plan material exists |
| 13. Agent on Build | NOT_CONNECTED | Agent region present; empty source; no ask flow exercised | Shared provider; Build publishes context (`CODE-ONLY`) | No Build material | First failure: nothing to ask about and no exercised Agent interaction | Same as Build material |
| 14. Agent on Ingest/recap | NOT_CONNECTED | Agent region present; no ask/query chrome observed; bound recap has no prose/object | Shared chrome; Ingest publishes surface context | Bound run id only | First failure: Agent cannot see recap text the human also cannot read | Publish recap/selection after inspect path exists |
| 15. Agent on Play | NOT_CONNECTED | Agent region present; empty Play; no ask flow exercised | Shared chrome | No Runbook/Run | First failure: no playable object and no exercised Agent interaction | Same as Play material |
| 16. reload/restart durability | USABLE_WITH_GAPS | Ingest catalog remounted after route changes; World/Agent in-memory lease does not survive remount | Leftover ingest.run is PostgreSQL | 53 catalog rows | First failure: World chip and Agent conversation continuity reset on navigation | NAV1 + durable Agent thread already in localStorage (`CODE-ONLY`) |
| 17. VPC/off-hardware data readiness | NOT_CONNECTED | Recap files git-tracked; candidate/review bytes in primary-checkout `out/`; leftover Postgres is local; DungeonMind remote down | APP-STATE schema exists | 53 ingest rows local | First failure: laptop still owns review bytes + leftover DB + World unavailability | Relocate artifacts to durable storage; host leftover Postgres; restore DungeonMind |

---

## Assembled recap-review findings (highest-priority)

Browser pass: Graph Review Workbench at `/ingest` with leftover catalog.

### Required sessions

| Session | Catalog | Loaded exact run | HTTP review-package | What the human sees |
| --- | --- | --- | --- | --- |
| `longmont-c1 / session-10` | present | `graph-ingest:longmont-c1:session-10:20260722T023135Z` | `422` `run_not_promotable` / `extraction run is not reviewable: validated` | Session tab `· history`; after Load: bound, `validated`, **no recap prose** |
| `longmont-c2 / session-23` | 10 runs | `graph-ingest:longmont-c2:session-23:20260629T040857Z` | same `422` | Same banners; gold expected `graph-memory:session-23-candidate-graph-gold:v0` |
| `longmont-c2 / session-25` | 8 runs | `graph-ingest:longmont-c2:session-25:20260808T005650Z` | same `422` | Known current dead-end: catalog-visible `validated` history that Graph Review will not exact-review |
| additional rich session: C1 `session-1` | 4 runs | not promoted | n/a (same status class) | Gold expected `graph-memory:session-1-candidate-graph-gold:v1`; still history, not reviewable |

Git-tracked recap files for those sessions exist on `current-main` (see library). Graph Review does not render them on this path.

### Capability table

| Capability | Architecturally present? | Human-usable today? | Evidence |
| --- | --- | --- | --- |
| Recap prose | Exact-run projection can render `sourceProse` in `<pre>` **if** a review package loads | No | `LIVE-READ` no body; HTTP 422; `GraphReviewExactRunProjection.tsx` |
| Session navigation | Load-dialog campaign/session tabs | Partial | `LIVE-READ` among ingested sessions; no workbench prev/next; chrome nav drops selection |
| Entity pills | `GraphNodeHoverToken` for markdown-link lanes | No on this path | Exact-run is plain `<pre>`; no pills observed |
| Pill styling | Current hover-token CSS on main; Of Conks `GraphNodeHoverToken.tsx` / `GraphObjectCard.tsx` **identical** to main | Not exercised | `CODE-ONLY` + file compare; no richer disconnected Of Conks fork found |
| Pill interaction | Hover/click exist on token component | No | Nothing to click in exact-run prose |
| Node/object detail | `GraphReviewNodeGameCard` → `GraphObjectCard` | No | Exact-review package never loaded |
| Provenance | Assertions/evidence UI exists on exact-run projection | No | Same 422 |
| Threat projection | `ThreatCampaignGlance` + `useThreatHoverMechanics` (commit `500af749` on main) | No | Unused on exact-run / retired catalog lane |
| Statblock treatment | `ThreatSheetProjection` via `ResolvedGraphObjectProjection`; Graph Review inspect uses `GraphObjectCard`, not ThreatSheet | Not connected to recap review | `CODE-ONLY` |
| Existing extraction review | Catalog lists 53 historical runs | Catalog only | `LIVE-READ` |
| Review/correction | Promote/confirm for `reviewable` exact-run | No historical run is `reviewable` | `EXACT_REVIEWABLE_STATUSES = {"reviewable"}` |
| Agent | Shared Agent chrome on Ingest | Region visible; no recap-aware ask observed | `LIVE-READ` |
| Persistence | ingest.run in leftover PostgreSQL; recap git; candidate bundles local `out/` | Catalog durable; review bytes laptop-local | library §3 |

Catalog live projection sets `projectionStatus: "retired"` (CUTOVER D.3A; do not call UnionSupergraph). “Review and merge” toolbar gated on `projectionStatus === "ready"` is effectively dead for this lane (`CODE-ONLY` + tests).

Do not repair any of the above in this PR.

---

## Surface readiness

Provenance: `LIVE-READ` unless noted.

### Plan `/plan`

```text
historical C1/C2 material exists?     DFC-2a exact Plan bytes existed; not in current leftover DB
visible in product?                   no APP-STATE Plan; local-plan draft residue only
openable?                             blank/local-draft shell yes; historical Plan no
readable?                             template headings (Session intent, Memory, Scenes/beats)
editable?                             locked-editing chrome present; not saved this pass
save path exists?                     Markdown save / Save to Markdown chrome
save path live-proven?                CODE-ONLY this pass (leftover is read-only)
reopen after save?                    not exercised
hard reload behavior?                 shell remounts; leftover Plan count still 0
API restart behavior?                 not re-run; DFC-2c predecessor proved ingest catalog, not Plans
World/context projection present?     World chip authority_unavailable
Agent present?                        yes, shared chrome; PlanAgentInteractionBar in shell (CODE-ONLY ask)
Agent useful current context?         no historical Plan object
important local-filesystem dependency? local-plan drafts / browser storage for unsaved shell
main user-visible blocker?            leftover APP-STATE has 0 Plans
```

### Build `/build`

```text
historical C1/C2 material exists?     DFC-1 four NEEDS_ADAPTER identities only
visible in product?                   no
openable?                             empty chooser
readable?                             no
editable?                             New source / Import source chrome only
save path exists?                     CODE-ONLY
save path live-proven?                no
reopen after save?                    no
hard reload / API restart?            empty after remount
World/context?                        World chip error
Agent present?                        yes
Agent useful context?                 no
important local-filesystem dependency? historical Build bytes/metadata still on DFC-1 roots
main user-visible blocker?            “Choose source” disabled; nothing to open
```

### Ingest `/ingest`

```text
historical C1/C2 material exists?     yes — 53 leftover ingest.run + git recaps
visible in product?                   yes — Load recap campaigns/sessions
openable?                             catalog/session yes; exact-review package no
readable?                             recap body no
editable?                             no historical correction UI reached
save path exists?                     promote path for reviewable only
save path live-proven?                not exercised (would mutate)
reopen after save?                    n/a
hard reload behavior?                 catalog remounts
API restart behavior?                 predecessor DFC-2c W11 LIVE; not repeated here
World/context?                        World chip error; pills not on this path
Agent present?                        chrome region yes
Agent useful context?                 bound run without prose
important local-filesystem dependency? candidate_graph / span index under primary-checkout out/
main user-visible blocker?            validated history is not exact-reviewable; no prose
```

### Play `/play`

```text
historical C1/C2 material exists?     no admitted Runbook/Run
visible in product?                   empty-state copy
openable?                             no
readable?                             no
editable?                             Create blank / Edit / Start exact Run disabled until campaign filled
save path exists?                     CODE-ONLY / TEST-PROVEN predecessor
save path live-proven?                no (read-only leftover)
reopen after save?                    no
hard reload / API restart?            still empty
World/context?                        World chip error
Agent present?                        yes
Agent useful context?                 no
important local-filesystem dependency? none for missing Runbooks
main user-visible blocker?            no historical playable material
```

Edit/save claims are not `READY`. Leftover C1/C2 was not written.

---

## World / DungeonMind continuity

Cutover is complete. This survey used only the Buddy-facing contract.

| Check | Result | Provenance |
| --- | --- | --- |
| C1/C2 World content available now? | No through Buddy | `POST /api/live/world-graph/projection` `{schema:dmb_world_graph_projection_request_v1, world_id:eldyrwild, campaign_id:longmont-c2}` → **503** `authority_unavailable` / “DungeonMind authority is unavailable.” |
| Buddy surfaces query/use it? | Chrome tries; fails | `LIVE-READ` World chip on Ingest/Plan/Play |
| Visible “Graph” / World error origin | `AppChromeWorldGraphStatus` / `presentWorldGraphChromeStatus` from lens 503 — **not** recap pills | `LIVE-READ` + `CODE-ONLY` |
| Surfaces with useful World context | none observed | `LIVE-READ` |
| Recap pills/nodes use current World vs local artifacts? | neither: pills not rendered; candidate graphs are local `out/` URIs recorded on `ingest.run` (32 complete bundles on `primary-checkout`; see library §2.3) | `LIVE-READ` + library |
| NPC/place/threat openable from normal use? | not from this recap path; World chip error | `LIVE-READ` |

Do not bypass DungeonMind or give Buddy graph-architecture ownership to make chrome look healthy.

---

## Persistent application shell

Exercised: Plan → Build → Ingest → Play → Plan.

| Observation | Evidence |
| --- | --- |
| Full document navigation | `AppChrome` renders `<a href={item.href}>` (`AppChrome.tsx`). No React Router. |
| What remounts | `App.tsx` `window.location.pathname` switch mounts `PlanSurfacePage` / `BuildSurfacePage` / `MemoryIngestPage` / `PlaySurfacePage`. World lens + Agent chrome remount with the document. |
| Campaign/session/object context | Ingest `?session=&campaign=&run=` did **not** survive `/plan`. |
| Agent continuity | Shared provider is inside the document; in-memory lease is lost on navigation/reload. Threads in localStorage are `CODE-ONLY`. |
| World chip | Brief `World · C2 · Loading…` then `authority_unavailable` after each remount. |
| In-tab click quirk | With Graph Review load-dialog backdrop, Plan click was intercepted (`graph-review-projected-interaction-backdrop`). After close, in-tab `<a>` click still did not navigate in this browser automation; `browser_navigate` completed the chain. Treat reload as **LIVE-READ URL remount + CODE `<a href>`**; do not over-claim the click quirk as product design. |

DFC-NAV1 already intended to solve persistent shell. Not implemented here.

---

## Agent readiness

Shared implementation: `AgentInteractionProvider` + `AgentInteractionChrome` in `App.tsx` (not four separate Agents).

**Disposition:** `NOT_CONNECTED` on all four surfaces. Visible shared chrome alone is not user-usable: there is no historical Plan/Build/Play object, no readable recap/object context on Ingest, and no exercised ask/write flow in this survey (`LIVE-READ` + `CODE-ONLY`).

| Surface | Affordance visible? | Provider | Campaign | Session | Object/revision | Selected text/object | World | Answer vs write | Write approval | Survives nav? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Plan | Agent region yes; ask bar in shell not exercised | shared | default chrome campaign, not recovered Plan | no historical session | no APP-STATE Plan | `CODE-ONLY` | 503 | ask bar exists (`CODE-ONLY`) | not live-proven | lost on remount |
| Build | region yes | shared | empty source | no | no | no | 503 | not exercised | n/a | lost |
| Ingest | region yes; no ask chrome observed | shared | bound C1/C2 after Load | bound session | catalog run id, not review package | no recap selection | 503 | not exercised | promote is separate Ingest workflow | lost; ingest query dropped |
| Play | region yes | shared | empty until campaign typed | no | no Run | no | 503 | not exercised | n/a | lost |

Distance from “use the Agent naturally from every surface”: chrome is already shared; **useful context and exercised interaction are missing**. Navigation remount is a second gap.

---

## Persistence / VPC-readiness inventory

| Demo dependency | Current authority class |
| --- | --- |
| Leftover ingest.run catalog (53) | APP-STATE PostgreSQL (local `127.0.0.1:54329`) |
| Plan/Runbook/Play WorkObjects | APP-STATE PostgreSQL — **empty** |
| Canonical recap Markdown | Git-tracked file |
| candidate_graph / source_span_index / validation_report | local untracked artifact / repo-relative `out/` on `primary-checkout`; missing on this checkout |
| ingest.run component URI/sha256 claims | APP-STATE PostgreSQL |
| World / graph objects | DungeonMind controlled remote — **unavailable** |
| World chrome status | generated/transient (lens fetch) |
| `local-plan:` drafts | browser local/session storage (`LIVE-READ` id; authority class inferred) |
| Agent threads | browser localStorage (`CODE-ONLY`) |
| Agent in-memory lease | generated/transient |
| UI Vite / API process | generated/transient |
| Of Conks / stewardship-si6 registries | Git-tracked / local historical roots — locators only |

What prevents “the laptop no longer owns durable reading/writing state”:

1. Review/candidate bytes live under gitignored `out/` on a specific checkout.
2. Leftover APP-STATE is a local Postgres that has already lost DFC-2a Plans on tmpfs recreate.
3. DungeonMind remote authority is down from Buddy’s contract.
4. Recaps are git-tracked (good) but Graph Review does not read them when the run is not `reviewable`.

VPC design is out of scope.

---

## Navigation / assembled dogfood log

| Stop | Result |
| --- | --- |
| Start DungeonBuddy | API `:8000` + UI `:5173` from this worktree |
| C1 Session 10 | Load recap → validated, no prose |
| C2 Session 23 | Load recap → validated, no prose; richest catalog session |
| C2 Session 25 | Load recap → validated, no prose (resolver dead-end) |
| C1 Session 1 | Catalog + gold expected; not reviewable |
| Plan | blank/local-draft; 0 APP-STATE Plans |
| Build | empty chooser |
| Ingest | 53-history workbench |
| Play | no Runs/Runbooks |
| Plan→Build→Ingest→Play→Plan | document remount; ingest selection dropped |

No real C1/C2 prose, status, graph, Runbook, Plan, or Ingest lifecycle was mutated.

---

## Mutation / non-ingestion proof

```text
ingest identity digest before/after    59508725ad56789bc333af3cea9f311dda55b8eac1b89aa4639c49278b40f5f1
leftover ingest.run count              53 unchanged
new historical ExtractionRun           none
historical pipeline invocation         none
leftover Plan/Runbook/Play writes      none
product path edits                     none (docs only)
```

Post-merge leftover ingest apply that populated these 53 rows happened **before** this survey as operator dogfood of DFC-2c. This PR did not re-apply or re-ingest.

---

## Evidence provenance gaps

- In-tab AppChrome click did not navigate under this browser automation; URL remount was used. Full-page reload is still established by `<a href>` + remount observations.
- API process restart was not repeated (predecessor DFC-2c W11 already proved leftover catalog remount after restart).
- Plan/Build/Play save/reopen not live-proven against disposable authority.
- Agent ask/write approval not clicked.
- A11y snapshot of C2S23 picker listed fewer options than the 10 catalog runs; do not claim the UI hides runs without a second count.
- Ingest Recap tool button click failed (overlay/scroll); that panel is not claimed.
- `current-main` missing `out/` is **not** proof bytes are globally missing (`primary-checkout` still holds 31 complete triples).

---

## Materials / roots not fully re-opened

- Did not reopen Of Conks as a running product (file compare of hover/card components only).
- Did not dump every World node (forbidden / unnecessary).
- Did not copy or hash every `out/` component file; library §2.3–§2.4 records APP-STATE URI + SHA-256 for all 53 runs and path existence for `primary-checkout` / `current-main`.
- Did not re-adopt Plan `80630cc2-…` (would be a write).

---

## Proposed implementation sequence

Ranked by impact on: **a human can pleasantly use the existing C1/C2 corpus end-to-end.**

This does **not** automatically inherit DFC-2b / BF3B. Recommendation only; no successor handoffs in this PR.

### 1. Historical recap inspect-without-promote

```text
user-visible outcome
  Load a catalog-visible C1/C2 history run (validated/prepared) and read the
  actual recap comfortably, without implying promotion/reviewable.

evidence that justifies it
  C1S10 / C2S23 / C2S25 all bind then dead-end: no prose + 422 run_not_promotable.
  Recap Markdown is already git-tracked.

likely owning boundary
  Graph Review exact-run resolver / review-package seam (inspect vs promote).

what remains false afterward
  Pills, Threat/statblock, Agent recap context, World, NAV1, Plan/Build/Play.

collision/ordering dependency
  First. Do not silently remap validated → reviewable.
```

### 2. Serve exact review-supporting artifact bytes (no re-ingest)

```text
user-visible outcome
  When inspect needs candidate graph / span index, those bytes resolve from
  durable storage instead of primary-checkout out/.

evidence that justifies it
  0/53 complete triples on current-main; 32/53 on primary-checkout with explicit URI+digest
  recorded in APP-STATE (library §2.3); leftover rows already store component claims;
  unavailable_component_count was 246 at DFC-2c apply.

likely owning boundary
  Artifact storage / ingest.run component resolution (not extraction pipeline).

what remains false afterward
  Pill UX until a rendering path uses the spans; World remote; NAV1.

collision/ordering dependency
  After or with (1). Copy/adopt is a write; this survey only names it.
```

### 3. Recap entity pills + object inspect on the readable path

```text
user-visible outcome
  Entity-linked terms in historical recap; click/hover opens useful object
  cards; Threat glance if the node is a Threat.

evidence that justifies it
  Exact-run is plain <pre>; catalog projection retired; GraphNodeHoverToken
  and ThreatCampaignGlance exist on main but are unused here.

likely owning boundary
  Graph Review exact-run / markdown projection lane (not a new graph kernel).

what remains false afterward
  DungeonMind chrome if still 503; Agent; NAV1; Plan/Build/Play emptiness.

collision/ordering dependency
  Needs (1) readable prose; (2) if pills require span/candidate bytes.
```

### 4. Restore DungeonMind Buddy-facing availability

```text
user-visible outcome
  World chip is healthy; surfaces can query C1/C2 World without a Graph error.

evidence that justifies it
  503 authority_unavailable is the visible Graph/World error on Plan/Ingest/Play.

likely owning boundary
  DungeonMind service / Buddy world-graph proxy configuration — not Buddy graph ownership.

what remains false afterward
  Recap inspect if (1) unbuilt; NAV1; historical Plan/Play.

collision/ordering dependency
  Independent of recap resolver; parallel after (1) is in flight if leases split.
```

### 5. DFC-NAV1 persistent shell

```text
user-visible outcome
  Plan → Build → Ingest → Play without full document reload; ingest selection
  and Agent chrome survive.

evidence that justifies it
  <a href> remount; ingest query dropped; World chip reloads.

likely owning boundary
  AppChrome / router / App.tsx (existing DFC-NAV1 intent).

what remains false afterward
  Empty Plan/Build/Play catalogs; recap inspect if unbuilt.

collision/ordering dependency
  Independent of (1) on a split lease; do not combine with recap resolver.
```

### 6. Agent recap/object context on Ingest (then other surfaces)

```text
user-visible outcome
  From Graph Review, Agent can answer about the current recap or selected entity.

evidence that justifies it
  Shared Agent region exists; snapshot showed no ask chrome; no recap text to share.

likely owning boundary
  Agent surface-context publication on Ingest (shared provider already exists).

what remains false afterward
  Write-approval productization; Play/Plan material gaps.

collision/ordering dependency
  After (1); after (5) if continuity across surfaces is required.
```

### 7. Re-adopt surviving exact Plan bytes into leftover APP-STATE

```text
user-visible outcome
  /plan can open the one historically recovered C2 Session 27 Plan if those
  bytes still exist.

evidence that justifies it
  leftover list_plans() = 0 after Postgres recreate; DFC-2a recovered 80630cc2-…
  exactly once; local-plan chooser residue is not that WorkObject.

likely owning boundary
  DFC-2a-style Plan exact adoption against leftover (write). Confirm bytes first.

what remains false afterward
  Four missing-byte Plan identities (DFC-2p); Build; Play.

collision/ordering dependency
  Independent of recap inspect; do not invent prose for missing-byte Plans.
```

### 8. DFC-2b / DFC-2p / Play — later

```text
user-visible outcome
  Only if exact bytes/metadata become safe: Build adapter, Plan archive hunt,
  or a real C1/C2 Runbook. Otherwise leave empty.

evidence that justifies it
  Build four NEEDS_ADAPTER; Play admitted 0; four Plan identities lack bytes.

likely owning boundary
  existing DFC-2b / DFC-2p / DFC-2d

what remains false afterward
  Convention Play stories (BF3B/Combat) until playable C1/C2 exists.

collision/ordering dependency
  After human recap demo is pleasant; do not sequence BF3B ahead of recap.
```

---

## Explicit non-claims

- No product implementation in this PR.
- No historical content regenerated or re-ingested.
- No leftover C1/C2 mutation.
- Of Conks is not the surveyed corpus.
- Catalog visibility is not reviewability.
- `CODE-ONLY` is not `READY`.
- `current-main` missing `out/` is not `MISSING_BYTES` globally.
