# DungeonMindBuddy Live Control UI

React product surfaces for DungeonMindBuddy. The UI talks to the merged FastAPI
server; it does not treat corpus files, browser state, or surface-local state as
a substitute for server/graph authority.

The root launcher is the normal product entry. Plan, Ingest / Graph Review,
Build, and Combat Tracker are first-class doors; the older `/surface` Live
Control module board remains reachable for legacy smoke coverage but is not the
current product composition model.

## Current surface model

The shared chrome and document model are now explicit:

```text
AppChrome
  ├─ global World Graph status / lens
  ├─ Agent + Projection host
  ├─ Tool host
  ├─ Edit host
  └─ SurfaceContextHost
       └─ active surface publishes its own context modules

active surface
  └─ Canvas / work object
       └─ exact workspace documentId when document-backed
```

The governing distinction is:

> **World Graph tells DungeonBuddy what world is available. Surface Context tells each surface what the operator has loaded into it. Canvas tells us what work object is being edited.**

Important ownership rules:

- workspace `documentId` is opaque server-issued work-object identity;
- campaign/session graph lens is application context, not document identity;
- Surface Context owns context presentation; individual surfaces own what their
  modules mean and how their controls behave;
- `MarkdownCanvasSession` owns accepted document record, revision, body,
  content SHA, dirty draft, reconciliation, and Markdown Save CAS;
- shared Tool/Edit/Agent/Projection hosts consume surface publications rather
  than requiring each surface to own duplicate floating bars;
- graph writes and worldbuilding authority elevation remain governed operations,
  not ordinary document metadata edits.

### Plan

Plan publishes `PREP` into Surface Context. The operator can choose an exact
active prep document or intentionally create a new one. Multiple prep documents
may share the same **For session** affinity; each remains a distinct server-owned
workspace document with its own opaque `documentId` and workspace path.

Session affinity is planning metadata. It does not name the file, identify the
document, or imply promotion to a canonical `Session N Prep.md` artifact.

### Build

Build publishes `DOCUMENT` into Surface Context. Bare `/build` is read-only with
respect to document creation: no worldbuilding source is created until the
operator chooses **New source**. Existing sources can be selected across the
admissible Build scope by exact `documentId`.

The final DOGFOOD-POLISH slice adds source rename from DOCUMENT context. Rename
is metadata-only but revision-aware: it PATCHes against the live Canvas
revision, rebases the returned revision into the same Canvas, preserves body,
content digest, dirty state, and editor identity, and serializes against Save.
Build graph-reference search/insert already uses the active World Graph
projection; rename does not cold-reload that projection.

See [`Docs/Reports/DOGFOOD-POLISH-CLOSEOUT-2026-08-11.md`](../../Docs/Reports/DOGFOOD-POLISH-CLOSEOUT-2026-08-11.md)
for the closed workstream and residual product tracks.

## Prerequisites

- Node.js 20+
- DungeonBuddy live-control FastAPI server running (defaults from
  `apps/live_control_server/config.py`)

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_LIVE_API_BASE_URL` | `""` (same-origin) | API base URL when not using the Vite dev proxy |
| `VITE_LIVE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Dev-server proxy target (see `vite.config.ts`) |
| `VITE_LIVE_PLANNING_MANIFEST_PATH` | `evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json` | Repo-relative manifest for legacy Chat `context_lookup` dogfood |

**Server (repo `.env`):** LLM-backed paths require `OPENAI_API_KEY` via
`src/bootstrap_env`. Optional model/runtime settings are controlled by the
server and `MODEL_POLICY.json`; do not put API keys into Vite/client env.

## Commands

```bash
cd apps/live-control-ui
pnpm install
pnpm dev        # http://localhost:5173 — proxies /api to the server
pnpm test       # Vitest
pnpm build      # typecheck + production bundle
```

Focused verification commonly uses:

```bash
pnpm exec vitest run src/workspaceDocument/ src/markdownCanvas/ src/planSurface/ src/buildSurface/
pnpm exec tsc -b
pnpm build
```

## Manual smoke

Play first-time setup is **not** just `uvicorn` plus `pnpm dev`. Configure
`DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` and run
`uv run python scripts/bootstrap_local_play.py apply` first. See
[`Docs/Runbooks/RUNBOOK-local-play-dogfood.md`](../../Docs/Runbooks/RUNBOOK-local-play-dogfood.md).

After that bootstrap, ordinary runtime is:

Terminal 1:

```bash
cd /path/to/DungeonMindBuddy
uv run uvicorn apps.live_control_server.main:app --reload
```

Terminal 2:

```bash
cd apps/live-control-ui
pnpm dev
```

**Start at the launcher:** open `http://127.0.0.1:5173/`, then choose the
surface from the launcher or site nav. Deep links are useful for targeted
verification but are not the normal product door.

### Plan smoke

1. Open **Plan**.
2. Confirm World Graph status remains in global nav and `PREP` appears directly
   below it in Surface Context.
3. Select an existing prep by title; confirm the URL/Canvas converge on one exact
   `documentId`.
4. Create a distinctly titled prep. `For session` is affinity only; creating a
   second prep for the same session must produce a different `documentId` and
   remain independently editable/savable.
5. Switch A → B → A and confirm any unsaved local draft for A returns.

### Build smoke

1. Open bare **Build** and confirm `DOCUMENT` shows no source loaded and no new
   source is created merely by entering the route.
2. Select an existing source; confirm Canvas appears only after exact-document
   admission.
3. Create a meaningfully named source and verify selector/URL/Canvas converge on
   the server-issued `documentId`.
4. Rename the active source from DOCUMENT context. With an unsaved sentence in
   Canvas, confirm rename leaves the sentence and `Unsaved changes` state intact;
   Save, hard reload, and verify both the new title and body survive.
5. Open **Tools → Find existing object**, inspect/insert a graph reference, and
   verify document rename itself does not restart World Graph loading.

### Combat Tracker

**Combat Tracker** opens the mature Mireward command-board tracker
(`evals/c2_live_prep/mireward-prep/combat.html`) at `/combat` (alias
`/combat.html`) — circular initiative, HP, statblock drilldown, import/export.
It is not the older Live Control React `CombatRosterModule`.

From `/`, open **Combat Tracker** and confirm the saved/bootstrap combat state
loads as expected.

## Legacy `/surface` board

The full Live Control board at `/surface` and the old module-layout APIs remain
reachable for legacy regression coverage. They are not the architecture to
copy when adding new product capabilities. New Plan/Build composition should go
through AppChrome + Surface Interaction + Surface Context instead.

Legacy Chat smoke, when specifically needed, still uses `/surface` and the
existing server live-turn path.

## Tiptap spike routes

The isolated `/tiptap-callout-spike` route remains an experimental exception:
its editable working-board document is stored only in browser `localStorage`.
Tiptap JSON is the editable source and semantic Markdown is a derived export.
The spike performs no backend or corpus writes. See
[`src/tiptap/state/README.md`](src/tiptap/state/README.md) for that experiment's
schema and data-flow boundary.

## Backend regression

From repo root:

```bash
uv run pytest tests/test_live_control_server.py -q
```
