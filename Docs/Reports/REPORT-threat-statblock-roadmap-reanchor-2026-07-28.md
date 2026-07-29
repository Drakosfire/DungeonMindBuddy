# Report — Threat + Statblock Roadmap Re-anchor

**Date:** 2026-07-28  
**Status:** CURRENT-TRUTH RECONSTRUCTION COMPLETE; PRODUCT GATES NOT COMPLETE  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Observed `origin/main`:** `0f6f48ed6502a9a4e69b57f351ae9c795da54694` — `Capture Graph V2 semantic rejuvenation goal`  
**Roadmap branch:** `agent/statblock-roadmap-reanchor-2026-07-28`  
**Inspection mode:** GitHub repository and PR inspection. No operator browser, local checkout, user-local runtime stores, or configured DungeonMindServer were available to this agent.

## 1. Repository truth

```text
Observed handoff anchor:
0f6f48ed6502a9a4e69b57f351ae9c795da54694

Current origin/main:
0f6f48ed6502a9a4e69b57f351ae9c795da54694

Current working branch:
agent/statblock-roadmap-reanchor-2026-07-28

Current worktree:
No local worktree was available in this execution environment. Repository inspection and the docs branch were performed through the GitHub connector.

Relevant uncommitted files:
Not observable without a local operator worktree. No repository files were modified outside this dedicated branch.

Current open statblock PRs:
None found.

Current merged statblock ancestry:
#386, #387, #388, #397, #398, #402, #404, #405–#409, #413, #417, #425, #435, #439; product-roadmap re-anchor merged in #446.
```

The checked-in roadmap and tracker still declare `ff553bd81fc82e65d92ddbd1d05af5fc03f1adc7` as their repository anchor. Their sequencing is consistent with PR `#446`, but the immutable base metadata is stale relative to current `main`.

## 2. Repository rules and authority read

Read and reconciled:

- `AGENTS.md`
- `.cursor/rules/external-agent-pr-loop.mdc`
- `.cursor/skills/external-agent-pr-loop/SKILL.md`
- `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`
- `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`
- `Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md`
- `Docs/Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md`
- `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md`
- `Docs/Plans/HANDOFF-sbw06c-workbench-revise-ux.md`
- `Docs/Plans/HANDOFF-sbw07-persist-accepted-mechanics.md`
- merged PR history for `#425`, `#439`, and `#446`, plus the current sibling graph PR `#444`.

The active authority remains:

```text
current repository rules
→ accepted lifecycle decision
→ active roadmap and tracker
→ frozen completed-slice contracts
→ current implementation and owning-boundary tests
→ merged PR evidence
→ current product dogfood
```

## 3. Roadmap-to-code truth table

