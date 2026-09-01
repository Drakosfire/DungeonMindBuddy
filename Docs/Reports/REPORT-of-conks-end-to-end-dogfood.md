# Of Conks & Cons end-to-end dogfood report

Status: IN PROGRESS — living evidence ledger
Branch: `dogfood/of-conks-end-to-end`
Current head: (recorded at each evidence milestone)
Dogfood date: 2026-08-31
Operator: Cursor agent (local operator machine)
World / campaign: `eldyrwild` / Hempholm (Longmont campaign canon); campaign id recorded at Plan creation
Plan: (pending)
Runbook: (pending)
Run: (pending)

Canonical handoff: `Docs/Plans/HANDOFF-CON-READY-of-conks-end-to-end-dogfood.md`

## 0. Baseline

- Design base: `main` `24f7c25b49fdab8271b0d84d36e4a609b9832d69` (merge of PR #673, BF3B Scene-owned Decisions).
- Branch cut from `origin/main` at that exact SHA into worktree `DungeonMindBuddy-of-conks-end-to-end`.
- PR #674 `AGENT-INTERACTION: enable truthful Play Ask` is OPEN at head `c194c70947780d5248f938421615b28a262d7d37`. Its leased paths (union of §21 lease and changed files, including `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`, `apps/live-control-ui/src/api/liveApi.ts`, `apps/live-control-ui/src/api/types.ts`, `apps/live-control-ui/src/agentInteraction/**`, `apps/live_control_server/routes/agent.py`, `apps/live_control_server/services/agent_*`, `apps/live_control_server/services/hermes_graph_query.py`, `apps/live_control_server/services/live_agent_loop.py`, `apps/live_control_server/main.py`) are read-only to this branch until it merges.
- Runtime/state collision note (AGENTS.md invariant 5): this lane shares the operator-local APP-STATE PostgreSQL `dungeonbuddy_application_state` (127.0.0.1:54329) with other local worktrees. Lane servers use dedicated ports: API `127.0.0.1:8020`, Vite `127.0.0.1:5190`. The BF3B recut lane's servers (`8010`/`5180`) and the stale #670 servers (`8000`/`5173`) are not evidence for this branch.

## 1. Golden-path status

| Station | Status | Generic / dogfood-only | Evidence |
| --- | --- | --- | --- |
| Source | PENDING | — | — |
| Plan | PENDING | — | — |
| Runbook | PENDING | — | — |
| Play | PENDING | — | — |
| World/object | PENDING | — | — |
| Mechanics | PENDING | — | — |
| Roll | PENDING | — | — |
| Encounter/Combat | PENDING | — | — |
| Agent | NOT EXERCISED — PR #674 active | — | lease recheck 2026-08-31 |
| Reload | PENDING | — | — |

## 2. Learning ledger

| ID | Observation | Type | Severity | Evidence | Candidate disposition |
| --- | --- | --- | --- | --- | --- |
| OC-001 | (recorded as findings occur) | — | — | — | — |

## 3. Dogfood-only mechanisms

| Mechanism | Why it exists | Generic seam missing | Safe to delete? | Disposition |
| --- | --- | --- | --- | --- |
| (none yet) | — | — | — | — |

## 4. Product magic moments

(pending)

## 5. Friction

(pending)

## 6. Authority/truth problems

(pending)

## 7. Performance / table-speed observations

(pending)

## 8. Extraction candidates

| Priority | Candidate capability | Owning flow | Why independently useful | Suggested handoff |
| --- | --- | --- | --- | --- |
| (pending) | — | — | — | — |

## 9. Things to discard

(pending)

## 10. Final disposition

DO NOT MERGE WHOLESALE.

(pending — final handback per handoff §13)

## Bounded-discovery path log (handoff §7.5)

| Path | Station | Owner / collision | Change class |
| --- | --- | --- | --- |
| (none yet beyond §7.1 always-allowed) | — | — | — |
