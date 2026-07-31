# HANDOFF — SBW09 Governed Threat + exact statblock binding publication

**Created:** 2026-07-22  
**Status:** SUPERSEDED — historical bundled design; do not dispatch.  
**Superseded on:** 2026-07-30 after merged PR `#457` and publication-first capability decomposition.  
**Historical path:** `Docs/Plans/HANDOFF-sbw09-governed-threat-binding-publication.md`

> This document originally bundled publication-operation persistence, create-or-connect identity resolution, governed review/confirm, post-commit verification, and UI into one PR. That bundle no longer matches the active tracker or ownership boundaries.

## Current dispatch sequence

1. [`HANDOFF-sbw09a-publication-operation-ledger.md`](HANDOFF-sbw09a-publication-operation-ledger.md)  
   Durable, no-write publication operation authority pinned to one exact mechanics-saved ThreatDraft snapshot and expected World Graph parent. No future PR number is assigned by that handoff.

2. `SBW09b` — handoff to be designed after `SBW09a` merges  
   Explicit create-new versus connect-existing Threat resolution; no silent duplicate or merge.

3. `SBW09c` — handoff to be designed after `SBW09b`  
   Governed proposal, review, confirmation, immutable graph commit, and exact post-commit verification.

## Preserved historical lessons

The old design remains useful only as research for successor re-anchoring:

- accepted mechanics and graph publication are separate;
- graph failure must not recreate or mutate accepted mechanics;
- create/connect requires an explicit exact identity decision;
- prepare must write nothing;
- confirm must be bound to reviewed effects and exact parent authority;
- post-commit verification must be pinned to the committed revision;
- committed-but-unverified is distinct from not committed;
- retries must not silently duplicate Threats, resources, or bindings;
- no direct graph-file mutation or autonomous Hermes confirmation is permitted.

## Authority

The active publication-first roadmap and tracker, followed by the unnumbered handoff for the current slice, supersede every dispatch instruction formerly contained here.

Do not implement this file as one capability. Do not copy its old allowlist or UI scope into `SBW09a`.
