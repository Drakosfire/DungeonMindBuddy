# SURFACE — readable page suggestions across conversations

Status: MERGED/DELIVERED in #2359, merge4618102de53c4f7cd4b4e5bbbbbefa0c1e7d1df3; reviewed UIbecc5c4c76c40d12a2993fc5ccbd6b36609afd10. Live Plan/Play each show both retained suggestions without wrong-surface review controls. Exact source/integration/artifact Bugbot approval, hosted/build and full unchanged-baseline comparison are retained in the private cross-surface-proposal evidence. UI1517059 delivered; API447264 unchanged. This is bounded source settlement, not whole-goal completion.
Base: 999a5eabe00b282d605c72044c9bf8a15e3c8ee3, existing buddy-context-loop checkout, branch codex/conversation-proposal-history.

Live Build renders retained proposal text, while the same World conversation in Plan/Play shows only its generic preview acknowledgement. The proposal-history read is incorrectly coupled to Build write capability. Reuse its existing read/projection without granting placement authority to another surface. Keep current-page writes gated by Build eligibility and its original bridge/basis. Do not activate new API revisions or mutate retained story data for verification.

Exclusive expected paths:
- apps/live-control-ui/src/planSurface/components/BuildComposeProposal.tsx
- apps/live-control-ui/src/planSurface/components/BuildComposeProposal.test.tsx
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx
- apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx (existing no-proposal fixture only)
- this handoff

No open PR observed on these paths; Index/native Graph demo and CI/ingestion lanes remain separate. No new store, endpoint, provider path, schema or proposal execution contract. Do not eagerly load image sidecars outside Build.

Validation: readonly history content and originating-turn projection; no writes/review controls without Build authority; delayed response after World/conversation/visibility changes; existing Build review behavior. Run focused owner tests, local exact-SHA hosted/build and discovered diagnostic comparison; independent Bugbot exact-head review, then PRIME merge and UI-only protected delivery. Live Plan/Play must render retained text with no insertion controls and preserve the current document/Run.

Verification-discovered amendment: full diagnostic a55b270eb adds three PlanSurfacePage fixture failures because its synthetic empty history does not stub proposal reads. Include the existing file solely to return its empty proposal history; preserve its assertions. Retain the original failure report and compare the successor against the unchanged baseline.
