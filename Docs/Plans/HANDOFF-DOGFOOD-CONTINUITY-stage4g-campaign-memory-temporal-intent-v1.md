# HANDOFF — DOGFOOD-CONTINUITY: Stage 4G campaign-memory temporal intent

**Created:** 2026-09-12  
**Status:** DONE — PR #709 MERGED
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4g-campaign-memory-temporal-intent-v1.md`  
**Conversation/workstream:** `C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program`  
**Flow / owner:** `DOGFOOD-CONTINUITY` / campaign-memory temporal requirements  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `444b39963286667400c827b8765f8246763b8701` (main after PR #708 merge)  
**Branch:** `dogfood-continuity/stage4g-temporal-intent-overlay-impl`
**Accepted head:** `236ea6c5d1486ccf7012ed6b1ea8f33f4b3af457`
**Merge revision:** `0aa77bf791efa00cb51f45f3c7acd273ac3f351f`
**Formal review cycles:** `2`
**PR title:** `DOGFOOD-CONTINUITY: define campaign-memory temporal intent`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). Benchmark philosophy: [`Docs/Design/DESIGN-benchmark-philosophy-and-goals.md`](../Design/DESIGN-benchmark-philosophy-and-goals.md). Benchmark predecessor: [`HANDOFF-DOGFOOD-CONTINUITY-stage4f-campaign-memory-development-benchmark-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-stage4f-campaign-memory-development-benchmark-v1.md).

---

## §0 Where the program is now

The measurement and benchmark foundation now exists:

```text
P0a    trustworthy cross-contract comparison              DONE — PR #705
P0b1   one bounded isolated baseline/candidate pair       DONE — PR #706
P0b2a  repeated-pair qualification + variance summary     DONE — PR #707
P1a    campaign-memory entity/fact development benchmark  DONE — PR #708
P1a.1  temporal requirements overlay                      DONE — PR #709
P1b    unchanged-pipeline baseline characterization       current / Stage 4H
P2     bounded extraction or scorer/representation change later / evidence-selected
P3     frozen validation                                  later
P4     full-corpus rehearsal into disposable authorities later
P5     governed durable publication                       later
```

PR #708 merged at `444b39963286667400c827b8765f8246763b8701`, accepted head `8da461e21b69291d9f61b1d7309cb883a9dc06e5`, after 2 formal review cycles.

Its frozen benchmark authority is:

```text
benchmark_id:
  c2-mireward-campaign-memory-dev-v1

surface:
  campaign_memory_development

source cohort:
  7 exact pinned sources

entity anchors:
  6

fact anchors:
  5

identity expectations:
  2

corpus fingerprint:
  925ad24a54d888e2f1d3673919d126767b39cdeaf885c07057bfb5da346ba8c1

gold fingerprint:
  de072c175cc00a1dc7ed672cdaca317ee0f8cb381a8186e9cfc53a5885a4cd23
```

Stage 4 remains **HOLD**. No extraction improvement, identity coalescence, temporal reasoning, APP-STATE publication, or DungeonMind temporal representation has been accepted.

### Why another benchmark slice before P1b

The Stage 4F benchmark can now ask:

> Did ingestion recover the important entity and important fact?

It cannot yet express the different temporal meanings carried by those facts.

Examples from the same seven-source cohort:

```text
Brin is a cook from Edge.
  → durable background; S23 is evidence, not necessarily the beginning of the truth.

Orric/Orik is mayor of Mireward.
  → persistent state/role observed in S23 and again in S25; the evidence does not say he became mayor in S23.

Brin led the refugees to Mireward.
  → historical event in S23; it remains true history after the refugees move elsewhere.

Karsemine learned a tripod weakness to fire.
  → knowledge-acquisition event in S23 whose useful knowledge should persist afterward.

Mireward is under active siege pressure.
  → operational state observed across sessions; not an evergreen property of the town.

The North Gate battle is active, then ends.
  → bounded episode spanning S23–S24; ending this local battle must not erase broader siege pressure.
```

Those distinctions are useful **before DungeonMind is ready to ingest them**. They are requirements for the future temporal representation, not a demand to implement that representation now.

