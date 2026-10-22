# AGENT — reuse retained passages without inventing a fresh read

## Authority

PRIME owns this bounded contract and dependent implementation under the active
operator goal. Base: `8f43d37b301f7ddbbc8d56c6fadf109a3f996e7c` (PR #1613).
Existing checkout: `buddy-context-loop/DungeonMindBuddy`; design branch:
`codex/agent-retained-passage-reuse-contract`. Remote/open-PR census on 2026-10-22
found no overlapping implementation. Architecture critique from chat
`01a086f2-c457-7b10-b753-df6063cab1ce`, turn
`01a16598-89de-7620-8b71-7974678e6884`, is adopted below.

Topology: **serial**. This design PR writes only this handoff,
`HANDOFF-PLAY-current-answer-carrier.md`, and `../Roadmaps/ROADMAP-demo.md`.
Implementation is **BLOCKED pending exact-head Bugbot review and PRIME adoption of
this contract**, not another operator approval. After adoption PRIME activates one
implementation lane from then-current remote main and records its exact branch,
base and expected-path write lease here before edits. Design merge claims no
runtime delivery. Plan and Play share the implementation; Graph-object reuse,
retrieval-policy redesign and history pruning are separate. No Core/OverMind
runtime dependency changes.

## Observed defect

The real Conks Plan follow-up took 3.9 seconds but reread the same artifact,
revision, content hash and line window opened in the preceding completed turn.
That preceding 9.7-second turn had ten distinct windows. This is cross-turn
repetition. Private evidence remains local; public fixtures use synthetic prose.

Historical-source trace references grant observation access only. They do not
prove completed-turn ownership or actual producer inclusion. Never satisfy current
completion admission with an old trace pointer, fabricated fresh read receipt or
prior assistant statement. Fresh Graph admission for current anchors remains.

## Contract and failure cases

1. **Distinct admission.** Add an append-only current-turn passage-reuse event with
   its own identity, original turn/attempt/read-event/read ID, exact receipt and
   protected bytes. Reuse is not a source-read authorization or fresh receipt. Do
   not use a fresh-read discriminator or count it as a native IO call.
2. **Exact authority.** Under the current claim fence verify managed World,
   conversation, native World binding/version, campaign scope and immutable Graph
   revision. Match anchor, evidence reference, artifact and source revision to fresh
   current-turn admitted pins. Same text alone is insufficient; publication or
   rebinding makes the old receipt ineligible.
3. **Prior producer proof.** Choose the latest eligible prior completed turn per
   exact pin from the existing conversation-history window. Its acknowledged,
   completed producing provider must actually have included that exact sufficient,
   non-truncated receipt and complete bytes. Validate hash, length and line bounds.
   Failed/interrupted turns, incomplete traces, missing/corrupt bytes, authorized
   but unacknowledged producers and historical assertions are ineligible. When
   Rules composition wraps an answer, inspect the actual producing base, not an
   intermediate tool response.
4. **Bounded lookup.** Use the existing retained conversation window through a
   bounded owner query; no new full-history scan, per-anchor history/model loop or
   volatile-only cache. Introduce no new arbitrary token/character/history cap.
   Origins point directly to genuine original reads, never recursive reuse chains.
   Tie-break by prior turn order and event order deterministically.
5. **Atomic persistence.** Revalidate and persist admission plus exact current-turn
   protected bytes in one APP transaction under expected revision/attempt and an
   unexpired claim. Fence reset, supersession and stale retries. Identical retry is
   idempotent; changed origin/pins/bytes under one identity fail. Restart recovery
   uses durable state. Never rewrite historical turns, native data or user text.
6. **Actual input inclusion.** Provider authorization explicitly lists reuse
   admissions separately from fresh read IDs. Exact prepared-envelope proof must
   contain admitted bytes and opaque handles once per exact passage. Admission
   precedes preparation; the existing writer/provider owner subsequently binds it
   to the exact envelope hash atomically with authorization. Admission alone grants
   no citation. Completion requires actual final producing inclusion.
7. **Accounting and display.** Charge reused bytes against existing source-exposure,
   input and protected-trace budgets, including outstanding reservations. Do not
   increment fresh source-read calls. Debug identifies reuse, original receipt and
   current inclusion; exact prompt inspection shows actual bytes. Citations retain
   useful source names and distinguish reuse where acquisition is shown. Opening
   uses existing exact artifact/revision/window authority; historical citation
   existence never bypasses current pin verification.
8. **Miss versus failure.** Ordinary ineligibility leaves an anchor available to the
   normal fresh reader; only a genuine invocation records a new read. Stale fences,
   partial persistence and indeterminate acquisition are recovery errors, not silent
   reread opportunities. No extra model/judge, retry policy, compatibility execution
   route or arbitrary output limit. Preserve historical readers; current dispatch
   uses the new explicit contract.

## Implementation ownership and acceptance

Activation names exact files within APP agent-conversation event, transaction,
repository, trace, completion and Plan/Play input/inclusion owners; shared server
acquisition/context capture and Plan driver; shared UI/API trace/citation owners;
one new migration if closed JSON constraints require it; focused unit, PostgreSQL
boundary and UI integration tests. Amend the lease before editing another path.
Do not edit old migrations or silently broaden historical event semantics.

Required tests reject each identity/revision mismatch, wrong status/producer,
omitted final inclusion, partial/truncated receipt, trace loss/corruption, reset or
stale claim and conflicting replay. Prove atomic event+trace persistence,
idempotency and restart reconstruction at PostgreSQL ownership, including JSON
constraints and historical records. Actual prepared Plan/Play inputs must contain
reused bytes once. A hit performs no native source read; a miss records genuine IO.
Charge reused exposure and unresolved reservations without bypassing byte bounds.
Completion/source-opening tests cover Rules composition and exact selected passage.
Helpers alone do not prove these boundaries. Synthetic fixtures only.

Inspect cumulative diff, commit/push one implementation PR, exact-head Bugbot, PRIME
merge and guarded paired 8000/5202 delivery. Ordinary Plan and Play follow-ups must
reuse eligible passages, retain named citations/exact Debug prompts and reopen after
protected restart. Preserve APP/native rows, sources, drafts, notes, mechanics and
frozen evidence. Measure actual decision/read/writer timings; eliminating an IO
alone promises no latency gain. Full J1–J6 twice, original swamp/Edge repeated
latency, 8 GB measurements and operator acceptance remain open.
