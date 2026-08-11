# HANDOFF — Eldyrwild Session-24 Lysandra→Caelynn false `leads` correction

**Created:** 2026-08-10
**Status:** DONE — canonical P→Q₃ live exit proven (`P=rev:b8dfc063…` → `Q₃=rev:ba3abde1…`; delta `-1/0/-1/0`)
**Canonical handoff path:** `Docs/Plans/HANDOFF-eldyrwild-session24-lysandra-caelynn-false-leads-correction.md`
**Conversation name:** `DUNGEONMIND-CUTOVER`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**PR title:** `BUILD: contradict false Lysandra→Caelynn leads edge`
**Branch:** `build/eldyrwild-session24-lysandra-caelynn-false-leads-correction`
**Merge:** `#550` / `425333d03cd23007ed2ab7fe0392c45a3c7c9412`

**Required predecessor:** PR #549 merge
`bd1e4922a8b6f901d1671c04fdd2ceaa0f9b336f`

## §0 Mission

Contradict the complete current support for the single false Session-24 Lysandra→Caelynn `leads` assertion through one sealed replayable GM correction (`contradicts`, no replacement), leaving source history, C₁/C₂ authorities, and every unrelated assertion intact.

## §1 BUILD capture (implementation base)

```text
origin/main / implementation base:
  bd1e4922a8b6f901d1671c04fdd2ceaa0f9b336f
  (#549 merge ancestor: proven)

canonical world root:
  out/ (DUNGEONMIND_WORLD_GRAPH_ROOT)

P (canonical read-only at BUILD):
  rev:b8dfc063bc13a4fb297e83f5f9b313d9
  (== R_current after #549)
  payload SHA256:
    4539afb0e25ccca42f4a2ec479ab470f7c14cf31803f6caa581e0d03a1f0c776

E(P):
  368 / 311 / 57 / 3

A(X) on P:
  contribution:fe483d91c47590a1
  (historical candidates include contribution:a01be11c6967afd9, superseded)

X:
  edge:npc_lysandra:leads:pc:caelynn
  assertion:fed9280859610fd0

C₁ on P:
  already_applied
  contribution:4c65f668dc95ef4f

C₂ on P:
  already_applied
  contribution:6c13bc0f8edf4377

C₃ (sealed):
  contribution:222c55dadacfa67f
  correction digest:
    c053c3c640bdc56f5e46ba8772ba59ca30aef8e6471d3e949a1e8d469feb088b
  source-payload SHA256:
    96a874b4d1b29274f38b616318379ebae9c8af62729ba7f053005c1b13dc05e1
  raw artifact SHA256:
    2c2c8a6809e3909ece077d4453e4ed6c501ef8339e85c4ae02cba187530d7aae
  source_artifact_id:
    graph-native:eldyrwild-correction:session24-lysandra-caelynn-false-leads-v1
  source_revision_id:
    correction:eldyrwild:session24-lysandra-caelynn-false-leads-v1
```

## §2 Implementation surfaces

```text
Docs/Plans/HANDOFF-eldyrwild-session24-lysandra-caelynn-false-leads-correction.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
apps/live_control_server/services/eldyrwild_session24_lysandra_caelynn_false_leads_correction.py
graph_data/approved_graph_corrections/eldyrwild/session24-lysandra-caelynn-false-leads-v1.json
scripts/apply_eldyrwild_session24_lysandra_caelynn_false_leads_correction.py
tests/test_eldyrwild_session24_lysandra_caelynn_false_leads_correction.py
```

Kernel paths unchanged. Effective-conformance fixture remains anchored to P until the third re-anchor. Canonical World Graph mutation is post-merge only.

## §3 Operator seam

```bash
# read-only
uv run python scripts/apply_eldyrwild_session24_lysandra_caelynn_false_leads_correction.py \
  status \
  --expected-parent-revision-id rev:b8dfc063bc13a4fb297e83f5f9b313d9

# post-merge only — requires --allow-live-world
uv run python scripts/apply_eldyrwild_session24_lysandra_caelynn_false_leads_correction.py \
  apply \
  --expected-parent-revision-id rev:b8dfc063bc13a4fb297e83f5f9b313d9 \
  --allow-live-world
```

Delegates to `kernel.contradict_edge_assertion_support`.

## §4 Expected parent-relative effective delta

```text
semantic      -1
represented    0
residual      -1
mechanics      0

E(P)  = 368 / 311 / 57 / 3
E(Q₃) = 367 / 311 / 56 / 3   (when P is unchanged)
```

## §5 Post-merge DONE gate

Merged package alone is not DONE. Operator must perform the canonical live exit on exact P, prove `parent(Q₃)==P`, C₁/C₂ intact, sibling support preserved, delta `-1/0/-1/0`, retry `already_applied`, and pinned/unpinned replay equivalence before marking this slice DONE.

## §6 Canonical live exit (DONE)

```text
merge #550:
  425333d03cd23007ed2ab7fe0392c45a3c7c9412

P:
  rev:b8dfc063bc13a4fb297e83f5f9b313d9
  E(P): 368 / 311 / 57 / 3
  payload SHA256:
    4539afb0e25ccca42f4a2ec479ab470f7c14cf31803f6caa581e0d03a1f0c776

Q₃:
  rev:ba3abde1bfc3659795bcd77bb55eb9f7
  parent(Q₃) == P
  E(Q₃): 367 / 311 / 56 / 3
  payload SHA256:
    8aa2b90bd6d16fce4b034417e72b5e613deb0ec3baf029aeea5a426ffed7a7b4

delta:
  semantic     -1
  represented   0
  residual     -1
  mechanics     0

X:
  edge:npc_lysandra:leads:pc:caelynn
  assertion:fed9280859610fd0
  durable, contradicted, active support empty
  target supporter moved to contradicted lineage

C₃:
  contribution:222c55dadacfa67f
  revision-bound active (digest + replay manifest + ledger + index)

C₁ / C₂:
  unchanged / already_applied

post-apply status: already_applied
exact retry on Q₃: published=false (noop)
stale P retry: stale_expected_parent
pinned + unpinned rebuild: equivalent
siblings unchanged
source contribution:fe483d91c47590a1 remains active
```

Successor after proven Q₃:

```text
eldyrwild-effective-conformance-after-third-correction
```
