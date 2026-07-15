# Evaluation specification — Hermes × World Graph interaction

**Status:** PROPOSED  
**Principle:** deterministic tests prove contracts; agent-policy evals prove routing; product integration proves alignment; real dogfood proves usefulness.

## Evaluation layers

### 1. Contract tests

Prove:

- request/result schemas;
- scope injection and rejection of foreign context;
- visibility/admissibility filtering;
- one revision per turn;
- bounds and exact-ID behavior;
- claim authority class serialization;
- source-anchor/read integrity;
- graph reference versus source citation creation;
- stable error semantics;
- persistence round trips for referent and ledger summaries.

### 2. Deterministic retrieval tests

Prove:

- exact label/alias/ID candidate resolution;
- ambiguity without first-win;
- object claim packets;
- neighborhood/path/timeline/compare operations;
- claim-family coverage diagnostics;
- readable/unreadable/missing anchors;
- historical revisions;
- source/graph conflict representation;
- selected node revalidation;
- player admissibility filtering.

### 3. Agent policy tests

Run real Hermes/model calls against frozen graph fixtures and grade:

- operation choice;
- no-tool rate when retrieval is required;
- unnecessary-tool rate when initial packet suffices;
- multi-step expansion;
- source read when exact source requested;
- no source read for ordinary accepted graph facts;
- ambiguity clarification;
- inference disclosure;
- no Markdown fallback on graph gap;
- structured answer support mapping;
- recovery after partial/unreadable source;
- correction requests remain noncanonical.

Use deterministic validators for structural scoring and a human rubric for usefulness. Never use an LLM judge as the sole authority for factual correctness.

### 4. Product integration tests

Prove:

- panel and Hermes consume the same retrieval session;
- candidate versus used claims are visually distinct;
- answer references focus panel objects;
- selected-node follow-up sends durable referent;
- thread/campaign/focus isolation;
- reload preserves referent pointers without stale factual authority;
- source citation opens exact bounded content;
- unreadable source is explained;
- trace explains acceptance/abstention/error;
- old legacy turns display safely.

### 5. Real-agent dogfood

Evaluate during actual GM prep:

- naturalness;
- actionability;
- latency/friction;
- ability to modify encounter thinking;
- ability to recover from unexpected player choices;
- comprehension of fact/source/inference/gap distinctions;
- whether the GM trusts and uses navigation;
- whether abstention is precise rather than obstructive.

## Required scenario matrix

| # | Scenario | Required outcome |
|---:|---|---|
| 1 | Tripod exact lookup | unique resolution; graph-grounded role/location answer |
| 2 | Tripod pronoun follow-up | current referent resolves; fresh current-revision claims |
| 3 | Tripod prep implications | facts and inferences visibly separated |
| 4 | accepted claims, unreadable sources | partial graph answer; source warning; no fake citation |
| 5 | readable source | source read and source-verified detail |
| 6 | ambiguous alias | candidate choice/clarification; no first-win |
| 7 | relationship traversal | direct edge claims and meaningful connected objects |
| 8 | multi-object comparison | aligned claim classes; asymmetric gaps shown |
| 9 | current-state/timeline | current state plus chronology without revision mixing |
| 10 | historical revision | explicit historical label and pinned revision |
| 11 | graph gap, Markdown has answer | graph gap; no hidden Markdown fallback |
| 12 | missing relationship, known endpoints | endpoint facts + relationship gap |
| 13 | stale conversation versus current graph | current graph wins; stale prose only intent context |
| 14 | source/graph disagreement | conflict outcome; both shown |
| 15 | GM-authored graph assertion, no prose source | graph-grounded fact; provenance shown |
| 16 | player admissibility denial | no leaked IDs/content |
| 17 | selected-node follow-up | selection is strongest referent |
| 18 | Hermes calls no tool | only acceptable if initial claim packet suffices; otherwise policy failure |
| 19 | tool starts, no completion | execution error with exact reason |
| 20 | anchor unreadable | graph answer + unreadable state |
| 21 | source integrity failure | fail closed for source-backed detail; explicit integrity error |
| 22 | creative brainstorm | known facts separated from suggestions |
| 23 | proposed correction | noncanonical proposal preview only |

