# AGENT — test routing instructions at the question boundary

ACTIVE serial PRIME proof-only lease at294b48309c3e07799600131855d3b22cdf3b70cd,
branch codex/routing-question-instructions, existing Buddy context-loop checkout.
No runtime adoption: operator requires evidence before routing redesign.
Exclusive writes: evals/utterance_intent/, tests/test_utterance_intent_proof.py,
this handoff, predecessor context-ablation settlement, ROADMAP-demo.md. One PR.
Private .pytest_cache owns frozen inputs/raw results. No service/data writes.

SDK inspection confirms DecisionQuestion.question becomes TypeSafe instructions;
state is separately passed context. Existing prototype puts routing semantics in
state.routing_guidance and asks only a short question. This experiment moves the
same guidance verbatim into the actual question instructions, preserving all other
state/history/options/descriptions. One-call leaf choice derives Discuss/Create;
no extra sequential model call. Compare intent_flat and instruction_flat only.

Use retained private dogfood as explicitly exploratory regression and fresh frozen
constructed holdouts as limited generality probes. Preserve existing retrieval
benchmark question probes, with explicit answer/retrieve acceptable branches;
no downstream retrieval is claimed. Existing live Play Execute taxonomy gap is
unchanged and must not be called solved. Gold/case identity never reaches model.
Freeze inputs/policy/code before calls, two repetitions/all variants/no retries.
Full private TypeSafe sharing was explicitly approved. Exact prompt moves and
usage/errors must be auditable. No selective tuning/resubmission of scored cases.

Independent Bugbot reviews exact cumulative diff and results. A positive result
would support only this prompt hypothesis, not product execution, full-context
routing, latency noninferiority or operator acceptance. Runtime design/adoption
remains separate; failed variants remain preserved.

Operator clarified after inference: brainstorming a requested list of ten names
should stage a page suggestion. Add host-only adjudication of stored responses,
keyed by exact question digest and explicit authority; never rewrite frozen gold
or call the model. Report raw counts and equal-utterance weighting. This reverses
the initial raw fork comparison on the repeated-name cohort; it does not establish
a unique-utterance gain or runtime readiness. Original evidence remains intact.

Operator also wants visible table construction on the page: real progress cues,
progressive rows/fields and a preview-render beat, directly editable before Save.
This slice records that authoring direction; it does not implement streaming or
claim intermediate generation events currently exist.
