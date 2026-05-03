# Session Events Extraction Vertical Slice

**Two-phase events-first pipeline for session-recap -> timeline-append.**

- **Recap-to-events extraction** (`step1_session_events_run.py`): read a session recap, extract a complete structured list of `event_record`-shaped JSON objects covering all meaningful beats. The model emits a required per-event **`recap_evidence_span`** (corpus recap path + inclusive 1-based line range into the **numbered** recap block in the user prompt); the runner turns that into `source_anchors` (blake3 + `commit_sha`) before JSON-schema grading. Gates: SE1 schema, SE2 count, SE3 participant slugs, SE4 event classes, SE5 expected-event coverage, SE6 gold-span anchor coverage, SE7 hash-verified non-placeholder anchors (when `require_verified_event_anchors` is set in gold).
- **Events-to-timeline append** (`step2_timeline_from_events_run.py`, landed 2026-04-22): per-slug events-driven `append_timeline_row` micro-turns. Recap reads explicitly forbidden — this phase sees only the events recap-to-events produced for that slug, plus pre-loaded timeline files. Grades against `evals/session_recap_timeline_pass_vertical_slice/` gold (TP1/TP2/TP3/TP5) so iteration history is comparable with the legacy single-stage Iteration-6 surface. **PC-only** — NPC rows in the same gold file are filtered out before running and grading.
- **NPC timeline-first attachment** (`step3_npc_timeline_from_events_run.py`): same chain as step2, but only `NPCs/<slug>/timeline.md` targets. **Append** slugs get an append turn when Stage A produced events; **skip** slugs get a no-append turn (or no model call if there are zero events). Grading uses the same timeline-pass gold with NPC-only `expected_appends` / `expected_skips` / `allowed_npc_slugs`. Artifacts: `step3_npc_events--*` under `artifacts/runs/`, plus `artifacts/last_step3_npc_run.{md,json}`.

The architectural premise: extracting all events in one model call removes the **compression** failure mode where a planner turn collapses a multi-beat character into a single row that drops lexical anchors. N=5 chained cohort confirms: per-PC anchor gates (`caelynn`, `karsemine`, `ephanna`) all 5/5, vs single-stage 0/5 for `karsemine`/`ephanna`.

## Layout

```
evals/session_events_extraction_vertical_slice/
  __init__.py
  README.md                              ← this file
  step1_session_events_run.py            ← recap-to-events runner (CLI entry point)
  step2_timeline_from_events_run.py      ← events-to-timeline chained runner (PC-only)
  step3_npc_timeline_from_events_run.py  ← events-to-timeline chained runner (NPC-only)
  grader.py                              ← recap-to-events gate logic + telemetry (SE1-SE7)
  session_events_run_report.py           ← per-run + cohort artifact writers
  gold/
    session_events_session20.json        ← Stage A gold (C2 Session 20 recap)
    session_events_session1_c1.json    ← Stage A gold (C1 Session 1)
    session_events_session2_c1.json    ← Stage A gold (C1 Session 2)
    session_events_session3_c1.json    ← Stage A gold (C1 Session 3)
    # Stage B (PC-only) grading gold + pre-state: evals/session_recap_timeline_pass_vertical_slice/gold/timeline_pass_session{1,2,3}_c1.json (+ manifests + C1 PC timeline seeds — not in live corpus until pre-state copy).
  artifacts/
    .gitignore
    last_session_events_run.{md,json}    ← latest Stage A run
    last_step2_run.{md,json}             ← latest Stage B (PC) chained run
    last_step3_npc_run.{md,json}        ← latest NPC chained run
    runs/
      YYYY-MM-DD/
        session_events--*.{md,json}            ← Stage A per-run artifacts
        session_events_summary--*--N*.{md,json}
        step2_events--*.{md,json}              ← Stage B per-run artifacts (sidecar carries
                                                  slug_events_sent / slug_beat_written / slug_model_message)
        step2_events_summary--*--N*.{md,json}
        step3_npc_events--*.{md,json}
        step3_npc_events_summary--*--N*.{md,json}
tests/
  test_session_events_grader.py          ← Stage A offline grader tests (no network)
  test_step2_timeline_from_events.py     ← Stage B runner tests (message builder, per-slug filter,
                                            beat extraction, infra-error abort, sidecar round-trip)
```

## Recap path strategy

The Session 20 recap is **not** duplicated into this slice's `gold/` directory. The runner reads it directly from the canonical corpus path:

```
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md
```

