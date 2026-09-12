# HANDOFF — DOGFOOD-CONTINUITY: Stage 4F campaign-memory development benchmark

**Created:** 2026-09-12  
**Status:** DONE — PR #708 MERGED
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4f-campaign-memory-development-benchmark-v1.md`  
**Conversation/workstream:** `C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program`  
**Flow / owner:** `DOGFOOD-CONTINUITY` / campaign-memory benchmark authority  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `4227f97da35e384e995263d5c6a62d9711333488` (main after PR #707 merge)  
**Branch:** `dogfood-continuity/stage4f-campaign-memory-development-benchmark-impl`
**PR title:** `DOGFOOD-CONTINUITY: define campaign-memory development benchmark`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). Benchmark philosophy: [`Docs/Design/DESIGN-benchmark-philosophy-and-goals.md`](../Design/DESIGN-benchmark-philosophy-and-goals.md). Execution predecessor: [`HANDOFF-DOGFOOD-CONTINUITY-stage4e-repeated-pair-qualification-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-stage4e-repeated-pair-qualification-v1.md).

---

## §0 Where the program is now

The experimental machinery is no longer hypothetical.

```text
P0a   trustworthy cross-contract comparison              DONE — PR #705
P0b1  one bounded isolated baseline/candidate pair       DONE — PR #706
P0b2a repeated-pair qualification + variance summary     DONE — PR #707
LIVE  one-source Stage 4D smoke                          DONE — 2026-09-12
LIVE  three-repetition Stage 4E run                      DONE — 2026-09-12
P1a   representative campaign-memory benchmark authority DONE — PR #708
P1b   baseline characterization on that benchmark        later / evidence-selected
P2    bounded extraction ablations                       later / evidence-selected
P3    frozen validation                                  later
P4    full-corpus rehearsal into disposable authorities  later
P5    governed durable publication                       later
```

PR #707 merged at `4227f97da35e384e995263d5c6a62d9711333488`, accepted head `4ca2c12c3ad15e6e6c18b0fab8fb5acb2a76ebcc`, after 2 formal review cycles. It can repeat one exact Stage 4D pair 2–3 times with isolated stores/caches and summarize metric, anchor, cost, token, and runtime variability without ranking a winner.

PR #708 merged at `444b39963286667400c827b8765f8246763b8701`, accepted head `8da461e21b69291d9f61b1d7309cb883a9dc06e5`, after 2 formal review cycles. It froze the seven-source campaign-memory benchmark with six entity anchors, five fact anchors, two unscored identity expectations, corpus fingerprint `925ad24a54d888e2f1d3673919d126767b39cdeaf885c07057bfb5da346ba8c1`, and gold fingerprint `de072c175cc00a1dc7ed672cdaca317ee0f8cb381a8186e9cfc53a5885a4cd23`.

The Stage 4 WOW gate remains **HOLD**. The UI work exposed that the product does not yet recover enough accumulated campaign truth for a World reference to feel like living memory.

### The newly visible benchmark problem

The default Extraction Lab gold is still the old Mirathorn vertical slice:

- 13 entity anchors;
- 10 fact anchors;
- every current anchor points to `The City of Mirathorn.md`;
- it is excellent regression history for that one worldbuilding document;
- it does **not** encode the Brin / Orric-or-Orik / Karsemine / Mireward failures that triggered this experiment program.

Therefore the next useful capability is not another executor and not a prompt tweak. We need a small, frozen, human-authored **development benchmark that represents the product problem we actually intend to improve**.

### Design correction: benchmark before bigger runs

Do **not** jump from the one-source smoke directly to a paid 10–20 document tuning loop. A larger run against gold that does not represent the target behavior produces more telemetry, not better evidence.

Stage 4F defines the benchmark authority first. It makes zero paid model calls.

---

## §1 Pre-dispatch gate — Stage 4E live repeated run

Stage 4E explicitly required one real repeated run before building the next experimental capability.

Run against the exact PR #707 merge SHA:

```text
repository SHA:
  4227f97da35e384e995263d5c6a62d9711333488

pair:
  same one-source Session 23 pair used by the Stage 4D smoke

repetitions:
  3

execution:
  realtime
  isolated caches
  fixed baseline → candidate order
```

Before implementation dispatch, amend this handoff with a **Repeated Run Gate Record** containing:

