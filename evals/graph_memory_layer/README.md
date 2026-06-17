# Graph Memory Layer Evals

## Purpose

This directory is the evaluation scaffold for the Graph Memory Layer experiment. It gives the experiment a dedicated, non-production place for smoke checks, future baseline captures, and later shadow artifacts.

## Current Phase

PR 1 is baseline/fork tracking only. It establishes branch safety documentation, baseline artifact directories, and a no-LLM smoke runner.

The smoke runner must not require an OpenAI key, environment variables, network access, production retrieval imports, or graph-memory implementation modules.

## Non-Goals for PR 1

- No graph schemas.
- No graph retrieval.
- No RDF export.
- No LLM extraction.
- No production retrieval behavior changes.
- No benchmark output regeneration or reinterpretation.

## Expected Commands

Run the scaffold-only/default smoke check during bootstrap work:

```bash
uv run python -m evals.graph_memory_layer.run_smoke
```

Validate the frozen baseline case manifest with the no-LLM baseline validator:

```bash
uv run python -m evals.graph_memory_layer.validate_baseline_cases
```

This validation is standard-library only and safe for scaffold/baseline work.

Once fork enforcement is active for later stacked PRs, run strict branch-policy validation:

```bash
uv run python -m evals.graph_memory_layer.run_smoke --check-git-context
```

Strict git-context mode accepts the experiment root branch (`experiment/graph-memory-layer`) and any stacked branch that starts with `graph-exp/`. For a handoff that must be validated against one exact branch, add `--expected-branch`:

```bash
uv run python -m evals.graph_memory_layer.run_smoke --check-git-context --expected-branch graph-exp/01-freeze-baseline-reports
```

## Future PRs

Later phases may add graph materialization, graph reports, graph-shadow retrieval, entity candidates, relationship candidates, taxonomy governance, and live retrieval shadow mode.

Any LLM-backed experiment must be added behind explicit CLI flags in a later PR.
