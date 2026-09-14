---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / campaign-memory ingestion experiments
  - Flow: DOGFOOD-CONTINUITY / Stage 4L
  - Direction: RE-ANCHOR → CODE → ZERO-COST PREFLIGHT → PAID S1–S10 CHRONOLOGICAL REHEARSAL → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4l-c1-s1-s10-chronological-graph-rehearsal-v1.md`
  - Archive authority: `Docs/Reports/ARCHIVE-DOGFOOD-CONTINUITY-stage4h-stage4i-ingestion-notebooks.md`

  ## Experiment
  Build one isolated Campaign 1 rehearsal World from canonical observed recaps Sessions 1–10 in strict chronological order. Session N may consume stable campaign identity plus only the admitted rehearsal World head through Session N-1.

  Model/profile is already selected: `deepseek/deepseek-v4.1-flash`, reasoning disabled, official DeepSeek through OpenRouter, provider fallback disabled, whole-document semantic context with local source-span evidence.

  This PR is an **experimental notebook and must not merge to main**. Its deliverable is evidence and a durable candidate/rehearsal graph, not production defaults.
---

# HANDOFF — DOGFOOD-CONTINUITY: Campaign 1 Sessions 1–10 chronological graph rehearsal

**Created:** 2026-09-14  
**Status:** ACTIVE — experimental notebook; do not merge  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4l-c1-s1-s10-chronological-graph-rehearsal-v1.md`  
**Conversation/workstream:** `C1/C2 demo-readiness / campaign-memory ingestion experiment program`  
**Flow / owner:** `DOGFOOD-CONTINUITY / Stage 4L`  
**Direction:** RE-ANCHOR → CODE → ZERO-COST PREFLIGHT → PAID CHRONOLOGICAL REHEARSAL → REVIEW  
**Steward base before this handoff:** `3c372ebacb88130ac7cda72b4bc81800c273806f`  
**Target branch:** `dogfood-continuity/stage4l-c1-s1-s10-chronological-graph-rehearsal`  
**Target PR title:** `DOGFOOD-CONTINUITY: build Campaign 1 memory through Session 10`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md). Historical experiment decisions are frozen in [`ARCHIVE-DOGFOOD-CONTINUITY-stage4h-stage4i-ingestion-notebooks.md`](../Reports/ARCHIVE-DOGFOOD-CONTINUITY-stage4h-stage4i-ingestion-notebooks.md).

---

## §1 Mission and experimental invariant

**Mission:** Build and inspect one coherent Campaign 1 rehearsal World through Sessions 1–10 so we can learn whether DungeonBuddy can accumulate campaign memory chronologically rather than producing ten isolated recap graphs.

**Experimental invariant:** For every Session `N` from 1 through 10, extraction consumes the exact canonical observed recap plus deterministic stable campaign identity and **only** the admitted rehearsal World head produced through Session `N-1`; its reviewable candidate is durably saved before publication; exact recap source authority is admitted before publication; accepted output advances the isolated rehearsal World; and the resulting head becomes the only prior-World identity context available to Session `N+1`.

The chain must be causally historical:

```text
stable Campaign 1 identity anchors + genesis rehearsal World
  ↓
Session 1 canonical recap
  ↓
S1 candidate (durable)
  ↓
source admission + review/publication
  ↓
rehearsal head through S1
  ↓
Session 2 canonical recap + identity context from head through S1
  ↓
...
  ↓
rehearsal head through S10
```

Never use the current production Eldyrwild head, Session 11+ facts, later campaign summaries, or final-corpus hindsight as extraction context for an earlier session.

### Forcing question

