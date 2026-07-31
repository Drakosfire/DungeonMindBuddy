# HANDOFF — Superseded open PR salvage and retirement

**Created:** 2026-07-31  
**Status:** ACTIVE — until salvage PR merges; then archive pointer to evidence ledger.  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Salvage branch:** `chore/mine-retire-superseded-prs`  
**Required base / actual base:** `c371d43178a2b83da299319a047f93bae50d0959`  
**Evidence ledger:** [`Docs/Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md`](../Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md) — canonical disposition for all eight source PRs.

> This checked-in dispatch record is intentionally shorter than a full worker handoff. Per-PR tables, evidence, and verification placeholders live in the REPORT. Do not expand salvage scope beyond what is listed here.

---

## §1 Mission

Retire eight superseded open PRs by mining durable documentation and one bounded code salvage (#433 extract-promote inspection status), naming successors for still-valid intent, and closing source PRs without rebasing stacked implementation or landing obsolete architecture.

**Invariant**

```text
Every source PR receives an explicit disposition (IMPLEMENTED / PRESERVED / ALREADY_PRESENT / REJECTED)
with evidence in the REPORT; no silent drops; no rebased stacked heads; protected PRs #431 and #462 untouched.
```

---

## §2 Source inventory (§2A)

| PR | Head SHA | Pre-salvage GitHub state |
|---|---|---|
| #231 | `006e53b27f175de0fb96f2a706745701bbbece84` | CLOSED |
| #395 | `bb7e4eb7485ee0923b5c45c01abf93ba9f68040a` | CLOSED |
| #432 | `5cdcd107e50cc89f16e44c4072705549e28d696e` | OPEN (superseded) |
| #433 | `543847c9484a0a57f1950f389680db70b4841bac` | OPEN (superseded) |
| #444 | `127168de48d2d94803f906ff69a26bbc9fefaf82` | OPEN (superseded) |
| #449 | `2369d32b3b574104cc09fc8abb0bddef69031f51` | OPEN (superseded) |
| #459 | `0abdb55d5779273e406643221e0a41e959371055` | OPEN (duplicate of #431) |
| #460 | `a4d95b68907a8b99e0991616817cd3c6a9e466e8` | OPEN (superseded by #462) |

Frozen disposition decisions are authoritative in the REPORT §2–§3. This handoff does not re-litigate them.

---

## §3 Protected work (do not close, retarget, or overwrite)

- **#431** — MC-02a surface-neutral graph reference loop (active).
- **#442** — Eldyrwild world-graph snapshot transfer vehicle (intentional OPEN; do not merge/close).
- **#462** — SBW09a publication operation ledger (active).
- **#463** — TL01F Timeline proposition-type temporal lane gate (active).

---

## §4 Allowlist

| Action | Path | Notes |
|---|---|---|
| Add | `Docs/Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md` | Evidence ledger |
| Add | `Docs/Plans/HANDOFF-superseded-open-pr-salvage-and-retirement.md` | This dispatch record |
| Add | `Docs/Design/PATTERN-openai-structured-outputs-complex-contracts.md` | Scrubbed from #449 head |
| Add | `Docs/Plans/HANDOFF-dms-generation-validation-diagnostics.md` | Scrubbed CONDITIONAL successor |
| Add | `Docs/Plans/HANDOFF-graph-review-browse-committed-sessions.md` | #444 successor |
| Add | `Docs/Plans/HANDOFF-build-stay-on-build-dogfood-after-mc02.md` | #432 successor |
| Modify (pre-authorized) | `apps/live_control_server/models/extract_promote.py` | #433 only — already in worktree |
| Modify (pre-authorized) | `apps/live_control_server/services/extract_promote.py` | #433 only — already in worktree |
| Modify (pre-authorized) | `tests/test_live_extract_promote_api.py` | #433 only — already in worktree |

---

## §5 Denylist

| Path / capability | Why excluded |
|---|---|
| Rebased/cherry-picked stacked heads from #432, #444, #449, #460 | Superseded architecture |
| `threat_statblock_publication*` parallel API/models/routes/store (#460) | #462 owns publication ledger |
| PDF/OCR implementation (#395) | Dormant framework prohibited |
| #444 first-wins / divergent-shadow projection | Main strict `semantic_assertion_divergence` 409 |
| PR449 R0-A report overwrite / stale tracker dispatch-now edits | Main reports + #462 authority |
| `PR-TRACKER-threat-statblock-authoring-projection.md` | Retain obligations in REPORT / HANDOFF-dms / #462 checklist |
| `ROADMAP-threat-statblock-authoring-projection.md` | Same |
| #459 as independent dispatch | Duplicate of #431 |
| Obsolete runners/shells (#231 precomputed runner, #432 BuildGraphReferenceShell, #395 monolithic shell) | REJECTED in REPORT |

---

## §6 Verification (worker must run before merge)

```bash
cd DungeonMindBuddy-salvage-prs
uv run pytest tests/test_live_extract_promote_api.py -q -k "inspection"
uv run pytest tests/test_live_extract_promote_api.py -q
git diff --check
```

Record results in REPORT §5 placeholders. Docs-only changes require no frontend build.

---

## §7 Acceptance rubric

- [ ] REPORT lists all eight PRs with IMPLEMENTED / PRESERVED / ALREADY_PRESENT / REJECTED evidence.
- [ ] #433 code matches REPORT §6D mapping; tests assert `blocked` / `invalid_evidence` and diagnostic retention.
- [ ] Scrubbed PATTERN and DMS handoff carry salvage banners; no dispatch-now tracker claims.
- [ ] Two new successor handoffs (#444 browse, #432 stay-on-Build) cite source heads and deny rejected paths.
- [ ] No denylist paths touched.
- [ ] #431 and #462 remain open and unmodified by salvage.
- [ ] `{{HEAD_AFTER_COMMIT}}` replaced in REPORT after merge commit.

---

## §8 Closure protocol

### §8A — GitHub closure comment template

Post on each superseded **open** source PR (#432, #433, #444, #449, #460) when salvage merges:

```markdown
## Superseded — salvaged and retired (2026-07-31)

This PR's stacked implementation is superseded by current `main`. Salvage branch `chore/mine-retire-superseded-prs` (base `c371d431`) mined durable intent without rebasing this head.

**Evidence ledger:** `Docs/Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md` on main after merge.

**This PR's disposition:** see REPORT §3 for PR #{{PR_NUMBER}}.

**Active successors:** named in REPORT §8 — do not reopen this branch.

Closing as superseded. Protected work continues in #431 / #462 as applicable.
```

Replace `{{PR_NUMBER}}` per PR. #231 and #395 were already CLOSED — no comment required unless operator wants ledger link.

---

## §9 Stop conditions

Stop and report if:

- salvage requires rebasing a source stacked head;
- any denylist path appears in the diff;
- #433 port expands beyond inspection-status enrichment documented in REPORT §6D;
- PR-TRACKER or ROADMAP edits are required to land salvage (they are not — use REPORT instead).
