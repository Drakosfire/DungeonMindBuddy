# Graph-memory recap ingest dogfood notes

**Purpose:** Capture friction and product observations while dogfooding the raw-recap → recap memory → preview graph → Recap View loop.

**Scope:** Ingest UI, backend pipeline steps, graph preview artifacts, Recap View chips/evidence. **Not canon** and not a prep source.

**Last updated:** 2026-06-29

**Related surfaces:** `/plan` → Raw Recap Ingestion; `generate_recap_memory` with optional `include_graph_extraction`; Recap View at `/plan?tool=recap&session=session-N`.

---

## How to Log

Add a row when an action reveals friction, a product gap, or something that worked well.

| # | When | Surface | Observation | Severity | Follow-up |
|---|------|---------|-------------|----------|-----------|
| 1 | 2026-06-28 | Ingest Recap → Generate Recap Memory | The full ingest is a long blocking run (stage, normalize, frontmatter seed, breadcrumb LLM, session memory, optional graph extraction + preview union materialize). The UI does not show **what step is running now**, **what finished**, or **what is left** — only generic copy like "Running full ingest..." / "Running recap + preview graph...". Operator cannot tell whether the job is stuck, slow, or progressing. | High | Add a live step progress model in the UI: current step label, completed steps, remaining steps, and optional per-step status (running / done / skipped / failed). Backend may need incremental status or staged polling; at minimum, surface the known pipeline order during the wait. |

