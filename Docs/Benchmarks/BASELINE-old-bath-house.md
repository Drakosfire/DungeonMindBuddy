# Old Bath House performance baseline

Measures the signed-in Buddy → Plan → Play → Combat workflow for Session 32 in Elderwyld. Both tracks ran on pinned Buddy source `2d4361fb05e0b6bbb4e652535b77acd7b30ad1fb`, image `sha256:a469deffc039f40de0459cd57f35c2412a50d2e3e6ba57bdb7de15202b57f418`, and App schema `20261123_0204`. Runs used a fresh Chromium context and disposable write state.

- **Pinned assets** used the same reviewed Edge Meat Mind and Meatling revisions and saved portraits. Three of three runs qualified. [PR #4555](https://github.com/Drakosfire/DungeonMindBuddy/pull/4555)
- **Live providers** replayed the saved brainstorm with Jev and OpenAI, accepted a new statblock, and timed fal image generation through a decoded private preview. It bound the existing reviewed portrait to that statblock for the handoff. Three of four runs qualified. One returned no reviewable statblock and was excluded from latency statistics. [PR #4562](https://github.com/Drakosfire/DungeonMindBuddy/pull/4562)

Every qualified run verified exact statblock revision and portrait provenance through Plan and Play, confirmed that parley left Combat unstarted, and required an explicit **Start this encounter** click to create a separate running encounter. A saved HP edit persisted without changing the Plan or prepared encounter.

## Results

Median in milliseconds with observed minimum and maximum. The sample count is too small for a useful p95.

| Phase | Pinned assets, n=3 | Live providers, n=3 |
| --- | ---: | ---: |
| First visible Buddy reply | — | 10,559 (10,326–11,357) |
| Buddy reply completion | — | 10,498 (10,266–11,300) |
| Statblock generation | — | 84,198 (78,278–111,985) |
| Portrait generation through decoded preview | — | 28,563 (27,607–30,807) |
| Bind saved portrait | 337 (333–368) | 319 (310–325) |
| Assemble encounter | 4,094 (4,006–4,140) | 4,000 (3,986–4,007) |
| Confirm Plan attachment | 96 (85–99) | 96 (85–98) |
| Create Play session | 863 (855–864) | 857 (852–862) |
| Open Play preview | 369 (359–370) | 362 (355–365) |
| Explicit Combat start | 94 (91–103) | 88 (80–108) |
| Render statblock portrait | 817 (815–820) | 818 (816–818) |

Reply completion measures receipt of the terminal response. First visible reply measures browser rendering. The live generation phases include provider variability. The replay excludes human deliberation time.

## Reproduce and compare

Use the [runner and fixture instructions](../../evals/old_bath_house/README.md). The fixture SHA-256 is `c2f6e3879a463002401c85f452a8de456beab46f558a357d3c4447c5020424d7` for pinned assets and `6e9dda08a93faa1f8423d5e1d684da3ca3483bba8bdee2dabe0f545398efb31b` for live providers. The comparator groups records by track, fixture digest, and run conditions, and retains failed samples separately.

```sh
python -m evals.old_bath_house.compare Docs/Benchmarks/old-bath-house-runs.json candidate.json
```