## Additional adversarial scenarios

- candidate label injection/citation-like prose;
- source anchor from another revision;
- selected node deleted/recreated under same label;
- parallel thread referent leakage;
- several readable anchors with conflicting content;
- truncated neighborhood that omits requested relation family;
- model returns unsupported factual sentence in otherwise valid answer;
- source read succeeds but model does not cite/use it;
- model cites anchor it never opened;
- graph claim becomes superseded between turns;
- tool callback is malformed or absent;
- retrieval operation exceeds bounds;
- foreign campaign ID embedded in conversation history.

## Gold fixture design

Each scenario fixture contains:

```json
{
  "question": "...",
  "scope": {},
  "explicit_referents": [],
  "expected_candidates": [],
  "expected_claim_ids": [],
  "expected_forbidden_claim_ids": [],
  "expected_source_read_policy": "required|optional|forbidden",
  "expected_outcome_states": [],
  "expected_gap_codes": [],
  "expected_inference_policy": {},
  "human_usefulness_notes": "..."
}
```

Freeze at least:

- Tripod/Under-Hymn/Mireward slice;
- ambiguous aliases;
- current/historical revisions;
- GM and player scopes;
- readable/unreadable/conflicting sources;
- graph-native GM assertion.

## Metrics

### Resolution and retrieval

```text
referent resolution accuracy
ambiguity precision/recall
claim recall at fixed bounds
irrelevant claim rate
path correctness
coverage-gap precision
revision/scope violation rate
```

### Source behavior

```text
required-source-read success rate
unnecessary-source-read rate
unreadable-source honesty rate
source integrity false-accept rate (target 0)
source/graph conflict detection rate
```

### Answer support

```text
supported factual statement rate
unsupported factual statement rate (target 0 for accepted output)
correct graph-reference mapping
correct source-citation mapping
inference disclosure precision/recall
unnecessary abstention rate
partial-answer usefulness
```

### Agent efficiency

```text
tool/operation count
retrieval latency p50/p95
model latency p50/p95
tokens per successful task
redundant rediscovery rate
no-tool policy failure rate
```

### Product comprehension

```text
can GM identify what is graph fact?
can GM identify what source was opened?
can GM identify inference?
can GM explain why answer was partial/withheld?
can GM navigate from answer to object/source?
```

## Acceptance gates by rebuild slice

### Gate A — authority/claim contracts

- all accepted claim classes deterministic;
- graph references cannot be created for derived summaries;
- source citations require successful read;
- no current security/revision regression.

### Gate B — shared retrieval session

- panel and agent session IDs identical;
- exact Tripod candidate/claim packet deterministic;
- candidates and used claims distinct;
- no duplicate independent preflight retrieval.

### Gate C — agent expansions

- ≥95% correct operation choice on deterministic intent suite;
- no-tool policy failure <5% on required-retrieval scenarios;
- zero scope/revision violations;
- bounded tool behavior.

### Gate D — answer validator/UI

- zero unsupported accepted graph-fact sentences in gold suite;
- unreadable-source scenario produces graph answer, not fake citation or full abstention;
- trace explains all 23 required scenarios.

### Gate E — real dogfood

Tripod journey and at least ten varied campaign-prep journeys must be useful without operator interpretation of developer traces. Require explicit operator acceptance before continuity/session work.

## PR011 unblock gate

PR011 remains blocked until:

1. authority ADR accepted;
2. shared retrieval session and claim ledger merged;
3. source/read/reference distinctions merged;
4. selected-object referent protocol merged;
5. required scenario suite passes;
6. real Tripod dogfood passes;
7. correction proposal seam reviewed;
8. obsolete read paths are identified for removal and no alternate truth plane remains.
