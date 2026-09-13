---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: C1/C2 demo-readiness / Stage 4 ingestion convergence
  - Flow: DOGFOOD-CONTINUITY / Stage 4J / P4 initial-quality corpus materialization
  - Direction: #710 EXPERIMENTS → DECISION FREEZE → CODE/OPERATE → REVIEW → MERGE → HUMAN DOGFOOD
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4j-initial-quality-corpus-materialization-v1.md`
  - Design branch: `dogfood-continuity/stage4j-initial-quality-corpus-materialization-design-v1`

  ## Verification pointer
  - Design base: `0aa77bf791efa00cb51f45f3c7acd273ac3f351f`
  - Experimental evidence notebook: PR #710
  - Implementation MUST NOT start until §2 Decision Record is frozen from #710 evidence.

  The checked-in handoff, frozen #710 decision record, cumulative diff, exact corpus
  inventory, candidate qualification, durable World publication receipt, and normal
  product dogfood are the review contract.
---

# HANDOFF — DOGFOOD-CONTINUITY: Stage 4J initial-quality full-corpus materialization

**Created:** 2026-09-12  
**Status:** DESIGN READY — BLOCKED ON #710 EXPERIMENTAL DECISION RECORD  
**Canonical handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4j-initial-quality-corpus-materialization-v1.md`  
**Conversation/workstream:** `C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** #710 EXPERIMENTS → DECISION FREEZE → CODE/OPERATE → REVIEW → MERGE → HUMAN DOGFOOD  
**Design base:** `0aa77bf791efa00cb51f45f3c7acd273ac3f351f` (`main` after PR #709)  
**Target implementation branch:** `dogfood-continuity/stage4j-initial-quality-corpus-materialization-v1`  
**Target PR title:** `DOGFOOD-CONTINUITY: materialize the initial-quality Eldyrwild corpus`  

> Repository law: `AGENTS.md`. Steward process: `Docs/Process/STEWARD-CYCLE.md`. Product sequence: `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`. World authority: `Docs/Design/ARCHITECTURE-campaign-supergraph.md`. Buddy source authority: `Docs/Design/ARCHITECTURE-application-state-layer.md`.

---

## §0 Steward ruling — what happens to PR #710

PR #710 is no longer treated as the next merge candidate.

Its useful role is now **experimental evidence notebook** for the ingestion-convergence program.

```text
#710 may receive:
  - sanitized experimental result comments;
  - exact experiment SHA / prompt / provider / model / corpus pins;
  - cost + token + latency telemetry;
  - benchmark and GM-usefulness findings;
  - deterministic salvage analyses;
  - explicit hypothesis updates / falsifications.

#710 must NOT become:
  - an ever-growing production implementation PR;
  - authority for silently widening write leases;
  - the branch merged to main to obtain experimental plumbing;
  - the durable production ingestion plan by inertia.
```

Do not add more production capability to #710 merely because the experiment needs it. Experimental implementation may live on disposable/stacked branches with exact SHA pointers; sanitized results land as comments on #710.

Once §2 below is satisfied:

1. post a **CORPUS INGESTION DECISION — FROZEN** comment on #710;
2. copy the decision identity into this handoff;
3. re-anchor Stage 4J on then-current `main`;
4. open the Stage 4J implementation PR from `main`, not from #710;
5. #710 may then be closed **unmerged / superseded by Stage 4J** after its decision evidence is durably referenced here.

Until then, keep #710 open as the experiment notebook.

---

## §1 Mission and product invariant

### Mission

Use the evidence-selected ingestion profile from #710 to materialize one **initial-quality, broad Eldyrwild corpus** into the durable DungeonMind World authority, through the existing contribution/revision/head write architecture, and prove that ordinary DungeonBuddy dogfood sees that corpus without special experimental stores, manual loading, or a developer remembering what was never published.

### Product invariant

> **After this slice lands and its one-time publication is completed, the GM can dogfood DungeonBuddy under the normal `eldyrwild` / C1 / C2 product paths and reasonably assume the campaign/world corpus is there. Missing ordinary corpus memory must be an explicit known limitation, not an accidental consequence of a skipped file, disposable store, stale head, or experiment-only runtime path.**

The target is **initial quality**, not perfect knowledge.

Known weaknesses are allowed when they are measured, named, provenance-preserving, and accepted before publication. Unknown coverage holes are not.

### One capability

This PR owns one capability:

```text
frozen evidence-selected ingestion profile
  + exact corpus inventory
  + isolated candidate materialization
  + qualification
  + governed publication to durable World
  + ordinary product read witness
