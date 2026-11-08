# RETRIEVAL: distinguish questions from Plan writing

Status: ACTIVE. Root owns this bounded slice under the operator's Q09 goal.

## Outcome, lane and topology

One serial PR from fetched main `38c3e11ff03f2d299c0b5c56249e456aa025eb86`, branch
`codex/q09-question-intent` in the existing isolated ingest-draft-navigation checkout.
No unmerged parent. PRIME explicitly confirmed no active lease on the classifier
or tests; its pending #2197/#2199/#2200 remain separate. No primary runtime lease.
Opening the PR is authorized; root has no merge/delivery lease. PRIME receives
the exact reviewed head for its standing merge process.

Correct semantic requested-work classification: asking for an explanation or
reconstruction stays conversational even when phrased imperatively. Availability
and placement apply only after identifying a request to write on the current page.
Preserve genuine writing without a target, different destinations, ambiguity and
explicit UI operation precedence. No keyword overrides or routing fallback.

## Evidence and scope checkpoint

Retained Q09 request/trace and actual2493-byte Jev request are in
`retrieval-benchmark-initial-cohort-v1` under the retained visualization workspace.
The question selected `write_unavailable` with no page target. Existing placement
instructions emphasize missing-target writing without clearly sequencing intent.
Independent design critique confirmed this boundary and the replay risk below.

Existing V1–V6 parent contracts reconstruct exact wire instructions during
authorization/proof checks. Do not rewrite those historical strings. Add one new
parent revision for the intent-first policy; the sole current emitter advances to
it. Old revisions remain deterministic evidence decoders, never fallback emitters.
This versioned read contract is indivisible from the classifier correction because
otherwise existing proofs change meaning. No schema migration, new producer or
parallel default is introduced. Stop/split if broader reader/storage changes prove
necessary.

## Exclusive expected write set

- `Docs/Plans/HANDOFF-RETRIEVAL-question-intent.md`
- `src/application_state/agent_conversation/plan_authoring.py`
- `src/application_state/agent_conversation/plan_placement.py`
- `src/application_state/agent_conversation/plan_jev_decision.py`
- `apps/live_control_server/services/plan_jev_dispatch.py`
- `tests/application_state/test_plan_authoring.py`
- `tests/application_state/test_plan_placement.py`
- `tests/test_plan_jev_authoring.py`

No retrieval, writer prompts, models, Gold, source, primary databases, UI or service
completion edits. Tests use generated disposable APP databases on54329. Ordinary
Q09 uses a separately qualified isolated evaluator lane on55447, fresh conversation
and retained source/graph pins; no original turn is reopened.

## Validation and acceptance

Preserve exact old wire rendering, including retained Q09 V6 bytes. Prove new
request JSON roundtrip/dispatch/admission, tampering rejection, explicit operation,
discussion without target, genuine writing without target, available placement,
ambiguous/missing location and another destination. Synthetic transports prove
contracts only. Use a predeclared generic semantic contrast set with actual Jev
decisions to test instruction behavior; preserve failures and normal accounting.
Then run exactly one ordinary unhinted Q09 logical turn with Gold/answer/IDs/handles
excluded. Keep all non-decision configuration fixed across control/treatment.

Independently assess retrieval support, answer completeness, citations and actual
delivery. Q09 reaching the answer path is routing acceptance; a later semantic or
retrieval failure is recorded as the next boundary, not absorbed into this slice.
Inspect cumulative diff, obtain independent review, commit/push/open one bounded
PR. Preserve artifacts and original failures. No unchanged retry-until-pass loop.

## Reader impact

V7 is the transient prepared-decision parent, consumed by authorization/selection
proof validation during service append. Durable AuthorizedV2/SelectedV2 event
variants retain the same parent digest, requested_work and placement fields;
no serialized parent revision or new closed event enters durable readers. No
APP reader fence or migration is needed. Verify service admission and existing
event reload; preserve older deterministic parent/wire reconstruction.
