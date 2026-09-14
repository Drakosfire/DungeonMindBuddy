# Full-corpus concurrency preflight

Generated: `2026-09-14T21:53:06Z`

## Document chronology

Policy: **serial C1 then C2**. 42 admitted recaps. Sample execution
max-active documents: `1`.

Campaign 1 sessions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]

Campaign 2 sessions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]

## In-document parallelism

Independent recap passes (node + beat): **6**.
Edge and party_claimed_fill stay after consolidation.

| Mode | max active independent passes | wall_ms | sum elapsed_ms |
|---|---:|---:|---:|
| workers=1 | 1 | — | — |
| workers=6 | 6 | 43.9 | 240.9 |

Safe `node_pass_workers`: **6**. Extra workers cannot overlap edge/claimed-fill.

APP-STATE ExtractionRun registration is skipped for this slice so the leased
worktree does not write into a live Buddy postgres.
