# HANDOFF — DEMO: guard World Plan saves against Markdown loss

- **Status:** ACTIVE — PRIME-authorized, bounded Buddy slice
- **Owner:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
- **Authority:** PRIME transfer decision on 2026-10-03
- **Repository/base:** `Drakosfire/DungeonMindBuddy`, `main@ea331ffee4e7f6b8603dcc8d2d2b18d4827f88cd` (#888 merge)
- **Branch/checkout:** `codex/demo-world-plan-save-guard`, `/tmp/demo-plan-save-guard-20261003`
- **Topology:** Serial. One independent guard PR from current main, not stacked on #886. #886 is frozen at its prior product head; this guard must merge before #886 is re-anchored and resolved.

## Blocked user action

A GM opens a saved World Plan containing Markdown the current TipTap grammar cannot represent, makes an ordinary edit, and saves. `PlanSurfacePage` currently projects the complete Markdown into TipTap JSON, exports the changed JSON back to Markdown in `onUpdate`, and sends that result through the normal prepare/commit path. Unsupported links, breaks, blocks, or marks can therefore be flattened or omitted from both the editor draft and durable source.

## Accepted invariant

- The saved Markdown remains authoritative. If source import diagnostics warn or the live TipTap document has semantic serialization warnings, ordinary editing and Save must fail closed at the World Plan boundary.
- A rejected editor update must not replace `markdownRef`, increment its edit generation, or persist an exporter projection over the source/recovery journal. Restore the last safe mounted projection and show an actionable warning.
- Save rechecks both source-import diagnostics and live serialization safety before any create/pending-write/prepare/commit transition. Unsafe content produces zero prepare and zero commit calls and leaves the authoritative source and local recovery bytes intact.
- Keep existing World/document/revision/CAS, pending-write recovery, draft-generation, document-switch, and Agent proposal-review fences.
- Root plain blockquotes and supported callouts that pass the accepted grammar remain editable and saveable. The checked-in Session 29 linked Plan remains a clean mounted input, including its quote paragraphs, 72 node links, and 90 v2 markers.
- No source-span patch engine, shared Markdown editor redesign, backend/API/Graph changes, provider call, live saved Plan mutation, or new runtime is in scope.

The guard is intentionally conservative: unsupported source is presented read-only until the parser/serializer can preserve it. It does not attempt to edit supported spans around opaque unsupported source.

## Re-anchor and collision decision

After #888 merged, GitHub reports Buddy `main@ea331ffee4e7f6b8603dcc8d2d2b18d4827f88cd`. All 13 current open PRs were checked for the leased paths; #886 was the sole collision. PRIME froze #886 at exact head `935bf04c48ff7ca0b45b8d08f4f4f433107d5fac` and transferred its `PlanSurfacePage.tsx` and `PlanSurfacePage.test.tsx` write ownership to this slice. #886 remains a draft and is not rebased or merged around this guard. No current open PR changes `WorldPlanAgentReviewedEdit.integration.test.tsx`.

## Exclusive expected-path write lease

Only these files may change:

1. `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
2. `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
3. `apps/live-control-ui/src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx`
4. `Docs/Plans/HANDOFF-DEMO-world-plan-save-fidelity-guard.md` (this handoff)
5. `Docs/Plans/HANDOFF-DEMO-root-plain-markdown-blockquotes.md` — status-only settlement of merged #888 and closed parser lease
6. `Docs/Plans/HANDOFF-DEMO-plan-navigation-shell.md` — status-only settlement of frozen #886 and transferred paths

No CSS, Markdown grammar, API, storage, corpus, generated asset, or other handoff/roadmap path is leased. #886's remaining visual witness is outside this code lane. No service, port, database, provider, Graph, browser route, or saved Plan is used or changed.

## Required owning-boundary verification

- Mounted Plan page regression loads unsupported Markdown, confirms the saved source and local recovery journal stay byte-for-byte unchanged, confirms the editor/Save are blocked with actionable diagnostics, and invokes the captured Save handler directly to prove both prepare and commit spies remain untouched.
- A mounted unsafe serialization attempt is rejected and cannot become the next recoverable/durable Markdown draft.
- The real checked-in `Session 29 - Buddy Plan.md` fixture mounts without a fidelity warning and remains saveable after #888; verify its root quote content, node references, and v2 markers survive the editor boundary. Supported quote/callout editing continues through mounted Apply → ordinary Save → reload coverage.
- Focused Plan page, Agent reviewed-edit integration, and relevant Markdown importer/serializer tests pass. `git diff --check` passes. Report inherited typecheck failures and any changed-path errors separately.
- Inspect the full cumulative `main` → head diff. Commit and push this branch, then open one PR titled `DEMO: guard World Plan saves against Markdown loss`; do not merge.

## Merge order and handback

PRIME reviews and merges this guard first. Afterward PRIME re-anchors #886 to the new main. Rebase #886 from its frozen head and resolve the overlapping Plan page/test changes while retaining both the fidelity guard and the navbar/header work. That resolution needs independent review, and #886's browser geometry witness remains required before its merge. The old #886 head must not merge around this guard.

## Predecessor settlement

PR #888 merged at `ea331ffee4e7f6b8603dcc8d2d2b18d4827f88cd` from reviewed code head `0aa89e758bbe62014c23c20d112f7bad430aa118`; its root-blockquote parser lease is closed. PRIME independently reported 235 focused Markdown/corpus tests passing. The merge makes root plain quotes in the Session 29 linked Plan supported; it does not remove this guard for other unsupported Markdown. The handoff for #886 is frozen at the head above, with its two overlapping Page paths transferred here. Neither predecessor is claimed to close the overall DEMO journey or operator acceptance.
