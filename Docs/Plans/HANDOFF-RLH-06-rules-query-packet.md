# HANDOFF — RLH-06 rules query packet

**Status:** ACTIVE — implementation candidate on PR #763; pending review
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Authority:** `Drakosfire/DungeonOverMind/Docs/Plans/PLAN-rules-lawyer-graph-experiment.md`  
**Predecessor:** `RLH_04_DUNGEONMIND_RETRIEVAL_BENCHMARK_ACCEPTED` plus accepted platform Phase A–G golden path  
**Primary question:** Can Buddy expose one read-only rules-query application contract that returns exact DungeonMind-backed evidence/citations without generating a ruling?  
**Unlocks:** RLH-07

## Re-anchor before coding

This branch was planted while Buddy UI foundation PRs #755–#761 were in flight. Rebase onto current `main` after those and all platform predecessors settle. Re-census the existing DungeonMind query integration and live-control server route/service patterns.

This PR is backend/application-contract work. It must not redesign ToolHost.

Re-anchored on Buddy `main@3f0d554919c3fa093598a18ef6d5c740f81ddc0e` after RulesIngestion PR #4 merged at `b4a06e8b28ac34d40add64978a11116c6a24cf9c`. The operator explicitly activated Phase H, which the central platform-refresh steward handoff permits before the platform golden path. This slice remains read-only backend work; UI foundation PR #761 is still open and belongs to RLH-07's re-anchor. Open Buddy PR #767 also edits `pyproject.toml`; the DungeonMind pin conflict must be reconciled before final merge.

**PR topology:** RLH-06 → RLH-07 → RLH-08 is stacked. This PR's implementation lease is `apps/live_control_server/{models,services,routes,integrations/dungeonmind}/rules_query*`, the trusted SRD rules binding JSON, `apps/live_control_server/main.py`, `pyproject.toml`, `uv.lock`, and focused tests. It does not write UI ToolHost paths.

## Contract

Define one small product DTO, conceptually:

```text
RulesQueryRequest
  question
  ruleset / configured rules-space selector

RulesQueryPacket
  query_id
  rules_space_id
  rules_revision_id
  evidence[]
  related rule/entity/assertion refs as needed
  retrieval trace summary
  explicit status
```

Every evidence item must contain durable DungeonMind identity plus enough source locator/citation data for the UI to open/inspect it.

Statuses must distinguish at least:

- success;
- no evidence;
- insufficient/partial evidence;
- rules space unavailable;
- downstream failure.

No answer text is generated here.

## Ownership

Buddy owns product selection and presentation. DungeonMind owns durable rules knowledge and admitted read semantics.

The browser never supplies an arbitrary trusted rules-space authority. Production configuration/authorization selects allowed space(s).

## Suggested lease

Use the current live-control server conventions after re-anchor. Likely bounded roots:

```text
apps/live_control_server/models/
apps/live_control_server/services/
apps/live_control_server/routes/
apps/live_control_server/integrations/
tests/ or existing live-control route tests
```

Create a dedicated rules-query module rather than adding branching to unrelated World query code unless the existing abstraction is already generic.

## Do not

- generate a ruling;
- call Jev;
- publish rules;
- use WorldKeeper;
- move rules knowledge into Buddy application-state Postgres;
- trust browser-supplied `space_id`;
- alter shared UI hosts.

## Acceptance witness

A server-level test with a fake/in-memory DungeonMind rules source must prove:

```text
question
→ exact configured rules space/revision
→ admitted evidence
→ RulesQueryPacket
→ durable citation/source refs preserved
```

Also prove no-result and downstream-unavailable states.

Acceptance token:

```text
RLH_06_RULES_QUERY_PACKET_ACCEPTED
```

## Implementation witness for review

The server route accepts only a ruleset selector, question, and bounded hit limit. A trusted server manifest pins the exact RLH-03 space/revision, payload digest, V3 descriptors, and SRD source descriptors/excerpt. The DungeonMind adapter performs admitted search and exact evidence/anchor reads. Focused FastAPI tests prove citation identity, no-result, partial, unavailable, failure, and rejection of browser-supplied space/revision authority. A live local PostgreSQL smoke against the RLH-03 revision returned admitted evidence. This is an implementation candidate; the acceptance token above is the review criterion, not a claim of merged completion.
