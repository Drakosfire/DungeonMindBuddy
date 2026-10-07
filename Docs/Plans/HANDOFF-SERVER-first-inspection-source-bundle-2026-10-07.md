# HANDOFF — SERVER: first saved-Plan inspection source bundle

**Status:** PREPARED, not activated. PRIME owns source review and runtime activation.  
**Deployed runtime:** clean detached `81ff1bacf233b6fa466e45c9cbe007590522c710`, tree `fc624117c3ed3a271dccdfc564b49f7e33acee84`.  
**Reviewed release base:** `0c83cb7a8a2f41440f31ef5944fd111913999f67`, which contains merged #1008 and #1009.  
**UX increment:** local reviewed #1007 functional commit `94f078c2b5e15399870fed67a3dd82955d355bcf`, tree `2ebc66da657c54836030f61323b387907da8a584`. It descends directly through three DOGFOOD commits from `0c83cb7a` and changes exactly the five #1007 handoff/UI paths. Final #1007 published head and code-blob equivalence remain gates before activation.

## Bounded purpose

Make the accepted source-read backend, saved Scene focus, and Plan conversation UI inspectable together in the local operator runtime. This is a source and operational readiness bundle, not an Ask, source-index product adoption, or a live usefulness witness. It intentionally excludes Buddy #1010 and its DungeonMind Core `5d4e989` pin. The candidate retains the existing DungeonMind `7c69e447` and patched Hermes 0.18.2 dependency declarations and locks. The source-index SDK and full-index admission can follow independently.

The candidate's `0c83cb7a`→UX diff is exactly:

- `Docs/Plans/HANDOFF-DOGFOOD-plan-conversation-redesign.md`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `apps/live-control-ui/src/planSurface/components/PlanConversationDockAdapter.css`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`

From deployed `81ff1bac` to the candidate, the cumulative diff is 143 paths: 140 paths in the base transition, then five UX paths, two of which overlap the base transition. The only new database migration is Buddy APP-STATE `20261007_0018_agent_turn_graph_context_execution_v2.py`. Dependency manifests and locks are unchanged across the deployed runtime and candidate. These are exact comparisons of the pinned refs, not claims about later `main`.

## Preparation evidence

In an isolated clean checkout at `94f078c2`, `git diff --check 0c83cb7a HEAD` passed. `npm ci` used the committed UI lock; bundled Node `v24.19.0` ran `pnpm --dir apps/live-control-ui build` successfully (TypeScript and Vite), and the changed conversation test passed 107/107. The generated assets are local build evidence, not checked-in deployment artifacts: JS SHA-256 `3de1ec2bee46d52aff2e27b0960699554ee8a5e15df76993846b349ddb5ea12d`, CSS SHA-256 `1d475c47d826306fb1f31c267e2438a09e7a318b13b7720ff469fc206d30d811`. The Vite large-chunk warning remains informational. No runtime process, database, Graph, provider, or source artifact was changed during preparation.

## Review and activation gates

1. Confirm #1007's final published implementation head and compare the five source/UI blobs to this bundle. A docs-only settlement may differ, but any functional difference requires a fresh candidate and verification. Independently review the exact cumulative `81ff1bac`→candidate diff and the APP-STATE `0018` migration. Do not replace this candidate with current `main`, which now includes #1010 and a different Core pin.
2. Pin a fetchable Buddy ref and exact candidate commit/tree. Verify the runtime's stable `.venv` imports the candidate's expected patched Hermes and DungeonMind versions. Rebuild the UI from the exact candidate with bundled Node 24, and verify the clean checkout and dependency lock identities. Verify the application-state schema head read-only. If behind `0018`, make backup, migration, data-preservation, and rollback limits an independently reviewed write lease; never migrate as an incidental launcher restart. The downgrade refuses once V2 rows exist.
3. Under PRIME's exclusive runtime lease, revalidate the clean detached `81ff1bac` checkout, owner of the launcher and each 5202/8000/7860 listener, current profile/symlink targets, health, zero open Agent turns/actions, and absence of competing QA. Capture a fresh ordered before snapshot of Plan/Run/Agent table counts and digests, Graph registry, source/candidate/span artifacts, live-session files, operator profile, and symlink targets. Old process IDs and snapshots are only historical evidence.
4. Fetch and verify the exact candidate before stopping anything. TERM only the freshly verified launcher PID. `./run` traps that signal and targets its recorded child PIDs individually; do not signal a process group blindly. Require all three ports to close. Any residual Vite or other listener needs separate verified PID ownership and an independently reviewed cleanup decision before proceeding. Switch only the clean runtime checkout, preserving credentials, data roots, source files, and symlink targets. Restart with the unchanged `nohup setsid ./run` profile, bundled Node 24, stable `.venv`, `RUN_NO_RELOAD=1`, `UV_NO_SYNC=1`, and the existing managed World profile.
5. Verify exact checkout tree, owned listeners, 5202/8000/7860 HTTP 200, read-only `elderwyld` history, and live process import paths. Compare the after snapshot to the fresh before baseline. Expected state delta is only the separately reviewed `0018` schema migration, if required; rows and preserved files must match. PRIME independently accepts the runtime proof before any fresh Ask/usefulness witness.

**Stop:** unpublished or differing #1007 code; changed candidate tree/locks; incompatible stable environment; unknown schema readiness; missing backup; active work; changed ownership/profile/symlinks/data; failed health/import/preservation. Send no Ask or replay. Rollback code only after verifying state and listener ownership; do not automatically downgrade `0018` after V2 data. If state is uncertain, stop and report to PRIME instead of retrying, repairing SQL, or switching blindly.
