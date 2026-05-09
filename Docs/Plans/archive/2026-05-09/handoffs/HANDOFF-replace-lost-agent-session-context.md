# Handoff: Replace Lost Agent Session (Context Bootstrap)

**Date:** 2026-04-03  
**Purpose:** Teach a new agent how to **consume** prior work quickly and safely after a long Cursor session was lost. This is a **map**, not a full spec. Follow links; verify with commands.

---

## 1) What you are inheriting

A prior multi-turn agent thread (parent transcript id: `90108b36-3536-4c48-a15d-c78916e08e70`) drove **Mirathorn vertical-slice hardening**, **readiness/falsification work**, **temporal selection fixes**, **benchmark artifact safety**, **ingest cost/cache improvements**, **frontmatter + ingest gates**, and a **RulesIngestion comparison design doc**. Your job is **not** to replay that chat; it is to **reconstruct truth from the repo + docs + tests**.

**Canonical machine-readable transcript (local only, not in git):**

`/home/drakosfire/.cursor/projects/home-drakosfire-config-Cursor-Workspaces-1774473223960-workspace-json/agent-transcripts/90108b36-3536-4c48-a15d-c78916e08e70/90108b36-3536-4c48-a15d-c78916e08e70.jsonl`

Cite that session to the user as: `[Lost-session recovery context](90108b36-3536-4c48-a15d-c78916e08e70)` (uuid only, no `.jsonl`).

---

## 2) Hard operational rules (DungeonMindBuddy)

- **Python:** always `uv run python …` and `uv run pytest …` (never bare `python` / `pytest`).
- **Primary repo for this work:** `DungeonMindBuddy/`.
- **Sibling repo:** `RulesIngestion/` is separate; compare patterns there, do not import across repos.
- **Secrets / models:** `.env.development` may live at workspace root  
`/home/drakosfire/Projects/DungeonOverMind/.env.development`  
with fallback resolution in Buddy—**tests that claim “no API key” behavior can be confounded** if dotenv repopulates keys. Treat “no key” as “absent from shell **and** absent from loaded env files” unless the test uses explicit isolation.

---

## 3) How to consume context (recommended reading order)

### Phase A — 10 minutes (orientation)

1. `**report/REPORT-current-status.md`** — current verified commands, gate outcomes, nano experiment caveats, git hygiene notes.
2. `**Docs/Design/DESIGN-ingestion-pipeline-architecture-and-refactor-assessment.md`** — **authoritative pipeline map** (CLI → frontmatter → chunk → entity → fact → stage artifacts → gates → store → projection/`ask`). Includes comparison to RulesIngestion and refactor posture (**incremental**, not rewrite).

### Phase B — 30 minutes (mission + skepticism)

1. `**Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-next-agent-mirathorn-event-slice.md`** — Mirathorn slice mission, non-negotiables, **Skeptical Investigation Continuation** block (Council Room gaps, temporal provenance, selection policy). This is the **active investigative brief** layered on top of “gates green.”
2. `**Docs/Design/REPORT-benchmark-shortcomings-and-successes.md`** (if present) — falsification themes: competing non-terminal facts, semantic scoring generosity, production-path canon decisions, artifact integrity, non-Mirathorn generalization.

### Phase C — deep dive (only when implementing)

1. **Code paths called out in the design doc** — start at `src/cli.py` (`ingest`, `ask`), then `src/ingestion/chunker.py`, `frontmatter.py`, `entity_extractor.py`, `fact_extractor.py`, `src/store.py`, `src/reducer/canon_projection.py`.
2. **Eval harnesses:**
  - `evals/llm_ingestion_slice/run_slice.py` — gates **A / V / B / C / D** for the event-sourced slice pack.
  - `evals/canon_layering/run_benchmarks.py` — reducer/scenario stress (includes non-terminal competing-facts scenario added during hardening).
  - `evals/mirathorn_vertical_slice/` — vertical slice experiments; **many outputs are runtime artifacts** (often untracked).

---

## 4) Mental model you must load

### Canon layers and campaign scope

- World evidence: `canon_layer=world`, `campaign_id=null`.
- Campaign evidence: `canon_layer=campaign`, `campaign_id` set.
- **Common benchmark footgun:** calling `ask` **without** `--campaign <id>` when post-play campaign facts are required. The investigation handoff explicitly treats this as a first-class failure mode.

### Temporal provenance (chronology)

- Facts carry `asserted_in_session` / `sequence_index_within_session` when the pipeline can infer or assign them (frontmatter + chunk metadata). **Absence** historically forced bad tie-breaks.
- Selection policy in `canon_projection.py` has been hardened to use **evidence `source_order_index` fallback** and more aggressive contradiction handling, but **cross-document narrative ordering** may still be incomplete—do not assume “chronology solved everywhere.”

### Ingest cost and caching

- `**--chunk-min-chars`** on `ingest` collapses small evidence units → fewer LLM calls (trade granularity for cost).
- Fact extraction cache keys were tightened toward **per-unit entity scoping** so unrelated entity-list growth does not invalidate the entire corpus cache.

### Benchmark artifact safety

- Council-room question-set writes were gated behind explicit opt-in:  
`**DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1`**  
plus non-empty answers. **Do not** assume “no API key” alone prevents writes if env loading restores keys.

---

## 5) Verification discipline (evidence before claims)

Run from `DungeonMindBuddy/`:

```bash
uv run ruff check .
uv run pytest tests/ --maxfail=1
uv run python evals/llm_ingestion_slice/run_slice.py
```

Optional deeper signals:

```bash
uv run python evals/canon_layering/run_benchmarks.py
```

**Interpretation:**

- `**run_slice` Gate A failures** usually mean **manifest / source file hash drift** (corpus edits without updating `evals/llm_ingestion_slice/slice_manifest.json`). This is **not** automatically “model regression.”
- `**evals/llm_ingestion_slice/output/current/`** and many `evals/mirathorn_vertical_slice/output/`* files are **runtime artifacts**; prefer **ignoring** them in commits unless the user explicitly wants baselines versioned.

---

## 6) How to choose your first task (triage)

Pick **one** lane; do not boil the ocean.


| If the user wants…                              | Start here                                                                                                                                   |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Continue Mirathorn / Council Room investigation | `HANDOFF-next-agent-mirathorn-event-slice.md` → run the **Required Minimal Experiments** with logged evidence                                |
| Pipeline efficiency / refactor                  | `DESIGN-ingestion-pipeline-architecture-and-refactor-assessment.md` → implement highest-ROI staged item (often batching or shared substrate) |
| Chronology correctness end-to-end               | Trace `frontmatter` → evidence unit session fields → fact fields → `canon_projection` selection; add a **failing-then-passing** benchmark    |
| Green CI / clean tree                           | `git status`, separate commits: **source/tests/schemas** vs **generated outputs**                                                            |


---

## 7) What to tell the user after bootstrap

A good first response includes:

- Which **doc + code path** you treated as canonical (usually the design doc + one handoff section).
- **Exact commands** you ran and **pass/fail**.
- Whether failures are **hash/manifest**, **test**, **environment**, or **logic**—with **one** concrete next action.

---

## 8) Explicit non-goals for this bootstrap handoff

- It does **not** restate the full Mirathorn plan; use `HANDOFF-next-agent-mirathorn-event-slice.md`.
- It does **not** freeze architecture forever; the design doc is versioned narrative—**verify against code** when they diverge.

