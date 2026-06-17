# Graph Memory Experiment Fork Tracking

Status: active experiment
Fork enforcement status: bootstrap-only / not yet active
Canonical repo: Drakosfire/DungeonMindBuddy (upstream remote not configured locally)
Experiment fork: local-only experiment branch stack (origin remote not configured locally)
Experiment root branch: experiment/graph-memory-layer
Current stacked branch: graph-exp/00-fork-tracking-baseline
Base commit: 01772eb graph experiment design
Created: 2026-06-16
Last verified: 2026-06-16

## Remote Contract

`origin` must point to the experiment fork.
`upstream` should point to the canonical DungeonMindBuddy repo.
No experiment work should be committed directly to canonical `main`.

Current local verification: no Git remotes are configured in this checkout, so this PR uses the local experiment branch fallback until a fork remote is available.

This first scaffold PR is a bootstrap PR targeting `main`; strict fork/branch enforcement begins with the next Graph Memory experiment PR. Strict mode accepts the experiment root branch (`experiment/graph-memory-layer`) and stacked branches matching `graph-exp/*`; use `--expected-branch` when a handoff needs one exact branch.

## Branch Contract

Root experiment branch:

`experiment/graph-memory-layer`

Stacked PR branches should use:

`graph-exp/<number>-<short-name>`

Current first PR branch:

`graph-exp/00-fork-tracking-baseline`

## Verification Commands

```bash
git remote -v
git branch --show-current
git status --short
git log -1 --oneline
```

Last verification output before edits:

```text
$ git remote -v

$ git branch --show-current
graph-exp/00-fork-tracking-baseline

$ git status --short

$ git log -1 --oneline
01772eb graph experiment design
```

## Future Strict Git-Context Check

Future PRs should run the smoke runner with strict git-context validation once the experiment fork/branch stack is active:

```bash
uv run python -m evals.graph_memory_layer.run_smoke --check-git-context
```

The strict check accepts `experiment/graph-memory-layer` and any `graph-exp/*` stacked branch. It rejects `main`, `master`, and arbitrary non-experiment branches. To enforce a specific handoff branch, pass `--expected-branch` with `--check-git-context`:

```bash
uv run python -m evals.graph_memory_layer.run_smoke --check-git-context --expected-branch graph-exp/01-freeze-baseline-reports
```

The strict check is intentionally opt-in for this bootstrap PR because fork enforcement is not yet active.

## Safety Rules

No production retrieval behavior changes in this experiment unless behind an explicit feature flag.
No LLM calls in baseline/fork tracking PRs.
No generated graph facts without provenance.
No graph summaries admitted as evidence.
No ontology/taxonomy mutation outside explicit proposal files.
No merge-back to main without promotion report.

## Promotion Path

Experiment branch first.
Shadow artifacts second.
Measured comparison third.
Production merge only after explicit promotion gate.
