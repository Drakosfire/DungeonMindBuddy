# HANDOFF — DEMO: repair World Plan Apply round-trip validation

**Status:** COMPLETE — the bounded Apply repair merged in PR #829 at
`a393eee9ae6ca26dfa67f65bfdde2a83037bc485`, and its separately authorized
two-proposal J2 witness passed. This completes the Apply round-trip gate only;
broader J2, graph-readiness, visual, and operator-acceptance gates remain open.

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Authority:** [STEWARDS-HANDOFF-demo.md](STEWARDS-HANDOFF-demo.md), the merged
World-only Apply contract in
[HANDOFF-DEMO-world-plan-agent-apply-v1.md](HANDOFF-DEMO-world-plan-agent-apply-v1.md),
and PRIME's 2026-10-01 authorization to fix the owning editor/Markdown
round-trip seam and add a focused regression.

**Implementation lane:** branch `codex/demo-plan-apply-roundtrip`, based on
fresh `origin/main@dc30a7379b927edd8d9bfb510019f0fccbc3c5c5`, in isolated
checkout `/home/drakosfire/.codex/worktrees/demo-plan-apply-roundtrip/DungeonMindBuddy`.

**Topology:** parallel-independent with open draft PR #826, branch
`codex/j3-world-space-binding`, exact head
`4fa28e586783f0e63edb85fa664afa53521367f6`. Its eight changed paths are
`apps/live_control_server/integrations/dungeonmind/world_space_provisioning.py`,
`apps/live_control_server/routes/world_containers.py`,
`apps/live_control_server/services/world_container_registry.py`,
`apps/live_control_server/services/world_space_binding.py`,
`tests/integration/test_world_space_binding_postgres.py`,
`tests/test_world_space_binding.py`, `pyproject.toml`, and `uv.lock`. This lane
owns only the Plan Apply helper and its focused tests plus the bounded
handoff/roadmap settlement below. There is no shared path or behavioral
dependency. Re-anchor and recheck the census before PR handback; do not merge.

## 1. Reproduced failure and invariant

After PR #828 merged at `dc30a7379b927edd8d9bfb510019f0fccbc3c5c5`, the
isolated J2 witness created synthetic World
`demo-j2-plan-apply-witness-2026-10-01` and saved Plan
`46e2e8fe-6d91-4552-be31-e69c818e77c6` at revision 3. Its one-paragraph body
was `Opening image: three lantern flashes ripple across the eastern ridge. The
scouts have returned, but no one will explain why they were silent.` Its
saved content SHA-256 was
`ada07dfb03c0f81d54bda66bc73dda8b0a460c743d630ce9ec5f21f50282d09d`. Two
configured-policy logical proposal submissions returned reviewable proposals:
a canonical READ-ALOUD callout and a plain prose sentence. Both Apply attempts
were rejected by the same guard: `Agent proposal would not round-trip in this
Plan location.` No edit was applied and the saved Plan stayed unchanged. The
configured model was `gpt-5.3-codex`; exact observed model, retries, token usage,
and cost are unknown because the client did not retain an attributable receipt.
The reviewed proposals described placement immediately after the first sentence.
Reproducing that collapsed mid-paragraph caret in the helper and mounted UI
identified the failing boundary.

The owning code is `applyWorldPlanEditProposal` in
`apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts`. It
simulates the mounted editor insertion, serializes to semantic Markdown,
reimports, and rejects warnings or a non-round-tripping result. Keep that
loss-prevention invariant. At a collapsed caret after the first sentence, block
insertion splits the paragraph and leaves its existing separator whitespace at
the start of the following paragraph. Markdown import normalizes that edge
whitespace, so the guard rejects the simulated result. Consume only whitespace
adjacent to that paragraph split in both simulation and mounted Apply; preserve
all surrounding words and keep the round-trip guard. Preserve stale editor,
selection, World, document, revision, Agent-thread, and scope rejection.

The existing focused helper suite passed 33/33 before the exact witness
regression; that did not cover the live one-paragraph/mid-paragraph caret. The
new regression exercises the exact body with a collapsed caret immediately
after the first sentence for both proposal shapes.

## 2. Historical exclusive write lease — released

This was the exact write allowlist for the ACTIVE implementation. It closed
after PR #829 merged and the separately authorized witness passed. No code path
remains leased by this completed handoff. While the lane was active, changes
outside these paths required a return to PRIME.

1. `Docs/Plans/HANDOFF-DEMO-world-plan-apply-roundtrip-v1.md` — this bounded
   authority and acceptance record; the lease is now released.
2. `Docs/Plans/HANDOFF-DEMO-world-plan-agent-apply-v1.md` — record the #828
   failure, #829 repair, and bounded runtime witness; do not claim broader J2
   acceptance.
3. `Docs/Roadmaps/ROADMAP-demo.md` — record the two failed pre-fix attempts and
   the later bounded pass; keep graph readiness and operator acceptance open.
4. `apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts`
   — repair the round-trip-safe Apply seam.
5. `apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.test.ts`
   — add the exact one-paragraph/after-first-sentence helper regression for
   plain prose and canonical READ-ALOUD content.
