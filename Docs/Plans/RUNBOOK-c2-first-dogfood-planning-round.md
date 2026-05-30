# Runbook — C2 First Dogfood Planning Round

Use this after PR90 (L5L) lands. The goal is one real planning pass: fresh recap → bootstrapped live workspace → live-control UI.

This runbook now has an additional authority-boundary purpose: do not flatten played recap, staged table notes, and GM planning scaffold into one kind of truth.

**C2S23 benchmark pack (PR94):**

- Charter: `Docs/Plans/BENCHMARK-c2s23-dogfood-planning-charter.md`
- Seed questions: `evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json`
- Manual baseline: `evals/c2_live_prep/benchmarks/c2s23_manual_baseline.template.md`
- Capability inventory: `Docs/Plans/CAPABILITY-INVENTORY-c2s23-planning-artifact-actions.md`

See also: `Docs/Plans/ROADMAP-c2s23-authority-activation-and-dogfood.md`.

## First C2S23 dogfood round (ordered checklist)

Use this sequence for the first real Session 23 planning pass. Details for CLI/UI commands are in sections below.

1. **Ingest raw Session 22 recap** — CLI (§2) or ingestion pane (§2, L5N) with recap/source session `22` while live workspace targets Session 23.
2. **Apply and normalize** with explicit non-generic slug and title.
3. **Stop if breadcrumb is required** — do not treat as failure; generate or bless breadcrumb by existing content process.
4. **Generate/bless breadcrumb artifact** — outside this runbook’s code path; use established breadcrumb workflow.
5. **Materialize Session 22 session memory** — only when breadcrumb exists.
6. **Start or activate Session 23 live workspace** — bootstrap (§3); set `DUNGEONMIND_LIVE_SESSION_DIR` or `--write-current-live`.
7. **Run benchmark questions manually first** — copy `c2s23_manual_baseline.template.md`; work from `c2s23_dogfood_questions.seed.json` (no gold, no corpus-oracle pass).
8. **Record source roles and authority notes** — per question in the template; use charter role vocabulary.
9. **Identify desired artifact actions** — from seed `expected_artifact_actions` and planning intent.
10. **Attempt only currently supported actions** — see capability inventory; log blocked actions explicitly.
11. **Log gaps** — missing tools, bad retrieval, context confusion, authority failures; update inventory and open PR95/PR96 as needed.

### What counts as success

- Session 22 ingest and derivatives are in a known state (including explicit `breadcrumb_required` if applicable).
- Session 23 live workspace is running in the UI with Timeline and Inspector used at least once.
- ≥15 seed questions have manual baseline rows with sources, roles, and attempted actions filled in.
- Authority trap questions are answered without using forbidden roles for play facts.
- Friction is captured with a recommended follow-up PR where the inventory says **missing** or **partial**.

### What counts as failure

- Play-fact answers sourced from prep scaffold, roll tables, or staging after canonical recap exists.
- Dogfood proceeds without ingest/bootstrap because tooling is broken (fix L5M/L5N/L5L first).
- Baseline filled by reading corpus files ahead of the live workflow (oracle leakage).
- Unscoped corpus writes outside allowlist.

### When to stop and create follow-up PRs

- Same **missing** capability blocks three or more questions → open PR95 (activation, roll-table seed/create, route workflow) or PR96 (live retrieval, context packets, hub write UX) per inventory.
- Repeated authority failures → prioritize activated manifest + admission (roadmap PR92/PR93), not more UI panes.
- Regression in `tests/test_live_recap_ingest_pipeline.py`, `tests/test_live_recap_ingest_api.py`, or `tests/test_live_session_bootstrap.py` → stop dogfood; fix tests before continuing.

## 0. Confirm Session 22 content state

Session 22 was played, and its table notes are staged at:

```text
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md
```

Before the first serious Session 23 dogfood pass, run the existing content operation:

```text
session_22 notes
→ recap-write pass
→ normalized recap
→ breadcrumbed recap
→ session memory JSONL
```

This is not a code PR. It is the content step that promotes table notes into play/canon recap memory.

If the staged notes are not final table notes, explicitly mark the dogfood pass as using a projected post-ingest state.

## 1. Place a fresh recap or planning input

Keep the recap or planning input as a local markdown file (not committed unless it is a test fixture). Example:

```text
~/notes/session_22_recap.md
```

Do not paste campaign-private prose into public issues or external tools.

Authority rule:

```text
table notes          → evidence awaiting recap-write
played recap         → canon/play memory after recap-write
planning anchor      → GM scaffold, not canon
prep brief/runbook   → intended possibility space, not canon
roll tables          → prep tools, not happened facts
live workspace       → active planning surface / observations
```

## 2. Raw recap ingestion path — CLI (L5M / PR92)

Use the ingestion orchestrator before bootstrap when the source recap is still raw notes:

```bash
uv run python -m src.live_play.recap_ingest_pipeline \
  --campaign-id longmont-c2 \
  --session 22 \
  --raw-path ~/notes/session_22_raw.md \
  --stage \
  --preview \
  --json
```

Then apply + normalize:

```bash
uv run python -m src.live_play.recap_ingest_pipeline \
  --campaign-id longmont-c2 \
  --session 22 \
  --raw-path ~/notes/session_22_raw.md \
  --slug "Mireward Road and Lysandro" \
  --stage \
  --apply \
  --normalize
```

