# Live Control UI (C2 L4)

React surface shell for the C2 Live Control product. The UI talks only to the merged L3 FastAPI server — it does not read or write session seed files directly.

## Prerequisites

- Node.js 20+
- L3 server running with Session 22 files on disk (default session dir from `apps/live_control_server/config.py`)

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_LIVE_API_BASE_URL` | `""` (same-origin) | API base URL when not using the Vite dev proxy |
| `VITE_LIVE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Dev-server proxy target (see `vite.config.ts`) |
| `VITE_LIVE_PLANNING_MANIFEST_PATH` | `evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json` | Repo-relative manifest for Chat `context_lookup` (hub/world dogfood: set to `c2s23_dogfood_full_manifest.json`) |

**L3 server (repo `.env`):** live turns are classified with an LLM (`src/live_play/classify_live_turn.py`). Requires `OPENAI_API_KEY` via `src/bootstrap_env`. Optional: `LIVE_TURN_CLASSIFIER_MODEL`, `MODEL_POLICY.json` action `live_turn_classifier` (defaults to `cheapest`). Set `LIVE_TURN_CLASSIFIER_ALLOW_HEURISTIC_FALLBACK=1` only for offline/deterministic runs (pytest sets this automatically).

## Commands

```bash
cd apps/live-control-ui
npm install
npm run dev      # http://localhost:5173 — proxies /api to L3
npm test         # Vitest unit tests (mocked fetch)
npm run build    # typecheck + production bundle
```

## Troubleshooting

**`Unexpected token '<', "<!doctype "... is not valid JSON`** — the browser received Vite’s `index.html` (or another HTML page), not the FastAPI JSON API. Fix:

1. Start the L3 server first (terminal 1 below) and confirm `curl -s http://127.0.0.1:8000/api/live/surface | head -c 40` prints `{"catalog"`.
2. Use `npm run dev` (port 5173 proxies `/api` → `http://127.0.0.1:8000`). Do **not** use `npm run preview` without also serving the API.
3. Leave `VITE_LIVE_API_BASE_URL` unset unless you point it at a running server base URL (never at the Vite dev URL alone).

## Manual smoke (with L3)

Terminal 1:

```bash
cd /path/to/DungeonMindBuddy
export DUNGEONMIND_LIVE_SESSION_DIR=evals/c2_live_prep/live/session_22
uv run uvicorn apps.live_control_server.main:app --reload
```

Terminal 2:

```bash
cd apps/live-control-ui && npm run dev
```

Submit in Chat:

```text
Weather 7. Caelynn Nature 19.
```

Expect answer containing `Hail dent`, badges `fast_live` and `roll_result`, and a new Record row.

## Modules (v0)

- **Required:** Chat, Record
- **Implemented optional:** Roll stack (human table labels), Now (when enabled in layout)
- **Unsupported:** catalog modules without a React implementation show a placeholder

Layout changes persist through `PUT /api/live/surface/layout` only (no localStorage authority).

## Backend regression

From repo root:

```bash
uv run pytest tests/test_live_control_server.py -q
```
