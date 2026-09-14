# Stage 4L Successor: Zero-Model Relationship Publication Replay Report

## Summary

- **Campaign ID:** `longmont-c1`
- **Generated at:** `2026-09-14T18:27:58Z`
- **Model calls:** `0` (zero new inference cost)
- **Cost:** `$0.00`
- **Authoritative S10 Revision:** `rev:c839ca5587f06dda2eb485dad1e50fe6`
- **Total relationships published:** 150 / 276 (54.3%)

## Comparison: Stage 4L Initial vs Relationship Publication Slice

| Metric | Stage 4L Initial Run | Relationship Publication Slice | Delta |
|---|---|---|---|
| Published relationships | 7 / 276 (2.5%) | 150 / 276 (54.3%) | +143 relationships |
| Inference cost | $0.098863 | $0.000000 | $0.00 (replayed from paid candidates) |
| PC identity | 6/6 `player_character` | 6/6 `player_character` | Stable |
| Rehearsal DB isolation | Enforced (:54329) | Enforced (:54329) | Maintained |

## Per-Session Breakdown

| Session | Extracted Edges | Admitted Predicates | Publishable | Published | Publication Mode | Parent Revision | Committed Revision |
|---|---|---|---|---|---|---|---|
| S01 | 31 | 30 | 25 | 25 | `edge_selective` | `rev:d5c54ab85691...` | `rev:bbb258ba3532...` |
| S02 | 7 | 7 | 7 | 7 | `all` | `rev:bbb258ba3532...` | `rev:c60ac9c4d73c...` |
| S03 | 37 | 34 | 12 | 12 | `edge_selective` | `rev:c60ac9c4d73c...` | `rev:3d242762b43f...` |
| S04 | 39 | 36 | 22 | 22 | `edge_selective` | `rev:3d242762b43f...` | `rev:14c03eb14f24...` |
| S05 | 27 | 25 | 14 | 14 | `edge_selective` | `rev:14c03eb14f24...` | `rev:cdfefa51ebff...` |
| S06 | 36 | 36 | 26 | 26 | `edge_selective` | `rev:cdfefa51ebff...` | `rev:3fa1e0c0ac56...` |
| S07 | 32 | 29 | 12 | 12 | `edge_selective` | `rev:3fa1e0c0ac56...` | `rev:70314e4ef047...` |
| S08 | 29 | 27 | 21 | 21 | `edge_selective` | `rev:70314e4ef047...` | `rev:2d8d5d260c43...` |
| S09 | 22 | 21 | 5 | 5 | `edge_selective` | `rev:2d8d5d260c43...` | `rev:a6affcce8861...` |
| S10 | 16 | 15 | 6 | 6 | `edge_selective` | `rev:a6affcce8861...` | `rev:c839ca5587f0...` |

## Next Steps & Product Decision

1. **Relationship publication successfully resolved**: 150 edges published across S1..S10 (54.3% across the entire corpus, with 100% of publishable semantic edges admitted).
2. **Evidence preserved**: Zero model calls, exact candidate digests match the paid manifest.
3. **Ready for C1 QA Benchmark**: Now that the World graph contains both entities and relationships, run the 16-question evaluation (oracle-answerable vs Agent-answerable) against this authoritative head.
