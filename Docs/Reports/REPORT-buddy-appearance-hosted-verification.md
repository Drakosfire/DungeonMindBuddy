# Buddy appearance and hosted load measurements

The [Surface Interaction Layer authority](../Design/ARCHITECTURE-surface-interaction-layer.md#appearance-and-authored-content) defines the shared tokens and settings. This report records hosted observations from November 19 and 20, 2026.

## Appearance

- The shared control opened by keyboard on Home, Graph, Plan, Play, Ingest, Build, and Combat Tracker. Both presets showed the selected radio and focused the dialog. Escape restored the saved palette and returned focus on Play, Combat Tracker, and Home, where focus return was checked explicitly.
- Computed Appearance dialog text contrast was 14.92:1 in Buddy and 12.47:1 in Deep Teal. These ratios cover the dialog's primary ink and background. Build's Conversation history button showed visible Sky blue keyboard focus.
- Deep Teal survived reload and navigation from Build to Plan. The app reads the browser preference before loading the frontend bundle.
- Corrupted Edge kept its paper, ink, font, and saved status. The linked Edge table retained its measured styles. A saved Sewer Meat Creature revision retained its background, heading ink and font, and measured width. That revision had no portrait.
- The Build message “Set Buddy’s accent to Sky blue” offered a preview on hosted Corrupted Edge. Cancel restored the previous accent. Apply saved through the shared settings model, and the navbar reset it. This bounded appearance request is handled locally.

## Hosted performance

Use the same signed-in browser tab and World. Leave the picker closed for the direct-open workload. Reload the Corrupted Edge link and measure elapsed wall time until the document heading is visible. Allow up to three consecutive 10-second heading waits after reload and record failures separately. These runs restart the app in a warm browser session. They leave the HTTP asset cache in its normal state.

For warm navigation, use the navbar to alternate Plan and Build. Measure from clicking the destination link until its shell marker appears. For picker opens, start with Corrupted Edge visible, search for Edge, select the exact Edge row, and measure to the Edge heading in the Build workspace. The picker and navbar timings include browser-control overhead.

| Workload and revision | Successful samples in seconds | p50 | Observed p95 |
| --- | --- | ---: | ---: |
| Corrupted Edge reload before picker deferral, `fe90223a` | 7.296, 19.520, 25.311, 19.180, 25.354 | 19.520 | 25.354 |
| Corrupted Edge reload after picker deferral, `954d5533` | 7.863, 15.592, 17.063, 18.524, 13.414 | 15.592 | 18.524 |
| Corrupted Edge reload after revision reuse, `11665f78` | 10.691, 9.012, 8.239, 7.686, 10.421 | 9.012 | 10.691 |
| Plan warm, before, `a3be5bd1` | 3.047, 3.041, 3.040 | 3.041 | 3.047 |
| Plan warm, after, `954d5533` | 3.055, 3.041, 3.043 | 3.043 | 3.055 |
| Build warm, before, `a3be5bd1` | 3.044, 3.043, 3.045 | 3.044 | 3.045 |
| Build warm, after, `954d5533` | 3.044, 3.044, 3.043 | 3.044 | 3.044 |

The reported p95 values use nearest rank. With three or five observations, they are the sample maximum and have limited predictive value. All runs in the table succeeded. Earlier original-palette Build reload observations ranged from 7.947 to 32.777 seconds, with an additional timeout. The controlled comparisons above measure successive startup changes after the presets shipped. Comparable true cold-cache samples and broader surface timing are still missing.

Edge opened from the picker in 3.762 seconds on `11665f78`. On `954d5533` it opened after the 12.276-second observation window. Before picker deferral the inventory failed during the timed attempt, which prevented selecting Edge. These observations establish a working path and the remaining measurement gap for picker percentiles.

To measure initial CSS transfer, fetch the public Build HTML with `Accept: text/html`, resolve its entry stylesheet, and request the stylesheet with `Accept-Encoding: gzip`. Count encoded body bytes. The original measurement was 12,102 bytes. On `11665f78` it was 12,264 bytes, up 162 bytes. This measures the initial stylesheet, with no claim about the transfer size of later chunks.

Native source catalog requests observed during the pre-cache reloads overlapped and sometimes took 38–48 seconds. The observed post-cache requests took 2.5–16.3 seconds. The inventories, source warmup, and auth still vary by load. The server log lines use bounded route templates and response-start times.
