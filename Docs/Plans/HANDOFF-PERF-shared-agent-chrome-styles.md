# Global agent chrome owns its styles

**Status:** COMPLETE; source lease released, paired1489/1490 delivery accepted on5202.
**Base:**279ba2e245437f23577f61e923fbb94f0a4921fe; branch codex/shared-agent-chrome-styles, existing buddy-context-loop checkout.
**Topology:**serial after source-merged1489. No concurrent implementation lease overlaps these CSS/import paths. 1489 runtime adoption is pending this correction.

## Invariant and witnessed failure

A fresh Index has only initial CSS after1487lazyroute loading, but globally mounted AgentInteractionChrome relies on shell/bar/resize/layout rules inside planSurface.css. Native rectangle evidence: Open button1277×1274, image1254×1254. The ordinary launcher is defined80×80. Shared chrome must own its complete base/responsive/focus/hidden rules independently of any surface activation. Move matching selectors/declarations/media ancestry in original order; retain surface-only styles/overrides. No duplicate compatibility selectors or restored eager Plan import. Do not resize/redesign the bitmap in this corrective slice.

## Exclusive expected write lease

- This handoff; predecessor HANDOFF-PERF-surface-code-loading.md regression evidence; HANDOFF-PERF-turn-inspection-acquisition.md source/delivery settlement.
- UI src/agentInteraction/AgentInteractionChrome.css (new global stylesheet), AgentInteractionChrome.tsx import only.
- UI src/planSurface/planSurface.css: transfer global chrome selectors only.
- UI src/planSurface/components/PlanAgentInteractionBar.tsx: explicitly import the same shared styles its chrome classes consume; no logic change.

Use a production CSS AST audit to prove exact scoped selector/declaration/media order preservation and no matching selectors stranded in lazy Plan CSS. Build manifest must place global chrome rules in initial CSS without eager Plan/tool JS. Existing chrome/index/host interaction tests, tsc/build; no implementation-mirroring CSS unit tests. Independently review exact cumulative head, merge, adopt the reviewed paired1489+correction artifact on owned5202. Native fresh Index before visiting Plan, Index→Plan→Index load order, Plan/Play/Build/Ingest desktop and narrow launcher/pane geometry, drafts/recovery, trace Debug→Prompt one-read/explicitRefresh and17protected JSON state unchanged. Keep original assets for active tabs/rollback, remove temporary probes/tabs. Source/API/provider/schema/image assets remain unchanged. Further payload/list bounds, media sizing, Rules user+Agent lookup and native Combat remain open.

## Author evidence before review

CSS AST audit against exact base proves50 moved rules/53selector occurrences preserve scoped declarations, ordering and media ancestry; every remaining surface rule is unchanged and no matching global selector remains in Plan. Production CSS audit finds every transferred selector/media condition in initial CSS. Initial JS1,326,841raw bytes, no eager static dependency chunks; Plan/Play/Build/Ingest remain dynamic entries. InitialCSS157,530raw bytes, preserving the code-loading reduction. Source changes outside CSS are two import lines only.

Chrome/Index/dock/AppChrome tests24pass/4fail; exact-base in-memory transform reproduces the same four inherited dock failures. TypeScript/build and diff check pass. Private native candidate leaves the default5202 index unchanged: fresh Index launcher restored80×80 (from1277×1274), retains80×80 after Index→Plan→Index; Index pane and unsent draft close/reopen work, original composer restored without Send. Desktop Plan and Build workspace launchers44px/panes fit viewport; Play launcher80px/side pane fits viewport; Ingest has no active agent entrance in this observed context, and remains rendered. Candidate native receipts are in established private experiment state. Narrow geometry, paired1489 trace one-read/Refresh and final protected17/default adoption remain pending; no unaccepted default rollout is claimed.

## Paired delivery accepted

Architecture ReviewCycle1 approved exacta27fa2da6929a8f202766f78645a3815afcd07e2; PR1490 merged7ab8340461a465b29744a4da143f84c1cd9f4187. Combined1489/1490 adopted atomically on owned5202, API untouched; default index-D-rXrI1c.js/indexSHA256371b1bbd42e64ae3a2b1cfafbdae91490d9653cfaa31be987a4ca9c2f313a34e. Native default root confirms80px launcher before visiting Plan and the exact accepted asset; saved Plan Cards renders normally. Candidate desktop/narrow/load-order checks prove existing launcher/pane geometry, with viewport reset. Debug→The Prompt shared one200trace GET; explicit Refresh added exactly one more200GET, zero provider turn POSTs. All17protected responses unchanged after candidate and default acceptance. Screenshots unavailable; native DOM/rectangle/request metadata evidence only, no target-laptop latency claim. Original assets retained for active tabs/rollback. Temporary probes/tabs cleaned after acceptance. Remaining payload/list/controller/media work and Rules/Combat stay open.
