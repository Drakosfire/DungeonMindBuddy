# DungeonMindBuddy

DungeonMindBuddy helps tabletop GMs turn campaign sources into material they
can build with, plan around, and use at the table.

- **Build** prepares source documents and reviews extracted material.
- **Plan** uses campaign context to prepare the next session.
- **Play** brings prepared material into the live session.
- **World Graph** lets you inspect what Buddy knows and trace it to its sources.

Try the [synthetic recap walkthrough](#try-a-synthetic-recap) to see how Build and Plan connect.

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
Then run `./run` and open [the Buddy landing page](http://127.0.0.1:5173/).

On a local Linux filesystem with available inotify watches, run
`CHOKIDAR_USEPOLLING=0 ./run` to opt into event-driven frontend reloads.
Use plain `./run` for the default two-second polling interval, including when
inotify reports `ENOSPC` or file changes fail to trigger reloads.

If Buddy's statblock client is enabled and uses the local DungeonMindServer,
set both values when choosing a nondefault Server port:

```bash
DUNGEONMIND_SERVER_PORT=7861 \
DUNGEONMIND_STATBLOCKS_BASE_URL=http://127.0.0.1:7861 \
./run
```

If the statblock client uses a remote DungeonMindServer, keep its configured
remote URL. The launcher port controls the local Server process.
The launcher starts the API and Vite UI and installs frontend dependencies
from the npm lockfile when needed.

| Page | Path |
| --- | --- |
| Home and surface navigation | `/` |
| Graph visualizer | `/graph` |
| Plan | `/plan` |
| Play | `/play` |
| Build, Ingest, and Combat Tracker | `/build`, `/ingest`, and `/combat` |

Plan and Play prompt for a World when none is selected. The legacy Chat smoke
uses `/surface`. See the [frontend smoke guide](apps/live-control-ui/README.md#manual-smoke).

## Try a synthetic recap

Start Buddy locally with an OpenRouter credential configured as
`OPENROUTER_API_KEY` or `DUNGEONBUDDY_OPENROUTER`. Recap extraction sends
the source text to OpenRouter, so use the synthetic text below. Select a
fresh test World. In Build, save a Markdown
document named **The sealed door beneath the mill** with this text:

```markdown
The party searched the old mill and found a sealed stone door beneath it.
Mira heard running water behind the door. The party left it unopened and
agreed to return with the miller's key.
```

With the saved document open, choose **Extraction**, set **Run mode** to
**Recap**, and fill in the campaign and session for your test World. Select
**Extract**. Review the proposed changes against the source text. Keep the
discovery and the unresolved lead, and check that the extraction does not
claim the party opened the door.

Choose **Prepare changes for review**. Check the selected changes before
merging them into campaign memory. Open **Plan** in the same World and check
the matching session's recap projection. Use the unresolved lead to draft
the next session's opening question: who has the miller's key?

## Hosted Buddy

The first hosted release supports DungeonMind sign-in, World selection,
read-only Graph, and sign-out. Build, Plan, Play, Ingest, Combat, and the
legacy Chat smoke are local workflows.

Follow the [production deployment runbook](Docs/Runbooks/RUNBOOK-buddy-production-deployment.md)
for database restore checks, the release build, DNS and TLS verification, and
the browser sign-in and sign-out smoke.

## Explore the repository

| I want to… | Start here |
| --- | --- |
| Understand the product and its contracts | [Documentation](Docs/README.md) |
| Contribute or pick up an agent task | [AGENTS.md](AGENTS.md) |
| Work on the UI | [Frontend guide](apps/live-control-ui/README.md) |
| Run tests for a change | [Verification standard](AGENTS.md#review-and-verification) and [frontend commands](apps/live-control-ui/README.md#commands) |
| Run an experiment or inspect evidence | [Lab and evaluation guide](evals/README.md) |

The product runs from `apps/` and `src/`. Versioned contracts live in
`schemas/`, and verification lives in `tests/` and `ci/`. DungeonMind owns
durable World state, and WorldKeeper coordinates governed changes. Campaign
sources are private. Use synthetic inputs in public demos and issue reports.
