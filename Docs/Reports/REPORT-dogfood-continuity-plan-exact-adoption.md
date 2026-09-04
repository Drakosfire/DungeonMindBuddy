# REPORT — DOGFOOD-CONTINUITY DFC-2a exact historical Plan adoption

**Created:** 2026-09-04
**Capability:** explicit exact-ID Plan adoption into APP-STATE (preview default; `--apply` required)
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-plan-exact-adoption-v1.md`
**Branch:** `agent/dogfood-continuity-plan-exact-adoption-v1`
**Runtime worktree:** `DungeonMindBuddy-dogfood-continuity-plan-exact-adoption`
**Historical root (one-time operator input):** `primary-checkout` (`DungeonMindBuddy`)

This report is the sanitized W8/W9 steward witness. Absolute home paths are omitted; DSN password is omitted.

DFC-2a itself is **not** marked complete here. Acceptance remains steward review.

Review Cycle 1 at `8224500c700972a937777ebb18a4a832809c6d60` rejected blank-shell adoption and an unpinned importer TOCTOU. Review Cycle 2 at `2b22f33469924de882f5d9cc7e43eac9667855a6` accepted that repair and requested two remaining P1s: bind the pin to the classified DFC-1 observation, and stop inventing empty historical content during `CURRENT_EXACT` no-op verification. This file records the Cycle 3 repair witness on code head `04dcc272910cd9f5589e8a9e585991f037ac4df5`.

---

## Authority coordinates (sanitized)

| Field | Value |
|---|---|
| Adoption source root | `primary-checkout` — one-time operator input; never product authority |
| Cycle 1 leftover product authority | APP-STATE PostgreSQL `dungeonbuddy_application_state` @ `127.0.0.1:54329` |
| Cycle 2 fresh-write authority | isolated disposable PostgreSQL `dungeonbuddy_app_state_dfc2a_c2_70626530a4` @ `127.0.0.1:54329` |
| Cycle 3 fresh-write authority | isolated disposable PostgreSQL `dungeonbuddy_app_state_dfc2a_c3_727bb330a0` @ `127.0.0.1:54329` |
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

## Cycle 1 leftover local witness (not mutated)

Cycle 1 `--apply` against the configured local APP-STATE inserted four blank WorkObjects plus one recovered Plan. Review Cycle 1 forbade silently deleting or overwriting those rows.

Re-read after the Cycle 3 repair and isolated W9 (same host/port/database; **zero writes** to this authority):

| Identity | Title | Status | Bytes | sha256 prefix |
|---|---|---|---:|---|
| `00000000-…0000` | probe | discarded | 0 | `e3b0c44298fc1c14` |
| `61b3a73b-…6055` | C2 Session 27 Prep | active | 0 | `e3b0c44298fc1c14` |
| `80630cc2-…5e17` | C2 Session 27 Prep | active | 2631 | `d8a8595d5211d00a` |
| `c2121a99-…3abf` | C2 Session 23 Prep | active | 0 | `e3b0c44298fc1c14` |
| `d6ed9790-…917d` | C2 Session 23 Prep | active | 0 | `e3b0c44298fc1c14` |

Active Plan count on leftover authority: **4**. Discarded: **1**. Those rows remain as Cycle 1 residue. They are **not** the Cycle 2 or Cycle 3 recovery witness.

---

## Cycle 2 isolated fresh-write witness (superseded as live evidence)

Fresh authority then: empty isolated database `dungeonbuddy_app_state_dfc2a_c2_70626530a4`. That witness was performed on repair tree `fe82508a`; report commit `2b22f334` recorded it. Review Cycle 2 correctly asked for a live witness on the later code head after the remaining P1 repairs. Cycle 2 outcomes (five-ID block; single-ID `80630cc2-…` recovery; leftover untouched) are unchanged as history and are not the current live proof.

---

## Cycle 3 isolated fresh-write witness

Code head: `04dcc272910cd9f5589e8a9e585991f037ac4df5` (observation-bind + no-op verification + Markdown `git diff --check` repair). Fresh authority: empty isolated database `dungeonbuddy_app_state_dfc2a_c3_727bb330a0`, schema upgraded to head. Pre-apply Plan count: **0**.

DFC-1 classification is unchanged. DFC-2a still requires admitted historical target bytes before import. The pin is now bound to the classified `workspace_documents_registry` `LedgerItem` observation (digest + durable metadata + revision). If live evidence changed between inventory and pin creation, the entire requested set is blocked. `CURRENT_EXACT` no-op verification checks product list/open identity and status visibility only; it does not invent missing historical content.

### Preview / apply of the exact five IDs (empty isolated DB)

`blocked=yes`, `applied=no`, historical evidence digest unchanged (`42da8a583989285b…`).

| Identity | DFC-1 class | DFC-2a action |
|---|---|---|
| `00000000-…0000` | `RECOVERABLE_EXACT` | **block** — admitted target bytes absent/empty |
| `61b3a73b-…6055` | `RECOVERABLE_EXACT` | **block** — admitted target bytes absent/empty |
| `80630cc2-…5e17` | `RECOVERABLE_EXACT` | adopt (eligible; sibling blocks the set) |
| `c2121a99-…3abf` | `RECOVERABLE_EXACT` | **block** — admitted target bytes absent/empty |
| `d6ed9790-…917d` | `RECOVERABLE_EXACT` | **block** — admitted target bytes absent/empty |

Apply of the same five IDs: `blocked=yes`, `applied=no`, `imported=0`. Isolated Plan count remained **0**. Historical root unchanged.

The four IDs without surviving target bytes are later archive/adapter work. They are not adopted as blank shells.

### Preview / apply / replay of the one ID with admitted bytes

Selected: `80630cc2-33ee-40db-bf9d-fb5217085e17` only.

| Step | Result |
|---|---|
| Preview | `RECOVERABLE_EXACT` / `adopt`; `blocked=no`; no writes |
| Apply | `imported=1`; `skipped_empty=0`; `product verification=passed`; Plan count **1** |
| Recovered content | title `C2 Session 27 Prep`; revision 2; 2631 bytes; sha256 `d8a8595d5211d00a57731354ea06bce25aa6236332b66dece59870ed9d77a511` |
| Replay `--apply` | `CURRENT_EXACT` / `noop`; `imported=0`; Plan count still **1**; no duplicate write |
| Historical root | unchanged (`42da8a583989285b…` before and after) |

### Five-ID preview after that recovery (live re-read on the same isolated DB)

`blocked=yes`, `applied=no`, `historical_root_unchanged=yes`, active Plan count still **1**.

| Identity | DFC-1 class | DFC-2a action |
|---|---|---|
| `00000000-…0000` | `RECOVERABLE_EXACT` | **block** — admitted target bytes absent/empty |
| `61b3a73b-…6055` | `RECOVERABLE_EXACT` | **block** — admitted target bytes absent/empty |
| `80630cc2-…5e17` | `CURRENT_EXACT` | **noop** — exact identity already in APP-STATE |
| `c2121a99-…3abf` | `RECOVERABLE_EXACT` | **block** — admitted target bytes absent/empty |
| `d6ed9790-…917d` | `RECOVERABLE_EXACT` | **block** — admitted target bytes absent/empty |

---

## W9 product surface (DFC-2a worktree runtime, Cycle 3 isolated authority)

Buddy API was started from the DFC-2a worktree against `dungeonbuddy_app_state_dfc2a_c3_727bb330a0` (not the leftover local APP-STATE). UI `:5173` proxied to that API. Historical checkout was not mounted as the runtime root. DSN was re-pinned after dotenv so `.env` could not clobber the witness database.

1. `GET /api/live/workspace-documents?kind=plan` returned **one** record: `80630cc2-…` / `C2 Session 27 Prep` / `committed` / revision 2.
2. The four byte-less Cycle 1 IDs returned HTTP errors on snapshot (absent from isolated authority).
3. Snapshot of `80630cc2-…` returned `file_fingerprint=postgres`, `file_exists=false`, sha256 `d8a8595d5211d00a…`, 2631 bytes. Markdown head: `# C2 Session 27 Prep` / `## Session intent`.
4. Plan chooser listed only `C2 Session 27 Prep` (`80630cc2-…`). Canvas showed historical Session 27 Prep (Session intent / Opening frame / Mireward Siege Climax).
5. Hard reload of `/plan?documentId=80630cc2-…` kept the same ID, chooser option, and historical prose.
6. API process was stopped and restarted against the same isolated database. Product list/snapshot were unchanged (`d8a8595d5211d00a…` / 2631 bytes / postgres). After restart, the Plan surface again listed/opened the same Session 27 Prep.