```text
operator/date
exact merge SHA
repeat-manifest SHA-256
pair-manifest SHA-256
repeat receipt durable evidence pointer or accepted sanitized record
receipt status
completed repetitions
all child comparisons comparable=true/false
observed model IDs
total and per-repetition cost/runtime/token telemetry
anchor stability summary
whether source/gold/model-policy/repository identity stayed pinned
failure classification if any
```

### Gate disposition

- orchestration/provenance/comparison failure → **STOP** and repair the P0 machinery;
- inability to complete three bounded realtime repetitions safely → **STOP** and re-brief P0b2b/P0b2c before dispatch;
- trustworthy completed run with high extraction/anchor variance → Stage 4F benchmark-definition work **may proceed**, because better human gold is useful for diagnosing that instability; however P1b paid cohort scaling remains blocked until variance is understood;
- trustworthy completed run with acceptable operation/variance → Stage 4F may dispatch normally.

### Repeated Run Gate Record

**PASS — 2026-09-12, operator: Codex with explicit user authorization.** This checked-in sanitized record is the accepted durable evidence artifact; raw artifacts existed under `/tmp/dmb-stage4e-live-repeat-20260912/` at execution time.

- exact PR #707 merge: `4227f97da35e384e995263d5c6a62d9711333488`
- repeat manifest SHA-256: `c2f68af429b9936cb14280683406ca666add3c174b4edea757171a4c7ec51a16`
- pair manifest SHA-256: `86b58f9986606bebb6fe5780e440efd2b79d5c56cc421209aafbbc16137b064c`
- parent receipt `completed`; 3/3 repetitions completed; all three comparisons `comparable=true`
- observed entity/fact model for both variants in every repetition: `gpt-5.3-codex`
- per-pair cost: `$0.8987`, `$0.9024`, `$0.9008`; total `$2.7019`
- per-pair summed variant runtime: `99.519s`, `102.141s`, `97.267s`; total `298.927s`
- total telemetry: 239,131 input tokens; 178,222 output tokens; 134,400 cached tokens; 99 API calls
- anchor stability: unrelated Mirathorn gold remained 0/13 entity and 0/10 fact anchors for both variants in all repetitions; all 23 transitions were unchanged. This proves the old gold cannot measure Session 23 campaign memory, not that either variant wins.
- stochastic output: baseline entities `[54,55,57]`, candidate `[60,55,51]`; baseline facts `[125,138,134]`, candidate `[136,143,144]`
- repository, source, gold, model-policy, observed-model, benchmark corpus, and benchmark gold identity stayed pinned
- disposition: P0 machinery/provenance PASS; Stage 4F dispatch authorized. P1b remains a successor decision after the new benchmark exists.

---

## §2 Mission and merge-ready invariant

**Mission:** Create one frozen, reviewable development benchmark for campaign-memory extraction that pins a small exact C2/Mireward source cohort and human-authored entity/fact expectations for the product failures discovered during Stage 4 dogfood, with a fail-closed validator that proves the benchmark definition is internally coherent before any model is run against it.

**Merge-ready invariant:** One strict benchmark manifest identifies the exact source files and their byte hashes; all development anchors use one dedicated evaluation surface, point only at sources in that cohort, carry exact source markers that resolve against the pinned bytes, and form an internally valid entity→fact dependency graph. Validation is deterministic, path-stable, and model-free. The PR does not tune extraction, score a live store, publish World state, or claim that current Extraction Lab scoring already proves alias coalescence, provenance, or temporal continuity that it does not yet evaluate.

### Why this is one capability

The independently useful capability is:

> **A trustworthy campaign-memory development benchmark definition exists and can be validated without executing ingestion.**

The source manifest, human gold, and validator are inseparable parts of that one authority. Running the benchmark, changing the scorer, and tuning extraction are successors.

---

## §3 Product questions this benchmark must encode

The benchmark exists because the Stage 4 WOW question became:

> When a GM encounters someone or something in old material, can DungeonBuddy recover the important accumulated campaign knowledge about that thing instead of showing implementation machinery?

The first development benchmark must represent at least these concrete questions:

1. **Brin Holloway** — can extraction recover that Brin is a person, a cook from Edge, and the leader/clear lead of the refugee/survivor group arriving at Mireward?
2. **Orric / Orik Tane** — can extraction recover the Mireward mayor identity and the mayor role while preserving the editorial fact that the Session 23 recap spells the name `Orik Tane` and the stable corpus hub canonicalizes the NPC as `Orric Tane`?
3. **Karsemine** — can extraction recover a table-useful played fact from Session 23, especially the Hunter's Mark discovery that the tripod creatures resist poison and are weak to fire?
4. **Mireward Reach** — can extraction recover the place and the immediate siege/refugee pressure around it rather than only generic location existence?
5. **Cross-source accumulation** — does the benchmark contain both stable reference material and played recaps so later scoring can detect whether useful campaign memory accumulates across source classes rather than treating every document as an isolated mention?

