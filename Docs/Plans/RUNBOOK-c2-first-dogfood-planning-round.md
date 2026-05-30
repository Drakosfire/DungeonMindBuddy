# Runbook — C2 First Dogfood Planning Round

Use this after PR90 (L5L) lands. The goal is one real planning pass: fresh recap → bootstrapped live workspace → live-control UI.

## 1. Place a fresh recap

Keep the recap as a local markdown file (not committed unless it is a test fixture). Example:

```text
~/notes/session_22_recap.md
```

Do not paste campaign-private prose into public issues or external tools.

## 2. Bootstrap a session workspace

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

## 3. Start server and UI

```bash
# optional: explicit session dir
export DUNGEONMIND_LIVE_SESSION_DIR=evals/c2_live_prep/live/session_23

uv run uvicorn apps.live_control_server.main:app --reload
```

```bash
cd apps/live-control-ui && npm run dev
```

## 4. Inspect first in Timeline

Open the Timeline module. Rows should come from recap-derived `planning_beats` with human labels (not corpus paths). Confirm at least one row references the fresh recap as a source packet.

## 5. Append observations

Use Inspector → **Append observation** on an open loop or timeline ref. Confirm Record shows a new event and current state refreshes.

## 6. Patch roll tables (if applicable)

Only when a real roll-table artifact exists in the workspace/corpus path the server can read. Use preview → confirm. Review **Write evidence** after confirm.

## 7. Capture dogfood evidence

Note:

- Bootstrap CLI output path
- Plan-view row count and first three labels
- Whether refresh-after-write verified token match
- Friction (missing beats, wrong open loops, UI confusion)

## 8. What not to trust yet

- Recap heuristics are deterministic stubs, not LLM understanding
- No retrieval index rebuild; context lookup may be empty or stale
- No UI upload/import; CLI file path only
- `known_roll_tables` stays empty unless you seed tables separately
- Multi-session routing is not a product feature; use `--write-current-live` or `DUNGEONMIND_LIVE_SESSION_DIR`

## Known rough edges

- Open-loop detection uses keyword heuristics; false positives/negatives are expected
- Entity mentions are naive proper-noun scans
- Plan-view may show a generic open-loop ref on every beat when multiple loops exist
- Accepted patch with failed pane refresh vs failed app refresh are not distinguished in UI (L5K follow-up)

## Verification (developers)

```bash
uv run pytest tests/test_live_session_bootstrap.py tests/test_live_recap_ingestion.py -q
uv run pytest tests/test_live_plan_view_projection.py tests/test_live_control_server.py -q
```
