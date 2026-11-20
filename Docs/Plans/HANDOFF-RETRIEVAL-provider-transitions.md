# RETRIEVAL: one provider execution transition owner

Status: MERGED / lease released. Root authored/adopted this bounded implementation under the active
six-second retrieval goal. Base f6e174e40 (fetched main), isolated branch
codex/retrieval-append-critical-path. Serial:2293 is closed/rejected; no open
implementation predecessor. Checked2288 CI and surface/reference/ingestion lanes
are disjoint. No PRIME dependency. Merge requires separate user authority.

## Outcome, boundary and topology

Replace the provider lifecycle/accounting full-history predicate with one pure
transition fold. Its current full-recovery consumer replays the same transition
implementation; it will not retain a separate fast validator or trusted flag.
Preserve event positions/IDs, prior-attempt resolution, outcomes, actual Build
accounting owners, completion placement and aggregate policy checks. Atomic event
groups have explicit finalization: limits are checked after the group, not after
each intermediate step. This state grants no provider, source, writer or DB IO.

This is the first independently reviewable owner transfer toward an immutable
accepted-prefix capability. It is NOT that capability, a speedup claim, or the
six-second goal's completion. Other native invariant owners and actual APP
integration remain required. Do not activate cached APP reconstruction or paid
comparisons in this slice. A successor is BLOCKED until this owner is qualified
and its exact base/topology is pinned. Further domain invariant transfer is a
separate capability boundary; do not quietly absorb nineteen files into this PR.

## Why this precedes APP integration

The retained baseline has a median39 distinct controller/lifecycle and source
append calls. Native source append and execution_append are distinct callsites;
source work is nested under selection, and controller rounds include host work.
Do not add nested spans or extrapolate one profiler sample as measured savings.
A fresh rollback-only source append measured246ms with profiler overhead.
A type-preserving mutable-view witness measured109ms, a disjoint copy20ms and
full-row decode41ms on one retained Turn. A wrapper that adds these costs cannot
be assumed faster. The goal-scale design must transfer invariant ownership,
including immutable views, rather than skip existing checks.

Evidence and42-owner invariant map are retained under
retrieval-acquired-records-v1 and retrieval-append-critical-path-v1.2293's fourteen
available contexts pass71atoms, but accepted-ready median regressed10.05→11.96s;
Q01's initial classifier timeout remains unknown, retained without replay.

## Exclusive expected writes

- This handoff.
- src/application_state/agent_conversation/provider_execution.py (pure owner).
- src/application_state/agent_conversation/types.py: replace only
  validate_provider_execution body with its single recovery consumer.
- tests/test_surface_native_context.py (existing lifecycle/context suite;
  append owner cases and fixed qualification oracle).

No schema, service/repository, runtime dispatch, model prompt, Core, Rules
implementation, writer, UI, primary DB or dependency changes. No new harness,
per-question script, alternate runtime producer or compatibility fallback.

## Qualification and completion of this slice

Before deletion, pin the original full predicate as a TEST-ONLY differential
oracle. Compare complete valid/negative histories, every accepted prefix and
atomic grouping, including sequence/duplicate-ID error priority, unknown outcomes,
completion finality, accounting and aggregate limits. Exercise actual existing
Build/accounting tests and native event types. State must contain immutable value
indexes, not mutable owner models; arbitrary state construction is not authority.
Preserve errors at the original full-recovery boundary. Do not infer an accepted
full execution from this provider-only fold.

Run relevant pure owner suites; inspect cumulative base→head diff; independent
subagent review. Commit/push/open one bounded PR with retained source/assessment
pins. No new paid calls for this internal validation refactor. The broader goal
remains active until APP integration, all15 contexts and actual response-ready
latency establish the requested result.

## Owner qualification before PR

Ninety-two pure provider/native context checks pass, including every grouping of the
short lifecycle fixtures,400 seeded partial/negative histories, error priority,
non-provider positions, immutable indexes, and actual native Build mode/accounting
owners. The frozen test oracle is AST-equal to the original predicate at the
base, apart from its test name and qualified relative imports. Production retains
one predicate implementation; the types module delegates its full recovery to it.

Read-only comparison on the actual fifteen retained baseline executions passes
677 prefixes and every two-group split, with original execution bytes unchanged.
This is provider-only parity, not fifteen freshly passing context captures.

Broader qualified suites:209pass,9skip,21fail. The same21cases fail after restoring
the exact original predicate in the test process: twenty initial Build fixtures
lack current GM source authority, and one ordinary Build tool-count fixture
produces zero tools. They are inherited fixture failures, not waived passes; no
Build/runtime repair was absorbed. Initial test invocations without the correct
isolated admin DSN were stopped and are not qualification evidence.

Evidence: retrieval-append-critical-path-v1/provider-owner-qualification-v1.json,
retained-provider-fold-parity-v1.json, inherited-failure-disposition-v1.json and
redacted logs. Source is pinned by hashes. This changes no provider request,
source acquisition, durable schema or publication path. No latency gain claimed.

Independent working review found two malformed mutable-model counterexamples:
None must not erase the fact that an outcome was observed, and numeric arithmetic
must not preempt earlier structural/attempt-limit refusals. Both are fixed and
covered explicitly, with None/empty outcomes and malformed token values added to
the seeded differential histories. The latest retained15execution/677prefix
comparison passes again (retained-provider-fold-parity-v2.json).

Complexity remains explicit: advancing a group copies prior event-ID and attempt
indexes; existing Build role accounting still scans execution history. This is
not constant-time APP incrementality. The immutable accepted-prefix session and
remaining native predicate transfers are not implemented or authorized for
activation by this provider-only state. No new latency claim follows from it.

The first CI inventory refused the newly named provider test module as
unclassified. Rather than editing the active CI lane's shared classification
contract, the same tests are consolidated into the existing classified native
context suite, alongside its provider lifecycle fixtures. No product logic or
assessment expectations change. The failed CI run is retained, not a pass.

## Settled predecessor

User explicitly approved2297; merged as5d63a5c742e60a3e5338847f3fecc02f12a9efc7.
Delivery headb1608cb57 passed independent code/delivery review,92focused tests,
677retained provider-prefix comparisons and all7CIchecks. Final broader suite
213pass/9skip/21inherited failures was retained, not waived. No latency gain,
APP cache or accepted native prefix claimed. The exclusive write lease is released;
the consuming record-transition handoff owns this truthful settlement.
