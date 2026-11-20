# Shared conversation recovery

Status: SHIPPED: PR #1662 merged as835cfc75d8434b00f448e379a3f76ec61521a810 after two exact-head Bugbot cycles (initial Play provider mismatch corrected). API/UI delivered with APP/native rows,89 product files and22 frozen components preserved. Ordinary terminal retry restored a question, protected another unsent draft, focused the composer and completed a fresh explicit submission while preserving both original interruptions. Keyboard resize and configuration readiness/recheck passed.

Original serial slice; PRIME owns implementation and delivery.
Base: 05f2d0ccedea56738d02fda8b1d773a6c239ca22.
Authorization: operator browser feedback requests removal of redundant surface labels,
compact resize chrome, explicit retry and meaningful readiness across shared surfaces.

## Boundary and failure critique
Terminal history remains immutable. Retry restores a question for explicit submission
against current saved work, never automatically replays an uncertain request or
replaces an unsent draft. Existing pending-turn reconciliation and submission guards
remain authoritative. Configuration readiness cannot guarantee remote availability.
User's active Build draft and tab must remain untouched.

## Exclusive expected writes
- this handoff; HANDOFF-BUILD-discussion-routing.md and HANDOFF-FOUNDATION-claim-local-attribution.md for truthful predecessor settlement
- apps/live-control-ui/src/agentInteraction/ConversationRecovery* and BuddyReadiness*
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx
- apps/live-control-ui/src/ui/ConversationDock.css and ConversationDock.test.tsx
- apps/live-control-ui/src/api/liveApi.ts
- apps/live_control_server/routes/agent.py
- apps/live_control_server/services/agent_readiness.py
- tests/test_agent_readiness.py

## Contract and verification
New authenticated metadata-only GET /api/live/agent/readiness accepts an explicit
surface and Graph mode. It checks local provider configuration and prepared Build
runtime, exposes no credentials and makes no provider calls. UI scopes responses,
shows current pending/history/work blockers and permits an explicit recheck.
Test terminal retry restoration, existing-draft preservation, uncertain-turn locks,
stale readiness responses, local configuration failures and no external IO.
Keep resize keyboard/pointer accessibility while reclaiming its separate row.
Review exact cumulative diff with independent Bugbot, then PRIME merges and performs
protected local delivery on established 5202/5055 services. No DB/schema changes.
Open PR census checked: no overlapping active implementation PR.
