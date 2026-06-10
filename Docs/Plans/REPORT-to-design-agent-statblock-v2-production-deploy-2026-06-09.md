# Report to design agent — StatBlock v2 production deploy

**Date:** 2026-06-09  
**Audience:** Agent working from command-board / StatBlockGenerator integration plans  
**Author:** Deploy session (ops + smoke test)  
**Status:** Production live; Buddy client integration not done

---

## 0. Copyable task prompt

```markdown
Re-anchor on production state after the 2026-06-09 StatBlock v2 deploy.

Read first:
- `Docs/Plans/REPORT-to-design-agent-statblock-v2-production-deploy-2026-06-09.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
- `Docs/Plans/HANDOFF-dungeonbuddy-statblockgenerator-proxy-client.md`
- `Docs/Plans/PLAN-command-board-combat-statblock-generator-roadmap.md`

Design against the **live** v2 producer contract (`command_board_draft_v2`), not the legacy `POST /api/statblockgenerator/generate-statblock` shape alone. Buddy must call v2 server-side with `X-DungeonBuddy-Internal-Key`; the browser never sees the key.

The next design/implementation slice should specify: proxy/client module, env vars, request mapping from command-board intent → `StatBlockDraftRequest`, response mapping → draft artifact + statblock drilldown + review surface + combat row hydration.
```

---

## 1. Executive summary

Production DungeonMindServer now exposes the StatBlockGenerator v2 command-board draft producer at `https://www.dungeonmind.net`, with internal API-key auth enforced.

What changed for product design: the command-board draft producer API described in the StatBlockGenerator v2 handoffs is now reachable in production and smoke-tested. DungeonBuddy integration can design against a verified live contract.

What did not change: DungeonBuddy has no code path that calls v2 yet. The existing planner statblock hook still targets a generic POST URL with `Authorization: Bearer` and a legacy payload/response shape, not the v2 draft envelope.

---

## 2. Production state after deploy

| Item | Value |
|---|---|
| Server | `alan@191.101.14.169` (`srv586875`) |
| Backend repo path | `/var/www/DungeonMind/DungeonMindServer` |
| Deployed commit | `b3cae86` — StatBlock v2 draft API + internal key lockdown |
| Previous production | `3a52f03` — 2026-05-23 CardGenerator fix only |
| API container | `dungeonmind-api-server-1`, healthy, port `7860` |
| External base URL | `https://www.dungeonmind.net` |

Monorepo note: production backend was pulled directly in `DungeonMindServer/`. The superproject at `/var/www/DungeonMind` may have stale submodule pointers; do not assume `git pull` at monorepo root updates the running API.

Untouched: `store-generator` container remains unhealthy from a pre-existing issue. Not in scope for this deploy.

---

## 3. Live API contract

### 3.1 Protected v2 routes

All three require `X-DungeonBuddy-Internal-Key` matching server env `DUNGEONBUDDY_INTERNAL_API_KEY`.

```text
GET  /api/statblockgenerator/v2/health
POST /api/statblockgenerator/v2/generate-draft
POST /api/statblockgenerator/v2/render-draft
```

Verified auth behavior:

| Condition | HTTP | Detail |
|---|---:|---|
| Key env unset on server | 500 | `Internal API key is not configured` |
| Header missing | 401 | `Missing internal API key` |
| Header wrong | 403 | `Invalid internal API key` |
| Header correct | 200 | route executes |

Implementation: `DungeonMindServer/routers/internal_auth.py` (`require_dungeonbuddy_internal_key`).

Design invariant: shared-secret gate only. Browser clients must not send this header. Buddy needs a server-side proxy or server-side caller.

### 3.2 v2 health response shape

```json
{
  "status": "ok",
  "service": "statblockgenerator",
  "contract": "command_board_draft_v2",
  "version": "0.1.0",
  "generator_ready": true,
  "openai_configured": true,
  "supports": ["generate-draft", "render-draft"],
  "timestamp": "..."
}
```

