# Right-sized launcher delivery

**Status:** COMPLETE; source lease released and accepted on5202.
**Base:** 7ab8340461a465b29744a4da143f84c1cd9f4187; branch codex/agent-launcher-delivery; existing buddy-context-loop checkout.
**Topology:** serial successor to accepted shared chrome1490. Current open PRs have no overlapping asset/chrome lease. Owned UI5202 artifact; API/data unchanged.

## Invariant and critique

Keep the existing launcher artwork and 80px global /44px workspace presentation while delivering a 256px lossless WebP derivative. 256px covers the largest ordinary80px launcher through3x display density. Retain the PNG as authoring source; no runtime fallback/import of it, new dependency, image generation or art redesign. Device scales beyond3x are outside this delivery size target. Image decoding falls from1254² RGB pixels to256²; do not claim total browser RAM or target-laptop latency from this calculation.

## Exclusive write lease

- This handoff and backward-looking settlement of HANDOFF-PERF-shared-agent-chrome-styles.md, HANDOFF-PERF-turn-inspection-acquisition.md and HANDOFF-PERF-surface-code-loading.md.
- apps/live-control-ui/src/assets/dungeonbuddy-agent-launcher.webp generated deterministically from the retained PNG using Pillow RGB LANCZOS256x256 and lossless WebP method6.
- src/agentInteraction/AgentInteractionChrome.tsx image import and its test expectedasset only under apps/live-control-ui.

Verify decoded dimensions/pixels against the specified source resize, import graph and production asset bytes, focused existing chrome tests/tsc/build. Inspect cumulative diff; exact-head independent review, merge, adopt5202 with retained old assets; native fresh Index/Plan launcher dimensions/image decode and protected17state unchanged. No CSS/layout/controller/Agent/prompt/API changes. Further read/list bounds, heavy controller loading, user+Agent Rules lookup and native Combat remain open; rule-graph experiments wait for all objectives.

## Author evidence

Derivative67,550bytes versus1,441,393byte master (95.3% smaller); decoded256²RGB pixels match the exact prescribed resize byte-for-byte after lossless WebP round-trip. Production contains only the hashed launcher WebP, not the original master. Existing chrome6/6tests, tsc/build and diff check pass. No CSS/controller behavior changed. Native decode/geometry/protected-state acceptance awaits reviewed merge/adoption.

## Review and accepted delivery

Architecture ReviewCycle1 approved exacte19d71512b79709a1b25d4432293aad45e1ede8f; PR1491 mergede4ab29157d98684bc1e1ad9362ce220dc499e03a. Owned5202 atomically adopted index-BfMQ7Ebc.js/indexSHA25641b5ee43c4702eb6acfb3bd275b46480b9e85213e3a70979f0c118ecfc5bcd40. Native freshIndex80px and Plan43.993px launchers both decode the256x256 hashedWebP completely, saved Plan renders intact. All17protected JSON responses unchanged. Screenshot API unavailable; native image/rectangle receipts in established private evidence. Prior product assets retained for active tabs/rollback; owned QA tab closed. API/runtime data unchanged. This is asset delivery/pixel evidence, not all-DPR visual equivalence or measured laptop latency/RAM.
