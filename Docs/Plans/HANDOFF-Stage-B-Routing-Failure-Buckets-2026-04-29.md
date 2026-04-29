# Handoff — Stage B sentence routing failure buckets (Session 20 PC scenario)

**Audience:** Agent implementing prompt or gold changes  
**Scope:** `scenario_c2_session20_pc` hub routing (`route_sentence_units_to_hubs`)  
**Gold file:** `evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc.json`  
**Prompt:** `evals/sentence_routing_retrieval_falsification/routing_prompt.py`

---

## Evidence baseline

Benchmark sidecar (live LLM run, **FAIL**):

`evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-29/sentence_routing_stage_b_hub_routes--sentence_routing_c2_session20_pc--FAIL--20260429T032359279641Z.json`

- `**routing_prompt_base_id` / `routing_prompt_id`:** `71a8dd86e427e3fabf642d10`
- `**wire_strict_parse_ok`:** `true`
- `**scenario_estimated_cost_usd`:** `0.038249`

Telemetry snapshot:

- `gold_gate_checks_pass` / `gold_gate_checks_total`: **67 / 74**
- `must_route`: **43 / 50**
- `must_abstain`: **24 / 24**
- `violation_failure_buckets`: `b1_missing_expected_hub` **5**, `b1_over_route` **2**, `b2_over_assigned` **0**

Exact violation strings from that sidecar:

```text
B1: must_route unit 'u-L0016-06': over-route: len(assigned_hubs)=6 > len(expected_hubs)+max_extra_hubs=1
B1: must_route unit 'u-L0018-02': missing expected hubs ['bonogo'] (assigned=[])
B1: must_route unit 'u-L0018-08': missing expected hubs ['bonogo'] (assigned=[])
B1: must_route unit 'u-L0026-06': missing expected hubs ['bonogo'] (assigned=['caelynn', 'ephanna'])
B1: must_route unit 'u-L0028-09': over-route: len(assigned_hubs)=6 > len(expected_hubs)+max_extra_hubs=2
B1: must_route unit 'u-L0030-03': missing expected hubs ['baergrom', 'bonogo', 'caelynn', 'ephanna', 'karsemine', 'stafl'] (assigned=[])
B1: must_route unit 'u-L0030-05': missing expected hubs ['caelynn'] (assigned=[])
```

**Citation convention:** Every quoted sentence below is **verbatim** from `sentence_units[].text` in the benchmark sidecar JSON above (not hand-copied from corpus markdown).

---

## Bucket A — Topic-of-question PC dropped (subset completeness)

**Dominant anchor:** `u-L0026-06`

### Sentence unit (complete)

**Unit:** `u-L0026-06` — recap line 26 (single-line slice)

> Marla approaches Caelynn and asks her how she should deal with Bonogo, but Ephanna quickly intervenes, letting her, and the town, know that the Questionable Company is leaving town to continue their journey.

### Model output (summary)

- **Assigned:** `caelynn`, `ephanna`
- **Missing vs gold:** `bonogo`

### Gold expectation

Match `line_start` **26**, `index_on_line` **6**:

```371:381:evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc.json
      {
        "match": {
          "line_start": 26,
          "index_on_line": 6
        },
        "expected_hubs": [
          "caelynn",
          "bonogo",
          "ephanna"
        ],
        "max_extra_hubs": 0
      },
```

### Failure shape

Bonogo is not the grammatical actor; he is the **named topic** of Marla’s question (“deal with Bonogo”). The model keeps obvious actors/addressees but drops the PC who is the **object of the decision**.

---

## Bucket B — Scene-owner continuity vs grammatical NPC focal (Bonogo thread)

### `u-L0018-02`

**Unit:** `u-L0018-02` — recap line 18

> According to Stuart this is where they will find Stacey.

### Model output (summary)

- **Assigned:** `[]`, `routing_diagnostic_bucket`: `npc_placeholder`

### Gold expectation

Match `line_start` **18**, `index_on_line` **2**:

```158:167:evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc.json
      {
        "match": {
          "line_start": 18,
          "index_on_line": 2
        },
        "expected_hubs": [
          "bonogo"
        ],
        "max_extra_hubs": 0
      },
```

### Failure shape

Reported speech centers Stuart/Stacey; gold still treats the unit as **Bonogo’s guided-search continuity**.

---

### `u-L0018-08`

**Unit:** `u-L0018-08` — recap line 18

> He sticks his hand out and demands his gold back, convinced that she is the one that stole it.

### Model output (summary)

- **Assigned:** `[]`, `routing_diagnostic_bucket`: `npc_placeholder` (model reads “He” as Stuart)

### Gold expectation

Match `line_start` **18**, `index_on_line` **8**:

