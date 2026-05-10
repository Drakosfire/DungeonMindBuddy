# HANDOFF: Close Phase A gate and validate route-id derivation — RETIRED

**Status: RETIRED 2026-05-10.** Do not execute as-written. Both objectives have been resolved by other work:

- **Step 1 (Phase A hierarchy gate):** `scripts/audit_world_campaign_alignment.py` returns `World/Campaign alignment audit: PASS` on current `main`. The three C1S13 location-context scenarios already carry non-empty `location_hierarchy_equivalences`. A separate content-quality concern (two scenarios appear copy-pasted) is captured in `Backlog.md` as `[IDEA] C1S13 hierarchy content audit` and is **not a Phase A blocker**.
- **Step 2 (route-id validation for directory-style hub_path):** Closed by PR #2 (merge commit `545cf37`, 2026-05-10T02:59Z). See `src/lexicon_phase_b/route_equivalence_manifest.py::_extract_entity_slug` and `tests/lexicon_phase_b/test_route_id_path_shapes.py`.

**Replaced by:** `Docs/Plans/HANDOFF-phase-b-route-equivalence-artifact-output.md` (canonical artifact path + byte-stable regression for `build_route_equivalence_manifest`).

**Original date:** 2026-05-09  
**Original status:** Ready for execution  
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`  
**Checklist anchor:** `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`

---

_Original content preserved below for audit/history. Do not act on it._

---

## Mission

Execute the next two steps from the active super-plan:

1. **Close Phase A red gate** by fixing missing `location_hierarchy_equivalences` in C1S13 natural gold and proving `audit_world_campaign_alignment.py` is green.
2. **Validate (and fix if needed) route-id derivation** for directory-style `hub_path` values in live `_npc_registry.json` files, with test evidence.

This handoff is operational. The work is not complete until a **separate report** is written (see "Required report output").

---

## Required report output

After implementation, write a separate report at:

- `Docs/Plans/archive/2026-05-09/reports/REPORT-phase-a-gate-close-and-route-id-validation.md`

The report must include:

- Commands run (exact CLI lines)
- Key artifact paths
- Before/after gate results
- One failure sample and one success sample for the route-id validation surface (if applicable)
- Any follow-up risks or open questions

---

## Files in scope

### Phase A gate close

- `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json`
- `scripts/audit_world_campaign_alignment.py`
- `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`
- `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`

### Route-id validation/fix

- `src/token_resolution/resolver.py`
- `tests/test_token_resolution_contracts.py`
- `tests/test_token_resolution_resolver.py`
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json`
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json`

### Report output

- `Docs/Plans/archive/2026-05-09/reports/REPORT-phase-a-gate-close-and-route-id-validation.md`

---

## Out of scope

- Retriever wiring (Phase C+)
- New lexical artifact promotion logic
- Canvas/template redesign work
- Broad gold rewrites outside the specific C1S13 hierarchy omissions

---

## Execution instructions

## Step 1 - Close Phase A hierarchy gate

### A. Patch known missing hierarchy fields

Target file:

- `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json`

Fix the three location-context scenarios called out in the checklist:

- `stormspire_activity_arrival`
- `meat_storage_strongholds_locations`
- `mossglade_residency_vs_association`

Requirement: each scenario must contain non-empty `location_hierarchy_equivalences` consistent with the world/campaign hierarchy contract.

### B. Re-run alignment gate

Run:

```bash
uv run python scripts/audit_world_campaign_alignment.py
```

Pass condition:

- No remaining hierarchy violations for the above scenarios.
- Script exits clean.

### C. Update plan/checklist state

After green audit:

- Update `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`:
  - Mark Phase A hierarchy/alignment items complete.
  - Append a new session-log entry with artifact/result.
  - Advance active phase from A to B only if all A gates are green.
- Update `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`:
  - Refresh `execution_state` (`active_phase`, blockers, next gate command).
  - Append changelog entry reflecting Phase A closure.

---

## Step 2 - Route-id validation for directory-style hub_path

Context:

- Plan follow-up explicitly requires checking that route-id slug derivation works for **directory-shaped** `hub_path` values (not just `README.md`-shaped paths).

### A. Validate current behavior against real registries

Use live registry rows from:

- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json`
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json`

Focus on records where `hub_path` is directory-style (for example ending in `.../NPCs/<slug>/`).

### B. Fix if mismatch is found

Primary implementation target:

- `src/token_resolution/resolver.py`

Expected behavior:

- Route IDs should resolve to the NPC slug from terminal directory segment for directory-style paths.
- Behavior remains correct for file-shaped paths (for example explicit `README.md` leaves).

### C. Add/adjust tests

Update tests in:

- `tests/test_token_resolution_resolver.py`
- `tests/test_token_resolution_contracts.py`

Minimum coverage:

- Directory-style `hub_path` case
- File-style `hub_path` case
- No regression to existing route-equivalence contract semantics

### D. Run verification commands

Run at minimum:

```bash
uv run pytest tests/test_token_resolution_resolver.py
uv run pytest tests/test_token_resolution_contracts.py
uv run python scripts/audit_world_campaign_alignment.py
```

If a broader suite is needed due to touched imports, include it in the report.

---

## Acceptance criteria

The handoff is complete only if all are true:

- Phase A hierarchy gate is green in `audit_world_campaign_alignment.py`.
- Checklist and super-plan reflect current phase/state accurately.
- Route-id derivation has evidence for directory-style and file-style path shapes.
- Token-resolution tests pass after any resolver changes.
- Separate report exists at the required report path and includes command evidence + artifact links.

---

## Suggested report outline (copy into report)

1. **Scope executed**
2. **Commands run** (exact)
3. **Phase A gate evidence**
4. **Route-id validation evidence**
5. **Code/test changes**
6. **Remaining risk / follow-ups**
7. **Final verdict** (`Phase A closed: yes/no`, `Route-id follow-up closed: yes/no`)

