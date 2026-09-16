# HANDOFF — DOGFOOD-CONTINUITY: accepted-world question gauntlet v1

**Created:** 2026-09-15  
**Status:** DONE — MERGED as PR #728 @ `982cfe04c6c976f9c9147ef48f3b7c29b4feec00` (reviewed head `ac18bfc59f9f2cfaf152116006a7923ff74353d9`, 5 review cycles); successor is published-object addressability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY / semantic truthfulness`  
**Direction:** DESIGN → EVALUATE → REVIEW  
**Design authority base:** `main@fd6e90cee7fee259b6da427f275d1e507d2c3d04`  
**Activation gate:** satisfied — #722–#726 merged; real-main pristine current-corpus structural acceptance PASS; stewardship recovery COMPLETE  
**Dispatch base rule:** fresh current `main` containing this checked-in handoff; record exact evaluation branch base and exact runtime SHA in the report  
**PR topology:** `serial`  
**PR authorization:** open/update exactly one evaluation PR for this gauntlet only; no repair/successor PRs  
**PR title:** `DOGFOOD-CONTINUITY: run accepted-world question gauntlet`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Benchmark authority: [`evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md`](../../evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md).

---

## §1 Mission and evaluation invariant

**Mission:** bring up the real local DungeonBuddy read/Agent stack against the already-accepted 44-session DungeonMind World, recover the exact historical Campaign 1 Session 10 revision from that accepted lineage, then walk the existing 16-question C1 S1–S10 gauntlet twice: first through oracle-controlled retrieval, then through the real current Agent with no benchmark hints.

**Evaluation invariant:**

> Every Q01–Q16 judgment is bound to the same immutable accepted World and the same exact historical C1S10 revision; the graph is read-only; the real Agent receives only the natural-language question plus ordinary bounded product context; gold answers never enter Agent context; each Agent question starts a fresh independent session; raw retrieval/Agent evidence is preserved before grading.

This is the first semantic-truthfulness read of the graph that passed structural current-corpus acceptance. It is not another ingestion experiment.

### Why the historical C1S10 revision is mandatory

The accepted World continues beyond Campaign 1 Session 10:

```text
C1 S1 → ... → C1 S10 → C1 S11 → ... → C1 S17 → C2 S1 → ... → C2 S27
```

The 16-question gold was authored for facts available through C1 S10. Running it against the final 44-session head would permit future-session knowledge to leak into answers and would invalidate the benchmark.

Therefore:

```text
accepted database/world = real 44-session acceptance authority
benchmark revision      = receipt_child_revision for longmont-c1/session-10
terminal acceptance head = lineage proof only, NOT the query revision
```

Do not substitute `rev:cce8d24621d65a018d3e2922552f56f2` as the query pin merely because it is the accepted terminal head.

---

## §2 Fixed authorities

### Structural acceptance authority

`Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`

Passing run:

```text
run_id:        execute-2026-09-16T020204Z-6e3b812a
world_id:      dogfood-current-corpus-acceptance-v1
database:      dmb_current_corpus_acceptance_v1
host/port:     127.0.0.1:54329
terminal_head: rev:cce8d24621d65a018d3e2922552f56f2
model_calls:   44
graph_writes:  45
stop:          null
```

The passing run's local artifact root is:

`out/graph_memory/current_corpus_admission_acceptance_v1/execute-2026-09-16T020204Z-6e3b812a/`

`session_ledger.json` is expected to contain the exact child revision after every accepted recap. Resolve the benchmark revision from the row where:

```text
campaign_id == longmont-c1
session_id  == session-10
```

and bind `receipt_child_revision` as `BENCHMARK_REVISION`.

If the passing run artifact is unavailable, recover the same immutable revision from the accepted DungeonMind revision/provenance lineage. Do not guess it, use a rehearsal-world revision, or rerun 44 paid extraction calls simply to rediscover it.

