# Anchor — DungeonMind.net Platform Refresh

**Status:** ACTIVE REFERENCE / PARALLEL DESIGN LANE  
**Created:** 2026-09-25  
**Cross-repository authority:** `Drakosfire/DungeonOverMind/Docs/roadmaps/ROADMAP-dungeonmind-net-platform-refresh.md`  
**Steward handoff:** `Drakosfire/DungeonOverMind/Docs/Plans/STEWARDS-HANDOFF-dungeonmind-net-platform-refresh.md`

## Why this exists

Once the local DungeonBuddy golden path is accepted:

```text
ingest
→ governed source-to-World authoring
→ durable publication
→ query
→ statblock generation
→ image generation
→ persistence/reopen
```

the product should be made available through `dungeonmind.net` with real authentication and persistence.

That launch is being treated as a wider DungeonMind.net platform-refresh opportunity rather than a narrow hosting task.

## Buddy's role

Buddy remains the owner of:

- persistent-world GM/campaign product behavior;
- Plan / Build / Play / Graph Review surfaces;
- application/work state;
- Agent orchestration;
- product semantics and workflow;
- Buddy-specific production UI/API behavior.

DungeonMind remains durable World authority.

DungeonMindServer remains public web backend/auth/platform owner.

LandingPage / DungeonMind Web remains public web frontend owner.

OverMind owns the cross-repository refresh architecture and sequence.

## Production questions the steward will resolve

- authenticated user→World authorization;
- durable world membership/selection;
- production application-state tenancy;
- same-origin routing;
- production migrations/bootstrap;
- health/readiness;
- statblock/image persistence integration;
- cost/quota/safety for paid generation;
- restart/reload durability;
- Buddy's deployment boundary relative to DungeonMind Web and Server.

## Scope guard

This anchor does **not**:

- resume paused broad UI work;
- override World Keeper/source-to-World authority;
- change the current Campaign Supergraph tracker;
- change the OverMind E5 inference sequence;
- authorize Buddy deployment code.

Platform-refresh implementation begins only from a future bounded Buddy handoff produced by the platform steward.

The live completion target is an authenticated browser flow that survives refresh, logout/login, and service restart while reopening the same authorized World, published knowledge, generated statblock, and generated image by durable identity.
