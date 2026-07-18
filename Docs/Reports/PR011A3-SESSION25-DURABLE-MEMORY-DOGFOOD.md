# PR011A3 — Session 25 durable memory dogfood

**Status:** `BLOCKED` — live product dogfood not run in this implementation PR  
**Date:** 2026-07-18  
**Implementation base:** `e2787c601910f4d8c63d821b35a5a429301861f8`  
**Preferred objects:** Hesta, Mireward apothecary, relationship to Mireward Reach

## Why blocked

Live Session 25 publication requires explicit operator approval to mutate the
configured Eldyrwild World Graph head (`allowLiveWorld` is server-owned on the
product confirm route). This PR does not perform that live mutation.

Automated isolated-world prepare → confirm → exact-retry → reload proofs are
covered by `tests/test_live_extract_promote_api.py` (author-local).

## Required live steps (operator)

1. Use the real Session 25 recap/run (prefer Hesta / apothecary when extraction supports them).
2. Open Graph Review → Review & merge → select a valid assertion set.
3. Record current World Graph head.
4. With explicit approval, click **Merge N changes into campaign memory**.
5. Record receipt (`outcome`, `committedRevisionId`, `affectedObjectIds`).
6. Confirm Graph Review reloads that exact revision and opens durable IDs.
7. Reload browser/server; confirm objects persist.
8. Ask Plan/Hermes a fresh graph question; confirm retrieval (not recap fallback).

## Evidence fields (fill when unblocked)

| Field | Value |
|---|---|
| Old revision ID | |
| New revision ID | |
| Run ID | |
| Proposal ID / digest | |
| Selected assertion IDs | |
| Confirm outcome | |
| Affected durable object IDs | |
| Operator approved live publish? | |
| Plan/Hermes graph retrieval | |
| Browser/server reload | |

## Waiver

Live dogfood acceptance requires an explicit operator waiver or a completed run
of the steps above. Automated temporary-world proofs alone do not satisfy the
Session 25 gate.