> **After ten chronological sessions, does this look like accumulated campaign memory — stable people/places/things gaining source-linked history and relationships — or like ten document parses piled into one graph?**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | Yes. The slice is one chronological rehearsal pipeline whose output is the S10 rehearsal head + per-session durable candidates/receipts. |
| Most likely false success | High node count and rich recap mentions while recurring identities fragment, PCs become NPCs, relationships fail publication, or future knowledge leaks backward. |
| Most likely adversarial sequence | S3 mints a duplicate identity → duplicate enters S3 head → S4 ledger treats both as canonical → fragmentation compounds through S10. |
| Easiest owning boundary to under-test | Extraction context actually derived from the exact prior rehearsal head rather than a current/final World or a static corpus-wide ledger. |
| Fact that forces stop/split | Full DungeonMind relationship-vocabulary redesign, production schema change, production UI work, or inability to preserve historical-context ordering without a new durable architecture. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | Archive report for #710/#711 plus current DungeonMind governed write/read contracts. |
| Base revision | Current `main` after this handoff lands; re-anchor and record exact SHA before implementation. |
| Historical predecessors | PR #710 closed unmerged; PR #711 closed/superseded unmerged. Their code is not ancestry. |
| Existing parallel notebook | PR #713 remains historical/active C2 rehearsal evidence; do not modify it. |
| Exact input consumed | Canonical raw Campaign 1 observed recaps Sessions 1–10 under `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/`. |
| Evaluator-only authority | Existing hand-authored C1S1 candidate-graph gold. Never pass gold into model prompts, identity context, deterministic enrichment, or candidate construction. |
| Stable campaign identity | Campaign 1 `_party_registry.json` and corpus-resident identity registries/hubs. |
| Prior-World identity context | Isolated rehearsal World head through N-1 converted via existing World→known-entity machinery. |
| Model | `deepseek/deepseek-v4.1-flash`, reasoning disabled. No model comparison. |
| Named successor | Evidence-selected productionization / larger chronological corpus build after this experiment. |
| What remains false | This does not make DeepSeek a production default, publish to live Eldyrwild, solve all edge predicates, tune Agent, or finish recap/Plan/Play UX. |
| Runtime/state ownership | Dedicated output root + isolated DungeonMind rehearsal database. Live Eldyrwild authority must be refused fail-closed. |

### Canonical cohort

Use exactly the raw authoritative recap files corresponding to Campaign 1 Sessions 1–10:

```text
Session 1 - Recap 3-27-24.md
Session 2 - Finishing the Job.md
Session 3 - The Stone Bridge Flood.md
Session 4 - The Grotesque Tree of Hempholm.md
Session 5 - Underneath Hempholm.md
Session 6 - The Road to Miraholm.md
Session 7 - Passing Mirathorn Gates.md
Session 8 - Captain Lysandra Quest.md
Session 9 - Battle with the Meat Monsters.md
Session 10 - Battle with the Meat Monsters.md
```

The runner must resolve these by frontmatter `campaign_id: longmont-c1` + exact numeric `session`, not by trusting filenames alone. Require `document_class: play`, `canon_layer: campaign`, `temporal_scope: session_specific`, and `source_class: observed_session_recap`.

Explicitly reject as cohort authorities:

```text
Session Recaps/_normalized/**
Session Recaps/_breadcrumbed/**
Session Recaps/_session_memory/**
.backups/**
archive/staging/generated derivatives
```

Those may be inspected as historical evidence but must not become duplicate source authority.

### Existing C1 advantage

Campaign 1 `_party_registry.json` establishes the six PCs at Session 1. Existing carry-forward semantics therefore provide stable identity through Sessions 1–10 without inventing an early-session roster patch:

```text
Baergrom
Bonogo
Caelynn
Ephanna
Karsemine
Stafl
```

Carry-forward establishes **identity availability**, not proof that every member participated in every session. The default recap profile currently does not automatically attach party participation; preserve that distinction unless source evidence supports participation.

---

## §3 Frozen inherited extraction profile

Do not reopen model/context selection in this PR.

```text
model: deepseek/deepseek-v4.1-flash
provider: official DeepSeek through OpenRouter
provider routing: order=[DeepSeek]
allow_fallbacks: false
reasoning: disabled / none
semantic context: whole authored recap
source evidence: granular local source spans
transport: Chat Completions
response_format: json_object
schema contract: schema included in system instructions
local validation: mandatory
transport retry: bounded same-request resend
max attempts: 5 unless the implementation proves a smaller equivalent bound
```

A retry may repeat the identical semantic request after transport/format failure. It must not rewrite the prompt, ask another model to repair semantics, or silently weaken validation.

### Deliberate graduation from #710/#711/#713