### Important honesty boundary

Current `EntityGoldAnchor` / `FactGoldAnchor` scoring resolves names and facts from the resulting store. The current resolver does **not** enforce that:

- two aliases from different source files resolve to the same entity;
- a matched fact came from a particular source file;
- session N evidence temporally precedes or supersedes session N+1 evidence.

Stage 4F must encode those editorial intentions where useful, but must **not** claim those dimensions are already scored. Source-local provenance, same-identity equality, and temporal ordering are candidate successor scoring capabilities.

---

## §4 Static development cohort v1

Create:

`evals/campaign_memory_development/benchmark.json`

Schema:

```json
{
  "schema": "dmb_campaign_memory_development_benchmark_v1",
  "benchmark_id": "c2-mireward-campaign-memory-dev-v1",
  "surface": "campaign_memory_development",
  "corpus_root": "corpus/eldyrwild-markdown",
  "sources": [
    {
      "locator": "...relative to corpus_root...",
      "sha256": "...",
      "role": "played_recap | world_reference | character_reference | continuity_reference",
      "reason": "human-readable selection rationale"
    }
  ],
  "entity_anchors": "gold/entity_anchors.json",
  "fact_anchors": "gold/fact_anchors.json",
  "identity_expectations": [
    {
      "expectation_id": "...",
      "anchor_ids": ["...", "..."],
      "intent": "editorial same-identity intent for future scoring"
    }
  ]
}
```

All fields are strict; unknown fields fail closed.

### Required source cohort

Use exactly these **7** source locators for v1 unless implementation discovers an exact path is stale, in which case stop and re-brief rather than silently substitute another corpus derivative:

```text
Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate.md
Longmont Campaign/Campaign 2/Session Recaps/Session 24 - Mireward Gate Battle.md
Longmont Campaign/Campaign 2/Session Recaps/Session 25 - Mireward Gate Battle II.md
Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md
Elderwyld/Cities and Towns/Mireward/NPCs/brin_holloway/character_seed.md
Elderwyld/Cities and Towns/Mireward/NPCs/orric_tane/character_seed.md
Longmont Campaign/Campaign 2/PCs/karsemine/timeline.md
```

Rationale:

- S23 is the direct dogfood witness for Brin, Orik, Mireward, and Karsemine.
- S24/S25 create a small chronological played sequence instead of a one-session toy.
- Mireward scaffold gives stable place/world context.
- Brin and Orric seeds provide stable character reference material alongside played spellings/events.
- Karsemine timeline gives stable PC continuity alongside the played recap.

### Source selection rules

The validator must reject:

- missing sources;
- duplicate locators;
- SHA mismatch;
- paths outside `corpus_root`;
- `_archive/`, `_normalized/`, `_breadcrumbed/`, `_session_memory/`, generated eval artifacts, or other derived copies;
- non-Markdown cohort sources;
- fewer or more than the exact seven v1 sources.

This PR freezes a development cohort; source expansion is a later reviewed benchmark change.

---

## §5 Human gold v1

Create:

```text
evals/campaign_memory_development/gold/entity_anchors.json
evals/campaign_memory_development/gold/fact_anchors.json
```

Reuse the existing `EntityGoldAnchor` and `FactGoldAnchor` schemas. Do **not** create a parallel anchor schema.

Every new anchor must:

- use `surface = "campaign_memory_development"`;
- have a unique non-empty `anchor_id`;
- include a full cohort-relative `source_file` locator, not only a basename;
- include a non-empty `source_text_marker` copied exactly from the pinned source bytes;
- represent human editorial intent, not whatever the current extractor happened to emit in the smoke run.

### Minimum entity witness set

The implementing agent may add a small number of additional high-value anchors if directly justified by the seven sources, but must include at least:

```text
brin_holloway_session23         actor
brin_holloway_reference         actor
orik_tane_session23             actor
orric_tane_reference            actor
karsemine_session23             actor
mireward_reach                  place
```

These paired Brin/Orric anchors intentionally preserve cross-source editorial intent without pretending current scoring proves identity equality.

Recommended expected names:

