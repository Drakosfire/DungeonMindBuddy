# Stage 4J rehearsal World database

Stage 4J publication must target an **isolated rehearsal** PostgreSQL instance — never live Eldyrwild World authority on `127.0.0.1:54330` / `dungeonmind_cutover_live`.

## Required env

```bash
export DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind
export DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL='postgresql://dungeonmind:dungeonmind-local@127.0.0.1:54329/dungeonmind_stage4j_rehearsal'
```

Optional OpenRouter key for extract:

```bash
export OPENROUTER_API_KEY='...'
# or
export DUNGEONBUDDY_OPENROUTER='...'
```

## Local rehearsal Postgres (example)

Use the DungeonMind dev port (`54329`), not authority (`54330`):

```bash
docker run --rm -d \
  --name dungeonmind-stage4j-rehearsal \
  -e POSTGRES_USER=dungeonmind \
  -e POSTGRES_PASSWORD=dungeonmind-local \
  -e POSTGRES_DB=dungeonmind_stage4j_rehearsal \
  -p 127.0.0.1:54329:5432 \
  postgres:16

# Apply DungeonMind schema/migrations for your checkout, then initialize world head if needed.
```

## Guard behavior

`assert_rehearsal_world_db_url()` fails closed when the DSN matches live fingerprints (`:54330`, `dungeonmind_cutover_live`, `cutover_live`). Override only with explicit operator ack:

```bash
export DMB_STAGE4J_ALLOW_LIVE_WORLD=1   # NOT for Stage 4J rehearsal
```

## Batch runner

```bash
uv run python tools/stage4j_c2_deepseek_graph_rehearsal.py census
uv run python tools/stage4j_c2_deepseek_graph_rehearsal.py extract --sessions 1,2,3
uv run python tools/stage4j_c2_deepseek_graph_rehearsal.py promote
uv run python tools/stage4j_c2_deepseek_graph_rehearsal.py dogfood
```

Receipts: `out/stage4j_c2_deepseek_graph_rehearsal/receipts/session_NN.json`