```

It does not own a new graph schema, a new UI, perfect temporal reasoning, perfect identity resolution, or a general autonomous ingestion service.

---

## §2 BLOCKING PRE-DISPATCH GATE — frozen #710 Corpus Ingestion Decision

**No Stage 4J implementation code may start until this section is filled with an exact decision record.**

The decision must be evidence-led and posted to PR #710 after the planned cheap-model loop.

### §2A Required experimental comparison before decision

At minimum #710 must contain a directly comparable experiment between:

```text
OpenAI GPT-5.6 Luna
vs
OpenRouter deepseek/deepseek-v4.1-flash
```

For the OpenRouter arm:

```text
env key: DUNGEONBUDDY_OPENROUTER
model:   deepseek/deepseek-v4.1-flash
```

Never print, persist, commit, or include the API-key value in receipts.

For comparability, pin one OpenRouter provider when supported and record the exact provider in every receipt. Do not silently compare Luna against an auto-routed mixture of upstream providers. As of 2026-09-12 the model is served by multiple OpenRouter providers; the experiment must record/pin routing behavior rather than assume provider equivalence.

The DeepSeek V4.1 Flash transport must locally validate returned JSON against the same experiment-owned Pydantic/schema contract used for comparison. Do not hide malformed output behind an unmeasured LLM repair pass.

### §2B Expanded metrics — quality is multi-dimensional

The decision record must report more than entity/fact recall.

At minimum:

```text
1. explicit entity recall
2. explicit fact recall
3. identity attachment / fragmentation
4. cross-entity semantic composition
5. authority correctness
6. temporal correctness / inspectability
7. continuity-obligation recall
8. GM top-K usefulness / salience
9. planning continuity-warning recall
10. planning continuity-warning false positives
11. unsupported / hallucinated output rate
12. low-value / trivia rate
13. source coverage / parser rejection buckets
14. entities + facts per evidence unit
15. visible output / reasoning output where provider exposes it
16. input cache behavior where provider exposes it
17. wall time / API calls / observed provider
18. actual cost and projected corpus cost
```

No single composite score is required.

The decision should answer:

> Which profile produces the most useful campaign memory per dollar while leaving the remaining failure modes deterministic enough for DungeonBuddy to repair or expose locally?

### §2C GM continuity benchmark — the product forcing question

The expanded benchmark must include at least one **continuity-protection** case shaped like the real Mossford/Stacy failure:

```text
prior played/source evidence establishes a minor NPC attribute
  e.g. species = X

later planning context reuses that NPC/family/context
  and proposes a detail that may conflict with X

expected DungeonBuddy behavior:
  retrieve the prior declaration fast enough to influence planning;
  surface the conflict/constraint with provenance;
  do not claim the new plan is impossible when fantasy-world explanations remain possible.
```

The benchmark question is:

> **Would a GM planning with DungeonBuddy have been reminded of the previously declared detail before committing the contradictory callback?**

This is a retrieval/continuity benchmark, not merely an extraction keyword benchmark.

If the exact historical Stacy source is locatable in the corpus, use and pin it. If it is not currently recoverable, do not fabricate a source citation; create a clearly labeled benchmark fixture from product-owner-provided facts and keep it separate from corpus-derived gold.

### §2D Continuity-obligation dimension without DungeonMind schema changes

The experiment may test one additional GM-usefulness dimension using **existing schema capacity only**.

Preferred candidate semantic:

```text
continuity obligation:
  a true/observed detail whose future contradiction should be surfaced to the GM
  even if the detail was narratively minor when first recorded.
