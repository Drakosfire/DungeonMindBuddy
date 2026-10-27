# GRAPH — keep selected evidence separate from authored aliases

Status: BLOCKED for independent invariant critique. PRIME owns serial branch codex/graph-explicit-object-aliases, base6236c1ad348709f4003de2d3de30488413db8fac, existing buddy-context-loop checkout. One bounded UI correction PR under current authoring/Graph dogfood authority. Remote open PRs inspected: held1764 owns separate writer/collaboration paths; hosted1828 remains separate. No new worktree/environment. Runtime UI1841/API1838/schema0081, API PID2572669 and UI2567966; all retained data/drafts protected.

## Confirmed boundary failure

Ordinary Conks Graph finder→Sarni→expanded Reference displays the whole source sentence as Also known as. Advanced shows authored:assert-6f8d9e8262619d47 at rev:cf8431be3a5f2e45a2e38e8d0764f51f. The original dogfood receipt already retained this rough edge. Current shared graphObjectAuthoringDraft.buildProposalAliases unconditionally appends selection.selectedText whenever the renamed label differs, despite empty Aliases input. Existing tests explicitly encode that behavior. This is a current shared UI producer defect; do not infer extraction/runtime model failure or rewrite historical published nodes.

Invariant: highlighted evidence remains exact source selection/provenance. A node label change is not consent to assert the selected evidence text as another name. Only values explicitly entered in Aliases are authored aliases; keep trim/case-insensitive deduplication. Explicit Link existing→Add as alias remains a deliberate separate operation and must continue to work. Label seeding, summary, source selection, source-span admission, node/edge IDs, prepare/commit authority and saved/staged drafts remain unchanged. Do not infer aliases using sentence/name heuristics, introduce compatibility modes, or silently sanitize retained proposals/publications.

## Expected writes

This handoff; predecessor HANDOFF-SURFACE-popover-viewport.md settlement with exact1841 delivery/restart facts. Shared planSurface/graphReviewWorkbench/graphObjectAuthoringDraft.ts, its test; GraphObjectAuthoringSurface.test.tsx and only necessary object form hint if current copy is false. Remove obsolete selected-source dependency from the internal alias-building helper/call sites. No backend/native/Core/schema/identity resolver changes, relationship direction/ID UI work, retrospective data cleanup, model or extraction changes.

## Verification and delivery

Preserve failing current-head case: highlight full Sarni sentence, rename label Sarni, blank Aliases must produce no alias while retaining exact selection. Owner tests cover explicitly entered alternative name, exact source sentence deliberately typed as alias, case-insensitive dedupe, and rename-to-same source label. Mounted ordinary form→stage→prepare payload verifies omitted inferred sentence and exact evidence; explicit link-as-alias controls unchanged. Typecheck/build, exact cumulative independent Bugbot, hosted gates, protected UI-only delivery. Ordinary synthetic existing source: highlight prose, name node, inspect staged/prepare review with no inferred alias; explicitly enter an alias and prove it appears. Do not publish synthetic test changes unnecessarily or repair existing Sarni. Full J1–J6 and exact edge-ID UI inspection remain open.