```text
Brin anchors:
  ["Brin Holloway", "Brin"]

Orik recap anchor:
  ["Orik Tane", "Orik"]

Orric reference anchor:
  ["Orric Tane"]

Karsemine:
  ["Karsemine"]

Mireward:
  ["Mireward Reach", "Mireward"]
```

Do not normalize the gold to current extractor mistakes merely to make the first baseline pass.

### Minimum identity-intent set

`identity_expectations` in the benchmark manifest is **editorial intent only in this slice**. It is validated structurally but not scored yet.

At minimum:

```text
brin_cross_source_identity:
  [brin_holloway_session23, brin_holloway_reference]

orric_orik_cross_source_identity:
  [orik_tane_session23, orric_tane_reference]
```

The validator proves the referenced entity anchors exist and share an expected entity class. It does not inspect a live store.

### Minimum fact witness set

Use only valid current fact attributes. Required intent:

```text
brin_role
  subject: brin_holloway_session23
  expected_attribute: role
  keywords should require both the cook/Edge idea across the allowed keyword set

brin_refugee_leadership
  subject: brin_holloway_session23
  expected_attribute: event_progression
  alternative_attributes may include role / operational_status
  keywords should cover refugee/survivor leadership or arrival

orik_mayor_role
  subject: orik_tane_session23
  expected_attribute: rank_or_title
  alternative_attributes may include role / governance
  keywords: mayor

karsemine_fire_weakness_discovery
  subject: karsemine_session23
  expected_attribute: event_outcome
  alternative_attributes may include event_progression
  keywords must cover the fire weakness; poison resistance may be included as additional signal

mireward_siege_pressure
  subject: mireward_reach
  expected_attribute: operational_status
  alternative_attributes may include event_progression
  keywords should cover siege/threat/monsters/refugee pressure
```

Do not add a fact anchor whose text cannot be directly grounded in one of the exact seven source files.

### Gold-authoring rule

The existing Session 23 candidate-graph gold is useful **evidence for what the source says**, not authority for Extraction Lab scoring. Human authors must verify every new anchor directly against the pinned corpus source and record an exact marker.

---

## §6 Validator contract

Create:

`extraction_lab/campaign_memory_benchmark.py`

It owns a strict Pydantic manifest model plus deterministic validation/normalization.

Preferred CLI:

```bash
uv run python -m extraction_lab.campaign_memory_benchmark \
  --manifest evals/campaign_memory_development/benchmark.json
```

The command performs **zero model calls** and writes no store.

On success, print one normalized JSON summary containing at least:

```text
schema
benchmark_id
surface
source_count
entity_anchor_count
fact_anchor_count
identity_expectation_count
corpus_fingerprint
gold_fingerprint
entity_fingerprint
fact_fingerprint
validated=true
```

Reuse `extraction_lab.benchmark_contract.compute_benchmark_contract(...)` for corpus/gold fingerprint semantics. Do not invent a competing corpus or gold fingerprint algorithm.

### Fail-closed validation

Reject at least:

1. unknown manifest fields;
2. wrong schema/surface;
3. source outside corpus root;
4. missing/duplicate source;
5. source SHA mismatch;
6. forbidden derivative/archive source;
7. anchor file missing/invalid;
8. anchor ID duplicate across its kind;
9. anchor surface mismatch;
10. anchor `source_file` not an exact cohort locator;
11. missing `source_text_marker`;
12. marker not found in the pinned source bytes;
13. fact `subject_anchor` missing from entity anchors;
14. identity expectation references missing anchors;
15. identity expectation has fewer than two anchors;
16. identity expectation groups anchors with incompatible expected classes;
17. zero entity or fact anchors for the development surface.

### Path independence

A copied checkout/worktree containing the same repository-relative corpus bytes and same benchmark definition must produce the same corpus/gold fingerprints. Absolute paths must not enter identity.

---

## §7 Explicitly out of scope

| Area | Why excluded |
|---|---|
| paid ingestion/model execution | This PR defines benchmark authority only. |
| Stage 4E repeated live run | Operator gate before dispatch, not implementation work. |
| changing Stage 4D's 1–3 source cap | P1b execution design, if/when needed. |
| prompt/model/taxonomy/filter tuning | P2; first baseline must be measured before tuning. |
| editing existing Mirathorn `core_extraction` anchors | Preserve old regression authority. |
| alias/same-identity live scoring | Current resolver cannot prove equality; successor capability. |
| source-provenance scoring | `source_file` is currently editorial metadata; successor capability. |
| temporal ordering/supersession scoring | Separate benchmark dimension. |
| negative-example / precision gold | Later benchmark expansion after first characterization. |
| automatic winner/composite score | Prohibited by experiment philosophy. |
| holdout split | P3 / later ratification. |
| APP-STATE or DungeonMind publication | P4/P5. |
| Session 23 historical source adoption | Separate continuity lane. |
| UI changes | Stage 4 UI lane remains separate. |

