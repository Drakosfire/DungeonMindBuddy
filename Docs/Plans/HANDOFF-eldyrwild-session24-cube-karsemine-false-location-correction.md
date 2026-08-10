# HANDOFF — Eldyrwild Session-24 cube→Karsemine false-location correction

**Created:** 2026-08-10
**Status:** IMPLEMENTATION COMPLETE — awaiting review (canonical live apply is post-merge)
**Canonical handoff path:** `Docs/Plans/HANDOFF-eldyrwild-session24-cube-karsemine-false-location-correction.md`
**Conversation name:** `Eldyrwild Session 24 Cube-Karsemine False Location Correction`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**PR title:** `BUILD: contradict false cube-to-Karsemine location edge`
**Branch:** `build/eldyrwild-session24-cube-karsemine-false-location-correction`

**Required predecessor:** #544 merge
`4b4d4f42d5035d17cb7d158edece1d25dbc120a8`

## §0 Mission

Contradict the complete current support for the single false Session-24 cube→Karsemine `located_in` assertion through one sealed replayable GM correction, leaving source history and every unrelated assertion intact while adding no replacement truth.

## §1 BUILD capture (implementation base)

```text
origin/main / implementation base:
  4b4d4f42d5035d17cb7d158edece1d25dbc120a8
  (#544 merge ancestor: proven)

canonical world root:
  out/ (DUNGEONMIND_WORLD_GRAPH_ROOT)

P (canonical read-only at BUILD):
  rev:b90646fb5b135988bd7842cde858c96e
  (== R_current)

A(X) on P:
  contribution:fe483d91c47590a1
  (historical candidates include contribution:a01be11c6967afd9, superseded)

X:
  edge:item-001:located_in:pc:karsemine
  assertion:d27dd4e9041147bc

C (sealed):
  contribution:6c13bc0f8edf4377
  source-payload SHA256:
    b48de88cad19a21360c103d86edd3de17818249c72f6146daf7e04e076747e6d
  raw artifact SHA256:
    a06a12f75c0d1ca1e8659aa0ad5fbfa01214c6b3b7d8db6638d7706f634da159
  source_artifact_id:
    graph-native:eldyrwild-correction:session24-cube-karsemine-false-location-v1
  source_revision_id:
    correction:eldyrwild:session24-cube-karsemine-false-location-v1
```

## §2 Implementation surfaces

```text
Docs/Plans/HANDOFF-eldyrwild-session24-cube-karsemine-false-location-correction.md
apps/live_control_server/services/eldyrwild_session24_cube_karsemine_false_location_correction.py
graph_data/approved_graph_corrections/eldyrwild/session24-cube-karsemine-false-location-v1.json
scripts/apply_eldyrwild_session24_cube_karsemine_false_location_correction.py
tests/test_eldyrwild_session24_cube_karsemine_false_location_correction.py
```

Kernel paths unchanged. No canonical World Graph mutation in this PR.

## §3 Operator seam

```bash
# read-only
uv run python scripts/apply_eldyrwild_session24_cube_karsemine_false_location_correction.py status

# post-merge only — requires --allow-live-world
uv run python scripts/apply_eldyrwild_session24_cube_karsemine_false_location_correction.py apply \
  --expected-parent-revision-id <P> \
  --allow-live-world
```

Delegates to `kernel.contradict_edge_assertion_support`.

## §4 Expected parent-relative effective delta

```text
semantic     -1
represented   0
residual     -1
mechanics     0
```

Formal fixture re-anchor is a separate post-merge successor after canonical Q exists.

## §5 Canonical fence

Pre-merge: status/clone only. No `--allow-live-world` apply against canonical Eldyrwild.

Post-merge DONE requires the explicit operator live-exit procedure in the design contract.
