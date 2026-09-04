# REPORT — SURFACE-INTEGRATION SI-6 clean-start assembled witness

**Created:** 2026-09-04  
**Buddy tip under witness:** `5e192966ae2086267569a7dbc5397852b7735550`  
**#681 merge ancestor:** `9d8c8a51c10bb2eb56739bc2661cb37f9f401ebb`  
**Stewardship handoff:** `Docs/Plans/HANDOFF-STEWARDSHIP-finish-surface-integration.md`  
**Judgment:** **ACCEPT** — assembled Surface Information / authority contract proven for the SI-6 journey; remaining gaps are non-blocking product work (post–SI-7 / CON-READY).

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
Ingest authority: EMPTY → READY after seeded ExtractionRun
Campaign registry: NOT_CONFIGURED (informational)
```

After API process kill/restart: Ingest remained **READY** with the same two APP-STATE runs; no `out/` tree required.

---

## 2. Phase B dispositions (no SI-5C/D code)

| Area | Disposition |
|---|---|
| Play | **NO CODE** — v2 path already APP-STATE-backed; SI-6 saw truthful EMPTY chooser |
| Combat | **NO CODE** — SI-6 journey does not consume changing Combat observations |
| Agent / #674 | **CLOSE/SUPERSEDE** — PR #674 closed 2026-09-04; A7 Play SurfaceContext remains on main; A8 Play Ask deferred |

---

## 3. Browser journey evidence

### 3.1 World chrome

- `/plan`, `/build`, `/ingest`, `/play`: **World · C2 · Ready** when DungeonMind authority is reachable.
- Ask chrome: **“Open Plan to enable graph-grounded ask”** on Build/Ingest — honest empty Ask plugin (supports #674 disposition).

### 3.2 Plan

- `/plan` loaded prep canvas with World Ready.
- World Graph retrieval API (owning boundary, not helper):

```text
POST /api/live/world-graph/retrieval/search
schema=dmb_world_graph_search_request_v1
worldId=eldyrwild campaignId=longmont-c2 queryText=Lysandra
→ dmb_world_graph_retrieval_result_v1 outcome=truncated matchedNodeIds includes npc_lysandra
```

### 3.3 Build

- `/build` with World Ready and empty source chooser (“Choose or create a source above”) — no fabricated source identity.
- Find-existing object UI not exercised with a loaded source in this run; World search API above is the shared World information contract used by Build SI-5A.

### 3.4 Ingest (SI-5B contract)

1. Initial clean catalog: UI **“No canonical ExtractionRuns are stored yet.”** while `out/` absent.
2. Seeded APP-STATE `ExtractionRun` `er_si6_6828bd1d89aa` (`campaign_id=longmont-c2`, `session_id=session-si6`, `status=reviewable`) with missing component URIs / missing SourceArtifact.
3. Load dialog showed **Live (canonical): er_si6_6828bd1d89aa** (after catalog refresh).
4. Load wrote URL:

```text
/ingest?session=session-si6&campaign=longmont-c2&run=er_si6_6828bd1d89aa
```

5. Hard reload of that URL restored **Exact run er_si6_6828bd1d89aa** with banner “Bound to exact ExtractionRun … no latest-run fallback.”
6. Exact review failed closed after identity fixed: `unknown source_artifact_id: sa_si6_…` (run remained catalog-visible). Preferred W10 “component file missing” seam was not re-dogfooded with a seeded SourceArtifact in this witness; server W10 already covers that seam on #681.
7. API process restart preserved both catalog rows with **no** `out/graph_memory/runs`.

### 3.5 Play

- `/play` chooser: **“No durable Runs are available.”** / **“No active Runbooks are available.”**
- Create blank / Start exact Run disabled until campaign/runbook chosen — does **not** invent a run from authored files.
- Full start-run → progress → reload resume not exercised in this witness because no startable Runbook was imported; APP-STATE Play durability remains covered by existing owning-boundary Postgres tests (`test_new_app_instance_and_different_root_resume_exact_current_moment`) plus this truthful EMPTY surface.

### 3.6 Combat / Agent

- Combat not used by journey (Phase B.2).
- Agent: Plan Ask available when Plan is open; Play Ask not present; #674 closed/superseded.

---

## 4. Phase D checklist

| # | Requirement | Result |
|---|---|---|
| 1 | World via supported DungeonMind config | **PASS** — preflight READY; World Ready chrome |
| 2 | Plan graph information reactive / truthful | **PASS** — Plan loads; World search returns head-scoped result |
| 3 | Build uses same World information contract | **PASS** — World Ready on Build; shared retrieval API succeeds |
| 4 | Ingest existence/selection from APP-STATE; survives fresh checkout/hard reload without `out/` | **PASS** |
| 5 | Play resumes durable moment from APP-STATE | **PASS (EMPTY + prior owning tests)** — surface does not reconstruct from files |
| 6 | Combat-owned if relied upon | **N/A** — not relied upon |
| 7 | Agent disposition explicit; no competing World/Play truth | **PASS** — #674 CLOSE/SUPERSEDE; A7 pointers + honest Ask empty |
| 8 | Unavailable/integrity fail visibly | **PASS** — exact-review SA miss visible; empty catalogs visible; World needs-attention when projection campaign mismatches |

---

## 5. Explicit non-blocking gaps

- PROMOTED historical exact inspection (named future seam).
- A8 Play Ask (closed #674; rebrief from CON-READY after thaw if desired).
- Blank Runbook / full Play resume dogfood in this environment (campaign field not auto-filled from World Ready).
- Build Find-existing UI click-path with a loaded source document.
- Campaign registry enumeration still NOT_CONFIGURED (informational since SI-1).
- Ingest catalog UI can briefly show EMPTY after external DB seed until refresh/event/remount — hard reload of exact `run=` URL is authoritative.

---

## 6. Acceptance

**SI-6 is ACCEPTED.**  

SURFACE-INTEGRATION’s blocking purpose — prove an assembled Buddy runtime can report and use its real authorities without silent file/latest reconstruction — is satisfied on tip `5e192966…`.  

Feature freeze may lift under SI-7 / CON-READY re-sequencing. Do not treat this ACCEPT as completion of all CON-READY user stories.
