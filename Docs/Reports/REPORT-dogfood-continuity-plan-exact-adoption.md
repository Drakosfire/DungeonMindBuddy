# REPORT — DOGFOOD-CONTINUITY DFC-2a exact historical Plan adoption

**Created:** 2026-09-04  
**Capability:** explicit exact-ID Plan adoption into APP-STATE (preview default; `--apply` required)  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-plan-exact-adoption-v1.md`  
**Branch:** `agent/dogfood-continuity-plan-exact-adoption-v1`  
**Runtime worktree:** `DungeonMindBuddy-dogfood-continuity-plan-exact-adoption`  
**Historical root (one-time operator input):** `primary-checkout` (`DungeonMindBuddy`)

This report is the sanitized W8/W9 steward witness. Absolute home paths are omitted; DSN password is omitted.

DFC-2a itself is **not** marked complete here. Acceptance remains steward review.

---

## Authority coordinates (sanitized)

| Field | Value |
|---|---|
| Adoption source root | `primary-checkout` — one-time operator input; never product authority |
| Current product authority | APP-STATE PostgreSQL |
| Host | `127.0.0.1` |
| Port | `54329` |
| Database | `dungeonbuddy_application_state` |
| Schema head | `at_head` |
| Current Buddy worktree | DFC-2a checkout (not the historical root) |
| Current Build/workspace files | not used as Plan authority after adoption (`file_fingerprint=postgres`, `file_exists=false`) |

Historical Plan markdown files were **not** copied into the DFC-2a worktree. The Plan chooser/snapshot seam read APP-STATE.

---

## Selected IDs (exact DFC-1 set only)

```text
00000000-0000-4000-8000-000000000000
61b3a73b-df4e-4133-9879-bb2096796055
80630cc2-33ee-40db-bf9d-fb5217085e17
c2121a99-d0da-4ba1-b1ef-511f4f2e3abf
d6ed9790-ebbf-401d-90ba-182aff80917d
```

Orphan IDs `0bcfbf24-…` and `0eab57a6-…` were not selected.

---

## Preview / apply / replay

Pre-apply Plan product count: **0** (`list_plans()` and `list_workspace_documents(kind="plan")`).

### Preview

All five reclassified `RECOVERABLE_EXACT` / `adopt`. `applied=no`. Historical evidence digest unchanged.

### Apply

| Identity | Title label | Historical evidence | Importer result | After apply |
|---|---|---|---|---|
| `00000000-…0000` | probe | draft registry; target bytes absent; `status=discarded` | skipped empty (WorkObject inserted) | `CURRENT_EXACT`; discarded; not in default active chooser |
| `61b3a73b-…6055` | C2 Session 27 Prep | draft registry; corpus target bytes absent | skipped empty | `CURRENT_EXACT` draft; listed; empty working copy |
| `80630cc2-…5e17` | C2 Session 27 Prep | committed registry + `out/workspace/plan/…md` bytes | **imported 1** | `CURRENT_EXACT`; listed; 2631 bytes; sha256 `d8a8595d5211d00a` |
| `c2121a99-…3abf` | C2 Session 23 Prep | draft registry; corpus target bytes absent | skipped empty | `CURRENT_EXACT` draft; listed; empty working copy |
| `d6ed9790-…917d` | C2 Session 23 Prep | draft registry; corpus target bytes absent | skipped empty | `CURRENT_EXACT` draft; listed; empty working copy |

First apply: `importer imported=1`, `skipped empty=4`, historical root unchanged. Initial post-apply product verification failed because discarded `probe` is absent from the default **active** Plan list. Snapshot of that ID still succeeded. Verification was then status-aware (active vs discarded lists). Replay `--apply` reported five `CURRENT_EXACT` no-ops, `imported=0`, `product verification=passed`, no duplicate writes.

Post-apply active Plan count: **4**. Discarded Plan count: **1**.

Honest content finding: DFC-1 still classifies the four drafts as `RECOVERABLE_EXACT` without surviving target bytes. The existing importer preserved exact identity/metadata and skipped empty working copies. Only `80630cc2-…` recovered historical prose.

---

## W9 product surface (DFC-2a worktree runtime)

Started Buddy API (`:8000`) and UI (`:5173`) from the DFC-2a worktree. Did not mount the historical checkout as the runtime root.

1. `GET /api/live/workspace-documents?kind=plan` returned the four active adopted IDs.
2. Snapshot of `80630cc2-…` returned `file_fingerprint=postgres`, `file_exists=false`, sha256 `d8a8595d5211d00a`, 2631 bytes.
3. Plan chooser listed all four active IDs (two Session 27 Prep, two Session 23 Prep).
4. Opened `80630cc2-…` — canvas showed historical Session 27 Prep (Session intent / Mireward Siege Climax).
5. Opened `c2121a99-…` — chooser selected C2 Session 23 Prep; canvas was the empty/blank authoring shell because no historical bytes survived at the registry locator.
6. Re-opened `80630cc2-…` in the same UI session (document reload) — same ID and Session 27 content remained.
7. Stopped and restarted the DFC-2a API. Product list/snapshot were unchanged (`d8a8595d5211d00a` / 2631 bytes / postgres). After restart, `/plan?documentId=80630cc2-…` still listed the four IDs and opened the same Session 27 Prep.

World Graph showed `authority_unavailable` in this runtime; that is unrelated to Plan adoption.

---

## Recovery PRs still justified (unchanged successors)

- **DFC-2b** Build adaptor/locator (four `NEEDS_ADAPTER` Builds)
- **DFC-2c** 53 manifest-era Ingest runs
- **DFC-2d** Runbook/Play archive hunt (no admitted evidence in scanned roots)
- **DFC-NAV1** persistent app-shell navigation (no UI lease here)
- Optional later: reconstruct missing draft Plan target bytes for the four empty drafts without synthesizing identity

---

## Explicit non-claims

- DFC-2a is not DONE pending steward review.
- No orphan Plan, Build, Ingest, Runbook, Play, or navigation code was added.
- `import_plans.py` was not modified.
- Historical `primary-checkout` files were not mutated or copied into the current worktree as authority.
