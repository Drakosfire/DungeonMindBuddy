# HANDOFF — DEMO: repair World Plan Apply round-trip validation

**Status:** ACTIVE — PRIME authorized one bounded successor fix after the
post-merge J2 witness reproduced an Apply failure.

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

The owning code is `applyWorldPlanEditProposal` in
`apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts`. It
simulates the mounted editor insertion, serializes to semantic Markdown,
reimports, and rejects warnings or a non-round-tripping result. Keep that
loss-prevention invariant. Fix the end-caret/paragraph case so both supported
plain-prose and canonical READ-ALOUD proposals can apply without changing the
existing Plan content or producing lossy Markdown. Preserve stale editor,
selection, World, document, revision, Agent-thread, and scope rejection.

The existing focused helper suite passes 33/33 with its current fixtures; that
is not evidence for the live one-paragraph/end-caret case. The new regression
must exercise the exact live body and end-caret target for both proposal shapes.

## 2. Exclusive write lease

Only these paths are authorized. Return to PRIME before editing another path or
changing a contract.

1. `Docs/Plans/HANDOFF-DEMO-world-plan-apply-roundtrip-v1.md` — this bounded
   authority and acceptance record.
2. `Docs/Plans/HANDOFF-DEMO-world-plan-agent-apply-v1.md` — record that PR #828
   merged and its runtime witness found the Apply guard failure; release its
   historical implementation lease without claiming J2 acceptance.
3. `Docs/Roadmaps/ROADMAP-demo.md` — record the two failed Apply attempts and
   this ACTIVE follow-up; keep J2, graph readiness, and operator acceptance
   open.
4. `apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts`
   — repair the round-trip-safe Apply seam.
5. `apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.test.ts`
   — add the exact one-paragraph/end-caret helper regression for plain prose
   and canonical READ-ALOUD content.
6. `apps/live-control-ui/src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx`
   — prove the two proposal shapes apply through the mounted World Plan
   editor and retain ordinary Save/reload behavior.

No server, provider, model/retry policy, API types/routes, storage schema,
conversation persistence, CSS, graph, or J3 paths are leased. Tests use local
fixtures and mocked generation only; no live provider, service, product
Database, demo World, or corpus is used by this code lane.

## 3. Runtime-state boundary

The separate completed two-call witness still has its own isolated app runtime
in `/home/drakosfire/.codex/worktrees/demo-world-plan-trace-inspector/DungeonMindBuddy`:
UI port 5202, API port 7868, and disposable PostgreSQL port 55460. Its synthetic
World, saved Plan, and local conversation history are not this implementation
lane's state. Do not use or stop those services/database until the witness
result is recorded and its owner cleans them up. This code lane and its fixture
suite use no app port, service, provider, database, World, or corpus.

## 4. Owning-boundary acceptance

1. A helper regression starts from the exact witness paragraph, places a caret
   at its end, and applies each of the two proposal shapes. Both preserve the
   full original prose and produce a stable semantic Markdown serialize/reimport
   result. Add a counterexample only if it protects the same invariant.
2. A mounted World Plan integration regression exercises review → Apply for
   both shapes, then the existing Save, reload, and saved-action history path.
   Rejected stale-target/thread/scope cases remain unchanged and fail closed.
3. Run the focused helper and mounted World Plan integration suites, scoped UI
   typecheck, and `git diff --check`; report the inherited
   `ThreatPublicationPanel.tsx:553` JSX namespace diagnostic if it remains.
   Inspect the exact cumulative `origin/main`→head diff.
4. Commit and push this bounded fix, open/update its PR for PRIME, and do not
   merge. Report exact head, tests, remaining limits, and PR #826 topology.

PRIME authorized exactly two fresh logical `gpt-5.3-codex` proposal submissions
only after this fix is integrated. Use them on the same isolated synthetic
World/Plan to rerun Review → Apply → ordinary Save/reload and local history/scope
verification. Preserve the first two failed attempts as evidence. Report exact
observed model, retries, token usage, latency, and attributable cost only when
an attributable receipt is available; otherwise record unknown. Do not use
status or elapsed time to infer receipts. This witness remains bounded J2
evidence and does not certify graph readiness, J1–J6, visual acceptance, or the
operator's full demo.
