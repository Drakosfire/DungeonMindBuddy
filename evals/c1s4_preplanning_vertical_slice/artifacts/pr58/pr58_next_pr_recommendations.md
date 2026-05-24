# Post-PR58 Planning Recommendations

1. **PR59 — query / ranking:** Direct probes hit corpus and support rows, but the real question text still misses (e.g. Q5 support buried under hempholm hub sections). Investigate query construction and top-k ranking before changing gold.
2. **PR60 — admission + renderer lanes:** `build_lane_budgeted_admission()` maps `location_context` and `party_timeline` into the budget bucket `prior_campaign_memory` and writes that back to `presentation_lane`, so materialized NPC/location evidence renders under Prior campaign memory instead of `character_party_behavior` / `location_worldbuilding`. Fix lane preservation end-to-end (admission budget keys + `render_context_packet` routing).
3. **Grishna corpus:** Thin README content is a separate retrieval-surface issue; do not inflate gold to match nav-only rows.
4. Re-run PR58 audit + Step2C multimode benchmark after PR59/PR60; keep gold unchanged until the earliest failing surface moves.
