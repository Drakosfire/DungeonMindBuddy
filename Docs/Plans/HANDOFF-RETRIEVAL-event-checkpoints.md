# Persist Plan session checkpoint events incrementally

ACTIVE under the Buddy Send-to-writer-ready objective. Serial slice on
`codex/buddy-event-checkpoints`, exact base
`3cb5a0a4178029ef83193eaf5803cb9d23975ec0`. #4335 is settled without
adoption. No unmerged dependencies. Follow the APP repository and lifecycle
owners. No Core, provider, writer, browser or primary database changes.

The bounded write set is the agent conversation APP repository, the
NativePlanSession owner, one internal event-checkpoint storage module and
migration, the claim/recovery owner if needed for atomic materialization,
the APP context trace and native assertion replay readers, their
database contract tests, and this handoff. Verify the lifecycle SQL
reader inventory before introducing an open-checkpoint state.

## Invariant and test

Keep the existing transaction per admitted operation. The same locked Turn
claim determines world, attempt, prior revision and event ordinal. A
checkpoint persists the immutable opening execution identity and each newly
admitted event once. Root revision advancement and event persistence commit
together. No event-only fast path may authenticate by trusting a process-local
ordinal or omit changes to locked references, Rules, or authority.

Recovery must reconstruct the same typed Turn for that revision using the
stored immutable opening prefix and ordered events. Define the snapshot and
retry behavior for a reader racing append or final materialization. Reject
foreign bindings and stale, missing, misordered or altered events. An
authorization with no outcome must remain visible after a worker exits.
Checkpoint closure persists the ordinary full execution and retires its open
state in the same transaction before writer authorization. Validate post-write
storage, retained references and Rules; preserve existing claim renewal,
interruption, rollback and duplicate-response behavior.

## Evidence and decision

A counterbalanced disposable SQL probe on the 60 observed D02 checkpoints
measured median checkpoint time of 4.36 s for growing execution writes and
0.11 s for incremental records. Final reconstruction and materialization
took 0.15 s in the incremental arm. This is storage feasibility evidence.
It excludes real APP admission, claim recovery and writer transport. Raw
paired samples, the real checkpoint trace, and the frozen controller inputs
are under Projects/.codex/buddy-ack-evidence.UuooU1.

Use real APP transactions first with injected rollback, stale expiry,
concurrent readers, lost acknowledgement and a new worker. Then qualify
D02, Q06 and WF01 with pinned controller tapes and the local writer sink.
Require exact context bytes, evidence ordering, citation reopening and
unchanged Core inventory. Time commit and recovery separately. Advance only
with a repeatable candidate improvement and at least 10% lower matched
writer-ready time on the small cohort. Verify the full 31-case cohort before
adoption. Keep evidence if the experiment is rejected and remove the
candidate path rather than leaving a runtime fallback.
