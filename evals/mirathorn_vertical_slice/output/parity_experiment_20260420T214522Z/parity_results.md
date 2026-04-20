# Mirathorn parity experiment — Phase A

Source: `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md`
Entity model: `gpt-5.4-mini` · Fact model: `gpt-5.4-mini`

## Counts per cell

| Cell | Path | bs | evidence | entities (extracted) | entities (post-store) | facts (extracted) | facts (post-store) | elapsed (s) |
|------|------|----|----------|----------------------|-----------------------|-------------------|--------------------|-------------|
| A | direct | 1 | 126 | 122 | — | 349 | — | 848.73 |
| B | direct | 5 | 126 | 146 | — | 359 | — | 405.0 |
| C | cli | 1 | 126 | 164 | 164 | 600 | 600 | 261.78 |
| D | cli | 5 | 126 | 87 | 87 | 382 | 382 | 123.7 |

## Slot-drop warnings per cell

| Cell | entity_missing | entity_duplicate | fact_missing | fact_duplicate |
|------|----------------|------------------|--------------|----------------|
| A | 0 | 0 | 0 | 0 |
| B | 0 | 0 | 0 | 0 |
| C | 0 | 0 | 0 | 0 |
| D | 1 | 0 | 1 | 0 |

## Auto-interpretation

- **A→B (direct path: bs=1 → bs=5)**: facts 349 → 359 (+10 (+2.9%)). Isolates batching effect on direct path.
- **A→C (bs=1: direct → CLI)**: facts 349 → 600 post-store (+251 (+71.9%)). Pre-store: 600 (+251 (+71.9%)). Isolates CLI overhead at fixed batch_size.
- **C→D (CLI: bs=1 → bs=5)**: facts post-store 600 → 382 (-218 (-36.3%)). Isolates CLI batching effect.
- **A→D (the headline gap)**: facts 349 → 382 post-store (+33 (+9.5%)). The full observed gap.

Pre-store vs post-store gap on CLI cells indicates how much the FactStore is dropping/merging:
- C: pre-store 600 → post-store 600 (+0 (+0.0%))
- D: pre-store 382 → post-store 382 (+0 (+0.0%))