### Benchmark authority

`evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md`

Benchmark ID:

`longmont-c1-sessions-01-10-graph-query-v1`

Question count: 16.

The checked-in gold owns exact question wording, difficulty, required concepts, negative constraints, evidence references, and scoring semantics. Do not rewrite the questions in the runner or report.

### Existing evaluation design authority

`Docs/Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md`

Preserve its two-layer distinction:

1. oracle-answerable — does the graph + current retrieval API expose enough correct evidence?
2. Agent-answerable — can the real current Agent investigate and synthesize it without benchmark hints?

Preserve its primary failure taxonomy:

```text
A GRAPH COVERAGE FAILURE
B GRAPH CONNECTIVITY / IDENTITY FAILURE
C RETRIEVAL API FAILURE
D AGENT ORCHESTRATION FAILURE
E SOURCE / AUTHORITY FAILURE
F SYNTHESIS FAILURE
```

---

## §3 What remains false before this run

Structural PASS established only that all 44 sources could move through the production extraction/admission/write chain with exact revision continuity.

It did **not** establish:

```text
semantic truthfulness
semantic precision
semantic recall
graph query answerability
Agent answerability
source-authority preservation quality
model superiority
SEMANTIC MODEL SELECTION
```

This gauntlet may establish evidence about the first six. It must leave `SEMANTIC MODEL SELECTION = HOLD` unless a separate model-comparison design later earns a selection claim.

---

## §4 Runtime topology — spin up these terminals

The evaluation uses the existing product runtime. Do not build a benchmark-only answer backend.

### Terminal 0 — authority / revision resolver

Purpose: establish exact repository, database, World, lineage, and historical C1S10 revision before any question is asked.

Required checks:

```text
git HEAD recorded
passing acceptance run artifact identified
acceptance database reachable at loopback:54329
database name == dmb_current_corpus_acceptance_v1
world == dogfood-current-corpus-acceptance-v1
live current head == rev:cce8d24621d65a018d3e2922552f56f2
C1S10 row exists exactly once in accepted session ledger
BENCHMARK_REVISION = that row.receipt_child_revision
BENCHMARK_REVISION exists in DungeonMind
BENCHMARK_REVISION is an ancestor of accepted terminal head
no graph write is performed
```

Write the resolved identities to the run's `AUTHORITY.json` before continuing.

Do not print database credentials or API keys into artifacts.

### Terminal 1 — FastAPI product backend

Point the product World Graph authority at the acceptance DungeonMind database using the actual acceptance DSN already available in the operator environment.

Required environment intent:

```text
DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL = acceptance World DSN
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL    = separate safe Buddy application-state DSN
DUNGEONMIND_LIVE_SESSION_DIR                    = isolated temporary live-session fixture
OPENAI_API_KEY / provider credentials           = existing operator secret environment only
```

The Buddy application-state DSN must not equal the World Graph DSN.

Use a copied temporary live-session fixture rather than mutating committed `evals/c2_live_prep/live/session_22` files. The Hermes route is allowed to use a graph campaign lens different from the outer live packet; the nested World context for every benchmark turn remains C1.

Start the backend without auto-reload so one stable process/model/runtime configuration owns the run:

```bash
uv run uvicorn apps.live_control_server.main:app --host 127.0.0.1 --port 8000
```

Record the resolved Agent runtime/model policy once. Do not change model/provider settings between questions.

### Terminal 2 — Vite product UI

Bring up the real UI so the operator can inspect the same mounted product surface while the machine-readable benchmark is running:

```bash
pnpm --dir apps/live-control-ui dev
```

The scored gauntlet is captured through the HTTP product contracts so request/response/trace evidence is durable. The UI is an observational surface, not a substitute scoring path.

### Terminal 3 — gauntlet operator / capture driver

This terminal owns:

```text
readiness smoke tests
oracle retrieval operations
real Agent turns
raw request/response capture
trace capture
post-response grading
report generation
```

