# HANDOFF — Shadow-verify Buddy Threat hydration through DungeonMind

**Created:** 2026-08-07  
**Status:** IMPLEMENTATION COMPLETE — ready for review  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Flow:** KERNEL / STATBLOCK  
**Canonical path:** `Docs/Plans/HANDOFF-statblock-dungeonmind-threat-hydration-shadow.md`

**Suggested branch:** `kernel/dungeonmind-threat-hydration-shadow`  
**Suggested PR title:** `STATBLOCK: shadow verify Threat hydration through DungeonMind`

---

## Repository identity

| Anchor | SHA |
|--------|-----|
| Buddy base (`main` = #518 merge) | `32d1c7ba0fb4e2cbc26a71ad449d404507926c58` |
| Branch | `kernel/dungeonmind-threat-hydration-shadow` |
| Implementation commit | *(set at PR open)* |
| DungeonMind dependency (PR #23 merge) | `8095321ed011b8a38640615a90cbc9efaf385e8c` |

Open adjacent PRs inspected before shared-file edits: #517 (PWO01 docs), #516 (benchmark), #510 (Build refs), #497 (navbar / docs only for threat roadmap), #442 (transfer). No shared-file collisions with `threat_query_hydration` or `dungeonmind_kernel`.

---

## Runtime wiring

```text
POST /api/live/threats/query-hydration
  → query_threats_with_hydration(...)           # sole authority
  → freeze ThreatQueryHydrationResponseV1
  → if DUNGEONMIND_THREAT_HYDRATION_SHADOW_ENABLED == "1":
        BackgroundTasks.add_task(run_dungeonmind_threat_hydration_shadow, ...)
  → JSONResponse(authoritative body, background=...)
  → after send: shadow loads exact response.revision_id once,
                bridges each explicit kind=threat,
                replays available ExactRevisionResourceV1 via
                AuthorityExactRevisionReplayResolver,
                logs dungeonmind_threat_hydration_shadow
```

Flag: `apps/live_control_server/integrations/dungeonmind_kernel/config.py`  
Only exact value `1` enables. Default / typo / any other value → disabled.  
Disable restores the pre-shadow path (one flag check, no graph read, no log).

---

## What shipped

| Path | Role |
|------|------|
| `integrations/dungeonmind_kernel/config.py` | Enable flag |
| `integrations/dungeonmind_kernel/threat_hydration_shadow.py` | Shadow runner + replay resolver + observation |
| `integrations/dungeonmind_kernel/world_object_conformance_bridge.py` | Private `_load_exact_buddy_revision_bridge_source` (one integrity load) |
| `routes/threat_query_hydration.py` | Post-response `BackgroundTasks` schedule |
| `tests/test_dungeonmind_threat_hydration_shadow.py` | Proof matrix A–N + digest + invariance |

No response-schema changes. No `_hydrate_binding` changes. No provider client changes. No graph/statblock writes.

---

## Provider isolation proof

From `test_authority_provider_call_count_unchanged_when_shadow_runs`:

```text
shadow disabled authority provider calls = 1
shadow enabled  authority provider calls = 1  (same MagicMock after shadow)
shadow provider HTTP client construction = 0
DungeonMindStatblockV1Client never constructed by shadow
```

Route body equality (`test_product_output_invariant_enabled_vs_disabled`):

```text
shadow disabled JSON == shadow enabled JSON
```

Error paths (404/422/500/503) do not schedule shadow.

---

## Digest proof (real checked-in fixture)

Fixture: `tests/fixtures/statblocks/v1/exact-revision-response.json`

```text
Buddy definition_digest =
  sha256:935dc0dff1ac7cc8405836764469761a1d26e9e38dd74cd856b8a8a31f0fae51
bare DungeonMind payload digest =
  935dc0dff1ac7cc8405836764469761a1d26e9e38dd74cd856b8a8a31f0fae51
canonical_sha256(json.loads(canonical_definition)) =
  935dc0dff1ac7cc8405836764469761a1d26e9e38dd74cd856b8a8a31f0fae51
PASS
```

`DndMechanicsResourceEnvelope` validates from that payload. No second digest field. No re-normalization.

---

## Multiplicity / matrix verdicts

| Case | Verdict |
|------|---------|
| A one available binding | `full_match` |
| B zero bindings | `structural_match` (`authority_no_binding`) |
| C primary+alternate same resource | `full_match` (2 attachments, 1 generic binding) |
| D phases `bloodied` / `enraged` | `full_match` |
| E `" enraged "`, `""`, `" night raid "` | `full_match` (byte-exact) |
| F `include_mechanics=false` | `structural_match` (`authority_mechanics_not_requested`) |
| G unavailable | `inconclusive` (never `full_match`) |
| H exact revision missing | `inconclusive` |
| I integrity failure | `inconclusive` (no false match) |
| J Buddy available + DM rejects | `mismatch` |
| K `kind=npc` compatibility hit | `not_eligible` |
| L pinned R1 vs newer head R2 | shadows R1 only |
| M several Threats | one exact graph load; independent observations |
| N shadow crash | `shadow_error`; runner does not re-raise |

---

## Coverage (this PR)

Synthetic matrix only. No live dogfood run in this environment.

```text
explicit Threats full_match — proven in tests A/C/D/E/L/M
explicit Threats structural_match — B/F
inconclusive — G/H/I
mismatch — J
not_eligible — K
shadow_error — N
```

---

## Real-domain gate

```text
REAL-DOMAIN PROMOTION GATE: NOT YET PROVEN
```

Reason: this environment has no operator dogfood of an explicit durable Buddy `kind=threat` with an accepted `uses_statblock` binding and authority `hydration_status=available` producing a live `full_match` shadow log. Synthetic matrix is green; live campaign evidence is still required before authority promotion (§26).

---

## Remains false

```text
DungeonMind is not yet Buddy runtime mechanics authority
Buddy _hydrate_binding still determines the product result
Buddy direct statblock client is still authoritative
shadow result cannot alter HTTP output
shadow performs no provider HTTP calls
no DungeonMind graph persistence exists
no Buddy graph migration exists
no old Buddy graph kernel is deleted
NPC mechanics cutover is not implemented
PC mechanics cutover is not implemented
Play remains downstream of KERNEL-0
```

---

## Successor (gated)

```text
STATBLOCK: promote DungeonMind Threat hydration authority behind the existing Buddy API
```

Dispatch only after §26 contract suite + failure safety + runtime isolation + real-domain `full_match` are all true.
