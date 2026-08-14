# Hermes small-slice (Of Conks Grotesque Tree)

Gold + runner for getting the most out of a ~24-node campaign slice: define a great tree answer, score Hermes turns, tune source-open habits, densify edges.

## Gold

[`gold/of_conks_grotesque_tree_v1.json`](gold/of_conks_grotesque_tree_v1.json) — questions, buckets, must-not, `source_read_required`, expand-ready bar.

## Score recorded baseline

```bash
uv run python evals/hermes_small_slice/run_small_slice.py score-file \
  --trial evals/hermes_small_slice/artifacts/baseline_observed_vague_talk.json \
  --question-id vague_talk --write
```

## Live multi-trial

```bash
uv run python evals/hermes_small_slice/run_small_slice.py live \
  --question-ids vague_talk,prep_gm_facing,authoring_gm_note --trials 3
```

## Authoring dogfood

```bash
uv run python evals/hermes_small_slice/run_small_slice.py authoring-dogfood \
  --document-id <plan-doc-id> --content-sha256 <optional>
```

## Edge densification

[`fixtures/of_conks_edge_densification_v1.json`](fixtures/of_conks_edge_densification_v1.json) merges at seed:

```bash
uv run python scripts/seed_of_conks_cons_world.py --force-reinit --skip-import
```

## Tests

```bash
uv run pytest -q evals/hermes_small_slice/test_score.py
```
