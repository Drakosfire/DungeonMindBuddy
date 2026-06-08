# Ingested corpus library

- **schema:** `dmb_ingested_corpus_library_v1`
- **generated_at:** 2026-06-06T23:11:15Z
- **corpus_root:** `corpus/eldyrwild-markdown`

## Summary

- Campaigns indexed: **2**
- Total corpus `.md` files: **388**
- Session pipeline tiers:
  - `breadcrumb_memory`: 5 sessions
  - `full_with_staging`: 2 sessions
  - `normalized_only`: 32 sessions

## Retrieval activation vs full ingest

The C2S23 planning manifest (`evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json`) activates **43** routes
for planning session **23** with source sessions **[21, 22]**.

- Ingest-related routes on disk (sessions + hubs + prep): **249**
- Overlap with C2S23 manifest: **40**
- Not in C2S23 manifest: **209**

The dogfood-full manifest (`evals/c2_live_prep/benchmarks/c2s23_dogfood_full_manifest.json`) activates **182** routes
with source sessions **[21, 22, 23]**.

- Overlap with dogfood-full manifest: **73**
- Not in dogfood-full manifest: **176**

## longmont-c1

Sessions: **17** | Prep docs: **0**
| Loose campaign markdown (Factions, Cards, etc.): **1**

| Session | Tier | Canon | Norm | Crumb | Memory | Staging | Blessed |
|---------|------|-------|------|-------|--------|---------|---------|
| 1 | `breadcrumb_memory` | yes | yes | yes | yes | — | yes |
| 2 | `breadcrumb_memory` | yes | yes | yes | yes | — | yes |
| 3 | `breadcrumb_memory` | yes | yes | yes | yes | — | yes |
| 4 | `normalized_only` | yes | yes | — | — | — | — |
| 5 | `normalized_only` | yes | yes | — | — | — | — |
| 6 | `normalized_only` | yes | yes | — | — | — | — |
| 7 | `normalized_only` | yes | yes | — | — | — | — |
| 8 | `normalized_only` | yes | yes | — | — | — | — |
| 9 | `normalized_only` | yes | yes | — | — | — | — |
| 10 | `normalized_only` | yes | yes | — | — | — | — |
| 11 | `normalized_only` | yes | yes | — | — | — | — |
| 12 | `normalized_only` | yes | yes | — | — | — | — |
| 13 | `breadcrumb_memory` | yes | yes | yes | yes | — | yes |
| 14 | `normalized_only` | yes | yes | — | — | — | — |
| 15 | `normalized_only` | yes | yes | — | — | — | — |
| 16 | `normalized_only` | yes | yes | — | — | — | — |
| 17 | `normalized_only` | yes | yes | — | — | — | — |

### locations — 10 entities (readme:10)

### npcs — 21 entities (dossier:4, readme:21, timeline:15)

### pcs — 6 entities (dossier:6, readme:6, timeline:6)

## longmont-c2

Sessions: **22** | Prep docs: **19**
| Loose campaign markdown (Factions, Cards, etc.): **13**

| Session | Tier | Canon | Norm | Crumb | Memory | Staging | Blessed |
|---------|------|-------|------|-------|--------|---------|---------|
| 1 | `normalized_only` | yes | yes | — | — | — | — |
| 2 | `normalized_only` | yes | yes | — | — | — | — |
| 3 | `normalized_only` | yes | yes | — | — | — | — |
| 4 | `normalized_only` | yes | yes | — | — | — | — |
| 5 | `normalized_only` | yes | yes | — | — | — | — |
| 6 | `normalized_only` | yes | yes | — | — | — | — |
| 7 | `normalized_only` | yes | yes | — | — | — | — |
| 8 | `normalized_only` | yes | yes | — | — | — | — |
| 9 | `normalized_only` | yes | yes | — | — | — | — |
| 10 | `normalized_only` | yes | yes | — | — | — | — |
| 11 | `normalized_only` | yes | yes | — | — | — | — |
| 12 | `normalized_only` | yes | yes | — | — | — | — |
| 13 | `normalized_only` | yes | yes | — | — | — | — |
| 14 | `normalized_only` | yes | yes | — | — | — | — |
| 15 | `normalized_only` | yes | yes | — | — | — | — |
| 16 | `normalized_only` | yes | yes | — | — | — | — |
| 17 | `normalized_only` | yes | yes | — | — | — | — |
| 18 | `normalized_only` | yes | yes | — | — | — | — |
| 19 | `normalized_only` | yes | yes | — | — | — | — |
| 20 | `breadcrumb_memory` | yes | yes | yes | yes | — | yes |
| 21 | `full_with_staging` | yes | yes | yes | yes | yes | — |
| 22 | `full_with_staging` | yes | yes | yes | yes | yes | — |

### npcs — 5 entities (dossier:5, other:2, readme:5, timeline:5)

### pcs — 6 entities (dossier:6, other:1, readme:6, statblock:6, timeline:6)

## Elderwyld (world layer)

- Markdown files: **126**
- Top-level dirs: Cities and Towns, Events, Inns and Shops, Item Cards, Migrating Forest, Roads, Shephards Flock, Wilderness

## Live workspaces (eval)

- Session **22**: `evals/c2_live_prep/live/session_22` — live_packet.json, event_log.jsonl, current_state.json, surface_layout.json
- Session **23**: `evals/c2_live_prep/live/session_23` — live_packet.json, recap.md, event_log.jsonl, current_state.json, surface_layout.json

## Regenerate

```bash
uv run python scripts/build_ingested_corpus_library.py
```
