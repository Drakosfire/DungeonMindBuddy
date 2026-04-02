# Model A/B Comparison (Task B, taxonomy v3)

Compared `structured_generation` with updated taxonomy/prompt pass (`phase_b_pass1_entity_extraction_v3_taxonomy_refresh`):
- **A (cheap)**: `cheapest` -> `gpt-5.4-nano`
- **B (fast_smart)**: `fast_smart` -> `gpt-5.3-codex`

Model policy was temporarily switched for the fast_smart run and restored to `cheapest`.

## Aggregate (3-file slice)

- Entities: nano 246 vs fast_smart 170
- Facts: nano 1123 vs fast_smart 583
- Weighted `other` rate: nano 24.80% vs fast_smart 22.94%
- Total ingest time: nano 217004ms vs fast_smart 180144ms

## Per-file

| File | Model | Entities | Facts | Other % | Runtime ms |
|---|---:|---:|---:|---:|---:|
| `The City of Mirathorn.md` | nano | 162 | 875 | 22.84% | 144026 |
| `The City of Mirathorn.md` | fast_smart | 116 | 426 | 22.41% | 129665 |
| `Longmont Campaign General Notes.md` | nano | 35 | 123 | 45.71% | 24126 |
| `Longmont Campaign General Notes.md` | fast_smart | 18 | 73 | 33.33% | 23699 |
| `Session 6 - The Road to Miraholm.md` | nano | 49 | 125 | 16.33% | 48852 |
| `Session 6 - The Road to Miraholm.md` | fast_smart | 36 | 84 | 19.44% | 26780 |

## Taxonomy Health (store-level)

### nano
- `entity_kind` missing: 0
- semantic facet unique count: 21
- semantic facet singleton count: 1
- top facets: theme (54), plot_hook (37), trade_good (37), consumable (32), conflict (31), settlement (30), profession (29), artifact (28), organization (24), route (21)

### fast_smart
- `entity_kind` missing: 0
- semantic facet unique count: 20
- semantic facet singleton count: 1
- top facets: consumable (21), organization (17), trade_good (15), settlement (13), profession (12), document_section (10), title (10), species (9), creature_species (8), artifact (7)

## Notes

- This run includes new fields: `entity_kind` and `semantic_facets`, with backward-compatible `entity_type` and `entity_tags` retained.
- `other` remains meaningful but should continue to shrink with targeted prompt/rules follow-ups for concept/event boundary cases.
