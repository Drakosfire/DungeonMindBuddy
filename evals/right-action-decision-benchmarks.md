# Right Action decision benchmarks

These three registered benchmarks reuse cases from the
[Right Action coverage matrix](right-action-coverage.md) and
[closed baseline](right-action-baseline.md). Their results are independent of
the end-to-end fulfillment grades. All three are unrun.

## 1. Utterance-only first action

**ID** `buddy.intent-utterance.v1`

Give the controller the exact submitted utterance and a fixed, versioned action
menu. Its only question is which action serves the user's present request.
The menu distinguishes discussion, clarification, chat drafting, current-page
edit, standalone and connected page review, explicit source reading, and
other relevant existing Build actions. Use an explicit
`needs_context_to_choose` option when the message alone does not identify an
action. That label requests relevant turn state and never authorizes a search
or sends a clarification to the user by itself. Use one semantic menu across
all context arms. Publish the mapping to existing Buddy action labels before
execution. In particular, the baseline's `discuss` can cover an explicit
read, so compare retained Jev votes only where that mapping is unambiguous.

Choose an action family without requiring the exact destination, source
identity or capability binding. Score each independently if subsequently
tested. For example, an instruction to edit the selected sentence identifies
the action without telling us which sentence it is. Label disclosure of the
necessary information separately from whether the host can execute.

## Starter cohort

Pin the exact captured user message for each reused case and freeze the
labels before viewing new outputs. First verify that the retained utterance
and relevant state match the intended fixture. Record a provenance or label
mismatch as unqualified before dispatch. For workflows, pin the tested turn
rather than classifying an entire conversation as one utterance.

| Case or variant | Utterance alone decides first action? | Expected first action and context boundary |
| --- | --- | --- |
| DISCUSS-1 | Yes | Brainstorm in chat. The invented premise is supplied. |
| CLARIFY-2 | Yes | Ask the single missing tone question. The user explicitly says to ask before drafting. |
| PAGE-EDIT-2 | Yes | Stage a current-page edit. Editor state binds the selected sentence. All table content is supplied. |
| SOURCE-READ-1 | Yes | Read the exact saved current page and cite the passage. Surface state binds the page. |
| CLARIFY-2 continuation, controlled variant | No | Use only `Playful.` as the utterance. Prior turns supply the pending welcome draft and the reason for the reply. |
| PAGE-EDIT-2 continuation, controlled variant | No | Use only `Do that.` as the utterance. In the pinned prefix the user authorizes staging a previously discussed edit. No prior confirmation or save is pending. |
| DISCUSS-1 with same-subject page, controlled variant | Yes | Keep the exact discussion-only utterance. The related saved page is a distractor. |
| PAGE-EDIT-2 with external lookup, controlled variant | Yes | Preserve the edit request but require the number of towels to be verified on another exact saved page. The first action is still to stage an edit. The evidence requirement changes. |

Candidate extensions include CHAT-DRAFT-1, SOURCE-READ-2, IMAGE-DIRECTION-2
and the Maelthor continuation in STANDALONE-PAGE-2. Admit each only after
checking its exact utterance against the rubric. Operator-only cases remain
execution controls. Account for reused and excluded cases by ID. The known
first choice on 25 graded cases is historical comparison evidence, separate
from the benchmark's independently reviewed acceptable labels.

Report correct choices by case and action family, false deferrals on
self-contained utterances, guesses on context-dependent utterances, and invalid
or missing outputs. A context-dependent utterance passes the utterance-only
arm by identifying the need for context. The full-information label stays
separate for scoring the next benchmark.

## 2. Context effect on first action

**ID** `buddy.intent-context-effect.v1`

Use the same cases, questions, model, action menu and expected outcome across
paired arms. Pin the option order, request settings and exact injected text.
Project only information that Buddy has at Send time. Hold the related-page
catalog and newly retrieved evidence outside these four arms.

