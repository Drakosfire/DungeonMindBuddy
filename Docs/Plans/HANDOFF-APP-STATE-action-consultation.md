# APP-STATE — sourced action clarification persistence

Status: ACTIVE under PRIME, 2026-10-12. Serial APP persistence PR, followed by
separately owned SERVER action-harness and DEMO composer/result adoption.

Pinned dispatch: `/tmp/HANDOFF-APP-STATE-action-consultation.md`, SHA-256
`8ab15e464ef75b8cdf34002473bd601a43c3a3b83a20fd39f81076641f6a3525`.
Pinned design: `/tmp/continuity-edit-contract-decision.json`, SHA-256
`0751fd8e159f35e94528c90228398167b98867873611a39593cee52141b756fa`.
Base: freshly fetched Buddy main `059fe3fd8c36d677261670f86b8d3f4e2d6f7e66`.
The initial implementation used `6dd0bda0`; disjoint #1100 was adopted on rebase.
Branch: `codex/app-state-action-consultation`. Checkout is isolated in `/tmp`.
Migration: `20261012_0020`, descending from current `20261008_0019`.

## Authority and ownership

PRIME activated the exact eight-path persistence slice and then explicitly
approved shared types/provider validation extraction and two migration-head
assertion updates. The complete exclusive lease is:

```text
src/application_state/plan_action_dialogue/types.py
src/application_state/plan_action_dialogue/service.py
src/application_state/plan_action_dialogue/repository.py
src/application_state/plan_action_dialogue/graph_consultation.py
src/application_state/migrations/versions/20261012_0020_plan_action_consultation.py
tests/application_state/test_plan_action_consultation.py
tests/application_state/test_plan_action_dialogue_postgres.py
Docs/Plans/HANDOFF-APP-STATE-action-consultation.md
src/application_state/agent_conversation/types.py
src/application_state/agent_conversation/service.py
tests/application_state/test_agent_conversation_service.py
tests/application_state/test_agent_conversation_postgres.py
```

The final two test paths change only current-head assertions; historical
downgrade targets remain unchanged. Agent service changes only delegate its
existing provider-envelope checks to the common function. Shared types retain
Ask wrappers and wire schemas, extracting common validation inputs and logic.

