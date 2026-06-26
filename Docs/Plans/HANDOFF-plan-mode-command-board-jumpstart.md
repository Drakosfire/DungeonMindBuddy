# HANDOFF — Plan Mode Command Board Jumpstart

**Created:** 2026-06-20  
**Status:** ACTIVE — prime agent re-anchor for Command Board Plan surface + recap ingest v1  
**Not an external-worker PR handoff** — design docs landed; implementation follows Plan anchor pane + deterministic ingest wizard.

---

## §0 Read This First

DungeonBuddy Command Board has **three named surfaces** — Plan, Play, Build — projecting the same campaign memory differently.

| Surface | Status | Role |
|---------|--------|------|
| **Plan** | Active design + first implementation slice | Anchor pane when overlays close; workshop; recap ingest; runbook/Tiptap prep; corpus indexes |
| **Play** | Active design | Focused beat, overlays, combat cockpit, rules hovers — no place loss |
| **Build** | Named, **not designed or built yet** | Future durable world objects (NPCs, locations, items, adversaries, rules depth) |

**Surfaces teach each other.** Each surface is a consumer and writer of lessons about the others. Record friction in dogfood notes so Build inherits evidence, not guesses.

**First Plan proof slice:** deterministic recap ingest through normalize, then **visible stop at `breadcrumb_required`**. Do not claim retrieval-ready until breadcrumb + session memory exist.

**Anchor phrase:** Runbook Lantern — reload `Docs/Design/ANCHOR-runbook-lantern.md` when context drifts.

---

## §1 Canonical design docs (read order)

1. `Docs/Design/DESIGN-play-mode-runbook-product-direction.md` — three-surface model; Plan vs Play; Build named
2. `Docs/Design/ANCHOR-runbook-lantern.md` — Layer 2 = Plan anchor pane; authority separation
3. `Docs/Design/DESIGN-runbook-roadmap-and-session-ingestion.md` — **§ Plan-mode recap ingest v1**
4. `Docs/Plans/DESIGN-session-runbook-command-surface.md` — §8 Plan anchor pane vs Play overlays
5. `Docs/Plans/C2S21-S22-DEMO-ARCHITECT-SESSION-NOTES.md` — full ingest stack §9; frontmatter seed gap
6. `Docs/CONVENTION-Session-Recap-Normalization.md` — normalized recap contract
7. `Docs/CONVENTION-Session-Recap-Breadcrumbs-Session-Memory-And-Tokens.md` — breadcrumb + memory lanes

**Dogfood context:** `Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md`, `Docs/Plans/RUNBOOK-c2-first-dogfood-planning-round.md`

---

## §2 Plan surface thesis (one paragraph)

Plan is the flexible Command Board home: ingest prior session recap into queryable corpus, edit runbooks/timelines with Tiptap, browse corpus indexes, and show ingest/descriptor/save status on the anchor pane. Play projects the committed runbook at the table with overlay-first chips. Build will author durable world objects later; Plan consumes those objects today via corpus hubs and indexes.

**Foundational UX rule:** No new tabs as default navigation. Popups, hovers, drawers project tools; **closing them returns to Plan anchor pane**, not a blank dashboard.

**Overlays are cross-surface.** Popups, hovers, and drawers are a shared projection primitive — Plan, Play, and Build can all emit the same overlay vocabulary (`inline chip -> popover -> drawer -> modal`). Build the overlay shell once and parameterize the **return target** per surface (Plan → anchor pane, Play → focused beat, Build → object under construction). Do not fork the overlay components per surface.

---

## §3 Recap ingest v1 contract

### Pipeline (canonical order)

```text
raw notes → _ingest_staging → canonical Session Recaps → _normalized → _breadcrumbed → _session_memory
```

### Plan-mode v1 scope (in orchestrator today)

| Operation | CLI / API | Terminal status |
|-----------|-----------|-----------------|
| Stage + preview | `stage_preview` | `recap_preview_created` → often `breadcrumb_required` after preview path |
| Apply + normalize | `apply_normalize` | **`breadcrumb_required`** (expected) |
| Materialize session memory | `materialize_session_memory` | `ready_for_planning_activation` only if breadcrumb blessed |
| Inspect | `inspect_status` | Resumes from disk |

**Status envelope:** `dmb_raw_recap_ingest_status_v1` — `src/live_play/recap_ingest_status.py`

**Implementation map:**

| Area | Path |
|------|------|
| Orchestrator CLI | `src/live_play/recap_ingest_pipeline.py` |
| API routes | `apps/live_control_server/routes/recap_ingest.py` |
| Assembly helpers | `src/agent/recap_ingest_helpers.py` |
| Deterministic seed skeleton | `src/agent/recap_frontmatter_seed.py`, `scripts/build_recap_frontmatter_seed.py` |
| Path resolver | `src/live_play/recap_stage_paths.py` |
| UI module (partial) | `apps/live-control-ui/src/modules/IngestionModule.tsx` |

### Proof artifacts (v1)