Use `GET /api/statblockgenerator/v2/health` as the seam test and readiness probe for Buddy's DungeonMind integration layer.

### 3.3 generate-draft — verified live

Fixture used on the server:

```text
DungeonMindServer/Docs/Design/fixtures/statblockgenerator-command-board-contract/generate_from_prompt.basic.json
```

Mode: `generate_from_prompt`  
Result: HTTP 200, `success: true`, full draft envelope including:

- `draft.statblock` — structured `StatBlockDetails`-compatible object;
- `draft.markdown` — rendered statblock markdown;
- `draft.combat_defaults` — fields like `name`, `armor_class`, `hit_points`, `initiative_bonus`, `passive_perception`, `speed_summary`, `primary_actions`;
- `draft.warnings` — array;
- `draft.provenance` — request id, mode, generator, generation info, persistence request;
- `draft.lifecycle_state` — `live_draft`;
- `draft.review_status` — `needs_dm_review`.

Example generated creature in smoke test: Reed-Cloaked Goblin Outrider (CR 1). OpenAI model reported in provenance: `gpt-4o-2024-08-06`.

Modes accepted by the contract but returning 501 in this slice:

- `generate_from_source_statblock`;
- `revise_existing`;
- `render_existing` on the `generate-draft` route — use `render-draft` instead.

### 3.4 render-draft — verified live

Request shape differs from generate: body uses top-level `statblock` (full `StatBlockDetails`), not `source_statblock`.

Smoke test: generated statblock from `generate-draft` was posted to `render-draft`; response was HTTP 200, `success: true`, `provenance.generation_info.generated: false`, `generator: statblock_draft_adapter.render_existing`.

This confirms render path wraps existing structured statblocks without a second LLM generation call.

### 3.5 Legacy app API — unchanged

```text
POST /api/statblockgenerator/generate-statblock
```

Still the app-facing OAuth/session workflow. v2 is additive. Command-board design should prefer v2 for draft envelopes; legacy remains for existing clients.

---

## 4. Environment and secrets

| Location | Variable | Status |
|---|---|---|
| Production `/var/www/DungeonMind/.env.production` | `DUNGEONBUDDY_INTERNAL_API_KEY` | Set during deploy |
| Local `DungeonMindBuddy/.env` | `DUNGEONBUDDY_INTERNAL_API_KEY` | Synced from production; gitignored |

Operator retrieval on server only; never commit the value:

```bash
grep DUNGEONBUDDY_INTERNAL_API_KEY /var/www/DungeonMind/.env.production
```

Local Buddy loads via `src/bootstrap_env.py` → `load_dungeonmindbuddy_dotenv()` (`.env` first).

### Integration gap

| Buddy today | v2 production |
|---|---|
| `DUNGEONMIND_STATBLOCK_URL` — generic POST target | `https://www.dungeonmind.net/api/statblockgenerator/v2/generate-draft` and siblings |
| `DUNGEONMIND_STATBLOCK_API_KEY` — `Authorization: Bearer ...` | `DUNGEONBUDDY_INTERNAL_API_KEY` — `X-DungeonBuddy-Internal-Key: ...` |
| Payload: legacy planner shape | Payload: `StatBlockDraftRequest` |
| Response: string-ish statblock extraction | Response: `StatBlockDraftResponse` nested draft envelope |

Design implication: Command-board generate/review flows should map to v2 modes and consume `combat_defaults`, `markdown`, `warnings`, and `provenance`, not the planner's current string-extraction loop.

---

## 5. Deploy steps executed

Full ops truth should also be captured in maintenance logs where available.

```bash
ssh alan@191.101.14.169

cd /var/www/DungeonMind/DungeonMindServer
git checkout main && git pull origin main

# DUNGEONBUDDY_INTERNAL_API_KEY appended to /var/www/DungeonMind/.env.production

cd /var/www/DungeonMind
docker compose build api-server
docker compose up -d api-server
```