The implementation may **read and narrowly transplant/reimplement** the proven DeepSeek provider seam from the old experiment branches, but those PRs remain unmerged.

Do not cherry-pick notebook commits wholesale.

The review must identify which lines/concepts were graduated and prove they preserve:

```text
provider pin
no fallback
reasoning disabled
json_object contract
mandatory local validation
bounded same-request resend
usage/cost/timing accounting
secret non-disclosure
```

---

## §4 Chronological context contract

This is the primary new experimental variable.

### 4.1 Session 1 seed

Session 1 receives:

```text
canonical Campaign 1 PC identities from party registry
safe standing campaign identity registries/hubs available at campaign start
empty/genesis isolated rehearsal World
Session 1 recap bytes
```

It must **not** receive identities/facts learned only from Sessions 2–10.

### 4.2 Sessions 2–10 seed

For Session `N`, construct known-entity context from:

```text
A. deterministic campaign identity anchors
   +
B. canonical known entities derived from the exact rehearsal World head through N-1
```

Use existing `known_entities_from_world_graph(...)` / `extra_known_entities` seams rather than inventing a parallel identity protocol.

The production extraction controller currently does not thread `extra_known_entities` through `ProductionExtractionRequest`; a narrow experiment seam may be added under this lease.

Party anchors win collisions with World-derived known identities.

### 4.3 Identity-only prior-World context

Default prior-World prompt context should expose only what is necessary to recognize existing identity:

```text
canonical node id
kind
label
aliases / safe match terms
campaign scope as needed
```

Do not dump the full accumulated World fact history into every extraction prompt in this slice. The question is whether identity carry-forward improves graph accumulation without hindsight/noise. Rich fact retrieval for extraction is a future ablation if identity-only context proves insufficient.

### 4.4 PC authority

Roster/corpus identity determines PC kind. The model does not decide whether a known PC is an NPC.

Required behavior:

```text
known roster PC + recap mention
→ observations/facts/edges attach to canonical PC identity
→ published kind remains pc
→ no duplicate NPC-shaped character represents the same PC
```

The existing party seed shape emits generic `character` with `corpus_ref.type=pc`, while current generic contribution mapping maps `character → npc`. This experiment must add the smallest deterministic identity-aware publication rule needed to keep rostered PCs as `pc`.

Do not globally redefine every `character` as PC. Unknown/unseeded characters remain ordinary extraction subjects.

---

## §5 Source admission and candidate durability

Every session must create/admit the exact raw recap source before its candidate is published:

```text
SourceArtifact / SourceRevision
source_domain: recap
campaign_id: longmont-c1
session_id: session-N
URI: exact canonical raw recap
revision: exact SHA-256 of source bytes
source spans: resolvable against those exact bytes
```

No source-authority compatibility transform may upgrade planning/seed material in this experiment because the cohort is observed recaps only.

### Candidate-first durability

For every Session N, persist before publication:

```text
candidate_graph.json
source_span_index.json
extraction run identity
model/provider/transport receipt
request/retry/cost/timing receipt
context receipt:
  party anchor identities
  prior World revision id
  World-derived known entity ids
  fingerprints/counts
```

Once the candidate is saved and fingerprinted, provenance or publication repair must be replayable with **zero new model calls**.

Do not delete or overwrite a candidate because later publication fails.

---

## §6 Publication and edge truthfulness

Publish only to an isolated DungeonMind rehearsal database. Refuse the live Eldyrwild authority / known live port fail-closed.

For each session, attempt the normal governed prepare/review/confirm path against the exact current rehearsal head.

### No silent node-only success

Do not treat `non_edge_fallback` as successful graph publication.

For every session report separately:

```text
edges_extracted
edges_with_canonical_endpoints
edges_with_admitted_predicates
edges_publishable
edges_published
```

If relationships cannot publish because DungeonMind lacks mappings, preserve the candidate and record the exact predicates/endpoints/blockers. The experiment may continue **only if** node/object publication can advance the chronological identity head without falsely claiming relationship success, and the report marks relationship publication PARTIAL/FAILED for that session.

A need to design a broad new relationship vocabulary is a stop/split into a successor. Do not consume this experiment by solving all graph semantics.

### Chronological commit rule