6. `apps/live-control-ui/src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx`
   — prove the two proposal shapes apply through the mounted World Plan
   editor and retain ordinary Save/reload behavior.

No server, provider, model/retry policy, API types/routes, storage schema,
conversation persistence, CSS, graph, or J3 paths are leased. Tests use local
fixtures and mocked generation only; no live provider, service, product
Database, demo World, or corpus is used by this code lane.

## 3. Runtime-state boundary

The completed post-merge witness used an isolated app runtime in
`/home/drakosfire/.codex/worktrees/demo-world-plan-trace-inspector/DungeonMindBuddy`:
UI port 5202, API port 7868, and a dedicated PostgreSQL container on port 55460.
The API and UI processes are stopped. The container is stopped but retained,
and its persistent volume remains. The earlier APP-STATE witness database had
been auto-removed before this rerun; the witness reconstituted the same
synthetic World/Plan identities in a fresh revision chain. The old failed
proposals remain in their original browser-local history, separate from the
fresh conversation used for the successful rerun.

## 4. Owning-boundary acceptance

1. A helper regression starts from the exact witness paragraph, places a
   collapsed caret immediately after its first sentence, and applies each of
   the two proposal shapes. Both preserve the full original prose and produce a
   stable semantic Markdown serialize/reimport result.
2. A mounted World Plan integration regression exercises review → Apply for
   both shapes, then the existing Save, reload, and saved-action history path.
   Rejected stale-target/thread/scope cases remain unchanged and fail closed.
3. Run the focused helper and mounted World Plan integration suites, scoped UI
   typecheck, and `git diff --check`; report the inherited
   `ThreatPublicationPanel.tsx:553` JSX namespace diagnostic if it remains.
   Inspect the exact cumulative `origin/main`→head diff.
4. Commit/push the bounded fix and open its implementation PR for PRIME. PRIME
   retains merge authority. This requirement completed as PR #829; the
   separate runtime witness is recorded below.

**Fix checkpoint (2026-10-01):** The helper and mounted regressions now cover
plain prose and canonical READ-ALOUD insertion at the witnessed paragraph
boundary. Focused tests passed 39/39 (35 helper and 4 mounted integration cases),
including ordinary Save/reload/action history and existing stale-target,
thread, and scope guards. Redirecting TypeScript build-info to `/tmp` isolated
the inherited app diagnostic at `ThreatPublicationPanel.tsx:553` (`Cannot find
namespace 'JSX'`); the UI node config passed. The normal `tsc -b` command also
reports read-only `node_modules/.tmp` build-info writes. `git diff --check`
passed. This is local fixture evidence only; no provider or witness runtime was
used by the code lane. PR #829 merged at
`a393eee9ae6ca26dfa67f65bfdde2a83037bc485` from code head
`07cb2b7d2ab5fb655cbf51f16efb96ca40f7415a`.

## 5. Post-merge J2 Apply witness — PASS (2026-10-01)

The original APP-STATE witness database/container had been auto-removed. That
loss is preserved as a limitation; no continuity with its revision chain is
claimed. A dedicated PostgreSQL container and volume were created on
`127.0.0.1:55460`, then the same synthetic World
`demo-j2-plan-apply-witness-2026-10-01`, Plan
`46e2e8fe-6d91-4552-be31-e69c818e77c6`, title, and opening body were
reconstituted. Before the first proposal, the fresh database showed object
revision 2 / content revision 1 and opening-body SHA-256
`ada07dfb03c0f81d54bda66bc73dda8b0a460c743d630ce9ec5f21f50282d09d`. This is
a new synthetic revision chain. The two earlier failed proposals remained
separate historical browser-local evidence; neither was reapplied.

Exactly two new logical proposals were submitted in a fresh conversation. Both
were reviewed, applied to the same mounted Plan draft, saved through the normal
prepare/commit routes, and verified after reload:

- The canonical READ-ALOUD proposal: observed `gpt-5.3-codex`; 422 input / 151
  output tokens; one provider attempt; zero transport retries and zero
  conformance retries; 5,818 ms model latency / 5,825 ms request wall time.
- The plain-prose proposal “A lone watcher keeps vigil above the marsh.”:
  observed `gpt-5.3-codex`; 554 input / 106 output tokens; one provider
  attempt; zero transport retries and zero conformance retries; 4,238 ms model
  latency / 4,251 ms request wall time.

No attributable `cost_usd` was returned for either call; cost is unknown, not
zero. After the second ordinary Save and page reload, the database snapshot
and committed-revision endpoint agreed at object revision 6 / content revision
3, SHA-256
`86e10d0283d650573170b241da529f9b57a560484514d3f9ef673dfe1b6222ef`, with no
divergent working copy. The saved body retained all original prose, the
READ-ALOUD block, and the new plain-prose sentence. Browser action history
showed both new turns applied to the local draft.

Page loads also emitted a separate `POST /api/live/world-graph/projection`
503. No graph write or graph read-after-write was attempted or proved. This
Apply witness does not establish managed-World graph awareness, Session 28
native graph read, recap ingestion, visual acceptance, or full DEMO/J1–J6
acceptance.
