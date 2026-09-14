# Full-corpus recap ingest — scale / health (`openai-gpt-5.4-mini`)

Generated from this arm's `INGEST.json` after the serial C1→C2 run.
Do not overwrite this directory with a later provider arm.

## Execution

Generated from `INGEST.json` after the serial C1→C2 run.

## Execution

| Item | Result |
|---|---|
| Documents | 42 / 42 ok (C1 S1–S17, then C2 S1–S25) |
| Model | `gpt-5.4-mini` |
| `node_pass_workers` | 6 (intra-document only) |
| Document chronology | serial; extra-known-entity count 28 → 886 (monotonic) |
| APP-STATE registration | skipped (worktree isolation) |
| Worldbuilding | DEFER |
| Wall time (full run) | 981 s (~16.4 min), S1 resumed from canary |
| Independent-pass overlap | mean wall 10.4 s vs sum 40.0 s (ratio 3.83) |
| Total cost | $3.332783 |

C1 S1 canary (paid, before resume): independent wall 12.6 s vs sum 54.5 s; document wall 30.0 s; $0.066.

## Candidate inventory

| Metric | Min | Max | Sum |
|---|---:|---:|---:|
| Nodes per recap | 15 | 61 | 1265 |
| Edges per recap | 0 | 27 | 463 |

No recap produced an empty node set.

Recaps with **zero edges** (extraction succeeded; relationship pass emitted none):

- `longmont-c1/session-17`
- `longmont-c2/session-7`
- `longmont-c2/session-8`
- `longmont-c2/session-11`
- `longmont-c2/session-12`

## What this is not

These are durable **candidates and receipts**, not a published World Graph and not a UI GO/HOLD. Publication still needs an isolated DungeonMind rehearsal env and a continuity review.

## Next

Scale/health/continuity review of the candidate graphs, then a UI GO/HOLD. Do not ingest worldbuilding on this path.