---

## §1 Core design decision — evidence time is not truth time

This slice must preserve one rule above all others:

> **The session in which evidence is recorded is not automatically the session in which the underlying truth began.**

If Session 23 says `As mayor, Orik Tane ...`, that means the mayor role is supported by S23 evidence. It does **not** mean Orik became mayor in Session 23.

By contrast, when Session 23 says Karsemine used Hunter's Mark and discovered the creatures were weak to fire, the source directly establishes a knowledge-acquisition event in Session 23.

Therefore the temporal-intent artifact separates:

1. **evidence time** — which pinned source/session supports the expectation;
2. **truth window** — only populated when the source directly gives us enough information to say when the event/state begins or ends;
3. **persistence intent** — the human requirement for how the remembered truth should behave after observation.

A missing truth-window boundary means **unknown**, not `session 0`, not `forever`, and not `the first session where we saw it`.

---

## §2 Mission and merge-ready invariant

**Mission:** Add one strict, model-free temporal-intent overlay to the frozen Stage 4F campaign-memory benchmark so future ingestion/scoring/DungeonMind designs can be evaluated against real examples of background, event history, persistent state, knowledge acquisition, and bounded episodes without requiring DungeonMind or changing current Extraction Lab scoring.

**Merge-ready invariant:** One sidecar artifact is pinned to the exact Stage 4F benchmark ID, corpus fingerprint, and gold fingerprint; it contains exactly seven human-authored temporal expectations grounded by exact markers in the existing seven-source cohort; it cleanly separates evidence session from truth-window claims; all subject/fact/identity references resolve against Stage 4F authority; and a deterministic validator proves structural coherence without calling a model, loading a FactStore, or mutating benchmark, ingestion, APP-STATE, World, or DungeonMind state.

### Why this is one capability

The independently useful capability is:

> **A small executable requirements corpus now says what temporal distinctions a future campaign-memory implementation must be able to explain.**

The JSON expectations and their model-free validator are one authority. Scoring those expectations, changing extraction to satisfy them, and teaching DungeonMind to represent them are separate successor capabilities.

---

## §3 Explicit non-goal — do not design the DungeonMind time ontology

This PR is **not** permission to create a comprehensive temporal graph schema.

The vocabulary in this handoff is benchmark vocabulary only. It exists to describe seven real examples. A future DungeonMind design may reuse, rename, combine, or reject these labels if it can still faithfully represent the underlying human requirements.

Do not add speculative concepts merely because a temporal system might someday need them.

No interval algebra, calendars, world-clock service, temporal query language, bitemporal database model, event sourcing rewrite, causal graph, or generic timeline engine belongs in this slice.

The test is:

> Can we describe the temporal meaning already present in the Mireward examples without pretending we have implemented the temporal engine?

---

## §4 Temporal intent sidecar contract

Create:

`evals/campaign_memory_development/temporal_expectations.json`

Top-level semantic shape:

```json
{
  "schema": "dmb_campaign_memory_temporal_intent_v1",
  "benchmark_id": "c2-mireward-campaign-memory-dev-v1",
  "benchmark_corpus_fingerprint": "925ad24a54d888e2f1d3673919d126767b39cdeaf885c07057bfb5da346ba8c1",
  "benchmark_gold_fingerprint": "de072c175cc00a1dc7ed672cdaca317ee0f8cb381a8186e9cfc53a5885a4cd23",
  "expectations": [
    {
      "expectation_id": "...",
      "subject_anchor": "...",
      "fact_anchor": "... or null",
      "identity_expectation_refs": [],
      "temporal_kind": "background | event | state | knowledge_acquisition",
      "persistence": "historical | enduring | until_changed | bounded",
      "truth_window": {
        "start_session": null,
        "end_session": null
      },
      "evidence": [
        {
          "source_file": "... exact Stage 4F cohort locator ...",
          "source_session": 23,
          "source_text_marker": "... exact marker ...",
          "role": "supports | confirms | starts | ends"
        }
      ],
      "intent": "human-readable temporal requirement"
    }
  ]
}
```

All fields are strict; unknown fields fail closed.

### Benchmark pinning

