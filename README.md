# DungeonMindBuddy

DungeonMindBuddy helps tabletop GMs turn campaign sources into material they
can build with, plan around, and use at the table.

- **Build** prepares source documents and reviews extracted material.
- **Plan** uses campaign context to prepare the next session.
- **Play** brings prepared material into the live session.
- **World Graph** lets you inspect what Buddy knows and trace it to its sources.

For example, start with a synthetic recap saying that the party found a sealed
door beneath the mill. Review the door and its source in Build, then bring the
unresolved lead into your next session plan.

## Run locally

Use Python 3.13, uv, and Node 22. Prepare the pinned Hermes source before
installing the locked Python dependencies.

```sh
python3.13 scripts/prepare_patched_hermes.py
uv sync --locked
```

Set up a local DungeonMindServer checkout beside Buddy, or point
`DUNGEONMIND_SERVER_ROOT` at it. Configure the database and runtime prerequisites
in the [local Play runbook](Docs/Runbooks/RUNBOOK-local-play-dogfood.md).
Then run `./run` and open [the local launcher](http://127.0.0.1:5173/).
The launcher starts the API and Vite UI and installs frontend dependencies
from the npm lockfile when needed.

## Explore the repository

| I want to… | Start here |
| --- | --- |
| Understand the product and its contracts | [Documentation](Docs/README.md) |
| Contribute or pick up an agent task | [AGENTS.md](AGENTS.md) |
| Work on the UI | [Frontend guide](apps/live-control-ui/README.md) |
| Build and configure the hosted package | [Production Compose example](deploy/production/compose.production.yaml) |
| Run an experiment or inspect evidence | [Lab and evaluation guide](evals/README.md) |

The product runs from `apps/` and `src/`. Versioned contracts live in
`schemas/`, and verification lives in `tests/` and `ci/`. DungeonMind owns
durable World state, and WorldKeeper coordinates governed changes. Campaign
sources are private. Use synthetic inputs in public demos and issue reports.
