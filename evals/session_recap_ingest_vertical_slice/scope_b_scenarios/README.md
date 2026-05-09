# Scope-B Perturbation Scenarios

These fixtures extend the canonical `gold/scope_b_session_20.json` contract with
small adversarial setup metadata used by offline pytest coverage in
`tests/test_scope_b_perturbation_scenarios.py`.

Each `*.json` keeps the live-runner fields (`schema`, `fixture_relpath`,
`ingest_raw_notes_relpath`, `expected_tool_trace`, `followup_turn`) and adds:

- `perturbation_setup`: deterministic corpus-seeding and synthetic-tool-trace hints
  for the offline verifier.
- `documented_expectations`: the contract the tests assert. These use substring
  matching rather than full-message equality so the docs stay readable while still
  pinning the relevant hard/soft outcomes.

`documented_expectations` fields:

- `summary`: one-line human description.
- `gates_passed`
- `tool_trace_gates_passed`
- `payload_gates_passed`
- `scope_b_tool_substrings`
- `scope_b_payload_substrings`
- `soft_observation_substrings`

The default CI path is offline:

```bash
uv run pytest tests/test_scope_b_grader.py tests/test_scope_b_perturbation_scenarios.py -q
```

If `OPENAI_API_KEY` is available, you can also run a live scenario with:

```bash
PLANNER_REVIEW_MODE=summary uv run python -m \
  evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run \
  --scenario-json evals/session_recap_ingest_vertical_slice/scope_b_scenarios/guarded_staging_read_recovery.json
```

**Live vs offline:** For live runs against the default **tmp pre-state** corpus (omit `--live-corpus`), `step1_recap_ingest_run.py` applies **live-portable** `perturbation_setup` fields before the planner turn: `seed_kind`, `prep_variant`, `inject_existing_target_recap_after_snapshot`, and (via the existing ingest path) `ingest_raw_notes_relpath`. **`trace_variant` is offline-only** — it only shapes the synthetic tool trace in pytest; the runner logs a warning for variants with no live equivalent (`guarded_staging_read_then_recover`, `assemble_raw_notes_path_traversal`). `commit_rejected_existing_target` is mirrored live by `inject_existing_target_recap_after_snapshot`, not by fabricating tool rows. **`--live-corpus` skips all corpus mutations** (would be destructive on a real tree). A five-scenario **negative-control** cohort (N=2 each, 2026-04-21) predates this wiring and showed live/pass divergence when perturbations were not applied — see [REPORT-Perturbation-Live-Negative-Control-2026-04-21.md](../../../Docs/Plans/archive/2026-05-09/reports/REPORT-Perturbation-Live-Negative-Control-2026-04-21.md). After wiring, cohort outcomes and planner findings are in [REPORT-Perturbation-Live-Wired-2026-04-21.md](../../../Docs/Plans/archive/2026-05-09/reports/REPORT-Perturbation-Live-Wired-2026-04-21.md).
