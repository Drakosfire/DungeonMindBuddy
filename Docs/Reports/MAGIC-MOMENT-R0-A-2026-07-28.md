# Magic Moment Dogfood — R0-A

**Date:** 2026-07-28  
**Operator:** ChatGPT roadmap agent; repository inspection only  
**Repository SHA:** `0f6f48ed6502a9a4e69b57f351ae9c795da54694`  
**World / campaign:** intended `eldyrwild` / `longmont-c2`  
**Graph revision:** not observed; no operator runtime was connected  
**Result:** BLOCKED_DEPENDENCY

## Intent

Attempt the real GM-facing Statblock Workbench sequence for **Mireward Latchling**:

```text
create ThreatDraft
→ generate through current DungeonMindServer
→ inspect complete mechanics
→ make one meaningful mechanical edit
→ validate the exact working definition
→ request one explicit revision
→ inspect proposal lineage
→ accept one exact immutable revision
→ reload and reopen the exact accepted mechanics
```

## Starting state

The repository was re-anchored to current `main`, but this execution environment had:

- no local checkout or operator worktree;
- no Live Control browser session;
- no access to the operator’s configured environment variables;
- no access to the user-local DungeonMindServer endpoint or internal API key;
- no access to the durable `out/` ThreatDraft, candidate, acceptance-operation, or accepted-mechanics stores.

No source document, candidate fixture, mock provider, corpus-promotion output, or remembered ID was substituted for the user-facing path.

## Steps actually taken

1. Verified current `main` at `0f6f48ed6502a9a4e69b57f351ae9c795da54694`.
2. Read the active roadmap, tracker, lifecycle decision, and dogfood runbook.
3. Inspected the current ThreatDraft model, CRUD routes, and route tests.
4. Inspected Workbench create, exact candidate read, complete-definition edit/validation, revise, acceptance, reconciliation, and browser recovery seams.
5. Inspected current provider configuration, readiness projection, strict contract name/version, generated DTO ownership, and OpenAPI source path.
6. Inspected PR `#425`, the most recent partial real-provider attempt. It created a real draft but generation failed because the configured DungeonMindServer connection was refused.
7. Confirmed no current provider health probe or user-facing browser execution could be performed from this environment.
8. Stopped rather than manufacturing hidden state or treating automated tests as the product gate.

## Durable identities

- retrieval session: not applicable
- selected node IDs: not created
- admitted source anchors: not created
- draft ID/version: no current gate identity created
- candidate ID: not created
- revise proposal ID: not created
- statblock ID/revision/digest: not created
- Threat ID/binding ID: not applicable
- placement ID: not applicable
- combat encounter/runtime entity IDs: not applicable

Historical evidence from PR `#425`, not current gate evidence:

```text
draft: 0c5603d9-e819-4f33-9bfb-6bed12505f43 v1
name: Mireward Reedlatch
generate result: downstream_unavailable / connection refused
configured endpoint reported in PR: 127.0.0.1:7860
```

That identity is not reused as proof for this gate.

## What felt magical

Not exercised. No current user-facing Workbench session reached real candidate generation.

## Friction and misses

### Environmental blocker

The real provider and browser runtime were unavailable to this agent. Current provider health, authentication, capability advertisement, and response compatibility remain unobserved.

### Known product friction visible in code

The backend can list, get, and update durable ThreatDrafts, but the current `liveApi` and Workbench do not provide a normal ThreatDraft library. The Workbench can recover a joined draft/candidate and local working copy from browser session state or use exact IDs through recovery controls, but this is not equivalent to normal browse/reopen usability.

This friction is recorded but does not select an implementation slice before the real mechanics path is exercised.

## Failure / retry / reload observations

No current product observations were made.

Code and owning-boundary tests establish that:

- draft records survive a fresh app instance;
- list/get/update routes are durable and version-fenced;
- local candidate working copies can be restored from browser session storage;
- revise attempts and acceptance operations retain exact IDs for stable retry/reconciliation;
- exact accepted locators include statblock ID, revision ID, and definition digest;
- candidate misses, expiry, dependency failure, and integrity failure do not silently fall back to mock or corpus output.

Those are implementation facts, not a substitute for this gate’s real-provider and GM-visible reload proof.

## Verdict

`BLOCKED_DEPENDENCY`.

The gate did not pass or fail as a product capability because the real external provider and normal product runtime were not reachable. Historical PR `#425` confirms that draft creation can survive a downstream generation failure, but it also explicitly leaves generation, rendering, editing, validation, revise, acceptance, and reload unproven against the real provider.

No broad parser relaxation, mock fallback, hidden store edit, or corpus-promotion path was used to manufacture a pass.

## Required next slice

No implementation slice is justified yet.

The next exact operation is:

```text
On the operator machine, start the configured DungeonMindServer and Live Control UI, confirm `/api/live/statblocks/v1/readiness` reports the current contract/capabilities, then run the complete Mireward Latchling R0-A sequence through the normal Workbench.
```

Classify the first real miss after that run:

- strict current-provider response mismatch → narrow provider/consumer contract-sync slice;
- real mechanics path succeeds but normal durable reopening requires opaque IDs → smallest ThreatDraft browse/reopen client + Workbench library slice;
- dependency failure destroys unsaved local mechanics → separate local in-progress recovery slice;
- only revise-from-exact-accepted remains absent → re-anchor `SBW06d`;
- clean pass → record `PASS` or `PASS_WITH_FRICTION`, then wait for `R0-B` before selecting broader continuation.
