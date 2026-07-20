# HANDOFF — PR011A3 slice 1: promote-IR closeout

**Status:** `DOING` (GitHub PR #369)  
**Base:** `#366` merge `37c0a79d`  
**Branch:** `agent/pr011a3-promote-ir-closeout`  
**Umbrella:** #367 (DO NOT MERGE fat tip `eb509dae`)

## Mission

Make Session-class extracts seal/prepare with typed `SemanticState` + promote-eligible `EvidenceRef`, and project promote-safe candidate IR so typed validation succeeds for **session-evidenced** graph objects.

## Invariant

Live A3 acceptance remains **PARTIAL / NOT_READY_FOR_CANONICAL_RECAP_BACKFILL** until a fresh prepare→confirm→**exact committed revision reload** (+ Hermes retrieve if claimed) is recorded. Repair of a later head is not forward proof.

## Explicitly out of scope (remaining false)

- Standing_context + recap multi-slice confirm / atomic bundle (#375)
- Existing-object support-only observation rewrite (#370)
- C1 Model B migration, Plan lens, hover/cards, Author Node, known-entity registry

Empty-evidence party/context anchors survive sanitize via `context_anchor` but are **dropped** at promote projection so this slice does not depend on standing-context partition. Party standing promotion is a successor capability.

## Dependencies

- Requires: PR011A2 / #366 on `main` (`37c0a79d`)
- Unblocks: #370, #375 (and downstream promote slices)

## Dogfood authority

[`Docs/Reports/PR011A3-SESSION25-DURABLE-MEMORY-DOGFOOD.md`](../Reports/PR011A3-SESSION25-DURABLE-MEMORY-DOGFOOD.md) — Session 25 waived → Session 24; terminal NOT_READY.
