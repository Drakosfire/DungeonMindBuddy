# REPORT — Design request: governed recap World genesis for full-corpus dogfood

**Status:** DESIGN REQUIRED — blocks the final publication phase of PR #715.  
**Recorded:** 2026-09-14  
**Workstream:** DOGFOOD-CONTINUITY / full-corpus automated World Graph ingestion  
**Implementation head:** `7a29388c6f42a65a10ead4030208882e248d0e65`  
**Primary handoff:** `DOGFOOD-CONTINUITY: publish both full-corpus model arms, select a dogfood World, exit ingestion`

## Decision requested

Design one production-owned, governed way to create the **initial immutable
World revision for recap ingestion** from an admitted, deterministic campaign
baseline. It must support creating two equivalent isolated rehearsal Worlds for
the already-sealed 42-session OpenAI and DeepSeek candidate arms.

The design must answer:

> How can a new recap campaign obtain its first governed World revision — with
> the canonical party identities and source provenance it needs — without
> inventing an empty head, writing SQL, or treating worldbuilding as played
> recap canon?

## Observed blocker

PR #715 now has a zero-model replay tool that verifies all 42 sealed candidate
graphs in each arm, admits their sources, resolves identity, qualifies
assertions, confirms governed writes, and records an immutable chronological
revision chain. It deliberately requires an existing parent World revision.

Two local, loopback-only authorities were provisioned with identical DungeonMind
schema and no copied data:

| Arm | Database | Heads | Revisions |
| --- | --- | ---: | ---: |
| OpenAI | `dmb_full_corpus_openai` | 0 | 0 |
| DeepSeek | `dmb_full_corpus_deepseek` | 0 | 0 |

The current code head contains no supported governed recap-genesis capability.
The historical Eldyrwild bootstrap wrapper is not available on this head. A
direct SQL-created head would be false evidence: it bypasses source admission,
identity resolution, assertion qualification, governed mutation, and immutable
revision creation. It was not used.

Provisioning and teardown details are recorded in
`out/full_corpus_world_graph_ingestion/publication/PROVISIONING.md`.

## Why this is a product capability, not experiment plumbing

The missing step is not “make a test database nonempty.” A real campaign recap
workflow has the same first-publication problem:

```text
new campaign
  → canonical party / campaign baseline
  → first observed-session recap candidate
  → first durable campaign-memory World revision
  → normal existing-World chronological publication
```

Today only the final three stages have a governed existing-World path. Requiring
a human to manufacture a head, reuse another campaign's graph, or initialise
from unplayed worldbuilding would violate authority boundaries.

## Frozen constraints for the successor

The design and its eventual implementation must preserve all of the following:

- The two #715 model arms remain isolated; no hybrid graph or cross-arm identity
  reuse.
- No new LLM calls, prompt changes, candidate regeneration, or manual candidate
  retyping.
- Campaign recap (`observed_session_recap`) remains distinct from worldbuilding,
  prep, secrets, rumor, and planned material.
- The initial baseline must establish the same six canonical PCs for both Worlds:
  Baergrom, Bonogo, Caelynn, Ephanna, Karsemine, and Stafl.
- Party availability is identity authority, not invented evidence that every PC
  participated in every session.
- The first durable revision must be source-backed, immutable, idempotent, and
  readable through the same DungeonMind-native contracts as later revisions.
- A malformed, foreign, stale, duplicate, or partially initialized request must
  fail closed without a head or partial source state.
- The subsequent S1→S42 chain must use the exact committed predecessor revision.

## Required design output

Please produce a narrowly scoped design/handoff for a single independently
useful capability, including:

1. **Authority model.** Identify the canonical input(s) for the campaign
   baseline and why their epistemic/source class is valid for identity seeding.
2. **User/operator intent.** Define the explicit action that asks to initialize
   recap memory for a campaign; do not hide it inside ordinary extraction or
   world creation.
3. **Prepare/confirm contract.** Specify exact request, sealed plan, selection
   rules, idempotency key, confirmation actor, and receipt fields.
4. **Genesis contents.** State whether the first revision contains (a) only
   party/campaign identity anchors, or (b) those anchors plus the first recap's
   reviewed contribution. Explain the causal ordering and source provenance in
   either case.
5. **Identity rules.** Require roster PCs to become durable `pc` identities,
   prevent a later `character` candidate from minting an NPC duplicate, and
   distinguish baseline identity from participation claims.
6. **Atomicity/recovery.** Define behavior for failed source admission,
   duplicate initialization, lost confirm response, stale parent, and a source
   whose bytes change between prepare and confirm.
7. **Isolation.** State how a rehearsal World is named and how it avoids live
   Eldyrwild, another arm, and later-session knowledge. Include database/runtime
   ownership and teardown requirements.
8. **Read/write compatibility.** Prove the generated revision enters the same
   native mutation-context and retrieval lifecycle that the existing #715 replay
   runner consumes.
9. **Evidence plan.** Name owning integration tests and a real isolated-PG
   witness. Tests must exercise the actual initialization boundary, not only
   a mapper or in-memory helper.
10. **Non-goals.** Explicitly exclude full worldbuilding ingestion, ontology
    widening, identity cleanup beyond the roster invariant, Agent tuning, and
    UI work.

## Design alternatives to adjudicate

| Option | Outline | Primary concern |
| --- | --- | --- |
| A. Baseline-only genesis | Admit a canonical party/campaign baseline, initialize a World containing only stable identities, then publish C1 S1 normally. | Requires a valid canonical baseline source and a useful first-world operation without played claims. |
| B. Atomic baseline + S1 genesis | Admit baseline and exact C1 S1 recap; initialize one revision from a sealed combination. | Must preserve separate authority/provenance and avoid treating roster data as session participation. |
| C. Reuse worldbuilding first-world init | Extend the existing reviewed initialization contract to recap baseline sources. | High risk of flattening source class and smuggling worldbuilding semantics into recap memory. |

Option A appears most causally legible, but this report does not select it. The
design must establish whether the current DungeonMind initializer can express
it without a misleading “reviewed worldbuilding source” fiction.

## Acceptance criteria for the successor

The later implementation is sufficient for #715 only when it can create two
fresh equivalent rehearsal Worlds and show, for each:

```text
canonical baseline source admitted
→ six stable PC identities present
→ immutable genesis revision and receipt
→ exact head readable as an existing World mutation context
→ C1 S1 can publish against that exact revision with zero model calls
```

It must be possible to destroy the rehearsal authority after the experiment
without touching live World authority. The existing scoped drop procedure must
remain documented and deliberate; no credentials may enter tracked artifacts.

## What remains true about PR #715

- Both arms have 42 readable, digest-verified candidate graphs.
- Candidate generation is complete and sealed; it must not be rerun.
- The governed replay harness is implemented and tested (17 focused tests
  passing at the recorded head).
- No model call was made while discovering or provisioning this blocker.
- Publication, Oracle comparison, terminal probes, selection, and UI GO/HOLD
  are **not yet determined**. They remain blocked only on a truthful governed
  recap-genesis decision and implementation.