relative to the repo root. The `DUNGEONMIND_CORPUS_ROOT` env var can override the corpus root if needed.

## How to run

### Recap-to-events only (no timeline writes)

```bash
# Single run
uv run python -m evals.session_events_extraction_vertical_slice.step1_session_events_run --n 1 --model gpt-5.4-mini

# Cohort of 5
uv run python -m evals.session_events_extraction_vertical_slice.step1_session_events_run --n 5 --model gpt-5.4-mini

# Dry run (no artifacts written)
uv run python -m evals.session_events_extraction_vertical_slice.step1_session_events_run --n 1 --no-writes
```

### Recap-to-events -> events-to-timeline chained run

```bash
export DUNGEONMIND_PLANNER_ALLOW_WRITES=1
# Campaign 2 Session 20 (default recap-to-events + default timeline-pass gold)
uv run python -m evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run \
  --n 5 --model gpt-5.4-mini

# NPC-only timeline attachment (same Stage A default + same timeline gold; NPC rows only)
uv run python -m evals.session_events_extraction_vertical_slice.step3_npc_timeline_from_events_run \
  --n 5 --model gpt-5.4-mini

# Campaign 1 Sessions 1–3 (recap-to-events gold must match session; timeline-pass gold selects pre-state + grading)
uv run python -m evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run \
  --scenario-json evals/session_events_extraction_vertical_slice/gold/session_events_session1_c1.json \
  --timeline-gold evals/session_recap_timeline_pass_vertical_slice/gold/timeline_pass_session1_c1.json \
  --n 1 --model gpt-5.4-mini
# … repeat with session2 / session3 gold + timeline_pass_session2_c1.json / session3_c1.json
```

Events-to-timeline writes to a pre-state corpus copy, never to `corpus/eldyrwild-markdown/` directly. Cohort aborts cleanly above $5.00 cumulative cost. Per-run sidecars carry `slug_events_sent`, `slug_beat_written`, and `slug_model_message` for each slug micro-turn so failure attribution does not require re-runs.

**C1 pre-state:** manifests delete duplicate `Campaign 2/PCs/<slug>/timeline.md` files for the six C1 PCs (so `append_timeline_row` slug resolution is unambiguous), copy empty `Campaign 1/PCs/<slug>/timeline.md` seeds from `gold/c1_pc_timeline_seeds/`, then strip the target session row if present. Recaps are read from the corpus copy (canonical files under `Longmont Campaign/Campaign 1/Session Recaps/`).

## Gates

| Gate | Description | Threshold |
|------|-------------|-----------|
| **SE1** | Every parsed event validates against `event_record.schema.json`. Fail closed. | Hard fail on any violation |
| **SE2** | Event count is within `[min_event_count, max_event_count]` (gold: 10–25). | Hard bounds |
| **SE3** | Every slug in `must_cover_participants` appears in at least one event's `participants[]`. | All required |
| **SE4** | Every class in `must_cover_event_classes` appears in at least one event's `event_class`. | All required |
| **SE5** | For each `expected_events[i]`: (a) **lenient coverage** — at least one model event matches on `event_class` + participant overlap + name/outcomes text overlap (ratio reported in telemetry, soft-fail < 0.5); (b) **outcome-vocabulary preservation** — every entry in `must_preserve_terms` must be satisfied (case-insensitive substring on *some* model event sharing ≥1 participant); a single entry may be an **OR group** `a\|b` meaning either substring counts. | Hard fail on any missing required term, OR coverage ratio < 0.5 |
| **SE6** | When `expected_anchored_spans` is present: each gold span must be covered by some event for that slug whose `source_anchors` include a recap path + line range that **contains** the span (max span width configurable). | Hard fail on any unmatched span |
| **SE7** | When `require_verified_event_anchors` is true: every event's `source_anchors` must (1) name the scenario recap path, (2) **`content_hash`**-match current on-disk bytes for the declared 1-based line span (same check as `lint_source_anchors`), and (3) not span the **entire** recap when it has multiple lines (rejects whole-file placeholders). | Hard fail on any violation |

**Primary capture signal:** SE6 + SE7 together approximate `Docs/Design/DESIGN-citation-grounded-corpus-architecture.md` extraction-mode provenance. **SE5 / Stage B TP1** remain vocabulary / render-adjacent checks — useful, but not a substitute for verifiable line anchors.