---

## §8 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/campaign_memory_development/benchmark.json` | Frozen seven-source development cohort + identity intent. |
| Create | `evals/campaign_memory_development/gold/entity_anchors.json` | Human campaign-memory entity intent. |
| Create | `evals/campaign_memory_development/gold/fact_anchors.json` | Human campaign-memory fact intent. |
| Create | `extraction_lab/campaign_memory_benchmark.py` | Strict model-free benchmark validator + normalized identity summary. |
| Create | `tests/extraction_lab/test_campaign_memory_benchmark.py` | Validation, pinning, marker, dependency, identity-intent, path-independence tests. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4e-repeated-pair-qualification-v1.md` | Backward-looking #707 merge/PASS + repeated-run gate disposition only. |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Record #707 merged/PASS and Stage 4F benchmark-definition lane current. |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Record measurement stack + benchmark-definition step; Stage 4 remains NOT DONE. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4f-campaign-memory-development-benchmark-v1.md` | Gate record, implementation evidence, review handback. |

### Expected no-change paths

Do not modify:

```text
extraction_lab/anchor_schema.py
extraction_lab/anchor_resolver.py
extraction_lab/benchmark_contract.py
extraction_lab/run_extraction_lab.py
extraction_lab/run_pair_experiment.py
extraction_lab/run_repeat_experiment.py
extraction_lab/compare_experiment_runs.py
tools/batch_ingest_corpus.py
MODEL_POLICY.json
src/ingestion/**
evals/mirathorn_vertical_slice/gold/**
corpus/eldyrwild-markdown/**
```

If the benchmark cannot be expressed without changing the existing anchor schema/resolver or corpus bytes, stop and re-brief. Do not silently broaden this slice into scoring or source repair.

### Bounded discovery exception

The implementing agent may read any of the seven pinned source files and the existing Session 23 candidate-graph gold for authoring evidence. No extra production write paths are authorized.

---

## §9 Required evidence to merge

### Deterministic tests

At minimum prove:

```text
valid checked-in benchmark → PASS
same benchmark in another checkout root → identical corpus/gold fingerprints
unknown field → fail
missing source → fail
source SHA drift → fail
forbidden _archive/_normalized/_breadcrumbed path → fail
duplicate source → fail
wrong anchor surface → fail
anchor source outside cohort → fail
missing marker → fail
marker absent from source → fail
duplicate anchor ID → fail
fact subject anchor absent → fail
identity expectation missing anchor → fail
identity expectation incompatible classes → fail
```

### Human gold witness review

The PR handback must include a compact table showing, for every required anchor:

```text
anchor_id
source locator
exact marker excerpt (brief)
editorial intent
why it matters to Stage 4 WOW
```

Do not paste entire source documents.

### Commands

```bash
uv run pytest tests/extraction_lab/ -q
uv run ruff check \
  extraction_lab/campaign_memory_benchmark.py \
  tests/extraction_lab/test_campaign_memory_benchmark.py

uv run python -m extraction_lab.campaign_memory_benchmark \
  --manifest evals/campaign_memory_development/benchmark.json

git diff --check
git diff --name-only 4227f97da35e384e995263d5c6a62d9711333488...HEAD
```

### No paid evidence required

This PR must not call the model API. Its evidence is benchmark-definition correctness.

---

## §10 State-authority sync

Backward-looking sync in this implementation PR must record only facts already true before Stage 4F implementation:

- PR #707 merged at `4227f97da35e384e995263d5c6a62d9711333488`;
- accepted #707 head `4ca2c12c3ad15e6e6c18b0fab8fb5acb2a76ebcc`;
- #707 required 2 formal review cycles;
- P0a/P0b1/P0b2a measurement machinery exists;
- the Stage 4E live repeated-run disposition once actually performed;
- Stage 4 WOW remains HOLD;
- no extraction improvement has yet been accepted;
- P1 baseline characterization, P2 tuning, and publication remain false.

Do **not** pre-mark Stage 4F complete or invent its merge SHA/review count.

---

## §11 Immediate successor decision

