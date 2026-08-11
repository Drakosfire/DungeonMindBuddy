# HANDOFF — Eldyrwild Session-25 Ephanna→Thrin false `hires` correction

**Created:** 2026-08-11
**Updated:** 2026-08-11 — BUILD in progress; Q₃ capture complete
**Status:** BUILD DOING — bounded C₄ source correction
**Canonical handoff path:** `Docs/Plans/HANDOFF-eldyrwild-session25-ephanna-thrin-false-hires-correction.md`
**Conversation name:** `DUNGEONMIND-CUTOVER`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**PR title:** `BUILD: contradict false Ephanna→Thrin hires edge`
**Branch:** `build/eldyrwild-session25-ephanna-thrin-false-hires-correction`

**Required predecessors:**

* PR #554 third effective re-anchor — DONE
* PR #557 Session-25 descendant residual adjudication — merged:
  `e88ac88bd511452e354ac0d804731475b8527e71`
* Canonical World Graph and formal effective baseline remain exact Q₃ before this correction.

---

## §0 Mission

Contradict the complete **current support** for one false Session-25 assertion:

```text
Ephanna --hires--> Thrin
```

through one sealed, replayable GM-authored `contradicts` correction with **no replacement assertion**.

### One-sentence invariant

> On exact Q₃, contradict exactly the current assertion support that makes `Ephanna --hires--> Thrin` current, publish no replacement semantics, leave the Session-25 contribution and every sibling assertion intact, and produce exactly one child revision whose effective relationship delta is `-1 / 0 / -1 / 0`.

---

## §4 BUILD dispatch gate — CAPTURED

Proven on canonical Eldyrwild without mutation:

```text
HEAD == rev:ba3abde1bfc3659795bcd77bb55eb9f7
payload == 8aa2b90bd6d16fce4b034417e72b5e613deb0ec3baf029aeea5a426ffed7a7b4
effective == 367 / 311 / 56 / 3
UNADJUDICATED == 0
#557 merge ancestor == e88ac88bd511452e354ac0d804731475b8527e71
```

### Exact target X₄

```text
TARGET_EDGE_ID:
  edge:pc:ephanna:hires:node:thrin-branchborn

TARGET_ASSERTION_ID:   # BUILD CAPTURE FROM EXACT Q₃
  assertion:9b68a1cbcbd9015b

active_contribution_ids ==
  { contribution:a4231edb9a228963 }

composed authority row:
  authority_id = eldyrwild-session25-descendant
  anchor_revision_id = rev:df92031efcd379b9c52e0df2e3ff7217
  requested_revision_id = rev:ba3abde1bfc3659795bcd77bb55eb9f7
  continuity_state = CARRIED_FORWARD
  disposition = SOURCE_CORRECTION_REQUIRED
  reason_code = PREDICATE_MISAPPLIED
```

X₄ is **not** in historical `ELDYRWILD_RESIDUAL_FINDINGS`.

---

## §6 C₄ approved correction artifact — SEALED

```text
path:
  graph_data/approved_graph_corrections/eldyrwild/
    session25-ephanna-thrin-false-hires-v1.json

C4_CORRECTION_CONTRIBUTION_ID:
  contribution:d044a019d814968e

C4_CORRECTION_DIGEST:
  ead72c9b2a702ab3098a94c1a7cb7f271b7ce4cce0482a256894d4b332d80d2d

C4_SOURCE_PAYLOAD_SHA256:
  b9f0c283316057e859a00ae7374dd061260a5d21f8f00538ede3335e5a55a53c

C4_RAW_ARTIFACT_SHA256:
  d4e679582a6764a1d846944a761eb697130fd54c63ead705cdf80e0c447f4e3d

assertion_corrections:
  - correction_kind: contradicts
    target_contribution_id: contribution:a4231edb9a228963
    target_assertion_id: assertion:9b68a1cbcbd9015b
    replacement_assertion_id: null
```

Factory-authored via `kernel.create_edge_assertion_contradiction_contribution`.

---

## §10 Expected parent-relative semantic delta

```text
E(Q₃): 367 / 311 / 56 / 3
E(Q₄): 366 / 311 / 55 / 3
delta: -1 / 0 / -1 / 0

SOURCE_CORRECTION_REQUIRED: 37 → 36
remaining(Q₄) == remaining(Q₃) - {X₄}
```

Clone smoke (pre-test suite): published `rev:3759d8d6a02f09306397918234a2ded2` with exact delta and retry `already_applied`.

---

## §15 Paths

```text
A Docs/Plans/HANDOFF-eldyrwild-session25-ephanna-thrin-false-hires-correction.md
A graph_data/approved_graph_corrections/eldyrwild/session25-ephanna-thrin-false-hires-v1.json
A apps/live_control_server/services/eldyrwild_session25_ephanna_thrin_false_hires_correction.py
A scripts/apply_eldyrwild_session25_ephanna_thrin_false_hires_correction.py
A tests/test_eldyrwild_session25_ephanna_thrin_false_hires_correction.py
M Docs/Plans/PR-TRACKER-campaign-supergraph.md
M Docs/Design/STATUS-world-graph-continuity-spine.md
```

---

## §20 Post-merge canonical live gate

After merge:

```bash
uv run python scripts/apply_eldyrwild_session25_ephanna_thrin_false_hires_correction.py \
  status --expected-parent-revision-id rev:ba3abde1bfc3659795bcd77bb55eb9f7

uv run python scripts/apply_eldyrwild_session25_ephanna_thrin_false_hires_correction.py \
  apply --expected-parent-revision-id rev:ba3abde1bfc3659795bcd77bb55eb9f7 \
  --allow-live-world
```

Capture actual Q₄; only then mark DONE. Successor: `eldyrwild-effective-conformance-after-fourth-correction`.

---

## §22 BUILD handback

```text
implementation base SHA: e88ac88bd511452e354ac0d804731475b8527e71
final PR head SHA: <pending>

TARGET_ASSERTION_ID: assertion:9b68a1cbcbd9015b

C4 correction contribution ID: contribution:d044a019d814968e
C4 correction digest: ead72c9b2a702ab3098a94c1a7cb7f271b7ce4cce0482a256894d4b332d80d2d
C4 source-payload SHA256: b9f0c283316057e859a00ae7374dd061260a5d21f8f00538ede3335e5a55a53c
C4 raw artifact SHA256: d4e679582a6764a1d846944a761eb697130fd54c63ead705cdf80e0c447f4e3d

locked active target supporters:
  contribution:a4231edb9a228963

source seal verified: yes
clone parent: Q₃
clone child (smoke): rev:3759d8d6a02f09306397918234a2ded2
clone effective: 366 / 311 / 55 / 3
exact delta: -1 / 0 / -1 / 0

focused tests: <pending>
cumulative tests: <pending>
```
