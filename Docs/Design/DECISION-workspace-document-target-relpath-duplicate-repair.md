# DECISION — workspace-document duplicate `target_relpath` repair

**Status:** Accepted for PR #543 follow-up  
**Date:** 2026-08-10  
**Scope:** Local/dev `out/registries/workspace_documents.json` (gitignored) and the bounded registry repair helpers that other environments must use instead of ad-hoc identity deletion.

## Problem

HANDOFF §5 required a **read-only** preflight before enforcing unique non-null `target_relpath` ownership. This environment already had two active Plan records sharing:

`corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md`

| document_id | status (at STOP) | title |
|---|---|---|
| `381d62b4-7a53-4452-8eb2-b90dbea8ae54` | active | C2 Session 23 Prep |
| `bcaa65da-e9c9-4ae9-afba-2d8190ec09d5` | active | C2 Session 23 Prep |

The implementation run correctly **STOPped** and reported this, then — after operator approval to discard pre-session-26 Plan docs — discarded both twins. It then **deleted** `bcaa65da-…` from the registry so uniqueness looked clean. That identity deletion was **outside** the governed repair surface: it can orphan local drafts / locks and is not a portable migration for other duplicated registries.

The new create-time **409** guard correctly blocks *future* duplicate ownership. It does not heal already-duplicated registries.

## Operator facts already approved

- Discard anything before Session 26 prep (2026-08-10 chat).
- Active Plan authority remains Session 26: `40700cb6-d13d-4fbf-93f6-6ae2986455a7`.

## Bounded repair policy (portable)

For duplicated non-null `target_relpath` ownership:

1. **Report** via `find_duplicate_target_relpath_ownership` (read-only). Do not choose winners in create/409 code.
2. **Discard** records the operator no longer wants active (existing `discard_workspace_document`).
3. **Release path from the loser** via `release_target_relpath_from_discarded_duplicate`:
   - survivor keeps the durable `target_relpath`
   - retiree stays in the registry as `discarded` with `target_relpath: null`
   - both identities remain addressable (local draft keys / history are not orphaned by registry deletion)
4. If an identity was already deleted incorrectly, **reinstate** it with `reinstate_workspace_document_record` as discarded + `target_relpath: null`, then verify the scan is empty.
5. Never treat manual gitignored JSON edits or silent identity deletion as the migration.

## This environment — applied reconciliation

| Role | document_id | outcome |
|---|---|---|
| Path survivor (discarded) | `381d62b4-7a53-4452-8eb2-b90dbea8ae54` | Keeps Session 23 `target_relpath`; status `discarded` |
| Path retiree (restored identity) | `bcaa65da-e9c9-4ae9-afba-2d8190ec09d5` | Reinstated `discarded` with `target_relpath: null` |
| Active Plan | `40700cb6-d13d-4fbf-93f6-6ae2986455a7` | Session 26 unchanged |

**Why survivor is `381d62b4`:** earliest `created_at` among the Session 23 twins (`2026-08-08T17:55:27Z`) and the identity that remained after the unauthorized deletion; no corpus file existed for Session 23 Prep at STOP time, so path ownership is a registry lock only.

**Why not leave `bcaa65da` deleted:** identity retirement by deletion orphans client-local state keyed by `document_id` and is not expressible as a reviewable repair API. Restoring discarded identity with a released path is the minimal reversible fix.

## Falsification

- `find_duplicate_target_relpath_ownership(root) == []` after repair.
- Creating a Plan doc with the Session 23 path still returns **409** against survivor `381d62b4`.
- `get_workspace_document(bcaa65da)` succeeds with `status=discarded` and `target_relpath=null`.

## Non-goals

- Automatic filename suffixes / silent reuse / auto-restore to active.
- Rewriting corpus Markdown.
- Healing remote production registries without an explicit apply of this policy.