| Capability | Roadmap says | Code proves | Product dogfood proves | Action |
|---|---|---|---|---|
| Draft create | Implemented | `ThreatDraftV1`, durable store, POST route, Workbench create path, strict context shape | PR `#425` proved a Buddy API create for one real draft; no current full browser gate | Re-run in `R0-A`; do not count the historical partial run as current proof |
| Generate | Implemented; live-provider debt | Exact draft/version generation route and typed candidate path exist | PR `#425` generation was blocked by connection refusal to DMS at `127.0.0.1:7860` | Restore/verify provider, then run `R0-A` |
| Edit | Implemented | Complete typed definition editor and session working-copy persistence exist | Not proven against a current real-provider candidate | Exercise one meaningful mechanical edit in `R0-A` |
| Validate | Implemented | Exact working definition is submitted to authoritative validation; stale receipts are quarantined | Not current-product proven | Exercise in `R0-A` |
| Revise | Implemented through `SBW06c` | Exact edited-working-copy revise, lineage, durable attempt/reconciliation, proposal history, and candidate-scoped edits exist | PR `#439` reports 168 focused frontend tests; real-provider dogfood explicitly not run | Exercise explicit revise instructions in `R0-A` |
| Accept | Implemented | Acceptance operation journal, recovery/reconciliation, exact locator, and accepted draft reference exist | Automated evidence exists; current real-provider user path not proven | Exercise in `R0-A` |
| Reload accepted revision | Durable backend and recovery paths implemented | Exact acceptance operation and draft read paths exist; browser join/operation state is rehydrated from `sessionStorage` | No normal browse/reopen product proof; opaque IDs or retained browser state are still required | Classify honestly during `R0-A` |
| Browse/reopen ThreatDraft | Backend list/get/update exists | `GET /api/live/threat-drafts`, exact GET, and versioned PUT are route-tested across app restart | Workbench has no library; `liveApi` has create/get but no ThreatDraft list/update client | Likely `AUTHORING-LIBRARY` decomposition, but only after `R0-A` observation |
| Hermes grounding | Required by `R0-B` | User-facing query client accepts World Graph context; lifecycle context fields exist on drafts | No recorded broad admitted-union investigation-to-description gate | Keep `R0-B` blocked until authoritative projection is restored |
| Graph publication | Not implemented | No governed accepted-mechanics → Threat/binding commit in this lifecycle | None | Do not dispatch before `MAGIC-D2` |
| Placement | Not implemented | No generic durable placement contract | None | Remains after `MAGIC-D3` |
| Combat import | Legacy path only | Live combat persists, but exact Threat/binding/revision/placement authority is absent | Legacy generated/corpus add-to-combat is not this lifecycle | Remains blocked by `MAGIC-D4` |

## 4. Provider and consumer-contract readiness

Current repository contract boundary:

```text
provider: DungeonMindServer statblocks v1
Buddy contract: dungeonmind.dungeonbuddy-statblocks
contract version: 1.0.0
OpenAPI source:
apps/live_control_server/integrations/dungeonmind_statblocks/openapi/dungeonbuddy-statblocks-v1.json
Generated backend DTOs:
apps/live_control_server/integrations/dungeonmind_statblocks/generated/
Generated frontend client:
apps/live-control-ui/src/contracts/dungeonbuddy-statblocks-v1/client.ts
```

Runtime configuration requires:

```text
DUNGEONMIND_STATBLOCKS_ENABLED
DUNGEONMIND_STATBLOCKS_BASE_URL
DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY
DUNGEONMIND_STATBLOCKS_TIMEOUT_SECONDS (optional)
```

The readiness boundary probes both downstream readiness and health, then projects generation/read/persistence capability labels. Strict generated models remain the intended consumer boundary.

Current provider health, authentication, and current Server response compatibility could not be observed from the GitHub-only execution environment. The most recent real-run evidence is PR `#425`, where the Buddy API created draft `0c5603d9-e819-4f33-9bfb-6bed12505f43` v1 but generation failed with `downstream_unavailable` because the configured local DMS refused the connection. That historical result is evidence of honest failure preservation, not a current `R0-A` verdict.

## 5. Sibling-lane status

```text
Main Graph V1 repair owner:
Separate graph lane; current visible candidate is PR #444 (`feat/graph-review-world-graph-browse-load`).

Current graph head:
Not observable from repository source alone. A transfer PR (#442) describes a local snapshot head `rev:2a72ef7a40ba37bc33e3f2680d528970`, but it is explicitly a transfer vehicle and not an authoritative product proof.

Projection currently usable:
Not proven. PR #444 remains open and non-mergeable.

R0-B available:
No.

Temporal worktree path/branch:
Not observable from the GitHub connector. No temporal/timeline branch was found through repository-visible state.

Runtime-store isolation confirmed:
No runtime stores were accessed or shared by this agent.

Graph V2 backlog remains deferred:
Yes. Current `main` only captures the long-horizon semantic rejuvenation goal; it is not a prerequisite for Threat + Statblock continuation.
```

### Graph-lane architectural concern

