# Stage 4L Successor: Zero-Model Relationship Publication Replay Report

## Summary

- **Campaign ID:** `longmont-c1`
- **Generated at:** `2026-09-14T20:03:24Z`
- **Model calls:** `0` (zero new inference cost)
- **Cost:** `$0.00`
- **Authoritative S10 Revision:** `rev:b82db72693c27e0218026fd1ff514a68`
- **Total relationships published:** 219 / 276 (79.3%)

## Comparison: Stage 4L Initial vs Relationship Publication Slice

| Metric | Stage 4L Initial Run | Relationship Publication Slice | Delta |
|---|---|---|---|
| Published relationships | 7 / 276 (2.5%) | 219 / 276 (79.3%) | +212 relationships |
| Inference cost | $0.098863 | $0.000000 | $0.00 (replayed from paid candidates) |
| PC identity | 6/6 `player_character` | 6/6 `player_character` | Stable |
| Rehearsal DB isolation | Enforced (:54329) | Enforced (:54329) | Maintained |

## Per-Session Breakdown

| Session | Extracted Edges | Admitted Predicates | Publishable | Published | Publication Mode | Parent Revision | Committed Revision |
|---|---|---|---|---|---|---|---|
| S01 | 31 | 30 | 25 | 25 | `edge_selective` | `rev:d5c54ab85691...` | `rev:b5f21874667a...` |
| S02 | 7 | 7 | 7 | 7 | `all` | `rev:b5f21874667a...` | `rev:13958eaf6090...` |
| S03 | 37 | 34 | 25 | 25 | `edge_selective` | `rev:13958eaf6090...` | `rev:f028f280fffa...` |
| S04 | 39 | 36 | 28 | 28 | `edge_selective` | `rev:f028f280fffa...` | `rev:805502327249...` |
| S05 | 27 | 25 | 22 | 22 | `edge_selective` | `rev:805502327249...` | `rev:491d14cec5cd...` |
| S06 | 36 | 36 | 34 | 34 | `edge_selective` | `rev:491d14cec5cd...` | `rev:d597b5fca1e7...` |
| S07 | 32 | 29 | 24 | 24 | `edge_selective` | `rev:d597b5fca1e7...` | `rev:a5aee4b86bce...` |
| S08 | 29 | 27 | 25 | 25 | `edge_selective` | `rev:a5aee4b86bce...` | `rev:2d30359fbe9d...` |
| S09 | 22 | 21 | 15 | 15 | `edge_selective` | `rev:2d30359fbe9d...` | `rev:494e5dd86f1e...` |
| S10 | 16 | 15 | 14 | 14 | `edge_selective` | `rev:494e5dd86f1e...` | `rev:b82db72693c2...` |

## PC Continuity (Zero Duplicate Objects)

All six Campaign 1 Player Characters maintain stable canonical identity (`dnd5e:player_character`) without duplicate object creation.
Candidate kind `pc` is normalized to `player_character` at the general identity/type equivalence boundary in `apps/live_control_server/models/world_graph_mutation_context.py`.

## Detailed Relationship Analysis

Comprehensive edge-by-edge rejection analysis and accounting available in `relationship_analysis/`:
- `relationship_analysis/summary.json`
- `relationship_analysis/relationships.json`
- `relationship_analysis/REPORT.md`

## Next Steps & Product Decision

1. **Relationship publication significantly increased**: 219 / 276 edges published (79.3%), up from 150 / 276 (54.3%).
2. **PC blackout resolved**: 72 unique PC relationships published (up from 3), with 0 blocked identity collisions.
3. **Ready for C1 QA Benchmark**: Core PC continuity across Sessions 1–10 is restored without model calls or graph re-extraction.