Session N+1 may begin only after Session N has a truthful disposition:

```text
A. published enough admitted identity/object state to define head N
or
B. explicit operator-approved experimental node/object partial publication with edge gap recorded
```

If Session N extraction itself fails, source authority is unresolved, or no truthful head N can be produced, stop the chronological chain. Do not skip forward because N+1 would no longer be testing the declared context invariant.

---

## §7 Evaluation contract

This experiment is not a scalar benchmark contest.

### 7.1 Session 1 hard witness

Use the existing C1S1 hand-authored candidate-graph gold strictly as **evaluator-only** authority.

Report at least:

```text
gold node identities represented / missing / fragmented
gold relationship intents represented / missing / unpublishable
gold source anchors/evidence resolvable
six PCs attached to canonical PC identities
novel Session 1 entities preserved
obvious false/document-shaped entities
```

Never put gold labels, expected aliases, edges, or anchor language into generation context.

### 7.2 Sessions 2–10 graph-growth metrics

Per session report:

```text
source bytes / evidence spans
model HTTP attempts / retries
wall time / cost / input/cache/output usage where available
candidate nodes
candidate edges
new candidate identities
candidate mentions attached to pre-existing canonical identities
candidate identities that appear to duplicate a pre-existing identity
PC mentions attached to canonical PCs
PC duplicate/NPC-shaped mints
novel entities preserved
source/evidence coverage
published objects/assertions
edge publication funnel
World object count after commit
World edge count after commit
World revision id
```

The useful identity metric is not “how many nodes did we extract?” It is:

> **When the recap refers to something the campaign already knows, did the new evidence attach to that durable thing?**

### 7.3 Cumulative graph review after Session 10

Generate a compact, inspectable graph review packet showing:

```text
recurring PCs
recurring NPCs
recurring locations
recurring creatures/threats
major factions/groups
major items/clues
session/event history
relationships that published
relationships that failed publication
identity/alias clusters that still look fragmented
objects with implausibly large/noisy fact histories
objects that accumulated useful multi-session history
```

Use actual graph contents to choose witnesses. Do not preregister a list of later C1 facts into model context.

Human review should answer:

```text
1. Does a recurring entity get richer across sessions, or get reminted?
2. Can we inspect where every important claim came from?
3. Are small continuity facts retained on useful identities?
4. Does historical/current state remain understandable rather than flattening into one blob?
5. Do relationships make the graph meaningfully navigable, or are we still building node islands?
6. Would this graph be more useful than reopening Sessions 1–10 individually?
```

### 7.4 Rich recap projection witness

If the ordinary existing recap projection can consume the isolated rehearsal World without extra product code, use one early and one late session (recommend S1 and S10) as a manual dogfood witness:

```text
canonical recap prose
+ inline mentions
+ correct PC badges
+ openable projected objects
+ provenance/source open/highlight
```

This is evidence, not permission to add UI work. If product projection needs new UI code, record the blocker and keep the experiment centered on graph construction.

---

## §8 Speed / spend contract

This experiment intentionally buys **one** extraction per session, not repetitions or model arms.

```text
paid semantic runs: 10 maximum planned sessions
model variants: 1
reasoning variants: 1
repetitions/session: 1
```

Before any paid call, census exact source bytes/spans and print projected request count.

After each session, record actual cost/time before continuing. A single-session result may be stochastic; this experiment accepts that limitation because its main signal is chronological identity accumulation across ten heterogeneous recaps.

Do not rerun a session merely because quality looks imperfect. Rerun only for a classified transport failure after the bounded same-request retry contract has failed and the operator explicitly approves another semantic execution.

The runner should support:

```text
census       zero model calls
run --through N
resume       resume only from verified saved candidate/publication receipts
report       zero model calls
replay N     zero model calls from saved candidate when repairing deterministic publication
```

Resume must verify source digest, candidate digest, previous World revision, and context receipt before continuing.

---

## §9 Files in scope — exclusive write lease

Expected paths may be adjusted only through the bounded discovery exception below.