The sidecar does not redefine corpus or gold identity.

The validator must call the existing Stage 4F benchmark validator and require exact equality for:

```text
benchmark_id
benchmark_corpus_fingerprint
benchmark_gold_fingerprint
```

If the Stage 4F benchmark changes, this overlay becomes invalid until deliberately reviewed and re-pinned.

### Temporal kinds

These labels are requirement vocabulary, not production ontology:

```text
background
  A durable descriptive fact whose beginning is not established by the evidence.
  Example: Brin is a cook from Edge.

event
  Something that happened at a particular point/episode and remains historical truth afterward.
  Example: Brin arrived at Mireward with the refugee group in S23.

state
  A condition/role that may remain true until evidence changes or explicitly ends it.
  Example: Orric is mayor; Mireward is under siege pressure.

knowledge_acquisition
  A moment when a character/party learns something whose usefulness persists afterward.
  Example: Karsemine learns the tripod creatures are weak to fire.
```

### Persistence labels

Again, benchmark vocabulary only:

```text
historical
  The occurrence remains part of history; it is not a current-state assertion.

enduring
  Human intent says the knowledge/background should remain available afterward unless contradicted.

until_changed
  Treat as continuing campaign state/role after observation until later evidence changes it.

bounded
  The state has explicit ending evidence in the benchmark cohort.
```

### Truth-window semantics

`truth_window.start_session` and `truth_window.end_session` are optional truth claims.

Rules:

- `null` means unknown.
- Never fill a start merely because that is the first source where the fact appears.
- Never fill an end merely because the cohort stops.
- A non-point truth start requires evidence with `role = "starts"` in that session. Ordinary `supports`/`confirms` evidence cannot establish when a background/state began. A point event with `start_session = end_session` is the narrow exception because observing its occurrence establishes its session.
- An explicit end requires evidence with `role = "ends"` in that session.
- `persistence = "bounded"` requires a non-null `end_session`.
- If both boundaries are present, `end_session >= start_session`.
- A non-null boundary session must correspond to at least one evidence record from that session.

---

## §5 Exact seven temporal expectations

Implement **exactly these seven** expectations for v1. Do not expand the temporal vocabulary or add more cases in this slice without re-briefing.

### 1. `brin_cook_from_edge_background`

```text
subject_anchor:
  brin_holloway_session23

fact_anchor:
  brin_role

identity expectation refs:
  [brin_cross_source_identity]

temporal_kind:
  background

persistence:
  enduring

truth window:
  start unknown
  end unknown
```

Evidence:

```text
S23 recap
marker: "Brin Holloway, a cook from Edge"
role: supports
```

Intent:

> By S23 we know Brin is a cook from Edge. S23 is evidence for that background, not evidence that he became a cook or came from Edge during S23.

### 2. `brin_refugee_leader_state`

```text
subject_anchor:
  brin_holloway_session23

fact_anchor:
  brin_refugee_leadership

identity expectation refs:
  [brin_cross_source_identity]

temporal_kind:
  state

persistence:
  until_changed

truth window:
  start unknown
  end unknown
```

Evidence:

```text
S23 recap
marker: "A clear leader of the group steps forward, Brin Holloway"
role: supports

S25 recap
marker: "talking with the leader of the refugees, Brin"
role: confirms
```

Intent:

> Brin's refugee-leadership state is supported in S23 and still true in S25. Neither source proves when that leadership began.

### 3. `orric_mayor_state`

```text
subject_anchor:
  orik_tane_session23

fact_anchor:
  orik_mayor_role

identity expectation refs:
  [orric_orik_cross_source_identity]

temporal_kind:
  state

persistence:
  until_changed

truth window:
  start unknown
  end unknown
```

Evidence:

```text
S23 recap
marker: "As mayor, Orik Tane can easily command the room."
role: supports

S25 recap
marker: "they find the mayor, Orik"
role: confirms
```

Intent:

> Orik/Orric is the mayor in S23 and remains mayor in S25. Do not infer that the office began in S23. The temporal requirement depends on the existing Orik/Orric same-identity intent.

### 4. `brin_refugee_arrival_event`