Ops constraints on this host:

- Use `docker compose` as user `alan`; `sudo docker-compose` prompts for password.
- `sudo nginx -t` requires password; nginx was not reloaded during this session because existing config already proxies `/api/` to `api-server`.

---

## 6. Verification summary

| Check | Result |
|---|---|
| Global + v1 statblock health | 200 |
| v2 health + auth matrix | 500 / 401 / 403 / 200 as expected |
| v2 health via nginx external | 200 with key |
| generate-draft basic fixture | 200, full draft envelope |
| render-draft round-trip | 200, no LLM regeneration |
| CardGenerator regression | 200 |
| Container health | healthy |

---

## 7. Implications for command-board design

### 7.1 Producer is ready; client is not

Design the Buddy → DungeonMind boundary as:

```text
Command board UI / Statblock Workbench / Planning Mode
→ Buddy backend or planner tool, server-side
→ POST /api/statblockgenerator/v2/generate-draft | render-draft
→ StatBlockDraftResponse
→ draft artifact + review surface
→ accept → combat entity fields or corpus promotion path
```

Do not assume the current planner `generate_statblock` hook is this boundary; it predates v2.

### 7.2 combat_defaults maps to the combat tracker

Live smoke test returned fields aligned with the combat tracker columns:

- `armor_class`;
- `hit_points`;
- `initiative_bonus`;
- `passive_perception`;
- `speed_summary`;
- `primary_actions`;
- `suggested_tactics`.

Design statblock drilldown and add-to-combat hydration from `combat_defaults` first, structured statblock second, markdown for display.

### 7.3 Review is first-class

Generate responses use `review_status: needs_dm_review`. UI and agent flows should assume review/edit before durable acceptance, not silent auto-insert into initiative or corpus.

### 7.4 Terrain and encounter context are in the contract

The basic fixture includes `encounter_context` and `terrain_context`. Command-board terrain panel and planning mode should feed these fields on generate requests, not only free-text prompts.

### 7.5 Mode matrix for UX planning

| User intent | v2 mode / route | Live in prod? |
|---|---|---|
| New creature from prompt | `generate_from_prompt` | yes |
| Quick combat reinforcement | `quick_reinforcement` | yes |
| Terrain-aware controller | `terrain_pressure` | yes |
| Variant from corpus statblock | `generate_from_source_statblock` | no — 501 |
| Revise existing | `revise_existing` | no — 501 |
| Wrap existing structured statblock for display | `POST /render-draft` | yes |

Plan UI affordances accordingly: ship generate + render first; defer revise / variant-from-source until server implements those modes.

---

## 8. Recommended next design deliverables

1. Integration ADR or plan section for Buddy proxy module: env vars, header name, base URL, timeout, error mapping.
2. Request mapper spec: command-board / planning intent + terrain + corpus context → `StatBlockDraftRequest`.
3. Response mapper spec: `StatBlockDraftResponse` → `StatblockDraftArtifact` → combat entity JSON + statblock drilldown markdown.
4. Seam test checklist: v2 health + one fixture generate + render round-trip.
5. Security note: `DUNGEONBUDDY_INTERNAL_API_KEY` is equivalent to production statblock generation access; rotation procedure is update server env + Buddy env + restart relevant services.

---

## 9. Open follow-ups

- Implement Buddy v2 client / proxy.
- Wire command-board UI to review + accept flow using live draft envelope.
- Update monorepo submodule pointer when convenient.
- Investigate store-generator unhealthy state if Store Generator is needed.
- Sync local DungeonMindServer checkout to production commit for offline fixture/model reference.
- Write key rotation runbook if needed.

---

## 10. Bottom line

Production now exposes the draft producer the command-board design was aiming at. The remaining work is on the Buddy client boundary, statblock lifecycle model, agent-operable commands, review UX, storage/corpus promotion, and combat state hydration.
