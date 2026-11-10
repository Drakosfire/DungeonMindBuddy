# RETRIEVAL: one actual selected-source acquisition batch

Status: BLOCKED at workspace allocation and the explicit design gates below.
This is a portable proposed contract, not an active implementation lease.
Root owns the retrieval goal and bounded design; Core owns source-access atomicity,
Buddy owns actual SDK selection, APP grants/results and model exposure.

## Current evidence and required result

Buddy base: fetched main 73f2d42d755978a95ac1a8d7a253b8c9b852c2d6, merged #2324.
Its reviewed/captured head is 095223227783dbbf06757d92edd2fc90d68bbb49.
All 15 context cases and 72 required atoms pass; original APP/native and retained
evidence are conserved. Median request-start to context-ready is 6356.70 ms,
mean 7737.09 ms, maximum 16624.50 ms. The six-second goal is not achieved.
Catalog preparation fell from 125.43 to 11.92 ms without meaningful whole-cycle
improvement. The initial failed startup captured no turn or provider activity;
it remains separate, ungraded evidence.

Current cohort source admission used 179 commits for 25 consecutive selected-source
segments. A real batch could approach 80 commits, including initial search, before
accounting for full-document dependencies. This is an opportunity bound, not an
implemented plan or causal latency saving. Source append median is 1571 ms; nested
materialization is 410 ms and must not be added to it. Accepted predecessor traces
account for about 3232 ms median serialized source/execution/trace admission work.

Evidence in out/retrieval-object-catalog-v1/:
- selected-source-batch-ceiling-v1.json (actual selections and transaction counts)
- accepted-critical-path-accounting-v1.json (nested versus elapsed accounting)
- comparison-v2/ (actual captures, timing and conservation)
- independent-context-review-v1.json (fresh 15/72 support assessment)

Pinned Core main: 430c1a6db631d097dfa0a273f8933067f708bc56, also the accepted installed
Core dependency. Its NativeTextSourceView exposes only per-member body access.
Postgres opens a separate transaction for each member; operator access first calls
the base view and then opens another transaction. open_coherent_view pins an epoch,
not a shared body snapshot. A Buddy loop around these calls is NOT atomic capture.
Independent design evidence: retrieval-record-transitions-v1/
selected-source-atomic-batch-design-v1.json in this task's retained visualization area.

## Serial delivery topology

1. **MIND: atomic native source access.** One Core PR from the freshly fetched Core
   main. Add one closed bulk source-access capability across application, Postgres,
   memory and operator owners. Existing single-item entry points delegate to the
   same implementation; remove superseded per-member acquisition implementations.
   Preserve existing result DTOs and integrity/admission owners. No schema or data
   migration is currently justified. Deliver and merge before the Buddy consumer.
2. **RETRIEVAL: consume selected-source capture batches.** A separate Buddy PR from
   current main, pinned to the actual merged Core dependency. Batch existing exact
   grants before IO and existing observations after ONE real Core batch capture.
   It remains BLOCKED until Core delivery and its own selection-plan gates pass.