| Action | Path | Purpose |
|---|---|---|
| Create | `tools/stage4l_c1_s1_s10_chronological_graph_rehearsal.py` | Exact cohort census, chronological extraction/publication orchestration, resume/replay/report. |
| Create | `tests/test_stage4l_c1_s1_s10_chronological_graph_rehearsal.py` | Cohort, ordering, future-leak, resume, isolated-DB, receipt and stop-chain proofs. |
| Create/graduate | `src/graph_memory/extraction/deepseek_category_graph_pass_client.py` | Minimal reviewed DeepSeek transport seam selected from prior notebook evidence. |
| Create/modify | focused test for DeepSeek client | Pin/no-fallback/reasoning/json validation/retry/secret-safety proof. |
| Modify | `src/graph_memory/extraction/graph_preview_runner.py` | Narrowly thread precomputed `extra_known_entities` into existing category extraction options. |
| Modify | `apps/live_control_server/services/graph_preview_runner.py` | Narrow recap wrapper seam for experiment-provided known-entity context if required. |
| Modify | `src/graph_memory/party_context.py` **only if required** | Preserve deterministic PC identity/kind without asserting participation; prefer publication override if smaller. |
| Modify | `src/graph_memory/candidate_graph_to_contribution.py` **only if required** | Narrow identity-aware `pc` kind preservation for known roster anchors; do not globally change character semantics. |
| Create | `tests/...` focused PC-kind/known-entity publication test(s) | Prove canonical roster PC stays `pc` and unknown character behavior is unchanged. |
| Create | `out/stage4l_c1_s1_s10_chronological_graph_rehearsal/REPORT.md` | Sanitized experiment report suitable for PR review. |
| Create | `out/stage4l_c1_s1_s10_chronological_graph_rehearsal/receipts/*.json` | Sanitized deterministic run/publication receipts; no secrets/raw provider payloads. |
| Modify | this HANDOFF only if execution findings/stop report need an exact historical addendum | Handback/status only; do not rewrite the experiment contract after paid execution. |

**Bounded discovery exception:**

```text
Directories:
  src/graph_memory/extraction/**
  apps/live_control_server/integrations/dungeonmind/**
Maximum additional runtime paths: 4
Allowed path kinds:
  existing owner of World-head read → KnownEntity conversion;
  existing owner of source admission / governed publication;
  existing rehearsal DB safety guard;
  exact tests for those seams.
Decision rule:
  only when the named path already owns a contract explicitly required by §1;
  record the reason in the handoff before or with the first edit.
```

**Bounded-discovery record (implementation):**

- `apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py` — the existing owner must apply the requested World scope before validating a recap artifact and persist DungeonMind's canonical `session_recap` domain key.
- `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py` — the existing governed-publication owner must rehydrate sealed `source_extraction` evidence from the admitted recap pair instead of beginning with an empty evidence view.
- `src/graph_memory/extract_identity_gate.py` — the existing identity-aware publication owner is the narrowest seam that can preserve a resolved `corpus_ref.type=pc` without globally redefining `character`.

These are three of the maximum four additional runtime paths. They directly own §4.4/§5 and are covered by focused fail-closed tests.

No other path is implicitly leased.

---

## §10 Explicitly out of scope / collision boundary

| Path/capability | Why this slice must not touch or claim it |
|---|---|
| `corpus/eldyrwild-markdown/**` | Exact source bytes are experimental authority; do not edit corpus to improve extraction. |
| `_normalized/**`, breadcrumb/session-memory derivatives | Not cohort authorities. |
| `evals/graph_memory_layer/examples/session_1_candidate_graph_gold/**` | Evaluator-only frozen witness; never edit to fit output. |
| `MODEL_POLICY.json` | This is an explicit experiment model, not production model policy. |
| production UI / Plan / Play / Ingest styling | Graph rehearsal only. |
| Agent tuning | Separate capability. |
| Combat integration | Separate capability. |
| DungeonMind schema redesign | Stop/split. |
| broad relationship vocabulary redesign | Stop/split; report predicate census first. |
| live Eldyrwild World database | Never mutate. |
| PR #713 branch/files | Parallel historical C2 experiment; read-only evidence. |
| PR #712 branch/files | Separate C2 corpus lane. |

---

## §11 Implementation contract

