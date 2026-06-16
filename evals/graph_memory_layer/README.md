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

```bash
uv run python -m evals.graph_memory_layer.run_smoke
```

## Future PRs

Later phases may add graph materialization, graph reports, graph-shadow retrieval, entity candidates, relationship candidates, taxonomy governance, and live retrieval shadow mode.

Any LLM-backed experiment must be added behind explicit CLI flags in a later PR.