These are two repository-owned pieces of one capability, not parallel experiments
or an unmerged stack. No Core or Buddy implementation worker has been dispatched.
No current open Core PR touches the proposed source-access paths (checked against
open PRs #143 and #145–150). Recheck active leases before activation.

## Core contract and design gates

- The application bulk operation accepts existing exact evidence identities under
  an existing NativeTextSourceAccessContext and returns ordered existing
  NativeTextSourceAccessV1 results. Host-only repository keys use existing
  artifact/revision/span identities; no new evidence representation or authority.
- Acquire selected native, extension, operator and legacy-backed records at one
  actual SQL snapshot. Prefer a set-based source-body statement that supplies all
  fields needed by the existing reconstruction owner. A loop of separate
  transactions, a cached body or a fabricated batch receipt is not an alternative.
- Validate every item's child membership, principal/visibility, exact revision,
  authority epoch, fingerprints, body hash, span identity/bounds and UTF-8 with the
  existing owner before returning any result. Preserve native-versus-operator
  precedence and legacy active/current-revision checks. Corrupt native data must
  never fall through to an operator source.
- Explicit per-item unavailability remains typed unavailability. Integrity and
  transport exceptions fail the entire physical capture before any batch output.
  Prior COMPLETED captures remain durable. No earlier independent read may be
  relabelled as part of an atomic batch to erase its known successful prefix.
- Specify duplicate-key ordering and return detached, strictly reconstructed
  result snapshots in an ordered tuple. Existing NativeTextSourceAccessV1 DTOs
  are mutable; do not silently freeze/change them or share mutable result objects
  between slots. Retain no caller-owned query/record objects in a cache.
- Preserve the passed context.source_view epoch. Buddy explicitly refreshes the
  existing context before a new acquisition; singleton delegation must not
  secretly advance the caller's pinned epoch. No request-spanning cache,
  compatibility producer or silent fallback.
  Existing singleton calls must retain their refusal and result semantics through
  the same canonical bulk implementation.
- Prove one-snapshot behavior in actual Postgres, including concurrent changes
  between preparation and acquisition. Preserve existing resource/transfer bounds
  and normal product accounting; introduce no arbitrary provider/call caps.
- Independently review this contract and the actual exact-head implementation.
  If required paths or public contracts expand, checkpoint and revise the slice
  before absorbing the expansion.

## Proposed Core write set after activation

- A Core-local HANDOFF-MIND-native-source-batch.md consuming this pinned contract
- src/dungeonmind/application/vnext/native_source_access.py
- src/dungeonmind/application/vnext/ports.py
- src/dungeonmind/application/vnext/__init__.py (public export only)
- src/dungeonmind/infrastructure/postgres/vnext_sources.py
- src/dungeonmind/infrastructure/postgres/vnext_operator_sources.py
- src/dungeonmind/infrastructure/postgres/vnext_knowledge.py (extract the existing
  publication-receipt row validator used by extension lineage; no publication
  behavior or new capability)
- src/dungeonmind/infrastructure/memory/vnext_sources.py
- src/dungeonmind/infrastructure/memory/vnext_operator_sources.py
- Existing native/operator source unit and Postgres integration tests, with a
  focused batch test file only if their owning structure requires it

SQL-owner review checkpoint: extension reconstruction also verifies its original
admission's full record/body/span index and the actual publication receipt. The
bulk snapshot must supply those rows to shared pure validators. Factor the current
fetch/validation helpers at their owners; do not copy predicates or introduce a
connection-shaped snapshot adapter that pretends additional queries are real IO.
This required extraction is part of the same atomic-read capability, not a new
publication slice. Existing legacy artifact/revision reconstruction helpers are
already pure and need no change.

Core checkout must be a managed isolated checkout under the verified Projects
filesystem, never the dirty legacy Core checkout. The managed worktree tool refused
allocation because DungeonMind is not one of this chat's workspace folders. It
allows only the attached Buddy/visualization folders. Add the Core repository to
the workspace before activating this slice; do not bypass that boundary using a
manual checkout or take over another chat's worktree.
The user confirmed adding Core, but the subsequent managed-tool validation still
returned the old Buddy-only folder list. The remaining prerequisite is the chat's
effective workspace binding, not further user authorization for this work.

## Buddy consuming gates and expected scope

Resolve consecutive source segments under the actual acknowledged controller.
Direct-source/full-document coverage dependencies are real boundaries: do not
pre-grant a section and later orphan its observation because a full read covered
it. Prove the plan for full-document success, unavailability, failure and overlap
before activating the consumer. Model full-document exposure still requires the
explicit actual Buddy decision. No metadata/Rules/Graph operation may be folded
into a source capture or used to infer answer sufficiency.

Use one closed source grant/materializer path, existing individual durable events,
and the current private session's freshness, claim, callback and complete ACK checks.
Unknown physical outcomes remain unresolved and fail-stop; no automatic replay.
Remove superseded live source producers after the replacement is verified, while
retaining historical event readers and all evidence. Expected owner paths are
native_reads.py, service.py, native_plan_session.py, corpus_source_navigation.py,
the actual Plan driver if necessary, the pinned dependency configuration and their
existing owning tests. Confirm the exact lease after the Core result is known.

## Verification and acceptance

Core: native/extension/operator/legacy parity; unknown/denied/unavailable slots;
duplicate/order behavior; malformed hashes, fingerprints, spans and UTF-8; no
operator fallback on native corruption; fresh epochs and single-snapshot mutation
tests; unchanged singleton behavior. Use local CI and disposable DBs only.

Buddy: actual SDK selection through grants, real Core batch, exact selected extent
projection, complete durable observations and context-ready closure. Test late
refusal, SQL rollback, stale claim/authority, unknown outcome, full-document
dependencies and prior completed-batch preservation at their owners.

Then reuse the existing consolidated 15-question context workflow in two isolated
workers, with the retained #2324 cohort as baseline. Pin actual code, dependencies,
sources and graph state; keep Gold and evaluator hints out. Independent assessment
must preserve all 72 atoms, attribution, chronology, uncertainty and exact citation
support. Writer output is excluded. Report actual request-start to genuine
context-ready distribution, controller/input/output counts, billed cost or unknown,
actual capture/commit counts and contention limits. Do not add nested cumulative
spans or claim a helper/transaction-count bound as elapsed saving. No unchanged
paid reruns or retry-until-pass.

Preserve primary/original evaluator/native state, retained baselines and resources.
Only specifically owned disposable tests/candidate APP clones may change. No
deployment or GitHub CI. Standing user implementation and merge authority applies;
the workspace issue is an access/tooling prerequisite, not a PRIME approval gate.