The fetched open Buddy PR inventory (#1014, #869, #844, #826, #798, #765, #764,
#763) supplies no active lease on this APP write set. PRIME separately confirmed
SERVER's current publication-procedure lease, RAKE evidence append and MIND
private semantic review are disjoint. SERVER/DEMO action consumers follow this
contract. No SERVER, UI, Core, corpus, provider, runtime or retained DB paths are
leased here.

Merged APP handoffs that still say ACTIVE describe completed predecessor
implementations, including Graph execution/source/context receipts. They grant
no current conflicting worker lease. This handoff is the current APP action
persistence authority and reuses those accepted types. Related recap receipts
landed through #1092 (`8b5e73ec`, reviewed implementation `ade479bb`); the parent
broker landed through #1094 and is a SERVER reuse dependency.

## Durable contract and public adapter

`plan_action.action.consultation` is the single nullable JSONB addition. Legacy
rows remain null and omit that key from record/history serialization. Existing
status, request fingerprint, dispatch token, fence, lease and proposal payload
non-replay meanings remain. First adoption is initialized-World saved Plan
`replace_selection` revise actions. Existing blank World, caret and Playable
actions retain their existing paths.

The action receipt binds action ID and request fingerprint, Plan surface
instance, exact committed `PlanActionBasis`, draft digest/match witness,
selection digest, instruction and creative-input commitment separately from
the server-resolved managed/native World, binding, GM Graph revision, retrieved
packet and actual initial provider-envelope commitment. It has its own schema
and digest; it is neither an Ask receipt nor a hidden Turn. SERVER alone resolves
current authority, interprets the model outcome and identifies required reads.

Reuse `PlanWorldGraphExecutionV2`, its exact policies/events and the common
validators for selected source scope, related recap admission, provider envelope,
claim membership and successful evidence source reads. Related recap context
can inform prose but never satisfies evidence citations or source-read IDs.
Ask wrappers still pass their original receipt fields to the same validators.

SERVER's adapter sequence is:

1. Reconcile/get an existing key before current authority or provider work.
   `reserve(request)` returns `(record, created)`; only a newly created action
   owns the token. Include all normalized request identity and a predecessor
   reference in the SERVER fingerprint when present.
2. Resolve current World/work/Graph authority and assemble the actual initial
   envelope. `build_consultation_receipt(action=record, ...)` derives and
   validates both action-input and receipt commitments. `freeze_consultation`
   freezes it with the existing Graph policy under token/fence/expiry. A matching
   retry returns `fresh=False`; changed frozen input conflicts.
3. `append_consultation_event` records existing Graph/source/context/provider
   event types in sequence under the same token/fence. A fresh provider
   authorization is the one-shot dispatch permission; identical event retry
   returns `fresh=False`. It does not grant another provider call.
4. `finish_consultation` atomically persists result and its terminal completion
   binding. A clarification is completed with a message, result ID and typed
   attribution; it has no replacement payload. The displayed message and stored
   assistant summary must equal the ordered claim/connective segment texts
   joined by LF, without normalization. Questions and creative prose are explicit
   connective segments. Unrelated visible text is rejected before completion.
   A proposal persists disposition
   and the inert proposal-response digest, preserving response non-replay.
   SERVER supplies the existing proposal response separately only after this
   durable terminal write succeeds. Required failed reads cannot become a
   no-fact/applicable proposal. Unknown outcomes cannot expose a terminal result
   and remain pending until existing expiry reconciliation marks indeterminate.
5. `get_by_key`, `list_status` and `completed_context` return typed consultation
   provenance/result after reload. SERVER derives action source-open targets
   from the matched citation/source-read identity and revision commitments in
   the receipt, using its accepted source reader. History is not an Apply payload.

Linked replies use a new key/action and a `PlanActionContinuation` carrying the
predecessor action, clarification result identity/digest and explicitly attributed
previous instruction. Freeze locks the completed clarification, validates same
World/surface/work/draft/selection and consumes it once. A unique JSONB expression
index plus parent lock fences concurrent successors. Foreign, stale, unrelated,
changed and already-superseded predecessors fail. New invocation Graph pins may
advance; older citations remain historical until freshly admitted.

Optional typed Ask history preserves source conversation/turn IDs and attribution
beside its committed Plan basis. SERVER supplies only active exact-basis eligible
history. APP checks receipt membership, basis and frozen included-history pins;
each pin's `answer_sha256` must equal SHA-256 of the full ordered attribution
segment texts joined by LF and encoded as UTF-8. This is the existing saved Ask
answer rendition: `CompletedPlanAskPair` and the Ask repository check it against
the stored answer, and SERVER renders completion answers the same way. The
current Ask assembler emits empty `included_history`; its wire/hash behavior is
unchanged. This action adapter commits the complete validated source answer,
before any bounded prose view. An abbreviated prose view is separately bound
by the actual provider-envelope commitment and cannot replace the full typed
attribution or silently redefine its source-answer pin. Duplicate history turn
pins and same-turn changed answers are rejected.
Historical facts must still be admitted in the current execution before citation.

## Verification and external state

PRIME confirmed the truthful authority-unavailable variant: the same action
receipt may freeze `authority_status=unavailable` and a bounded failure code,
with Graph authority/packet/assembled input and execution all null. It permits
only a failed matching `context_unavailable` result. It cannot append events,
authorize a provider, cite a claim or complete a proposal/clarification. A retry
needs a fresh action and fresh authority resolution. It does not represent a
verified blank/no-knowledge World; those retain legacy authoring behavior.

Use synthetic mechanics and focused owning tests only. PRIME supplied the
exclusive isolated container `prime-action-consultation-tests-20261012`, loopback
54340, with private credentials held outside the repository. Each test creates
and drops a unique `prime_action_consultation_*` DB. Capture/redact failure output
before showing it; never print DSN/password. No 54330/54331 or retained DB access,
retained migration, provider call, fixture publication or runtime action is
authorized. PRIME owns container/credential cleanup after independent review.

Required checks cover freeze/provider/result fencing, one-shot retries, source
versus context attribution, typed history reload, lawful/foreign/concurrent
clarification replies, unknown/expired outcomes, legacy/caret/Playable actions,
populated migration upgrade and guarded downgrade, and old Ask V1/V2 validation
and wire compatibility. Run changed-path lint and inspect the cumulative diff.
Implementation completion includes commit/push/open PR. Independent PRIME review
and merge remain separate; operator semantic acceptance belongs to the later
SERVER/DEMO vertical slice.

Initial author verification: 37 distinct action/legacy owning checks passed, including
the focused rerun of one corrected freeze-test fixture; nine unchanged Ask
source/context validator checks and four unchanged Ask PostgreSQL provider,
evidence and source-read boundaries passed. All PostgreSQL checks used unique
`prime_action_consultation_*` databases on the isolated 54340 cluster. Changed
Python paths pass Ruff and compilation; cumulative diff passes whitespace checks.
This proves persistence/validation mechanics, not model semantic behavior or UI
operator acceptance.

Independent review held implementation `5e084c22` for two attribution defects:
unrelated result prose and unchecked historical answer pins. The amendment binds
visible result/summary to the canonical segments and independently computes the
full source-answer hash. Focused repair evidence: eight model checks (including
current/older Graph revision history positives and same-ID changed-answer
negatives) and four real PostgreSQL canonical-terminal/history-pin checks passed.
The rebased cumulative implementation must receive independent review again.

Rebased final author verification: all 39 action/legacy cases, nine unchanged
Ask validator cases and four unchanged Ask PostgreSQL boundaries passed.
Changed-path Ruff, compilation and cumulative diff checks also passed. Only
the isolated 54340 resource was used; no retained/provider/runtime action ran.