SE5's outcome-vocabulary sub-gate is the policing layer for Stage A's system-prompt OUTCOMES CONTRACT (verbatim preservation of weapon/spell/ability/item/place/NPC names). Each expected event in the gold can declare a per-event `must_preserve_terms: list[str]` of distinctive named terms (use `drawing|blueprint` when recap and table vocabulary diverge but either substring is acceptable). The check is **per-term across the participant-overlap pool**, deliberately decoupled from event_class drift and from the model's choice of how to split a beat across multiple events:

- **Class drift is OK** — if the model classifies Caelynn's bracelet de-escalation under `ritual` instead of gold's `social_conflict`, the term `bracelet` is still considered preserved as long as it appears in some actual event involving Caelynn/Marla/Bonogo.
- **Beat-splitting is OK** — if the model legitimately splits "Karsemine rounds up horses; observes magical storm" into a wagon-discovery event with `horses` and a separate camp-setup event with `storm` + `shimmering rain`, all three terms count as preserved.
- **Paraphrasing is NOT OK** — replacing "Eldritch Blast" with "attack spell", or silently dropping "antidote" / "Tealeaf" / "Questionable Company" anywhere in a participant-overlap event triggers a `kind="missing_outcome_terms"` structured violation with the precise missing terms list.

Telemetry exposes `expected_events_with_missing_terms`, `missing_terms_total`, and `se5_term_violations` (per-event payload with the best representative actual for human triage).

The lenient coverage threshold is documented at `_SE5_PASS_THRESHOLD = 0.5` in `grader.py`; it will be raised once we have cohort data.

### Grader contract: `referenced_slugs[]` vs `participants[]` (Branch (a))

**Policy decision:** SE3 and SE5 intentionally remain **`participants[]`-only** gates (actor identification and coverage overlap). Model output may still carry **`referenced_slugs[]`** for entities that appear in the beat but are not full participants. **Stage A graders do not union `referenced_slugs[]` into SE3 or SE5.** Downstream **Stage C** is allowed to use **`participants ∪ referenced_slugs`**; broader entity merge across fields is a **Stage D** concern, not something Stage A should silently fold into participant-based gates.

**Why:** The lowest extraction layer keeps a narrow, inspectable meaning for `participants[]` (“who this event is *about* / who acted”) instead of treating every mentioned slug as a participant for coverage. Editors should not “fix” the grader by expanding SE3/SE5 to `referenced_slugs[]` without an explicit pipeline decision—doing so would change the contract this slice was tuned against.

**Canary:** `tests/test_session_events_grader.py::TestReferencedSlugsGraderRegression` — if that test fails after a grader change, treat it as a deliberate behavior change and update tests plus this section together.

### Stage B gates

Stage B is graded against `evals/session_recap_timeline_pass_vertical_slice/`'s gold using its `collect_timeline_pass_violations`:

- **TP1** APPEND completeness (count + flat-anchor-words on rows on disk)
- **TP2** SKIP correctness (out-of-scope today: events-only Stage B over-extracts on background participants like `thrin_branchborn`)
- **TP3** Tool contract (no `write_corpus_file`; no recap-assembly tools)
- **TP5** Hallucination guard (`allowed_npc_slugs`)

## Gold curation (Session 20)

Gold events were hand-curated by reading `Session 20 - Recap.md` directly. The gold contains 16 `expected_events` covering:

- **combat**: red gnat swarm battle
- **social_conflict**: Stacey warehouse confrontation; Bonogo knife threat; Marla vs Bonogo confrontation; Caelynn de-escalation
- **conversation**: party reports to Stafl; mayor denies Lysandra; Sara/Lysandra rockie-talkie call; Caelynn reports tainted meat to Sara; Ephanna announces departure
- **discovery**: fortification fires drive forest retreat; Lysandra found with cult eyes and a tower drawing in the dirt (recap also says top-down blueprint; SE5 anchors on drawing + tower + shimmery)
- **travel**: Karsemine tracks Lysandra; group reaches wagon camp
- **ritual**: Caelynn administers antidote tea to Lysandra
- **investigation**: Stafl finds tainted meat; Karsemine rounds up horses and spots approaching storm

**SE6 (`expected_anchored_spans`):** `line_range` values come from **corpus recap line numbers** (per-span `rationale` ties each slug to that text). They **tighten SE6** against recap-grounded spans, **not** model output. When editing this list, justify anchors from the recap file, not from a model run.

**SE7 (`require_verified_event_anchors`):** Session 20 gold sets this flag so every emitted event must carry anchors that **round-trip to the recap file on disk** (blake3 over the UTF-8 bytes of the anchored line span). This is the mechanical “no fake line numbers / no stale hash” gate; `commit_sha` on the anchor is informational for SE7 — drift is tracked separately from HEAD verification.

