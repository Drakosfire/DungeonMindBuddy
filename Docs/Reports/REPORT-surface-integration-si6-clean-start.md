# REPORT — SURFACE-INTEGRATION SI-6 clean-start assembled witness

**Created:** 2026-09-04  
**RC1 repair:** 2026-09-04 (after formal review `5108972325` on PR #682 @ `a5f3d816…`)  
**Buddy tip under witness:** `5e192966ae2086267569a7dbc5397852b7735550`  
**#681 merge ancestor:** `9d8c8a51c10bb2eb56739bc2661cb37f9f401ebb`  
**Stewardship handoff:** `Docs/Plans/HANDOFF-STEWARDSHIP-finish-surface-integration.md`  
**Judgment:** **PENDING STEWARD RE-REVIEW** — RC1 P1/P2 witness gaps closed in this revision; freeze remains until ACCEPT.

---

## 1. Environment (no credentials)

| Item | Value |
|---|---|
| Worktree | `DungeonMindBuddy-stewardship-finish-si` |
| APP-STATE DB | `dungeonbuddy_application_state` @ `127.0.0.1:54329` (created via `bootstrap_local_play.py apply`; schema `20260902_0005`) |
| World Graph DB | `dungeonmind_cutover_live` restored from local Aug-23 dump, then `alembic upgrade` `0006→0007` |
| Required world | `eldyrwild` genesis `existing_world_adoption` head `rev:680c2460…` |
| `out/graph_memory/runs` | **absent** (clean-start; no file-run authority) |
| API | `uvicorn apps.live_control_server.main:app` `:8000` |
| UI | Vite `:5173` (polling mode; inotify ENOSPC workaround) |

Operator preflight (after World migrate + APP-STATE bootstrap):

```text
Overall: READY
Buddy application state: READY (0 startable runbooks initially; empty valid)
DungeonMind World Graph: READY (1 world: eldyrwild)
Ingest authority: EMPTY → READY after seeded ExtractionRun(s)
Campaign registry: NOT_CONFIGURED (informational)
```

After API process kill/restart: Ingest catalog remained **READY** with the **same two** APP-STATE runs (see §3.4 accounting); no `out/` tree required. Play active-run pointer also survived restart (see §3.5).

---

## 2. Phase B dispositions (no SI-5C/D code)

| Area | Disposition |
|---|---|
| Play | **NO CODE** — v2 path already APP-STATE-backed; RC1 assembled resume exercised via blank Runbook |
| Combat | **NO CODE** — SI-6 journey does not consume changing Combat observations |
| Agent / #674 | **CLOSE/SUPERSEDE** — PR #674 closed 2026-09-04; A7 Play SurfaceContext remains on main; A8 Play Ask deferred |

---

## 3. Browser journey evidence

### 3.1 World chrome

- `/plan`, `/build`, `/ingest`, `/play`: **World · C2 · Ready** when DungeonMind authority is reachable.
- Ask chrome: **“Open Plan to enable graph-grounded ask”** on Build/Ingest — honest empty Ask plugin (supports #674 disposition).

### 3.2 Plan (RC1 — reactivity + fail-closed)

Assembled reactivity (not API-only):

1. `/plan` with prep canvas mounted and World chrome **Ready** showing **80 nodes** (Focus session = None / plain union).
2. Changed Focus session to **C2 · Session 25** via World chrome while Plan canvas stayed mounted.
3. Chrome updated in place to **World · C2 · S25 · Ready**; URL became `/plan?campaigns=longmont-c2&session=longmont-c2%3A25` without reconstructing prep from a new surface mount.

Owning SI-3 structural-stability proof (no structural-publication churn on graph channel resolve):

- `apps/live-control-ui/src/planSurface/PlanSurfaceGraphInformation.integration.test.tsx` — *“updates the mounted Edit World Graph objects panel without graph-driven editorTools republication”* (LOADING → READY keeps the same panel instance; `onEditorToolsChange` not called on resolve).

Authority outage browser witness (safe local dependency unavailable; then restored):

1. Pointed only `DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL` at unreachable `127.0.0.1:59999`, restarted API (APP-STATE DSN untouched).
2. Hard-navigated `/plan`: World chrome showed **World · Needs attention · DungeonMind authority is unavailable. (authority_unavailable)**.
3. Expanded chrome: **no Ready node-count fallback**; projection API returned `503` / `dmb_world_graph_projection_error_v1` / `code=authority_unavailable`.
4. Restored `.env` from backup and restarted API; projection returned `200` with 80 nodes again.

INTEGRITY_ERROR remains covered by the same owning Plan Surface Information suite (*“renders verification failures as INTEGRITY_ERROR, not EMPTY”*) plus the browser UNAVAILABLE path above for dependency outage.

### 3.3 Build (RC1 — loaded source + Find-existing UI)

1. `/build` → **+ New source** → destination `longmont-c2`, title **SI-6 Find-existing Witness** → created document `d10bd414-d461-48eb-a514-2c34d0fe2d8d`.
2. URL: `/build?documentId=d10bd414-d461-48eb-a514-2c34d0fe2d8d&campaign=longmont-c2`.
3. Tools → **World Graph Find existing object** opened with:

```text
longmont-c2 · Current head · loaded rev:680c246047d67f9fe0293ee90526f670
```

4. Search **Lysandra** → results included **Captain Lysandra Ironveil** and **Lysandra**.
5. **View** on Captain Lysandra Ironveil opened Reference article with related objects + evidence badges (session_recap domains) — assembled Build UI, not retrieval API alone.

Supporting owning tests (non-substitute): `BuildReferenceCapability.test.tsx` Find-existing paths; structural non-republish *“does not republish Surface Interaction when graph channel commits LOADING → READY”*.

### 3.4 Ingest (SI-5B contract) + run accounting

1. Initial clean catalog: UI **“No canonical ExtractionRuns are stored yet.”** while `out/` absent.
2. **Two** APP-STATE seeds (explains “same two APP-STATE runs” after restart):

| Order | `run_id` | `campaign_id` | `session_id` | Notes |
|---|---|---|---|---|
| 1 (mis-aimed UI campaign) | `er_si6_cf27a1748f35` | `eldyrwild` | `session-si6` | Seeded first; wrong campaign for the `/ingest` longmont-c2 chooser path |
| 2 (journey run) | `er_si6_6828bd1d89aa` | `longmont-c2` | `session-si6` | Catalog-visible Live (canonical) row used for exact load |

3. Load dialog showed **Live (canonical): er_si6_6828bd1d89aa** (after catalog refresh).
4. Load wrote URL:

```text
/ingest?session=session-si6&campaign=longmont-c2&run=er_si6_6828bd1d89aa
```

5. Hard reload of that URL restored **Exact run er_si6_6828bd1d89aa** with banner “Bound to exact ExtractionRun … no latest-run fallback.”
6. Exact review failed closed after identity fixed: `unknown source_artifact_id: sa_si6_84bcd808` (run remained catalog-visible). Preferred W10 “component file missing” seam was not re-dogfooded with a seeded SourceArtifact in this witness; server W10 already covers that seam on #681.
7. API process restart preserved **both** catalog rows (`er_si6_cf27a1748f35` + `er_si6_6828bd1d89aa`) with **no** `out/graph_memory/runs`.

### 3.5 Play (RC1 — assembled start-run → moment → reload → API restart)

Supported blank Runbook path (not EMPTY-as-PASS):

1. `/play`, campaign `longmont-c2` → **Create blank Runbook** → playable artifact `f1ae51e5-bdba-4aa7-8fb9-5890aaef6433`.
2. **Start exact Run** → `6136bf90-45c3-4462-ae77-6c2984de3b67` with `playable_revision=1`, `playable_content_sha256=c51e34307d0e33df97eaa2271567f6e63db5d3dee280a129ce936c1c55d8ede7`.
3. Established durable current moment: **Untitled Beat** `beat:0ca9ab6c-2378-422c-9eb5-daf65c9f3b36` (`current_scene_id=null`).
4. Hard reload of `/play?run=6136bf90-45c3-4462-ae77-6c2984de3b67` restored the **same** run + pinned revision + beat.
5. API process kill/restart; navigate `/play` (no query) → `GET /api/live/play-active-run` returned the same `run_id`; UI resumed the same beat/moment from APP-STATE (not authored-file reconstruction).

Prior EMPTY-chooser observation remains historically true for the pre-seeded environment but is **no longer** the acceptance evidence for requirement 5.

### 3.6 Combat / Agent

- Combat not used by journey (Phase B.2).
- Agent: Plan Ask available when Plan is open; Play Ask not present; #674 closed/superseded.

---

## 4. Phase D checklist

| # | Requirement | Result |
|---|---|---|
| 1 | World via supported DungeonMind config | **PASS** — preflight READY; World Ready chrome |
| 2 | Plan graph information reactive / truthful | **PASS** — Focus session change updates chrome in place; SI-3 owning non-republish test cited |
| 3 | Build uses same World information contract | **PASS** — loaded source + Find-existing UI View path |
| 4 | Ingest existence/selection from APP-STATE; survives fresh checkout/hard reload without `out/` | **PASS** |
| 5 | Play resumes durable moment from APP-STATE | **PASS** — blank Runbook → start-run → beat → hard reload → API restart |
| 6 | Combat-owned if relied upon | **N/A** — not relied upon |
| 7 | Agent disposition explicit; no competing World/Play truth | **PASS** — #674 CLOSE/SUPERSEDE; A7 pointers + honest Ask empty |
| 8 | Unavailable/integrity fail visibly | **PASS** — World `authority_unavailable` browser chrome (no Ready fallback); Ingest exact-review SA miss; Plan INTEGRITY owning test retained |

---

## 5. Explicit non-blocking gaps

- PROMOTED historical exact inspection (named future seam).
- A8 Play Ask (closed #674; rebrief from CON-READY after thaw if desired).
- Campaign registry enumeration still NOT_CONFIGURED (informational since SI-1).
- Ingest catalog UI can briefly show EMPTY after external DB seed until refresh/event/remount — hard reload of exact `run=` URL is authoritative.
- Browser INTEGRITY_ERROR injection not re-dogfooded in RC1 (owning Plan test retained); UNAVAILABLE dependency outage was witnessed live.

---

## 6. Acceptance

**SI-6 is not self-ACCEPTED in this revision.**  

RC1 required Play resume, Build Find-existing, Plan reactivity/fail-closed, and two-run accounting. Those clauses are now documented with assembled evidence above.  

Feature freeze **remains in force** until the steward re-reviews PR #682 and records ACCEPT. Do not treat this report revision as thaw or SURFACE-INTEGRATION CLOSED.