```text
subject_anchor:
  brin_holloway_session23

fact_anchor:
  null

identity expectation refs:
  [brin_cross_source_identity]

temporal_kind:
  event

persistence:
  historical

truth window:
  start_session = 23
  end_session = 23
```

Evidence:

```text
S23 recap
marker: "A clear leader of the group steps forward, Brin Holloway"
role: supports
```

Intent:

> Brin's arrival with the survivor/refugee group is an S23 historical event. Later movement of the refugees must not overwrite the fact that this arrival happened.

This expectation intentionally has no current fact anchor. It is a requirements witness for a temporal fact the Stage 4F scorer does not yet express.

### 5. `karsemine_tripod_fire_weakness_knowledge`

```text
subject_anchor:
  karsemine_session23

fact_anchor:
  karsemine_fire_weakness_discovery

identity expectation refs:
  []

temporal_kind:
  knowledge_acquisition

persistence:
  enduring

truth window:
  start_session = 23
  end unknown
```

Evidence:

```text
S23 recap
marker: "the creatures are resistant to poison, but weak to fire"
role: starts
```

Intent:

> The acquisition occurs in S23. Afterward, the useful discovered knowledge should remain available as campaign memory; the temporal engine must not reduce it to a transient S23-only state.

### 6. `mireward_siege_pressure_state`

```text
subject_anchor:
  mireward_reach

fact_anchor:
  mireward_siege_pressure

identity expectation refs:
  []

temporal_kind:
  state

persistence:
  until_changed

truth window:
  start unknown
  end unknown
```

Evidence:

```text
S23 recap
marker: "shadows are coming from the Reach to the north gate"
role: supports

S25 recap
marker: "three new hybrid creatures wrapped around something and beginning to burrow into the ground"
role: confirms
```

Intent:

> Mireward is under continuing operational pressure across the played sequence. The benchmark does not claim when the broader threat began or ended, and it must never become an evergreen property of Mireward merely because a reference document describes the siege.

### 7. `mireward_north_gate_battle_state`

```text
subject_anchor:
  mireward_reach

fact_anchor:
  null

identity expectation refs:
  []

temporal_kind:
  state

persistence:
  bounded

truth window:
  start_session = 23
  end_session = 24
```

Evidence:

```text
S23 recap
marker: "shadows are coming from the Reach to the north gate"
role: starts

S24 recap
marker: "Finally Thrin finishes off the writhing creature, ending the battle."
role: ends
```

Intent:

> The North Gate battle is a bounded local episode that ends in S24. Its end must not erase the broader Mireward siege-pressure state, which remains supported by later S25 danger.

This expectation intentionally has no current fact anchor. It forces a future design to distinguish a local bounded episode from a broader continuing state.

---

## §6 Evidence-source rules

Every temporal evidence record must:

- reference one exact `source_file` already present in the Stage 4F seven-source cohort;
- use an exact non-empty `source_text_marker` found in the pinned source bytes;
- carry the correct source session for that pinned source;
- use `source_session = null` only for cohort reference sources whose frontmatter session is null;
- use one of `supports`, `confirms`, `starts`, or `ends`;
- not claim source provenance that current ingestion does not already provide.

For this v1 overlay, use played S23/S24/S25 evidence only for the seven required expectations. The stable reference files remain available through Stage 4F identity/fact intent but are not needed as temporal clock witnesses.

Hard-code or otherwise deterministically derive this exact source-session mapping for validation:

```text
Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate.md
  → 23

Longmont Campaign/Campaign 2/Session Recaps/Session 24 - Mireward Gate Battle.md
  → 24

Longmont Campaign/Campaign 2/Session Recaps/Session 25 - Mireward Gate Battle II.md
  → 25

all four non-recap sources in the Stage 4F cohort
  → null
```

Do not infer session numbers from filenames alone when validating an arbitrary source outside the frozen cohort; arbitrary sources are out of scope.

---

## §7 Validator contract

Create:

`extraction_lab/campaign_memory_temporal_intent.py`

Preferred CLI:

```bash
uv run python -m extraction_lab.campaign_memory_temporal_intent \
  --benchmark evals/campaign_memory_development/benchmark.json \
  --temporal-intent evals/campaign_memory_development/temporal_expectations.json
```

The command performs **zero model calls**, loads no FactStore, and writes no state.

### Required validation flow

1. Call `validate_campaign_memory_benchmark(...)` from Stage 4F first.
2. Require benchmark ID/corpus fingerprint/gold fingerprint to equal the pins in the temporal sidecar.
3. Load the Stage 4F benchmark's entity anchors, fact anchors, identity expectations, and source cohort.
4. Validate temporal expectations against those frozen authorities.
5. Validate exact source markers against the pinned corpus bytes.
6. Emit one normalized summary.

### Fail-closed validation

Reject at least:

```text
unknown top-level or nested field
wrong temporal schema
benchmark ID mismatch
benchmark corpus fingerprint mismatch
benchmark gold fingerprint mismatch
expectation count != 7
duplicate expectation ID
unknown subject anchor
unknown non-null fact anchor
fact anchor whose subject_anchor differs from expectation subject_anchor
unknown identity expectation ref
duplicate identity expectation ref
invalid temporal_kind
invalid persistence
source outside Stage 4F cohort
source-session mismatch
empty/missing source marker
source marker absent from pinned bytes
duplicate identical evidence row
end_session < start_session
truth boundary session with no evidence from that session
persistence=bounded without end_session
role=ends with no matching end_session
role=ends in a session different from end_session
more or fewer than the exact seven v1 expectation IDs
```

### Important non-validation

The validator must **not** inspect an ingestion store and must not pretend these expectations passed or failed against current extraction.

It validates human intent, not system performance.

### Temporal intent fingerprint

Return a `temporal_intent_fingerprint` computed from a canonical, path-independent serialization of the validated temporal sidecar.

Absolute checkout paths must not enter the fingerprint.

This fingerprint is additive requirement identity; it does not replace Stage 4F corpus/gold fingerprints.

### Normalized success summary

Print JSON containing at least:

```text
schema
benchmark_id
benchmark_corpus_fingerprint
benchmark_gold_fingerprint
temporal_intent_fingerprint
expectation_count = 7
linked_fact_expectation_count
requirement_only_expectation_count
evidence_ref_count
temporal_kind_counts
persistence_counts
validated = true
```

No quality score, winner, pass rate, or readiness claim belongs in this output.

---

## §8 Human review requirement

The PR handback must contain one compact witness table with:

```text
expectation_id
subject/fact anchor
kind
persistence
truth window
evidence session(s)
brief exact marker(s)
why the temporal distinction matters
```

The reviewer should explicitly inspect all seven source markers against the pinned corpus bytes.

The most important human checks are:

1. We did not turn “first observed in S23” into “became true in S23.”
2. We did not turn “historically happened” into “currently true.”
3. We did not turn “local battle ended” into “broader threat ended.”
4. We did not turn the temporal labels into an accidental DungeonMind production schema.

---

## §9 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/campaign_memory_development/temporal_expectations.json` | Seven grounded temporal requirements pinned to Stage 4F authority. |
| Create | `extraction_lab/campaign_memory_temporal_intent.py` | Strict model-free overlay validator + temporal intent fingerprint. |
| Create | `tests/extraction_lab/test_campaign_memory_temporal_intent.py` | Pinning, marker, session, truth-window, reference, and path-independence tests. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4f-campaign-memory-development-benchmark-v1.md` | Backward-looking #708 merge/PASS only. |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Record #708 merged/PASS and Stage 4G current. |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Record P1a benchmark complete and P1a.1 temporal intent active; Stage 4 remains NOT DONE. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4g-campaign-memory-temporal-intent-v1.md` | Implementation evidence/review handback. |

### Expected no-change paths

Do not modify:

```text
evals/campaign_memory_development/benchmark.json
evals/campaign_memory_development/gold/entity_anchors.json
evals/campaign_memory_development/gold/fact_anchors.json
extraction_lab/campaign_memory_benchmark.py
extraction_lab/anchor_schema.py
extraction_lab/anchor_resolver.py
extraction_lab/run_extraction_lab.py
extraction_lab/run_pair_experiment.py
extraction_lab/run_repeat_experiment.py
extraction_lab/compare_experiment_runs.py
tools/batch_ingest_corpus.py
MODEL_POLICY.json
src/ingestion/**
corpus/eldyrwild-markdown/**
apps/**
```

