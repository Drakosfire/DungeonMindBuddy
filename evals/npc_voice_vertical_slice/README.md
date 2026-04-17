# NPC voice planner vertical slice

Live planner benchmarks in the same shape as Lysandra Step 1 (`input.user_message`, `final.require`, optional `followup_turn`). Grounded in ingested corpus under `corpus/eldyrwild-markdown/`.

## Corpus anchors

| NPC | Paths |
|-----|--------|
| Torbin | `Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/torbin_jove_statblock.md`, `Longmont Campaign/Campaign 2/NPCs/torbin_jove/torbin_jove_care_guidelines.md`, hub `Longmont Campaign/Campaign 2/NPCs/torbin_jove/README.md` |
| Dustwalker | `Elderwyld/Shephards Flock/NPCs/dustwalker/dustwalker_statblock.md`, hubs `Elderwyld/Shephards Flock/NPCs/dustwalker/README.md` and `Longmont Campaign/Campaign 2/NPCs/dustwalker/README.md` |

Post-planner **Step 2** Lysandra benchmark is **off** for this slice (`gold/step2_noop.json`).

## Run

From repo root (with `OPENAI_API_KEY` in `.env`):

```bash
# One scenario
uv run python -m evals.npc_voice_vertical_slice.npc_voice_planner_trace --scenario torbin_factual_ac

# List IDs
uv run python -m evals.npc_voice_vertical_slice.npc_voice_planner_trace --list-scenarios

# Full manifest suite (exit 1 if any fail)
uv run python -m evals.npc_voice_vertical_slice.npc_voice_planner_trace --all

# Repeat full suite 5 times; aggregate report: artifacts/reports/npc_voice_suite--<utc>.md + .json
uv run python -m evals.npc_voice_vertical_slice.npc_voice_planner_trace --all --runs 5

# Repeat one scenario 10 times; custom report path (extension optional)
uv run python -m evals.npc_voice_vertical_slice.npc_voice_planner_trace --scenario torbin_factual_ac --runs 10 --suite-report /tmp/npc_voice_torbin_ac

# Verbose: print full per-run reviews to stdout when --runs>1 (default is stderr one-liners only)
uv run python -m evals.npc_voice_vertical_slice.npc_voice_planner_trace --all --runs 3 --verbose
```

Environment:

- `NPC_VOICE_PLANNER_SCENARIO` — default scenario id when `--scenario` omitted.
- `NPC_VOICE_PLANNER_USER_MESSAGE` — optional override for `input.user_message` in the loaded gold.
- `NPC_VOICE_PLANNER_RUNS_ROOT` — optional absolute root for dated artifacts (default: `evals/npc_voice_vertical_slice/artifacts/runs`).

Artifacts: dated file under `artifacts/runs/YYYY-MM-DD/` plus `artifacts/last_npc_voice_planner_run.md`.

Multi-run (`--runs` > 1): per-cell artifacts include `runNNN--` in the filename; suite rollup lives in `artifacts/reports/` (Markdown + JSON with the same stem).

## Pytest (live)

```bash
NPC_VOICE_PLANNER_LIVE=1 pytest tests/test_npc_voice_vertical_slice_planner.py -m integration --runxfail
```

Requires corpus + API key.
