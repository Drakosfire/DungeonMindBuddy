# Runbook — C2 First Dogfood Planning Round

Use this after PR90 (L5L) lands. The goal is one real planning pass: fresh recap → bootstrapped live workspace → live-control UI.

This runbook now has an additional authority-boundary purpose: do not flatten played recap, staged table notes, and GM planning scaffold into one kind of truth.

See also: `Docs/Plans/ROADMAP-c2s23-authority-activation-and-dogfood.md`.

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

For PR91, answer the Session 23 planning questions manually through the current workflow before manifest-backed retrieval exists.

Capture:

- question
- manual answer
- sources you consulted
- whether each source was canon/play, planning scaffold, live workspace, roll table, or hub evidence
- friction / missing context
- uncertainty

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