| 2 | 2026-06-28 | Ingest Recap → Recap / Graph Preview tools | Recap memory for **session 24** completed (`Session 24 - 4.md`, normalized + breadcrumb + session memory on disk). Ingest UI shows a rendered preview of pasted raw text. Opening **Recap** or **Graph Preview** from the Plan toolbox fails or shows nothing useful. Root causes: (1) Plan context defaults to `ingestSession = liveSession - 1` (currently **session-21** when live workspace is 22), not the session number typed in Ingest Recap (**24**). (2) No graph-ingest run was created under `out/graph_memory/runs/` from this ingest — only an unrelated manual dogfood fixture (`session_24_manual_projection_dogfood`) registers as `preview_union_store_ready`, with placeholder recap text. (3) `_normalized_recap_graph_path` returned a corpus-relative path without joining `corpus/eldyrwild-markdown/` when `DUNGEONMIND_RECAP_INGEST_CORPUS_ROOT` is unset, so `include_graph_extraction` could not find the normalized recap file. (4) Union projection had no recap-first fallback when graph store markdown was empty. | High | Pass ingested session through Open Recap URL (`?session=session-24`); align toolbox session lens with ingested session; fix corpus path join; recap-first corpus fallback; re-run graph extraction after fix. |
| 3 | 2026-06-28 | Ingest Recap → Recap tab | Pasted raw ingest should make the Recap tab usable as soon as recap memory materializes. The previous Recap tab success path still treated **union-supergraph projection loaded** as the gate, so a missing latest graph-ingest manifest could block the whole recap reader or fall through to an unrelated default fixture. | High | Make Recap tab recap-first: if the selected session exists in the recap artifact registry but latest graph ingest is missing, load a clearly labeled **recap memory only** projection with zero graph mentions; graph pills/chips become an enhancement instead of a prerequisite. |
| 4 | 2026-06-28 | `/plan` toolbox session lens | Requiring `/plan?tool=recap&session=session-24` or `/plan?tool=graph-preview&session=session-24` after pasted raw ingest is wrong. Plain `/plan` should be the stable entry point; the toolbox can infer ingested sessions from the canonical recap artifact registry that already backs the session dropdown. | High | Recap / Graph Preview should default to the latest registered ingested recap artifact when no explicit `session=` deep link overrides it. |
| 5 | 2026-06-28 | Recap tab → Session 24 placeholder leak | Recap displayed `Session 24 Raw Recap Placeholder` from `session_24_manual_projection_dogfood`, even though the operator had ingested real pasted raw notes. Root causes: the artifact registry was stale and did not scan the canonical corpus `_normalized` save path, while latest graph-ingest discovery accepted an unrelated manual fixture for the same `(campaign, session)` without proving it came from the selected recap artifact. | Critical | Registry must infer ingested recaps from canonical normalized corpus files. Graph projection must be lineage-filtered by source recap path / normalized recap SHA. Product Recap must not fall back to fixture content when no constructed artifact exists. |
| 6 | 2026-06-28 | Recap tab → graph pills absent | The Recap dropdown now browses all 24 Campaign 2 normalized recaps, which is good, but none render graph pills. This proves the UI is rendering recap-only normalized markdown, not graph-projected markdown. On disk, the product graph-ingest registry finds no preview-union graph-ingest runs for Sessions 22/23 and only the rejected manual placeholder fixture for Session 24; candidate/gold/category-study artifacts are not yet product-ready graph projection artifacts. | High | Make the one-click ingest path produce a lineage-matched `preview_union_store_ready` graph-ingest run, then have Recap load that projected markdown. UI should label states clearly: raw/normalized recap-only, candidate graph ready, preview union ready, graph-projected recap with pills. |
| 7 | 2026-06-29 | Ingest Recap → re-run category graph extraction | Re-running LLM ingestion should **not** require starting from raw pasted notes. Operator wants to load an already-processed session (e.g. Session 23 normalized recap on disk) and jump straight to the **category graph extraction** step — source spans → 7-pass extract → preview union → projection. Today the UI still reads as a single raw→full-pipeline flow. | **Critical — pre-dogfood** | Add a **resume-from-checkpoint** entry point: select session / normalized recap artifact → run graph extraction only (`include_graph_extraction` without re-staging raw). Surface which upstream steps are already satisfied (normalized recap exists, source spans materialized, etc.). |
| 8 | 2026-06-29 | Ingest Recap → prior run inventory | No way to **view or interact with prior graph-ingest runs** and see **which step each run reached** (normalized only, spans ready, actor pass done, …, preview union ready). Operator cannot tell whether to resume, compare, or discard a partial run. | **Critical — pre-dogfood** | Run list per `(campaign, session)`: manifest status, current/last step, timestamps, model id, artifact paths. Allow open/resume from the run's checkpoint; distinguish live ingest runs from manual eval fixtures. |
| 9 | 2026-06-29 | Ingest Recap → duplicate session names | Stale or failed prior runs accumulate; re-ingesting the same session triggers **duplicate name / collision friction** (normalized recap collisions, ambiguous registry entries, operator confusion about which run is canonical). | **Critical — pre-dogfood** | **Delete run** (or archive-with-timestamp) for a session's graph-ingest artifacts + registry entry, with confirmation. Clearing a bad run should unblock a clean re-extract without manual corpus `_archive` surgery. |
| 10 | 2026-06-29 | Ingest Recap → in-flight progress copy | The spinning/working button does not update with the **current extraction pass** during category graph ingest. Operator sees generic "working" copy while 7 LLM passes run; cannot tell whether actors, edges, or union materialization is active. Category pipeline now has pass-level manifest steps on the backend, but the UI does not poll/stream them during the blocking POST. | **Critical — pre-dogfood** | Live step label on the working control: actors → locations → collectives → objects → threads → beats → edges → validation → union materialization. Requires incremental status (polling staged job, SSE, or split API) — static multi-pass message during wait is insufficient for dogfood. |

---

## Pre-dogfood blockers (category graph extract)

**Gate:** Do not treat category-graph dogfood as complete until items **#7–#10** are addressed. These are operator-facing requirements surfaced during first re-run of LLM ingestion (Session 23), not nice-to-haves.

| # | Requirement | Why it blocks dogfood |
|---|-------------|----------------------|
| 7 | **Resume from preprocessed state** — load Session N normalized recap, run graph extraction only | Re-running the LLM path from raw wastes time and re-triggers legacy breadcrumb noise; dogfood iteration is extraction-quality tuning |
| 8 | **Prior run inventory + step visibility** — list runs, show checkpoint/step reached | Cannot compare runs, resume partial work, or know what failed without filesystem archaeology |
| 9 | **Delete prior runs** — clear stale runs to fix duplicate-name collisions | Duplicate/collision friction makes every re-run painful and erodes trust in which artifact is canonical |
| 10 | **Live pass-level progress on working button** — update label per extraction pass | Multi-minute 7-pass runs feel hung; backend manifest steps exist post-hoc but not during the wait |