| Arm | Provider-visible inputs |
| --- | --- |
| U | Utterance only |
| S | U plus surface, active target and editor selection |
| H | U plus relevant prior dialogue and pending work |
| SH | U plus both context groups |

Freeze the minimum sufficient context for each case. Evaluate each arm both
for behavior given its available information and against the fully informed
action, reporting unresolved results separately. For each of S, H and SH
against U, report wrong-to-right, right-to-wrong, unchanged, resolved from
deferral and newly deferred. Include direct requests with tempting unrelated
context and identical short follow-ups with contrasting prefixes. Report
tokens and decision latency per arm. If the catalog itself is tested, add a
separately named SH-plus-catalog arm with no other changes. Keep all per-page
read questions out of the intent comparison.

The hypothesis is that utterance-only suffices for explicit requests and
relevant context helps dependent turns without degrading explicit ones.
Report help and harm per family alongside aggregate accuracy. Prefer the
smallest context that preserves correct decisions on the held-out contrasts.
Pin train, development and held-out scenario families before any tuning.

## 3. Anchored evidence enforcement

**ID** `buddy.anchored-zero-new-reads.v1`

Hold the correct requested action fixed when isolating the host rule. Test the
ordinary route with the real acquisition owners instrumented. Score the model's
evidence need separately from whether the host honored the resolved scope.
Use provider-free decision replay where request parity holds, and preserve
contradictory votes in the retained evidence.

| Control | Required observation |
| --- | --- |
| PAGE-EDIT-2, fully supplied edit | Anchored. Stage the same six rows at the bound selection, preserve adjacent text, and leave the saved page unchanged. |
| PAGE-EDIT-2, contradictory recorded votes | Inject or replay anchored scope together with optional related-page read votes, including a tied vote. No new read may start. Preserve the raw votes as evidence. |
| DISCUSS-1, supplied premise | Anchored. Discuss in chat with no write or proposal. |
| PAGE-EDIT-2, external lookup variant | Read the explicitly requested different source, preserve the intended edit, and reopen the exact supporting passage. |
| [Different saved source control](negative_retrieval/fixtures/development.json) | `dev-different-saved-source` must acquire the required source and reopen its citation even when other material is already supplied. |

The optional page-open guard covers the post-decision Build edit boundary.
The PAGE-EDIT-2 hard gate still counts catalog discovery and Graph preparation.

**Hard pass condition for every anchored turn: zero new evidence reads.**
Count acquisition attempts from Send onward, including work dispatched before
the intent vote, speculative reads, cancelled reads, and failures. Required
counts are zero for optional page catalog discovery, saved source opens, Graph
discovery/search/traversal, lexical or semantic search, and any other new
evidence acquisition. Report counts by owning boundary. Reading already-carried
context, validating a bound editor target, and independently reopening an
already delivered citation during scoring are separate operations. They must
not fetch additional decision evidence. A missing owner trace makes the zero
claim unproven. An observed new read fails even if the output is correct or
the retrieved material is discarded.

Also require correct fulfillment and unchanged protected state. For the
positive contrasts require the specific source, exact citation reopening,
and a correct result. A model that answers everything from carried context
fails those contrasts. Measure first decision, acquisition, and completion
times separately, and record unnecessary reads and missed required evidence.

## Capture and registration

Use the [shared benchmark workflow](../Docs/Guides/ordinary-benchmark-workflow.md)
and keep exact request/response captures, per-case label provenance and owner
observations. Gold stays local. Use one owned App clone for mounted controls,
with shared Core read-only and verified teardown. Keep held-out labels out
of the prompts, and report unknowns and failures explicitly.

These protocols refine the decision stage of the
[CPU decision model experiment](../Docs/Experiments/EXPERIMENT-CPU-Decision-Models.md).
Qualify the routing split with Jev pinned before comparing local models or
adding MPNet to the evidence-acquisition branch.