- `ingest_report.preview_diff` on preview
- On-disk `paths.staged_raw_notes`, `paths.canonical_recap`, `paths.normalized_recap`
- On-disk `paths.frontmatter_seed` after deterministic skeleton build
- `status: breadcrumb_required` with actionable `next_actions[]`
- **Not** retrieval-ready until breadcrumb + session memory exist

### Product copy rule

`breadcrumb_required` is an **expected boundary**, not a failure toast. UI metrics should not count it as a hard error.

### Explicit v1 non-goals

- Full automated `frontmatter_seed.md` / `entity_index` compiler with new-hub judgment (`Backlog.md` READY — deterministic skeleton now exists)
- In-pane LLM breadcrumb (`evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py --ingest-routing-only`)
- Session memory button without blessed breadcrumb on disk
- Build-surface editing
- Rules ingestion graph activation
- LLM recap-write from Plan pane (planner skill path is separate)

### Frontmatter seed skeleton (deterministic today; reviewed before LLM)

Routing-only breadcrumb **consumes** `*.frontmatter_seed.md` route allowlist; it does **not** generate `entity_index`. Plan now builds the easy deterministic skeleton from known vocabulary, then stops for review:

1. `uv run python scripts/build_recap_frontmatter_seed.py --campaign N --session S`
2. Review/bless `Session Recaps/_breadcrumbed/Session S - <slug>.frontmatter_seed.md`
3. Run `uv run python evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py --ingest-routing-only ...`
4. Promote breadcrumb artifact to corpus if harness output requires
5. `uv run python scripts/materialize_session_memory.py --campaign N --session S --check`

The deterministic skeleton owns known routes: party/PC roster, NPC registry routes, mentioned current-campaign and setting hub README routes, and registry aliases. Review still owns new hub candidates, open questions, missing aliases, and route-importance judgment. See `Docs/Design/DESIGN-plan-recap-ingest-frontmatter-seed.md`.

### Session 23 state (2026-06-20 conversation)

- Staging: `corpus/.../Campaign 2/_ingest_staging/session_23_raw_notes.md` (+ `.orig.txt`)
- Canonical + normalized may already exist for Mireward Gate Battle
- Breadcrumb + `frontmatter_seed` were missing → pipeline correctly reports `breadcrumb_required`

Re-verify with:

```bash
uv run python -m src.live_play.recap_ingest_pipeline --check \
  --campaign-id longmont-c2 --session 23
```

---

## §4 Verification commands

### Recap ingest regression (required before claiming ingest work done)

```bash
uv run pytest tests/test_live_recap_ingest_pipeline.py \
  tests/test_live_recap_ingest_api.py \
  tests/test_recap_ingest_helpers.py -q
```

### Live orchestrator smoke (adjust campaign/session as needed)

```bash
uv run python -m src.live_play.recap_ingest_pipeline --check \
  --campaign-id longmont-c2 --session 23
```

### No LLM cost for v1 deterministic path

Stage/preview/apply/normalize do not require `OPENAI_API_KEY`. Breadcrumb ingest does.

---

## §5 Files explicitly OUT OF SCOPE for ingest v1 UI slice

Do not expand scope into these without a separate handoff:

- `src/prompts/*.py` — planner prompts
- `evals/*/gold/*.json` — gold drift unless rubric verified first
- `breadcrumb_prompt.py` — unless implementing in-pane breadcrumb (v1.1+)
- Corpus content edits except through existing `write_corpus_file` apply path
- Play beat shell, combat tracker, rules graph (`HANDOFF-c2s24-live-combat-tracker-design.md` is Play surface)

---

## §6 Suggested next implementation slices

Pick one per PR; keep Plan anchor pane as home:

1. **Plan ingest wizard UI** — paste raw notes, show preview diff, apply+normalize, render `breadcrumb_required` calmly with next steps
2. **Plan anchor pane shell** — session descriptor stub + ingest status + save boundary (read-only first)
3. **Automated frontmatter seed compiler** — Backlog READY; unblocks one-click retrieval-ready
4. **Play beat shell** — `DESIGN-play-mode-runbook-product-direction.md` PR 10B sequence

When implementing Plan UI, check: **what does this teach us about Play overlays and future Build object depth?** Capture in `Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md` or a new planning session notes file.

---

## §7 Review questions

1. Does Plan remain the default surface when all overlays close?
2. Is `breadcrumb_required` visible and calm, not a hung-job toast?
3. Are authority lanes preserved in status `authority{}` map?
4. Did we avoid claiming retrieval-ready before breadcrumb + session memory?
5. Did we record Build-teaching friction without designing Build yet?

---

## §8 Compact restatement for chat pickup

> **Plan Mode Command Board:** Three surfaces (Plan, Play, Build) over one memory. Plan = anchor pane + workshop; first proof = deterministic recap ingest through normalize, stop at `breadcrumb_required`. Build not designed yet — surfaces teach each other. Runbook Lantern keeps canon, runbook prose, descriptor, and operational state separate. Read this handoff + ANCHOR-runbook-lantern + DESIGN-play-mode-runbook-product-direction §0 before coding.