```text
Input:
  canonical C1 raw recaps S1..S10
  Campaign 1 stable identity registries
  isolated rehearsal World genesis/head
  selected DeepSeek extraction profile

For N in 1..10:
  prove exact source metadata + digest
  admit exact recap source authority
  derive deterministic party identity context
  derive World known-entity context from head N-1 only
  record context receipt
  run one DeepSeek candidate extraction
  validate + persist candidate and receipt
  score/inspect candidate (S1 includes frozen gold evaluation)
  prepare governed contribution
  preserve deterministic PC kind
  attempt relationship publication truthfully
  confirm into isolated rehearsal World
  record new immutable World revision
  verify new head
  continue only from that head

Output:
  durable candidate_graph.json × up to 10
  exact context/source/model/publication receipts × up to 10
  isolated rehearsal World head through S10
  cumulative graph-quality report

Invariant:
  Session N never sees World knowledge from N or later before its own extraction,
  and every published claim remains linked to the exact admitted recap source.
```

### Replay / idempotency

```text
same saved candidate + same admitted source + same parent World revision
  → deterministic prepare/review package identity where the owning contracts guarantee it;
  → no model call required.

changed source digest
  → fail closed; candidate is stale for that source.

changed prior World revision/context receipt
  → fail closed for chronological resume; do not silently continue.

publication failure after candidate persistence
  → candidate remains durable and replayable.
```

### Trust boundary

Verifies:

```text
source bytes/digest/session/campaign/source class
provider/model routing identity
local structured-output validity
candidate evidence refs
prior World revision used for context
known-entity context fingerprint
publication parent/head revision
isolated DB target
```

Records without pretending to prove:

```text
perfect entity reconciliation
perfect temporal semantics
perfect relationship vocabulary
stochastic stability from one sample/session
full-corpus readiness beyond S1..S10
```

---

## §12 Evidence required for experimental PASS

This PR is intentionally unmergeable, so **PASS means trustworthy experiment completion**, not merge approval.

| Guarantee | Owning boundary | Required evidence | Stop condition |
|---|---|---|---|
| Exact C1 S1–S10 cohort only | runner preflight | manifest/census with raw paths + SHA-256 + metadata | missing/duplicate/derivative source |
| No future World leakage | runner/context builder | receipt per N names exact prior revision and known IDs; test injects future node and proves exclusion | cannot prove historical head |
| Stable PC identity | party/identity + publication | S1 gold + focused test + per-session report; rostered PCs remain `pc` | PC demoted/minted as NPC duplicate |
| Candidate durability | extraction run store | candidate digest exists before publication; replay test makes zero model calls | publication owns only copy |
| Source authority | source admission/governed write | every published assertion evidence resolves to exact recap artifact/revision/span | scope_unknown/other source domain/silent fallback |
| Chronological head advance | DungeonMind rehearsal DB | parent/child revision chain S1→S10 | skip/reorder/advance from wrong head |
| Edge truthfulness | candidate + governed write | extracted→published funnel per session; blocked predicates enumerated | node-only fallback reported as success |
| C1S1 known quality | evaluator | frozen manual gold comparison, no gold leakage | gold used in generation/context |
| Useful cumulative graph | human review packet | recurring identity/history witnesses through S10 | report is counts only |
| Isolation | rehearsal guard | live DB refusal test + receipt target identity | any write can reach live Eldyrwild |
| Cost/time honesty | provider/runner | actual attempts, retries, usage/cost/wall per session | failed paid attempts omitted |

### Zero-cost gates before first paid call

At minimum:

```text
1. re-anchor exact main and record SHA;
2. verify #710/#711 archived/closed and this PR is a fresh branch;
3. prove exact 10-source raw cohort and metadata;
4. prove C1 party roster resolves six canonical PCs at S1 and carries forward for identity;
5. prove the runner rejects _normalized/derivative paths;
6. prove provider pin/no-fallback/reasoning-none/json_object/local validation/retry contract;
7. prove secrets cannot enter logs/receipts;
8. prove isolated rehearsal DB refusal of live authority;
9. prove prior-World known-entity extraction can be generated from a synthetic N-1 head;
10. prove future/head-N entity cannot leak into context for N;
11. prove known roster PC publishes as pc while unknown character behavior stays unchanged;
12. prove saved-candidate replay makes zero model calls;
13. prove Session 1 gold is evaluator-only and absent from generation/context fingerprints;
14. run focused tests, relevant graph-memory tests, Ruff, and git diff --check.
```