Then materialize session memory (only after breadcrumb exists/blessed):

```bash
uv run python -m src.live_play.recap_ingest_pipeline \
  --campaign-id longmont-c2 \
  --session 22 \
  --slug "Mireward Road and Lysandro" \
  --materialize-session-memory \
  --check
```

Pipeline interpretation:

1. Stage raw recap under `_ingest_staging/session_<N>_raw_notes.md`.
2. Preview canonical recap assembly (frontmatter + H1 + de-dup report).
3. Apply only with non-generic slug/title.
4. Normalize the canonical recap.
5. Stop at `breadcrumb_required` if `_breadcrumbed/*.breadcrumbed.md` is absent.
6. Materialize `_session_memory/*.records_meta.{jsonl,json}` only when breadcrumb exists.
7. Treat session as planning-activation ready only after canonical recap + derivatives are in place.

### Operator pane (L5N / PR93)

When live-control is already running for Session 23 planning, enable the optional **Ingestion** module in the surface layout. Set **Recap/source session** to `22` (defaults to live session − 1) while the live workspace remains Session 23. The pane calls `POST /api/live/recap-ingest` with the same stage/preview → apply/normalize → materialize-session-memory flow as the CLI; it does not accept browser file paths.

## 3. Bootstrap a session workspace

```bash
cd /path/to/DungeonMindBuddy

uv run python -m src.live_play.session_bootstrap \
  --campaign-id longmont-c2 \
  --session 23 \
  --recap-path ~/notes/session_22_recap.md \
  --previous-session 22 \
  --next-session-label "Session 23" \
  --out-dir evals/c2_live_prep/live/session_23
```

To point the live server at the new workspace (overwrites the default live directory copy):

```bash
uv run python -m src.live_play.session_bootstrap \
  --campaign-id longmont-c2 \
  --session 23 \
  --recap-path ~/notes/session_22_recap.md \
  --previous-session 22 \
  --write-current-live \
  --force
```

`--force` is required when the output workspace or live directory already has live files.

## 4. Start server and UI

```bash
# optional: explicit session dir
export DUNGEONMIND_LIVE_SESSION_DIR=evals/c2_live_prep/live/session_23

uv run uvicorn apps.live_control_server.main:app --reload
```

```bash
cd apps/live-control-ui && npm run dev
```

## 5. Inspect first in Timeline

Open the Timeline module. Rows should come from recap-derived `planning_beats` with human labels (not corpus paths). Confirm at least one row references the fresh recap as a source packet.

As you inspect, classify each useful source mentally:

```text
canon_play
planning_scaffold
planning_input
reference_tool
live_observation
audit
```

Do not treat planning scaffold as proof of what happened.

## 6. Run the manual baseline questions

Use the PR94 seed and template (not ad-hoc question lists):

```text
evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json
evals/c2_live_prep/benchmarks/c2s23_manual_baseline.template.md
```

Answer through the current live-control workflow **before** manifest-backed retrieval exists. Do not pre-survey corpus files to write answers.

Capture per question:

- question id and text
- manual answer
- sources consulted (paths or APIs)
- source roles (charter vocabulary)
- authority notes
- artifact actions desired vs attempted
- friction and confidence

This baseline is intentionally pre–C2S23 activation manifest (see `ROADMAP-c2s23-authority-activation-and-dogfood.md`). It gives the later manifest-backed query path something to beat.

## 7. Append observations

Use Inspector → **Append observation** on an open loop or timeline ref. Confirm Record shows a new event and current state refreshes.

Observation authority should be clear:

```text
append_observation → live_observation
```

It is not automatically long-term canon.

## 8. Patch roll tables (if applicable)

Only when a real roll-table artifact exists in the workspace/corpus path the server can read. Use preview → confirm. Review **Write evidence** after confirm.

Roll tables are `reference_tool` / prep-tier artifacts. Patching a roll table changes the tool; it does not assert that a result happened in play.

## 9. Capture dogfood evidence

Note:

- Bootstrap CLI output path
- Plan-view row count and first three labels
- Whether refresh-after-write verified token match
- Which questions required S21 evidence
- Which questions required S22 play recap/session memory
- Which questions required S22/S23 planning scaffold
- Which sources were confusing because authority was unclear
- Friction (missing beats, wrong open loops, UI confusion)

## 10. What not to trust yet

- Recap heuristics are deterministic stubs, not LLM understanding
- No activated planning corpus manifest yet
- No manifest-backed retrieval/admission yet
- No retrieval index rebuild; context lookup may be empty or stale
- No UI upload/import; CLI file path only
- `known_roll_tables` stays empty unless you seed tables separately
- Multi-session routing is not a product feature; use `--write-current-live` or `DUNGEONMIND_LIVE_SESSION_DIR`

## Known rough edges

- Open-loop detection uses keyword heuristics; false positives/negatives are expected
- Entity mentions are naive proper-noun scans
- Plan-view may show a generic open-loop ref on every beat when multiple loops exist
- Accepted patch with failed pane refresh vs failed app refresh are not distinguished in UI (L5K follow-up)
- Prep scaffold and play recap can be confused unless the operator labels authority explicitly

## Verification (developers)

```bash
uv run pytest tests/test_live_session_bootstrap.py tests/test_live_recap_ingestion.py -q
uv run pytest tests/test_live_plan_view_projection.py tests/test_live_control_server.py -q
```