No DungeonMind service/schema/storage path is leased.

If implementation requires any production temporal representation, scorer behavior, anchor schema change, corpus change, or ingestion change, stop and re-brief.

---

## §10 Required deterministic evidence

At minimum prove:

```text
checked-in temporal intent + checked-in Stage 4F benchmark → PASS
same benchmark/intent copied to another checkout root → same temporal_intent_fingerprint
benchmark corpus fingerprint drift → fail
benchmark gold fingerprint drift → fail
unknown subject anchor → fail
unknown fact anchor → fail
fact/subject mismatch → fail
unknown identity expectation ref → fail
source outside cohort → fail
wrong source session → fail
missing marker → fail
absent marker → fail
duplicate expectation ID → fail
missing required v1 expectation → fail
extra eighth expectation → fail
end before start → fail
bounded persistence without end → fail
ends evidence without matching end session → fail
boundary session absent from evidence → fail
valid unknown-start persistent role → pass
valid S23 knowledge-acquisition start → pass
valid S23–S24 bounded battle → pass
```

### Commands

```bash
uv run pytest tests/extraction_lab/ -q

uv run ruff check \
  extraction_lab/campaign_memory_temporal_intent.py \
  tests/extraction_lab/test_campaign_memory_temporal_intent.py

uv run python -m extraction_lab.campaign_memory_temporal_intent \
  --benchmark evals/campaign_memory_development/benchmark.json \
  --temporal-intent evals/campaign_memory_development/temporal_expectations.json

git diff --check
git diff --name-only 444b39963286667400c827b8765f8246763b8701...HEAD
```

No paid/model evidence is required or allowed by this slice.

---

## §11 State-authority sync

Backward-looking sync in this implementation PR records only facts already true before Stage 4G implementation:

- PR #708 merged at `444b39963286667400c827b8765f8246763b8701`;
- accepted #708 head `8da461e21b69291d9f61b1d7309cb883a9dc06e5`;
- #708 required 2 formal review cycles;
- Stage 4F/P1a campaign-memory benchmark authority exists;
- benchmark corpus fingerprint is `925ad24a54d888e2f1d3673919d126767b39cdeaf885c07057bfb5da346ba8c1`;
- benchmark gold fingerprint is `de072c175cc00a1dc7ed672cdaca317ee0f8cb381a8186e9cfc53a5885a4cd23`;
- identity expectations exist but remain unscored;
- temporal intent is not yet represented/scored by DungeonMind or Extraction Lab;
- Stage 4 WOW remains HOLD;
- P1b baseline characterization, P2 tuning, and publication remain false.

Do **not** pre-mark Stage 4G complete or invent its future merge SHA/review count.

---

## §12 Immediate successor decision

After Stage 4G merges, the preferred next action is still **P1b: run the current unchanged extraction pipeline against the frozen seven-source Stage 4F benchmark**.

The baseline must report two different classes of evidence:

```text
SCORED NOW
  entity anchor recall
  fact anchor recall
  per-anchor failure buckets
  repeated-run stability if used
  entity/fact count and cost/runtime telemetry

EXPLICITLY UNSCORED REQUIREMENTS
  Stage 4F same-identity expectations
  Stage 4G temporal expectations
```

Do not turn unscored identity/temporal requirements into automatic zeroes or automatic passes.

After the baseline, choose the next capability from evidence:

- if entity/fact recovery is poor, the next slice may be an extraction ablation;
- if entity/fact recovery is strong but Orik/Orric/Brin identity is wrong, identity scoring/representation should precede tuning;
- if entity/fact recovery is strong but temporal semantics are flattened or contradictory, temporal scorer/representation work should precede tuning;
- if current store artifacts cannot even expose enough evidence to inspect those questions, that missing observability becomes the next slice.

The benchmark should decide whether the next change belongs to extraction, scoring, or DungeonMind—not the roadmap label alone.

