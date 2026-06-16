# Graph Memory Experiment Fork Tracking

Status: active experiment
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