```178:187:evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc.json
      {
        "match": {
          "line_start": 18,
          "index_on_line": 8
        },
        "expected_hubs": [
          "bonogo"
        ],
        "max_extra_hubs": 0
      },
```

### Failure shape

Surface grammar favors the child NPC; gold expects **Bonogo alley / confrontation scene** routing anyway.

---

## Bucket C — Whole-party under-spread (roster-copy miss)

### `u-L0030-03`

**Unit:** `u-L0030-03` — recap line 30

> Thirty minutes later they come across an unusual sight: a wagon partly unloaded and horses wandering around a stack of crates.

### Model output (summary)

- **Assigned:** `[]`, `routing_diagnostic_bucket`: `event_or_object_placeholder`

### Gold expectation

Match `line_start` **30**, `index_on_line` **3**:

```489:502:evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc.json
      {
        "match": {
          "line_start": 30,
          "index_on_line": 3
        },
        "expected_hubs": [
          "baergrom",
          "bonogo",
          "caelynn",
          "ephanna",
          "karsemine",
          "stafl"
        ],
        "max_extra_hubs": 0
      },
```

### Failure shape

Model treats the unit as **pure scenery**; gold treats it as **party travel discovery** immediately after group departure (`u-L0030-02`).

---

## Bucket D — Perceiver PC vs NPC focal (`lysandra`)

### Adjacent context (same recap line 30)

**Unit:** `u-L0030-04`

> Caelynn approaches the makeshift shelter and hears mumbling from inside.

### `u-L0030-05` (failing unit)

**Unit:** `u-L0030-05` — recap line 30

> She finds Lysandra drawing in the dirt.

### Model output (summary)

- **Assigned:** `[]`, `routing_diagnostic_bucket`: `npc_placeholder` (centers Lysandra)

### Gold expectation

Match `line_start` **30**, `index_on_line` **5**:

```514:522:evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc.json
      {
        "match": {
          "line_start": 30,
          "index_on_line": 5
        },
        "expected_hubs": [
          "caelynn"
        ],
        "max_extra_hubs": 0
      },
```

### Failure shape

Gold wants **Caelynn** as perceiver/finder; model routes only to **NPC placeholder** for Lysandra.

---

## Bucket E — Continuity emphasis causing full-roster over-expansion

These are `**b1_over_route`** failures: model assigns **six** manifest PCs where gold caps hubs tighter.

### `u-L0016-06`

**Unit:** `u-L0016-06` — recap line 16

> As Thrin and Caelynn move back the swarm finally gives up and heads back into the forest.

### Gold expectation

Match `line_start` **16**, `index_on_line` **6** — **only** `caelynn`, plus diagnostic expectation:

```121:131:evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc.json
      {
        "match": {
          "line_start": 16,
          "index_on_line": 6
        },
        "expected_hubs": [
          "caelynn"
        ],
        "expected_routing_diagnostic_bucket": "npc_placeholder",
        "notes": "PC-only manifest: Thrin is focal alongside Caelynn but has no hub — npc_placeholder alongside caelynn.",
        "max_extra_hubs": 0
      },
```

### Model output (summary)

- **Assigned:** all six PCs (`baergrom`, `bonogo`, `caelynn`, `ephanna`, `karsemine`, `stafl`)

### Failure shape

Strong continuity / “group resolution” interpretation expands to **full roster**; gold wants **narrow PC + npc_placeholder**.

---

### `u-L0028-09`

**Unit:** `u-L0028-09` — recap line 28

> Caelynn tells her to stop where she is and make a camp and rest, Karesmine will lead the team to her.

### Gold expectation

Match `line_start` **28**, `index_on_line` **9**:

```453:462:evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc.json
      {
        "match": {
          "line_start": 28,
          "index_on_line": 9
        },
        "expected_hubs": [
          "caelynn",
          "karsemine"
        ],
        "max_extra_hubs": 0
      },
```

### Model output (summary)

- **Assigned:** all six PCs

### Failure shape

Model treats **“the team”** as **whole-band movement** and enumerates roster; gold expects **leader + Caelynn thread** only (`caelynn`, `karsemine`).

---

## Recommended next lever (for the implementing agent)

**Primary:** Add explicit prompt mechanics for **“named PC as topic/object of a question or handling decision”** so Bonogo cannot be dropped on `u-L0026-06`-shaped rows.

**Guard:** Pair that with an explicit **anti-expansion** rule so continuity language does not promote to **six-hub roster** when gold expects **one PC + diagnostic** (`u-L0016-06`) or **two PCs** (`u-L0028-09`).

**Falsification:** Re-run the same benchmark command; compare `gold_gate_checks_pass`, `b1_missing_expected_hub`, `b1_over_route`, `wire_strict_parse_ok`, and `scenario_estimated_cost_usd` against the baseline numbers in this document.