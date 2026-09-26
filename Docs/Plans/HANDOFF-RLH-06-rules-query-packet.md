# HANDOFF — RLH-06 rules query packet

**Status:** DEFERRED DRAFT  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Authority:** `Drakosfire/DungeonOverMind/Docs/Plans/PLAN-rules-lawyer-graph-experiment.md`  
**Predecessor:** `RLH_04_DUNGEONMIND_RETRIEVAL_BENCHMARK_ACCEPTED` plus accepted platform Phase A–G golden path  
**Primary question:** Can Buddy expose one read-only rules-query application contract that returns exact DungeonMind-backed evidence/citations without generating a ruling?  
**Unlocks:** RLH-07

## Re-anchor before coding

This branch was planted while Buddy UI foundation PRs #755–#761 were in flight. Rebase onto current `main` after those and all platform predecessors settle. Re-census the existing DungeonMind query integration and live-control server route/service patterns.

This PR is backend/application-contract work. It must not redesign ToolHost.

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