```

Candidate representation, if evidence supports it:

```text
existing fact attribute: species / role / relationship_tags / etc.
existing factValue.category: continuity_constraint
existing interpretation_level / strength when inferred rather than direct
existing evidence_ids / source anchors
existing temporal fields
```

Do not add a new DungeonMind column, new fact attribute enum, or new durable node type in the experimental loop merely to represent continuity salience.

Other candidate categories may be tested in the same existing `factValue.category` field:

```text
continuity_constraint
active_pressure
callback_hook
portrayal_anchor
texture
```

The final Stage 4J plan may choose fewer categories if the experiment shows a smaller vocabulary works better.

### §2E Deterministic/local enrichment is part of the experiment

The comparison is not limited to raw model output.

It may measure a pipeline shaped like:

```text
cheap model explicit extraction
  → deterministic normalization
  → existing-graph alias lookup
  → bounded local probabilistic identity candidate scoring
  → cross-entity relationship/composition inference
  → authority mapping from source metadata
  → continuity/salience classification
  → existing Fact/Entity contracts
```

Rules:

- facts already known from graph/source metadata should not be regenerated by a model merely to restate them;
- deterministic IDs remain code-owned;
- source authority/truth state remain metadata/workflow-owned;
- local probabilistic inference must preserve evidence and be labeled interpretive when not direct;
- ambiguous identity remains ambiguous rather than being silently merged;
- Karsemine learning a tripod property is a relationship/composition problem, not an alias merge;
- Mireward ↔ Mireward Reach and Orik ↔ Orric are identity/alias problems.

### §2F Required frozen decision record

Before Stage 4J dispatch, fill this table from the exact #710 comment:

| Decision | Frozen value |
|---|---|
| #710 decision comment | `<REQUIRED>` |
| experiment execution SHA(s) | `<REQUIRED>` |
| selected base extraction model | `<REQUIRED>` |
| selected provider + routing | `<REQUIRED>` |
| model reasoning/effort settings | `<REQUIRED>` |
| entity prompt/contract ID | `<REQUIRED>` |
| fact prompt/contract ID | `<REQUIRED>` |
| continuity/salience enrichment | `<REQUIRED>` |
| identity reconciliation policy | `<REQUIRED>` |
| cross-entity composition policy | `<REQUIRED>` |
| source-authority mapping | `<REQUIRED>` |
| source-class chunking/budget policy | `<REQUIRED>` |
| escalation policy, if any | `<REQUIRED>` |
| benchmark quality result | `<REQUIRED>` |
| continuity benchmark result | `<REQUIRED>` |
| known accepted weaknesses | `<REQUIRED>` |
| measured seven-source cost | `<REQUIRED>` |
| projected corpus cost | `<REQUIRED>` |
| execution budget ceiling | `<REQUIRED>` |

This table is the publication profile. Stage 4J may not retune it while ingesting the corpus.

If corpus execution reveals a reason to change prompt/model/routing/enrichment semantics, STOP and return to #710 experimentation rather than tuning against the corpus during publication.

---

## §3 Re-anchor before implementation

At dispatch time:

1. fetch then-current `main`;
2. record exact `main` SHA;
3. record current PR #710 head and the frozen decision-comment URL/ID;
4. verify the experimental implementation needed for the selected plan has either:
   - already landed on `main` under an accepted contract; or
   - can be implemented as bounded subordinate plumbing inside this one materialization capability.

### Split trigger

If the selected plan requires a substantial independently useful prerequisite — for example a general provider abstraction, a broad metadata migration, or a new identity engine — **do not hide it inside Stage 4J**.

Split and land that prerequisite first, then re-anchor this handoff.

Small provider plumbing used only to execute the frozen materialization profile is acceptable. A new general-purpose provider framework is not.

---

## §4 Corpus universe and coverage contract

### §4A Corpus root

Target the real Eldyrwild Markdown corpus:

```text
corpus/eldyrwild-markdown
world_id = eldyrwild
```

Historical Stage 4I census evidence found approximately:

```text
434 Markdown sources
282 parseable through that experiment path
152 rejected / bucketed
5,336 evidence units among the parseable set
```

These numbers are **historical evidence only**. Recompute and pin the exact inventory at Stage 4J dispatch/execution.

### §4B Full-corpus means no silent holes

Every Markdown file in the corpus universe must receive a terminal inventory disposition before paid extraction begins.

Allowed dispositions should be explicit and small, for example:

```text
SELECTED_UNIQUE_SOURCE
DUPLICATE_DERIVED_COPY
MANAGED_PRODUCT_STORAGE
NON_NARRATIVE_INDEX_BY_POLICY
UNSUPPORTED_BY_FROZEN_PROFILE
BLOCKING_METADATA_CONFLICT
```

Do not use generic `skipped`.

A technical parser/frontmatter rejection is **not** an acceptable final reason to silently omit ordinary authored corpus material. Either the frozen profile has a truthful compatibility/classification rule for it, or Stage 4J stops before claiming full-corpus materialization.

### §4C Duplicate/copy policy

The inventory must explicitly disposition known duplicate/derived families such as normalized recap copies if both original and normalized files are present.

Do not pay to extract both copies and then call duplicate graph state an identity problem.

The frozen decision record must name which source is canonical for publication and why.

### §4D Coverage receipt

The final report must include:

```text
files discovered
files selected
bytes selected
files excluded by each named disposition
source-class counts
campaign/session counts where known
evidence-unit counts
expected entity/fact request counts
selected-source fingerprint
```

No publication claim without this receipt.

---

## §5 Initial-quality semantic contract

Initial quality is a deliberate quality tier, not a euphemism for uncontrolled output.

### Must be true

- source provenance survives;
- source authority is truthful;
- planning material is not silently published as played/CANON truth;
- played recaps remain campaign-scoped observed evidence;
- world/reference material keeps its correct authority class;
- deterministic IDs are code-owned;
- known aliases/identity candidates are considered before minting new identities;
- ambiguous identity is inspectable;
- model-produced unsupported claims remain below the frozen accepted threshold;
- exact source bytes are never rewritten simply to make ingestion succeed;
- corpus publication does not require a DungeonMind schema migration.

### May remain imperfect when explicitly accepted in §2F

- some spelling-drift identities may remain fragmented;
- temporal truth may remain partially inspectable rather than fully reasoned;
- salience/continuity categories may be incomplete;
- low-value facts may remain present;
- not every cross-entity knowledge relation must be perfectly composed;
- compact GM summaries may still need future work.

Those are quality debts, not permission for missing source coverage.

---

## §6 Publication architecture — use the existing World write path

DungeonMind remains the durable World authority.

Do not publish the selected corpus by copying a disposable FactStore into production or by direct SQL.

Required shape:

```text
exact selected source revisions
  → frozen extraction profile
  → candidate entities/facts/relations + evidence
  → GraphContribution / existing write contract
  → identity/reconciliation under existing semantics
  → proposed immutable World revision
  → validation
  → atomic `eldyrwild` graph-head advance