No operation from this terminal may mutate the World Graph.

---

## §5 Pre-question readiness gate

Do not begin Q01 until all of the following are green.

### 5.1 Exact historical projection

Call the ordinary World Graph projection/retrieval path with:

```text
world_id      = dogfood-current-corpus-acceptance-v1
campaign_id   = longmont-c1
scope_mode    = campaign
admissibility = gm
revision_pin  = BENCHMARK_REVISION
focus         = none
```

Require:

```text
returned revision_id == BENCHMARK_REVISION
returned world_id matches acceptance World
returned campaign_id == longmont-c1
historical pin is accepted even though is_head == false
no revision-not-found / integrity diagnostic
```

### 5.2 Retrieval smoke

Use the real retrieval endpoint:

`POST /api/live/world-graph/retrieval/search`

Search for one known C1 term such as `Torbin`.

Require a valid retrieval envelope. This is a transport/readiness test only; do not score it as Q01–Q16.

### 5.3 Agent smoke

Use the real Hermes-backed live query route:

`POST /api/live/query`

with:

```json
{
  "campaign_id": "<outer isolated live-fixture campaign>",
  "session": "<outer isolated live-fixture session>",
  "mode": "live",
  "query_backend": "hermes",
  "text": "<non-benchmark smoke question>",
  "world_graph_context": {
    "schema": "dmb_agent_world_graph_query_context_request_v1",
    "world_id": "dogfood-current-corpus-acceptance-v1",
    "campaign_id": "longmont-c1",
    "focus": {"kind": "none", "session_id": null, "campaign_id": null},
    "admissibility": "gm",
    "revision_pin": "<BENCHMARK_REVISION>",
    "scope_mode": "campaign",
    "selected_node_id": null
  }
}
```

Require:

```text
HTTP 200
mode == hermes_graph_agent
status == ok OR a truthful grounded/abstention product outcome
agent trace present
resolved graph revision == BENCHMARK_REVISION
no graph write
no committed live fixture mutation
```

If the Agent backend/provider is unavailable, STOP. Do not substitute another answer backend for the Agent layer.

---

## §6 Gauntlet execution — Q01 through Q16

Run questions in checked-in order. Do not change wording.

For every question create a question artifact directory, e.g.:

```text
out/graph_benchmark/current_corpus_question_gauntlet_v1/<run-id>/Q01/
...
out/graph_benchmark/current_corpus_question_gauntlet_v1/<run-id>/Q16/
```

### Layer A — oracle retrieval

The evaluator may know the gold and may deliberately choose sensible retrieval calls. The model does not participate in choosing the retrieval sequence.

Allowed production operations are the existing read contracts only:

```text
search
object
neighborhood
support/evidence
source-anchor read
complete-object when useful
```

For each question preserve:

```text
question text
ordered retrieval requests
ordered retrieval responses
matched node IDs
relationship IDs
assertion/attribute IDs
source anchor IDs
source content actually opened
coverage/truncation diagnostics
oracle synthesis notes
oracle_answerable: yes | no
primary failure bucket if no
```

The oracle question is narrow:

> Does the accepted graph at BENCHMARK_REVISION plus the current bounded retrieval API expose enough reachable, authority-correct information to construct the checked-in gold answer?

Do not silently fall back to repository/corpus Markdown to rescue an oracle miss. Gold source files are evaluator authority for grading, not an alternate retrieval backend.

### Layer B — real Agent

After the oracle artifacts for the question are saved, invoke the real current Agent using the exact question text.

Every Q01–Q16 Agent request must use:

```text
same world_id
same BENCHMARK_REVISION
campaign_id = longmont-c1
scope_mode = campaign
admissibility = gm
focus = none
conversation_history absent
hermes_session_id absent
hermes_session_pointer absent
benchmark hints absent
gold answer absent
must-include list absent
oracle retrieval sequence absent
```