PR `#444` currently advertises “first-wins edge-map tolerance” as part of its solution. That is directly incompatible with the active handoff’s prohibition on first-wins projection tolerance and with strict integrity ownership. The statblock lane must not adopt or depend on that degraded behavior as an `R0-B` substitute.

## 6. Confirmed immediate dogfood sequence

```text
1. Restore or verify the configured real DungeonMindServer.
2. Run R0-A through the normal user-facing Workbench with Mireward Latchling.
3. Record exact draft, candidate, proposal, accepted locator, digest, retry, and reload behavior.
4. Do not dispatch a statblock implementation slice until that observation is classified.
5. Keep R0-B blocked until the graph lane supplies an authoritative strictly projectable graph head.
6. Run R0-B through Hermes only after that dependency is real.
7. Select one smallest implementation slice from the earliest failed gate.
```

## 7. Stale documents or assumptions

- Roadmap and tracker repository anchors are stale (`ff553bd…` versus current `0f6f48e…`).
- “Merged” remains distinct from “product-proven”; PR `#439` explicitly says real-provider dogfood was not run.
- PR `#425` is only a partial historical product attempt: draft creation passed, generation did not.
- A backend list endpoint must not be described as a Workbench library capability.
- Browser `sessionStorage` recovery proves a bounded join/recovery seam, not a durable browseable authoring library.
- PR `#444` cannot be treated as the authoritative graph recovery while it is non-mergeable and relies on forbidden first-wins tolerance.
- The graph snapshot in PR `#442` is a transfer artifact, not an authority declaration for `R0-B`.

## 8. Gate ledger at this re-anchor

```text
R0-A: BLOCKED_DEPENDENCY — current provider/browser runtime unavailable to this agent; report recorded separately.
R0-B: BLOCKED_DEPENDENCY — authoritative strict Graph V1 projection not restored; not attempted.
MAGIC-D1: DOGFOOD REQUIRED
MAGIC-D2: DOGFOOD REQUIRED
MAGIC-D3: BLOCKED_DEPENDENCY
MAGIC-D4: BLOCKED_DEPENDENCY
MAGIC-D5: BLOCKED_DEPENDENCY
```

## 9. First exact next action

```text
Start the configured DungeonMindServer and Live Control UI on the operator machine, open the normal Statblock Workbench, and run the complete R0-A Mireward Latchling sequence without manually manufacturing hidden state.
```

No implementation handoff is justified before that operation. The first likely implementation candidates remain:

- narrow provider/consumer contract sync, if current real responses fail strict parsing;
- ThreatDraft browse/reopen client + Workbench library, if mechanics succeed but normal reopening remains the earliest product miss;
- local in-progress recovery as a separate capability, if dependency failure destroys unsaved work;
- `SBW06d`, only if revise-from-exact-accepted is the isolated earliest gap.

## 10. Stop report

```text
Stop condition:
The real provider and user-facing runtime are not reachable from this execution environment, and the authoritative graph projection recovery is incomplete.

Current repository SHA:
0f6f48ed6502a9a4e69b57f351ae9c795da54694

Gate being attempted:
R0-A readiness and R0-B dependency verification

Exact user-visible failure:
Not exercised; no product browser/runtime was available. Historical PR #425 observed downstream connection refusal during generate.

Durable state observed:
Repository contracts and historical exact IDs only. No current operator runtime stores were read or modified.

Authority boundary involved:
External DungeonMindServer readiness/authentication/current contracts; separate Graph V1 strict projection recovery.

Why current scope cannot absorb it:
Running the gate requires the operator’s configured services and durable runtime state. Repairing graph projection belongs to the sibling lane. Weakening strict contracts or manufacturing hidden state would invalidate the gate.

Smallest decision or capability required:
Restore the real provider and run R0-A. Restore strict authoritative projection and run R0-B.

Suggested owner:
Operator for service/runtime dogfood; existing Graph V1 recovery owner for projection integrity.

Operator decision required:
None before the next dogfood attempt, unless current provider health or graph-repair ownership has changed.
```