After this benchmark merges, do **not** automatically start tuning.

If Stage 4E operation is healthy and the benchmark validates, the preferred next slice is:

> **P1b — run the current unchanged extraction pipeline against the frozen seven-source development benchmark and produce the first honest failure-class baseline.**

That successor will need to decide, from evidence, whether to:

- extend bounded execution beyond the Stage 4D three-source cap;
- run one baseline only rather than fake an A/B candidate;
- repeat the baseline enough times to separate stochastic failures from systematic misses;
- add source-aware / same-identity scoring before tuning if the current anchor resolver hides the key failure.

If the Stage 4E live run instead reveals an operational blocker, P0b2b/P0b2c may still precede P1b. Stage 4F does not override that evidence.

---

## §11A Implementation handback — human gold witnesses

| Anchor | Source | Brief exact marker | Editorial intent / Stage 4 WOW value |
|---|---|---|---|
| `brin_holloway_session23` | S23 recap | “A clear leader … Brin Holloway, a cook from Edge” | Brin is a named played actor with meaningful context, not a session-only label. |
| `brin_holloway_reference` | Brin seed | “Brin Holloway — character seed” | Preserves the stable reference half of Brin's cross-source identity. |
| `orik_tane_session23` | S23 recap | “As mayor, Orik Tane can easily command the room.” | Preserves the played spelling and why Orik matters. |
| `orric_tane_reference` | Orric seed | “Mayor Orric Tane — character seed” | Preserves the canonical spelling for later identity scoring. |
| `karsemine_session23` | S23 recap | “Karsemine uses her Hunter’s Mark” | Connects a PC to a table-useful discovery. |
| `mireward_reach` | Mireward scaffold | “Mireward Reach — place build scaffold” | Establishes the place whose accumulated pressure should be visible. |
| `brin_role` | S23 recap | “Brin Holloway, a cook from Edge” | Requires occupational/origin memory beyond entity existence. |
| `brin_refugee_leadership` | S23 recap | “A clear leader of the group …” | Requires Brin's survivor/refugee leadership context. |
| `orik_mayor_role` | S23 recap | “As mayor, Orik Tane …” | Requires the key contextual anchor missing from UI dogfood. |
| `karsemine_fire_weakness_discovery` | S23 recap | “resistant to poison, but weak to fire” | Requires actionable played knowledge. |
| `mireward_siege_pressure` | Mireward scaffold | “First **visible** siege pressure at Mireward” | Requires immediate siege/refugee context rather than generic place identity. |

The two manifest identity expectations link the Brin and Orik/Orric source pairs as editorial intent only. Stage 4F validates their references/classes but does not claim current scoring proves coalescence.

## §12 Acceptance rubric

- [x] Stage 4E post-merge three-repetition gate is durably recorded before implementation dispatch.
- [x] Exactly one capability is delivered: a validated campaign-memory development benchmark definition.
- [x] Exact seven-source cohort is frozen with content SHA pins.
- [x] No archive/normalized/breadcrumbed/generated source enters the cohort.
- [x] New gold uses a dedicated `campaign_memory_development` surface.
- [x] Every anchor is grounded by an exact marker in one pinned source.
- [x] Brin, Orik/Orric, Karsemine, and Mireward product witnesses are represented.
- [x] Cross-source Brin and Orik/Orric identity intent is recorded without claiming it is already scored.
- [x] Existing Mirathorn core gold remains untouched.
- [x] Existing benchmark fingerprint semantics are reused.
- [x] Validator is deterministic, path-independent, and model-free.
- [x] No prompt/model/taxonomy/filter changes.
- [x] No paid run, baseline promotion, APP-STATE mutation, or World publication.
- [x] Stage 4 WOW remains HOLD.

## Stop conditions

Stop and report rather than broadening if:

- Stage 4E live repeated execution fails machinery/provenance qualification;
- one of the exact seven source paths is stale/ambiguous and choosing a replacement requires editorial judgment;
- required product intent cannot be represented at all with existing entity/fact anchors without changing scoring semantics;
- source markers cannot be grounded directly in the pinned corpus bytes;
- implementation begins editing corpus, current core gold, prompts, model policy, or ingestion code;
- a second independently useful capability appears, especially live scoring or source-aware identity resolution.

Report:

```text
Stop condition:
Invariant clause affected:
Why Stage 4F cannot absorb it:
Required evidence missing:
Affected paths/authority:
Proposed successor/re-brief:
State-authority update needed:
```