Each question is a **fresh independent Agent turn/session**. Do not carry a Hermes session or prior benchmark answer forward. Q01 must not teach Q02; Q15 must not benefit from Q07's investigation.

Preserve before grading:

```text
exact request
raw product response
final answer
Agent status / grounding state
citations
full agent_trace available from product response
ordered tool events
retrieval outcomes
matched node/relationship/source-anchor IDs
observed model call count/model metadata when exposed
warnings/diagnostics
```

The Agent is forbidden from arbitrary repository/Markdown search as a hidden fallback. A graph miss must remain visible as a graph/retrieval miss.

### Layer C — grade only after evidence is frozen

Only after raw oracle + Agent artifacts for that question are written may the evaluator open/use its checked-in gold answer and must-include/must-not-claim rules for grading.

Use the existing benchmark semantics:

```text
FULL
  all required concepts present
  negative/authority constraints respected
  no unsupported certainty

PARTIAL
  directionally correct
  one or more required links/states/authority distinctions missing

FAIL
  contradicts source authority
  wrong identity merge
  planning laundered into played truth
  unsupported causal certainty
  materially wrong answer
```

Also assign one primary failure class A–F for every non-FULL result. If more than one contributed, record secondary classes separately but choose the earliest owning boundary as primary.

---

## §7 The 16-question stress ladder

Do not duplicate/re-author the gold in implementation code; this table is only an operator map. Exact wording and grading live in the benchmark file.

| Q | Stress target |
|---:|---|
| 01 | direct extraplanar-meat fact |
| 02 | mushroom → expert/location one-hop |
| 03 | Torbin ward commitment across sessions |
| 04 | Lysandra relationship evolution |
| 05 | Hempholm mushroom thread |
| 06 | Torbin multi-session danger chain |
| 07 | Lyra protest → Shepherd's Flock → meat distribution |
| 08 | guard infiltration evidence synthesis |
| 09 | ordered underground route reconstruction |
| 10 | learned combat/meat behavior synthesis |
| 11 | Sprite/fey-familiar temporal identity and final state |
| 12 | Lyra continuity warning |
| 13 | Torbin meat-exposure continuity warning |
| 14 | played truth vs `Looking Ahead` GM planning |
| 15 | end-of-S10 conspiracy operational picture |
| 16 | bounded inference: Shepherd vs Flock vs conspiracy |

Pay special attention to Q09, Q10, Q11, Q14, Q15, and Q16; they were intentionally designed to distinguish semantic coverage, identity continuity, retrieval ergonomics, source authority, Agent investigation breadth, and unsupported inference.

---

## §8 Failure interpretation

### Oracle failure

Use the first owning boundary:

```text
A — required proposition is absent from admitted World
B — proposition exists but identity/edges prevent coherent traversal
C — correct graph content exists but production bounded retrieval cannot expose it reasonably
E — proposition exists but source/temporal/planning authority is insufficient or wrong
```

Do not blame Agent orchestration for an oracle miss.

### Agent failure when oracle succeeds

Use:

```text
D — Agent chose an insufficient/incorrect investigation despite adequate tools
E — Agent retrieved material but mishandled played/planned/inference authority
F — Agent retrieved adequate correct evidence and still synthesized the wrong answer
```

A large `oracle answerable - Agent FULL` gap points toward Agent retrieval/orchestration/synthesis work.

A low oracle-answerable count means graph construction/publication/authority remains the bottleneck.

Do not compress these into one aggregate score and lose the distinction.

---

## §9 Artifact and report contract

### Untracked/raw run artifacts

Use:

`out/graph_benchmark/current_corpus_question_gauntlet_v1/<run-id>/`

At minimum preserve:

```text
AUTHORITY.json
READINESS.json
Q01/oracle.json
Q01/agent-request.json
Q01/agent-response.json
Q01/grade.json
...
Q16/...
SCORECARD.json
```

