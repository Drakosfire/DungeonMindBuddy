# REFERENCE: retained Build retry from lightweight history

Status: ACTIVE bounded PRIME slice under the References goal. Base
`d39db0c6a2a0493800f82eb77d69e3ef3deb3d4e`; branch
`codex/reference-build-light-retry`; existing buddy-context-loop checkout.
Topology: serial successor to merged/delivered2292, no unmerged parent.
Coordination remains off. Active Rules2291 and CI2288 paths are disjoint.

## Outcome

Failed/interrupted Build messages expose direct retry without opening Details
or eagerly loading execution history. On click, reuse the existing exact-turn
reader, verify eligibility, then use the existing retained-discussion input and
persisted sender. Both lightweight and hydrated controls use the same original
context flow. Do not capture the current editor or grant another write action.
Preserve original references, current page/drafts and pending recovery. Refuse
unknown results, reviewed-step-only attempts and stale World/conversation/surface
reads without dispatch. Preserve Plan2292 behavior and Details node identity.

## Write lease

- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx`
- this handoff
- predecessor `Docs/Plans/HANDOFF-REFERENCE-plan-light-retry.md` backward settlement

No API/schema/CI/provider/model changes. Play2172 and server2104 remain held.
Preserve API16cb/schema142/UIe994 and retained state until reviewed UI-only delivery.

## Verification

Reproduce the two baseline missing Build retry cases; use realistic exact-history
correlation and retained-input fixtures. Prove object/source references, original
snapshot/operation, current draft preservation, failed reads, late navigation and
one dispatch. Run focused mounted owners and Plan history regression, TypeScript
and build. Preserve the78 baseline failures without calling them passes or
absorbing unrelated old fixture work. Inspect cumulative diff, independent Bugbot
review and source checks, then merge/deliver under standing PRIME authority.
