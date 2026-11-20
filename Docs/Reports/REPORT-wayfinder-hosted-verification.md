# Wayfinder and Dossier hosted verification

Elderwyld on buddy.dungeonmind.net, November 20, 2026. Existing authenticated in-app browser. Entry CSS /assets/index-CFlN9PYC.css transferred 12,264 gzip bytes on five public requests. The running server image was confirmed as 11665f78bb9d8b200fa7c782a86a9052e6b3b30a, with uptime spanning the benchmark.

| Workload | Seconds in run order | p50 | Observed p95 |
| --- | --- | ---: | ---: |
| Fresh tab to Corrupted Edge heading | 1.378, 3.180, 1.995, 5.309, 7.997 | 3.180 | 7.997 |
| Picker saved page row click to heading | 1.319, 4.376, 4.729, 4.180, 6.013, 2.730, 5.400, 5.440 | 4.553 | 6.013 |
| Warm Build to Plan navbar marker | 0.073, 0.046, 0.046 | 0.046 | 0.073 |
| Warm Plan to Build navbar marker | 0.064, 0.045, 0.047 | 0.047 | 0.064 |

Fresh tabs reuse the authenticated browser profile and normal HTTP cache. Time starts before creating the tab. This measures a cold app instance and warm browser asset cache. Picker timing begins after search results appear, alternates Edge and Corrupted Edge, and selects the Pages row explicitly. An untimed setup attempt encountered two Edge rows and was corrected before collecting samples. Warm timing begins after opening navigation and measures the visible destination label, not a loaded Plan document. No timed attempt failed. With these sample sizes nearest-rank p95 is the sample maximum.

## Matched hosted release

Release 70f27ff1dac7eea2c79c7e1aa7016af884709d60 healthy. Wayfinder and Dossier selected together. Same authenticated browser, workloads, labels, and time windows. All timed attempts succeeded.

| Workload | Seconds in run order | p50 | Observed p95 |
| --- | --- | ---: | ---: |
| Fresh tab to Corrupted Edge heading | 2.095, 2.513, 2.408, 3.563, 2.971 | 2.513 | 3.563 |
| Picker saved page row click to heading | 1.381, 3.962, 4.461, 3.677, 4.257, 4.053, 4.577, 3.567 | 4.008 | 4.577 |
| Warm Build to Plan navbar marker | 0.053, 0.052, 0.049 | 0.052 | 0.053 |
| Warm Plan to Build navbar marker | 0.044, 0.047, 0.046 | 0.046 | 0.047 |

Hosted entry CSS /assets/index-XPUHb44_.css transferred 12,714 gzip bytes on five requests, up 450 bytes. Packaged Plex Sans and Mono total 60,360 bytes (45,712 and 14,648 respectively), with no font preloads. The navigation mark is inline SVG. The signed-in browser recorded both Plex faces as resources on themed Corrupted Edge. A fresh tab after resetting to Buddy and Original requested neither. Independent hosted requests returned 45,712 and 14,648 body bytes without extra HTTP compression. These are payload sizes on a cache miss, with request headers and cache hits excluded.

Preview verified independently on Corrupted Edge, including Wayfinder with parchment and Dossier with Buddy, and Cancel restored the original styling. Both applied styles survived reload and the document retained Saved status. Edge rendered a 21-row table with Plex Mono column headings. Published Sewer Meat Creature rendered in Dossier with its 280px natural-width portrait loaded. The opened Meat Mind revision displayed its mechanics without an image element.

## Shared controls and accessibility

- Keyboard activation opened Appearance and focused a radio on Home, Graph, Plan, Play, Ingest, Combat Tracker, and Build. Both saved selections and the default theme accent appeared on each surface. The shared navbar showed the gunmetal background and reticle while retaining the accessible Open navigation action. Escape closed Appearance.
- At a 390 × 844 test viewport, the Build canvas was 325 CSS pixels wide and the dialog was 337 CSS pixels wide. The observed document scroll width was within its viewport, and keyboard activation focused a radio.
- Token contrast ratios were 13.72:1 for Dossier ink against its canvas, 11.74:1 for headings against the canvas, 6.91:1 for muted ink against raised panels, and 12.31:1 for Wayfinder mint against navbar gunmetal. These are palette pair calculations.
- The inline bootstrap extracted from the deployed image passed seven cases, covering mixed and full appearance, legacy presets, and malformed preferences before the application bundle. The hosted reload restored both applied values. The bootstrap check does not measure font swap or paint timestamps.
- [Wayfinder #4241](https://github.com/Drakosfire/DungeonMindBuddy/pull/4241) and [Dossier #4245](https://github.com/Drakosfire/DungeonMindBuddy/pull/4245) were independently reviewed and merged. The hosted release applies the two changes over the measured baseline. See the [shared appearance design guide](../Design/ARCHITECTURE-surface-interaction-layer.md#appearance-and-authored-content).