```

The previous graph head must remain readable if validation/publication fails.

Campaign is scope, not a second graph.

Do not create separate durable C1 and C2 graph stores.

### Source-byte authority boundary

Buddy APP-STATE and DungeonMind remain separate authorities.

Stage 4J does not automatically re-adopt every corpus byte into APP-STATE merely because the graph ingests it.

However:

- Graph contributions must retain exact source identity/evidence sufficient for provenance;
- existing APP-STATE exact source revisions must be reused where already authoritative;
- if normal dogfood provenance for a selected source requires APP-STATE bytes and those bytes are absent, report that gap explicitly;
- do not fabricate APP-STATE revision identity or silently fall back to a checkout path as durable product authority.

If broad new APP-STATE source adoption becomes necessary to satisfy the product invariant, that is a stop/split decision unless it can reuse the already-accepted Stage 2C exact-adoption seam without changing its contract.

---

## §7 Operator sequence

### A0 — protect current durable authority

Before any model call or World write:

- record current `eldyrwild` graph head;
- take/verify the standing external backup required by current World operations;
- record object/contribution/source counts;
- record current APP-STATE source coverage relevant to the selected corpus;
- prove ordinary current projections still load.

### A1 — zero-write corpus inventory

Build the §4 coverage receipt.

No API calls. No World writes.

Fail on unknown/silent dispositions.

### A2 — costed dry-run

Using exact selected evidence-unit/request counts and the frozen §2F profile, emit:

```text
planned requests by stage/model/provider
estimated input/output ranges
estimated cache assumptions
projected dollar cost
hard budget ceiling
expected wall-time range
```

No paid calls.

### A3 — isolated candidate extraction/materialization

Run the entire selected corpus into an isolated candidate output/database that cannot advance the live World head.

Record exact:

```text
repo SHA
corpus fingerprint
profile fingerprint
model/provider
prompt IDs
request counts
provider receipts
cost/tokens/cache/runtime
candidate entity/fact/relation counts
source-class/authority counts
identity/ambiguity counts
```

Do not tune after seeing whole-corpus output.

### A4 — qualify candidate before publication

Run:

1. frozen #708/#709 campaign-memory benchmark/witnesses;
2. the expanded continuity/salience benchmark selected in §2;
3. source-authority audit;
4. corpus coverage audit;
5. identity-fragmentation inventory;
6. unsupported/noise sample;
7. GM top-K usefulness sample across multiple source classes;
8. known named witnesses from C1/C2, including at least one Mossford continuity case when source evidence is available.

Compare against the exact acceptance thresholds/known weaknesses frozen in §2F.

A candidate may be initial-quality and still pass. It may not move its own thresholds after seeing results.

### A5 — human publication checkpoint

Before touching the durable World head, present a concise publication packet:

```text
coverage
quality dimensions
known weaknesses
identity debt
authority audit
continuity benchmark
actual spend
candidate counts
projected user effect
rollback target
```

No automatic publish merely because tests passed.

### A6 — governed durable publication

After explicit operator approval, publish the already-qualified candidate through the existing World write architecture.

Requirements:

- exact prior head pin;
- no concurrent unexplained World advancement;
- proposed revision validates;
- one atomic head advance;
- failure leaves prior head active;
- receipt records prior/new head and contribution identity set.

Do not rerun the model between candidate qualification and publication unless the candidate itself is regenerated and requalified.

### A7 — idempotency / replay witness

Re-submit or replay the exact frozen contribution bundle through the accepted replay seam.

Require no duplicate durable assertions/contributions and no unexplained second semantic head advancement.

Do not prove idempotency by making a fresh stochastic model run and hoping it matches.

### A8 — ordinary product witness

Restart the normal product/runtime as needed and use the ordinary Buddy-facing World read path.

No experiment flags. No FactStore path. No manual fixture selection.

Dogfood at minimum:

```text
C1 historical material
C2 historical material
Mireward / Brin / Orric / Karsemine
Mossford or another corpus area not in the seven-source development cohort
one worldbuilding/reference object
one planning-derived PREP object/fact if such material is intentionally published
```

The user should be able to navigate/read/open World context and get the newly materialized memory without knowing which ingestion run produced it.

### A9 — restart/recovery witness

Prove the published graph head survives normal service/container restart.

Verify the new durable state is represented in the standing backup/recovery mechanism. A clean recovery target should be able to open the same published head or an equivalent accepted reconstruction according to existing World operations.

---

## §8 GM-facing acceptance questions

Review is not complete on database counts alone.

Human dogfood must answer:

1. **Presence:** “When I expect an old person/place/fact to exist, do I stop noticing that the corpus is missing?”
2. **Depth:** “Can I get from the object to useful accumulated facts/evidence without rereading the whole source?”
3. **Continuity:** “If I start planning something that conflicts with a previously declared minor fact, is the relevant prior fact retrievable/salient enough to protect me?”
4. **Authority:** “Can planning ideas remain planning ideas while played facts remain played facts?”
5. **Trust:** “When DungeonBuddy is unsure whether two names are the same person, does it expose uncertainty rather than silently invent continuity?”

The Stage 4 WOW question remains broader, but Stage 4J should materially change the answer by making campaign memory broadly present.

---

## §9 Quality and metric report

The PR handback must report the selected profile on multiple dimensions rather than one recall number.

Required sections:

```text
coverage
entity recall
fact recall
identity fragmentation
cross-entity composition
source-authority correctness
temporal inspectability
continuity-obligation recall
continuity false positives
GM top-K usefulness
unsupported/noise sample
low-value fact sample
entity/fact/evidence-unit density
cost by stage/model/provider
cache behavior
runtime
known weaknesses accepted for initial quality
```

Do not claim production routing superiority from a single comparative run. Stage 4J is allowed to publish a chosen initial-quality profile because the product owner explicitly accepts an evidence-backed starting point; that is different from claiming the model question is scientifically settled.

---

## §10 Write lease — BLOCKED until §2F is frozen

This design intentionally does **not** pre-authorize unknown implementation paths before the selected pipeline exists.

Before implementation begins, amend this section in one design-only commit with exact paths and reasons.

Expected path families, subject to the frozen plan:

```text
extraction_lab/**                  qualification / receipts only
tools/**                           bounded corpus operator only
src/ingestion/**                   only frozen-profile changes actually selected
src/llm/**                         only bounded selected-provider plumbing if required
tests/**                           owning deterministic + integration proof
Docs/Reports/**                    sanitized corpus publication report
Docs/Plans/**                      this handoff + predecessor state sync
Docs/Roadmaps/**                   backward-looking stage status only
```

Potentially in scope only if existing accepted World write seam requires it:

```text
graph_memory/**
apps/live_control_server/**
```

but **no semantic changes to DungeonMind contracts** are allowed without rebrief.

Explicit no-change unless separately rebriefed:

```text
schemas/v0.1/**
DungeonMind database schema/migrations
APP-STATE database schema/migrations
UI surface design/components
Agent orchestration behavior
#708 benchmark/gold
#709 temporal intent authority
corpus prose merely to make ingestion pass
MODEL_POLICY production defaults unless the frozen decision explicitly requires and separately justifies it
```

If implementation needs an independently useful provider framework, metadata migration, graph-kernel identity redesign, or schema change, STOP and split it.

---

## §11 Deterministic tests required before paid full-corpus execution

At minimum prove:

```text
inventory sees every Markdown source in the selected universe
no generic skipped bucket
source-selection fingerprint deterministic
normalized/derived duplicate disposition deterministic
managed storage excluded deterministically
source-authority mapping cannot promote planning material to CANON accidentally
selected provider/model identity explicit
OpenRouter key value never logged
provider mismatch fails when provider pin required
malformed model JSON fails local validation
no hidden repair-model call
budget dry-run makes zero paid calls
wrong repo/corpus/profile fingerprint fails
candidate output cannot advance live World head
live publish requires exact prior-head pin
validation failure leaves prior head unchanged
replay of exact contribution bundle is idempotent
normal projection reads new head without experiment flags
```

Also retain all existing #708/#709 benchmark validators unchanged.

---

## §12 Paid execution / budget rules

The hard dollar ceiling comes from §2F and the exact A2 census.

Rules:

- fail before execution if projected cost exceeds the frozen ceiling;
- record actual provider/model on every paid stage;
- no automatic escalation unless §2F explicitly selected it;
- no retries for quality;
- transport retries may occur only under the frozen retry policy and must remain visible in telemetry;
- stop and rebrief if spend or output volume deviates materially from the frozen plan before enough of the corpus has completed to justify continuing.

The purpose of using cheap models is to make corpus iteration economically ordinary, not to remove cost observability.

---

## §13 Required durable report

Create one sanitized report, recommended path:

```text
Docs/Reports/REPORT-stage4j-initial-quality-corpus-materialization.md
```

It must include:

```text
exact implementation SHA
#710 decision comment + experiment SHAs
corpus fingerprint + inventory summary
selected profile fingerprint
provider/model/prompt IDs
actual execution cost/tokens/runtime
candidate qualification metrics
accepted weaknesses
pre-publication graph head
post-publication graph head
contribution/source/object/assertion deltas
idempotent replay result
ordinary product witnesses
restart/recovery witness
explicit statement of what remains false
```

Do not commit secrets or raw model payloads containing unnecessary private material.

---

## §14 State-authority sync

Stage 4J implementation may record only backward-looking facts already true before it begins plus the current slice state.

At dispatch, sync:

- accepted merged predecessor state through then-current `main`;
- #710 is experimental evidence / not merged production authority;
- exact frozen #710 decision identity;
- Stage 4J CURRENT;
- Stage 4 WOW remains HOLD until human dogfood says otherwise.

Do not mark Stage 4J DONE before merge/publication proof.

Do not close Stage 4 or declare full ingestion production-ready merely because one initial-quality corpus is materialized.

---

## §15 Stop conditions

Stop and report rather than broadening if:

- §2F is not fully frozen;
- Luna vs DeepSeek experiment remains ambiguous enough that no publication profile can be named;
- selected profile requires a DungeonMind schema change;
- selected profile requires a substantial general provider framework not already landed;
- ordinary authored corpus files remain excluded only because legacy frontmatter is inconvenient;
- duplicate/normalized source policy cannot be made deterministic;
- planning/source authority cannot be preserved truthfully;
- candidate quality materially violates its frozen accepted weakness envelope;
- continuity benchmark shows the selected pipeline still cannot recover the kind of minor prior declaration needed for the Stacy-style use case;
- live World head moved unexpectedly between preflight and publication;
- publication requires direct SQL or bypassing GraphContribution/revision/head validation;
- product read path requires an experiment-only store/path/flag;
- a second independently useful capability appears.

Report:

```text
Stop condition:
Invariant affected:
Evidence:
Why Stage 4J cannot absorb it:
Needed prerequisite/successor:
State-authority impact:
```

---

## §16 Merge-ready invariant

Stage 4J is merge-ready only when all of the following are true:

```text
#710 frozen decision exists and is referenced exactly
selected profile is reproducible and unchanged during corpus run
100% of corpus-universe Markdown has a terminal inventory disposition
no ordinary selected source is silently omitted
candidate corpus was fully extracted/materialized outside live authority
candidate passed the frozen multi-dimensional acceptance envelope
source authority audit passes
pre-write World head/backup is pinned
publication advanced one validated immutable eldyrwild head atomically
prior head remained rollback-safe
exact contribution replay is idempotent
normal Buddy read path sees the published corpus without experiment flags
representative C1/C2/worldbuilding/Mossford dogfood succeeds
published head survives restart and is covered by recovery mechanism
sanitized report is complete
no DungeonMind schema change occurred
```

### Human acceptance sentence

The product owner should be able to say:

> **“I can dogfood DungeonBuddy and assume the Eldyrwild corpus is there. When something is imperfect, I notice the quality debt—not that the data never made it into the product.”**

That is the finish line for this slice.