`AUTHORITY.json` must bind:

```text
runtime git SHA
acceptance run id
acceptance world id
acceptance database identity without credentials
acceptance terminal head
BENCHMARK_REVISION / C1S10 receipt child
benchmark ID
gold file SHA256 or git blob identity
Agent runtime/provider/model policy identity
run start/end timestamps
```

### Durable repository report

Create:

`Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md`

The report must include one row per question:

| Q | Oracle answerable | Agent grade | Primary failure | Agent tool calls | Source anchors | Short finding |
|---:|---|---|---|---:|---:|---|

And totals:

```text
oracle answerable: N / 16
Agent FULL:        N / 16
Agent PARTIAL:     N / 16
Agent FAIL:        N / 16
A/B/C/D/E/F counts
```

Also include qualitative findings for:

```text
identity continuity
multi-hop connectivity
ordered path retrieval
learned encounter facts
source/play-vs-plan authority
broad campaign-state investigation
bounded inference / abstention quality
```

No result may claim semantic quality outside the tested C1 S1–S10 question set.

---

## §10 Files in scope — evaluation write lease

This is an evaluation lane. Production code is read-only.

| Action | Path | Purpose |
|---|---|---|
| CREATE | `evals/graph_benchmark/run_current_corpus_question_gauntlet.py` | thin evaluator/orchestration/capture driver only, if needed to make the terminal workflow reproducible |
| CREATE | `tests/test_current_corpus_question_gauntlet.py` | deterministic tests for gold parsing, revision/request sealing, fresh-session/no-gold-leak request construction, and artifact shape |
| CREATE | `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md` | durable benchmark result and failure taxonomy |

**Bounded discovery exception:** one additional evaluator-only file under `evals/graph_benchmark/` is permitted if the runner needs a static schema/manifest for raw artifact serialization. It may not contain rewritten benchmark questions or gold answers; those remain sourced from the canonical gold Markdown.

### Explicitly read-only / out of scope

```text
apps/live_control_server/**
apps/live-control-ui/**
src/graph_memory/**
src/model_policy/**
MODEL_POLICY.json / model policy authority
candidate extraction prompts
Candidate Graph Admission
DungeonMind writes / schema / ontology
evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md
accepted World contents
```

If the gauntlet exposes a defect requiring any of those paths, record the failure and hand it back. Do not fix production during the benchmark and do not open a second PR.

---

## §11 Exact evaluator safeguards

The runner/operator must prove these conditions, not merely intend them.

### No future leakage

Every graph request/Agent trace must resolve to `BENCHMARK_REVISION`, not terminal head.

Any Q01–Q16 response trace showing a different revision is invalid and must be rerun after fixing the evaluation harness itself.

### No gold leakage

Before sending an Agent request, persist a sanitized request artifact and prove it contains only:

```text
question text
required live-query transport fields
pinned graph context
ordinary non-benchmark surface context
```

It must not contain:

```text
gold answer
must-include fields
must-not-claim fields
expected hops
oracle plan
failure taxonomy expectation
source evidence list copied from gold
```

### No cross-question contamination

Every Agent question starts without prior Hermes session IDs/pointers and without conversation history.

### No hidden corpus fallback

The Agent/oracle path may read source content only through graph-admitted source anchors and the existing product source-read contract. Evaluator inspection of gold/corpus happens after raw response capture and does not become answer context.

### No graph mutation

Capture World head before and after the complete gauntlet. It must remain exactly the accepted terminal head. Historical `BENCHMARK_REVISION` remains immutable.

### No product-session mutation

Use a disposable copied live-session fixture and verify the committed seed fixture bytes remain unchanged. Hermes graph turns should not append live events/jobs for this benchmark.

---

## §12 Evidence required for review