World Graph showed `authority_unavailable` in this runtime; that is unrelated to Plan adoption.

---

## Cycle 1 report (superseded as completion evidence)

The first real apply against leftover local APP-STATE produced four `skipped_empty` WorkObjects and one imported Plan. Product verification was later made status-aware; the subsequent apply on that head was a five-`CURRENT_EXACT` replay. Review Cycle 1 correctly refused that as DFC-2a completion. It remains only as leftover local residue, documented above.

---

## Recovery PRs still justified (unchanged successors)

- **DFC-2b** Build adaptor/locator (four `NEEDS_ADAPTER` Builds)
- **DFC-2c** 53 manifest-era Ingest runs
- **DFC-2d** Runbook/Play archive hunt (no admitted evidence in scanned roots)
- **DFC-NAV1** persistent app-shell navigation (no UI lease here)
- Later archive/adapter: reconstruct missing draft Plan target bytes for the four DFC-1 `RECOVERABLE_EXACT` IDs that fail the DFC-2a admitted-bytes gate, without synthesizing identity

---

## Explicit non-claims

- DFC-2a is not DONE pending steward review.
- No orphan Plan, Build, Ingest, Runbook, Play, or navigation code was added.
- `import_plans.py` was not modified.
- `src/product_continuity/inventory.py` (DFC-1 classifier) was not modified.
- Historical `primary-checkout` files were not mutated or copied into the current worktree as authority.
- The four blank WorkObjects in leftover local APP-STATE were not deleted or overwritten.