---

## §12A Implementation handback — temporal witnesses

| Expectation | Subject / fact | Kind · persistence | Truth window | Evidence / brief exact marker | Why it matters |
|---|---|---|---|---|---|
| `brin_cook_from_edge_background` | Brin / `brin_role` | background · enduring | unknown → unknown | S23 “Brin Holloway, a cook from Edge” | Observation does not invent the start of Brin's background. |
| `brin_refugee_leader_state` | Brin / `brin_refugee_leadership` | state · until changed | unknown → unknown | S23 “A clear leader…”; S25 “leader of the refugees, Brin” | Later confirmation sustains the role without fabricating when it began. |
| `orric_mayor_state` | Orik / `orik_mayor_role` | state · until changed | unknown → unknown | S23 “As mayor, Orik Tane…”; S25 “the mayor, Orik” | Evidence time is not appointment time; identity intent links Orric/Orik. |
| `brin_refugee_arrival_event` | Brin / requirement-only | event · historical | S23 → S23 | S23 “A clear leader … Brin Holloway” | The arrival stays historical without becoming current location. |
| `karsemine_tripod_fire_weakness_knowledge` | Karsemine / fire weakness | knowledge acquisition · enduring | S23 → unknown | S23 “resistant to poison, but weak to fire” | The learning moment is known and its table value persists. |
| `mireward_siege_pressure_state` | Mireward / siege pressure | state · until changed | unknown → unknown | S23 “shadows … north gate”; S25 “three new hybrid creatures…” | Broad pressure remains open-ended rather than becoming evergreen. |
| `mireward_north_gate_battle_state` | Mireward / requirement-only | state · bounded | S23 → S24 | S23 north-gate shadows; S24 “ending the battle” | A local battle ends without erasing the broader continuing threat. |

The vocabulary above is benchmark-only requirements language. The validator loads no store and defines no DungeonMind production ontology.

## §13 Acceptance rubric

- [x] Exactly one capability: a validated temporal-requirements overlay.
- [x] #708 benchmark/gold files remain byte-for-byte unchanged.
- [x] Exactly seven temporal expectations exist.
- [x] All seven are grounded in the existing seven-source Stage 4F cohort.
- [x] Benchmark ID/corpus/gold fingerprints are pinned and revalidated.
- [x] Evidence session is modeled separately from truth-window boundaries.
- [x] Unknown truth start/end remains unknown.
- [x] Brin background does not falsely begin in S23.
- [x] Brin leadership and Orric mayor state are confirmed across S23→S25 without invented start dates.
- [x] Brin arrival is historical S23 event, not persistent current state.
- [x] Karsemine fire-weakness knowledge acquisition begins in S23 and is marked enduring.
- [x] Mireward siege pressure remains open-ended until changed.
- [x] North Gate battle is bounded S23→S24 without implying broader siege pressure ended.
- [x] Existing Brin and Orik/Orric identity expectations are referenced, not reimplemented.
- [x] Requirement-only temporal cases are allowed without pretending they have current fact anchors.
- [x] No current scorer behavior changes.
- [x] No DungeonMind schema/storage/reasoning changes.
- [x] No extraction/model/prompt/taxonomy changes.
- [x] No model calls or paid evidence.
- [x] Stage 4 WOW remains HOLD.

## Stop conditions

Stop and report rather than broadening if:

- the Stage 4F benchmark fingerprints do not reproduce on the exact base;
- a required source marker is not present in the pinned source bytes;
- one of the seven temporal requirements requires changing Stage 4F gold to express honestly;
- temporal intent cannot be represented without modifying shared anchor/scorer contracts;
- implementation begins designing a production DungeonMind temporal ontology;
- implementation needs a corpus edit or new source outside the frozen seven-source cohort;
- a second independently useful capability appears, especially automated temporal scoring, identity coalescence scoring, or temporal graph persistence.

Report:

```text
Stop condition:
Invariant clause affected:
Why Stage 4G cannot absorb it:
Required evidence missing:
Affected paths/authority:
Proposed successor/re-brief:
State-authority update needed:
```