| Guarantee | Evidence |
|---|---|
| accepted authority mounted | `AUTHORITY.json` + direct head read |
| exact C1S10 historical pin | accepted session-ledger row + successful projection of same revision |
| no future leakage | all retrieval snapshots + Agent tool events bind same `BENCHMARK_REVISION` |
| no graph mutation | before/after accepted World head equality |
| no gold leakage | request-construction deterministic test + persisted requests |
| no cross-question memory | 16 fresh-session requests; no carried Hermes IDs/history |
| oracle layer is production retrieval | captured existing retrieval endpoint request/response artifacts |
| Agent layer is real current Agent | `/api/live/query`, `query_backend=hermes`, real trace/model metadata |
| source authority can be inspected | source anchors/read results preserved where used |
| benchmark complete | exactly Q01–Q16 each has oracle, Agent, grade artifacts |
| failure attribution is grounded | report links every non-FULL result to raw evidence + A–F class |

Deterministic evaluator tests must pass before paid Agent calls begin.

Run the real Agent gauntlet only after readiness and evaluator tests are green. Do not spend model calls debugging request serialization or revision selection.

---

## §13 Stop conditions

STOP and report; do not open a repair PR if:

- the acceptance database/World cannot be reached or no longer matches the recorded terminal head;
- the exact C1S10 accepted revision cannot be recovered unambiguously;
- the C1S10 revision is not in the accepted terminal lineage;
- product reads cannot serve the historical revision without production changes;
- Agent graph context silently resolves to current head instead of the requested historical pin;
- the Agent requires arbitrary corpus/repository fallback to answer;
- running the Agent would require changing model/provider policy mid-suite;
- a benchmark question cannot be parsed exactly from canonical gold;
- the World head changes during the read-only gauntlet;
- a required production fix appears.

A STOP is useful evidence. Preserve it at the first owning boundary.

---

## §14 Review decision signal

The first decision is not “did the Agent get a good grade?” It is:

```text
How many questions are oracle-answerable from this structurally accepted graph?
```

Then:

```text
How many of those can the current Agent answer FULL without benchmark help?
```

Interpretation examples remain the backlog contract:

```text
oracle 14/16, Agent 8/16
→ graph is broadly sufficient; invest next in Agent retrieval/orchestration/synthesis

oracle 7/16, Agent 6/16
→ Agent is using available graph reasonably; graph construction/publication remains bottleneck
```

Do not mechanically force one of these examples. Report the actual distribution and concrete failure classes.

Q14 authority behavior and Q16 bounded inference are especially important. A confident answer that launders planning or unsupported inference into fact is worse than a truthful abstention/qualification.

---

## §15 Completion rubric

This handoff is review-ready only when:

- [ ] exact current-main runtime SHA is recorded;
- [ ] accepted database/World/terminal head are verified without mutation;
- [ ] exact accepted C1S10 historical revision is recovered and lineage-verified;
- [ ] FastAPI product backend is running against acceptance World authority;
- [ ] Vite UI is available for observational inspection;
- [ ] retrieval smoke passes at exact C1S10 revision;
- [ ] real Hermes Agent smoke passes at exact C1S10 revision;
- [ ] deterministic evaluator tests pass before Q01;
- [ ] Q01–Q16 all complete oracle retrieval with raw evidence;
- [ ] Q01–Q16 all complete independent real Agent turns;
- [ ] no Agent request contains gold/evaluator hints;
- [ ] no Agent question reuses prior question conversation/session state;
- [ ] no graph request leaks beyond C1S10 revision;
- [ ] accepted World head is unchanged before/after;
- [ ] all non-FULL outcomes receive evidence-backed primary A–F attribution;
- [ ] durable report records oracle-vs-Agent results and qualitative semantic findings;
- [ ] `SEMANTIC MODEL SELECTION = HOLD` remains explicit;
- [ ] no second PR/successor/repair lane was opened.

After review, the steward—not the evaluation worker—uses the observed failure distribution to design exactly one next semantic-truthfulness/retrieval/Agent slice.