### Suggested execution cadence

Do not launch all ten blindly.

```text
Phase A — S1
  run S1
  inspect against frozen C1S1 gold
  verify six PC identities + source authority + publication + edge funnel
  STOP if experiment mechanics are wrong

Phase B — S2..S5
  continue chronologically
  generate intermediate graph-growth report
  inspect recurring identity accumulation
  STOP if fragmentation compounds or context provenance is wrong

Phase C — S6..S10
  continue chronologically
  generate final graph report
  inspect transition into Mirathorn / recurring NPCs / threats from actual graph output
```

This is still one experiment and one PR. The phased gates exist to save money/time, not to create three separate slices.

---

## §13 Required handback

Return with:

```text
exact PR head / execution SHA
exact source manifest + fingerprints
model/provider/transport/reasoning identity
paid attempts including failures/retries
actual total cost + total wall
per-session receipts S1..S10
exact rehearsal DB identity (sanitized) and World revision chain
candidate digest per session
prior-World context revision + known-entity count/fingerprint per session
PC canonical-attachment summary
new-vs-known identity summary
fragment/duplicate candidate summary
edge extraction/publication funnel by session
source/evidence admission summary
C1S1 frozen-gold comparison
cumulative S10 graph review packet
known quality debt
explicit forcing-question verdict
```

The final verdict uses one of:

```text
PASS — chronological graph accumulation is materially coherent enough to widen
MIXED — useful accumulation exists but one named blocker should be isolated next
FAIL — graph still behaves like disconnected/reminted document parses
```

Do not use `PASS` merely because all ten API calls completed.

### Decision produced by this experiment

The report must recommend exactly one next direction, selected from observed evidence, for example:

```text
widen chronological ingestion to more C1 sessions
identity/reconciliation correction
relationship predicate publication slice
temporal/current-state correction
source/provenance correction
context contract refinement
ranking/projection dogfood
```

Do not preselect the answer before the S10 graph exists.

---

## §14 Review / acceptance rubric

- [ ] Fresh branch from current main; no ancestry dependency on #710/#711/#713 notebook code.
- [ ] Exactly one experiment capability: chronological C1 S1–S10 graph rehearsal.
- [ ] #710/#711 durable lessons consumed from the archive report, not re-litigated with another model matrix.
- [ ] Raw authoritative recaps only; no derivative source duplication.
- [ ] Whole-document semantic context + local evidence anchors preserved.
- [ ] C1 stable PC identity is deterministic and stays `pc`.
- [ ] Prior World context is historical N−1 only and identity-focused.
- [ ] Every candidate is durable before publication and replayable without inference.
- [ ] Exact recap source authority is admitted before ordinary World publication.
- [ ] Publication targets isolated DungeonMind only.
- [ ] Relationship failure is visible; no `non_edge_fallback` success claim.
- [ ] Existing C1S1 gold is evaluator-only and actually used to inspect S1.
- [ ] Per-session graph-growth metrics and cumulative human graph review are produced.
- [ ] One-run/session limitation is stated honestly.
- [ ] Actual changed paths stay inside §9 / bounded discovery.
- [ ] Final report answers the forcing question and identifies one evidence-selected successor.

## Stop conditions

Stop and report rather than widening when:

- canonical S1–S10 raw recap authority cannot be resolved uniquely;
- stable C1 PC roster cannot be used without changing corpus source truth;
- historical N−1 World context cannot be proven without reading future/current production state;
- source admission requires rerunning inference;
- candidate output is not durable before publication;
- PC kind can only be fixed by globally changing all `character` semantics;
- publication requires broad DungeonMind schema/predicate redesign;
- a session cannot produce a truthful next World head;
- live Eldyrwild cannot be guarded fail-closed;
- evaluator gold would need to enter generation context;
- a second independent product/UI/Agent/Combat capability appears.

Report using the repository stop format from `AGENTS.md` / the handoff template.