**Related implementation surfaces:** `IngestionModule.tsx` (run list, resume, delete, live step label); `recap_ingest.py` / `recap_graph_preview_ingest.py` (checkpoint-aware endpoints, run registry CRUD); `graph_preview_runner.py` manifest `steps` (already pass-level — wire to in-flight status).

---

## Friction and Product Ideas

| Observation | Why it matters | Candidate improvement | Priority |
|-------------|----------------|----------------------|----------|
| Long ingest with no step-level progress feedback | GM loses trust during multi-minute runs; cannot distinguish hang vs. slow LLM vs. near-complete | Progress strip or checklist: Source → Apply → Seed → Breadcrumb → Memory → Graph extract → Preview union → Done; highlight active step; show errors on the step that failed | ready |
| Recap / Graph Preview session lens ≠ ingested session | Operator ingests session N in the form but Plan toolbox assumes `liveSession - 1`; Recap defaults to wrong session and projection 404s or empty markdown | After ingest, always deep-link with `?session=session-N`; toolbox Recap/Graph should prefer URL session param or last-ingested session | ready |
| Graph panel shows ready from unrelated manual fixture | Ingest proof panel reports `preview_union_store_ready` even when user's run never extracted a graph | Registry should prefer runs tied to the same normalized recap hash / manifest lineage; distinguish manual fixtures from live ingest | ready |
| Recap View requires graph projection to show recap text | Recap memory exists on disk before graph extraction completes | Recap-first: load normalized recap from corpus when union store markdown is missing | ready |
| Recap tab treats graph readiness as the page readiness gate | Raw pasted ingest can be successful while graph extraction/materialization is blocked or pending | Add an explicit recap-only projection mode and label it clearly; show chip count as zero instead of failing the page | ready |
| Plain `/plan` forgets the pasted ingest session | Operator has to know implementation URLs instead of using the product entry point | Infer the default session from the canonical recap artifact registry that already populates the dropdown | ready |
| Manual graph fixture can masquerade as live ingested recap | Same `(campaign, session)` is insufficient lineage; placeholder content can leak into product UI | Require graph-ingest projection to match selected recap artifact path/SHA before showing graph chips; otherwise use recap-only or show unavailable | ready |
| Browseable recap text is not the same as graph-projected recap | Operator can browse normalized markdown and assume graph memory is attached, but pills require a lineage-matched preview union store | Show graph projection readiness per selected session and make one-click ingest produce the missing graph projection artifact by default | ready |
| Re-run graph extraction requires raw paste | Dogfood iteration is LLM extraction quality, not normalize/breadcrumb rework | Resume entry: pick session with normalized recap → "Run category graph extraction" only | **pre-dogfood** |
| No prior-run inventory or step checkpoint UI | Operator cannot see partial runs or choose which to resume | Per-session run list with manifest step, status, model, timestamps; open/resume actions | **pre-dogfood** |
| Stale runs cause duplicate-name collisions | Re-extract same session without cleanup hits registry/corpus collision friction | Delete (or archive) graph-ingest run + registry entry from UI with confirm | **pre-dogfood** |
| Working spinner shows generic copy during 7-pass extract | Backend has pass-level steps; UI does not update until POST completes | Poll/stream current graph step; update button label per pass (actors … union materialization) | **pre-dogfood** |

---

## Open Follow-ups

| Item | Status |
|------|--------|
| Step-level progress during `generate_recap_memory` | Logged (#1) |
| Recap/Graph Preview load failure after session-24 ingest | Logged (#2); corpus path + recap-first fallback patched |
| Recap-only fallback when graph projection is missing | Logged (#3); API + Recap tab fallback patched |
| Plain `/plan` should infer last ingested recap session | Logged (#4); artifact-registry default patched |
| Session 24 placeholder leak from manual fixture | Logged (#5); canonical registry scan + graph lineage filter patched |
| Recap-only browsing without graph pills | Logged (#6); needs one-click graph projection artifact generation |
| Resume graph extraction from normalized recap (no raw re-paste) | Logged (#7); **pre-dogfood blocker** |
| Prior run inventory + step checkpoint UI | Logged (#8); **pre-dogfood blocker** |
| Delete prior graph-ingest runs (duplicate-name cleanup) | Logged (#9); **pre-dogfood blocker** |
| Live pass-level progress on working button during category extract | Logged (#10); **pre-dogfood blocker** |