## Telemetry exposed

Each run report includes:

```json
{
  "event_count": <int>,
  "participants_seen": ["bonogo", "caelynn", ...],
  "event_classes_seen": ["combat", "conversation", ...],
  "expected_event_coverage_ratio": 0.75,
  "unmatched_expected_event_indices": [3, 11]
}
```

## Offline tests

```bash
uv run pytest tests/test_session_events_grader.py tests/test_step2_timeline_from_events.py -q
```

## Iteration history

- **2026-04-21** — Stage A proving slice landed (commit `233b6c3`). N=2 smoke at `gpt-5.4-mini`: SE1/SE2/SE4/SE5 PASS, SE3 (slug naming) FAIL on display-name leak. Slug-enforcement system-prompt fix queued.
- **2026-04-22** — **Stage A SE3 fix shipped**: system prompt now demands the exact slug from the supplied list, never the display name. Stage A N=5: 4/5 PASS, SE3 closed.
- **2026-04-22** — **Stage B chained runner shipped** (`step2_timeline_from_events_run.py`). First N=5 cohort: TP1 0/5, with all failures attributed to **second-order compression** (Stage B picked one event per character to summarize, often dropping the anchor-bearing event). Diagnostic capture (`slug_events_sent` + `slug_beat_written` + `slug_model_message`) added so the next iteration can attribute failures without re-runs.
- **2026-04-22** — **OUTCOMES CONTRACT (Stage A) + VOCABULARY/COMPOSITION CONTRACT (Stage B)** prompts shipped. Stage A now requires verbatim preservation of weapon/spell/ability/item/place/NPC names in `outcomes[]`. Stage B now requires preserving those terms verbatim in the beat AND composing multiple meaningful events into one sentence (was: "summarize the most important event"). N=5 result: TP1 **3/5**, per-PC anchor gates all **5/5** for `caelynn`, `karsemine`, `ephanna`. Cost ~$0.045/run.
- **2026-04-22** — **SE5 outcome-vocabulary sub-gate** shipped. Gold S20 expected events declare `must_preserve_terms`; SE5 enforces per-term verbatim preservation across the participant-overlap pool. Stage A N=5: **SE5 4/5 PASS** (one real model regression — dropped `storm`/`shimmering rain`). Stage B chained N=5: **TP1 4/5**, per-PC `caelynn` 4/5 / `karsemine` 5/5 / `ephanna` 5/5 (the one caelynn drop is the same correlated bad run). Cost: Stage A ~$0.012/run, Stage B chained ~$0.047/run.

## Open follow-ups

1. **TP2-thrin row-worthiness gap** — events-only Stage B has no signal beyond "this character has events" so it writes a row even when the recap framing said the character was background. Three viable fixes captured in `Backlog.md`: (a) Stage A `subject_significance`, (b) Stage B recap-read affordance, (c) harness pre-filter.

2. **SE5 outcome-vocabulary sub-gate landed 2026-04-22** — `must_preserve_terms` curated per expected event in `gold/session_events_session20.json`; grader checks each term per-participant-overlap pool; failures emit structured `missing_outcome_terms` violations. N=5 cohort with the tightened gate: 4/5 SE5 PASS at `gpt-5.4-mini`, with the one FAIL being a real OUTCOMES CONTRACT regression (model dropped `storm` and `shimmering rain` from any karsemine-related event).

3. **Lysandra Stage A recall regression** — 2/5 runs in the latest cohort drop Lysandra from events entirely (NPC, not blocking the PC criterion).

4. **Standalone Stage A `parsed_events` persistence** — **shipped 2026-04-22**. The per-run sidecar JSON now carries the model's `parsed_events` array verbatim (schema bumped to `session_events_run_report_v2`). Downstream consumers (Stage C, Stage D, post-hoc anchor audits) can read events directly from any Stage A cohort sidecar instead of re-running Stage B chained or generating hand-frozen fixtures. Tests in `tests/test_session_events_run_report.py` pin the contract.

5. **`FactStore.add_event_records()` persistence** — the runner validates events but does not persist them as canonical facts. Defer until Stage A pass rates are acceptable across more sessions.

6. **Robustness against unseen recaps** — current evidence is N=5 on a single recap (Session 20) the prompts were tuned against. A blind run on Campaign 1 Session 1 would tell us whether the contracts generalize.

7. **NPC + Location ingestion expansion** — same events-first scaffold should extend to NPC and Location updates, not just timelines.
