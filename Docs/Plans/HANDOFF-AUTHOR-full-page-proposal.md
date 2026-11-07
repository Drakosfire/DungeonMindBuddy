# AUTHOR: full-page proposal completion

Status: DELIVERED through PR2178, merge413021a988093b8ad28771f27e81752c378b8283.
Runtime3c69b41d0a44baeffd65311addb615d1c64517e4 is healthy on5202; independent review,
98 focused tests and seven CI checks passed. Original failure hash and retained
state are unchanged. No paid retry or operator acceptance is claimed. Lease released.

Original bounded contract: PRIME owns this operator-requested page-generation failure fix.
Base: b73333f3b74d74aa64d294d00331b2e358662cf6; branch codex/full-page-proposal
in the existing context-loop checkout. Serial, independently useful correction;
no dependency on held Play or INGEST PRs. The broader goal stays paused.

## Boundary and critique

The retained attempt 54302dde-7a19-473e-aacf-d72a736db3ed produced a complete
5,737-character proposal but completion rejected its 4,000-character DTO maximum.
Remove that arbitrary generated-proposal text maximum, without replacing it.
Keep nonempty text, closed shapes, creative labels, exact producer capture,
source binding and author confirmation. A proposal grants no publication or
page-creation authority. Do not suppress errors or replay this failed attempt.

## Exclusive expected writes

- This handoff.
- src/application_state/agent_conversation/types.py: proposal text field only.
- tests/test_surface_native_build_ordinary.py: existing native HTTP review with a full-page draft.
- tests/test_surface_native_collaboration.py: full-page proposal through actual
  captured SDK output normalization, retained completion and connected review.

Other open INGEST PRs own no listed paths. Draft2172 is held; its conditional
shared-type overlap transfers only this proposal field to PRIME for this serial
slice. No UI or activity wording changes in this PR; native UI already accepts
unbounded proposal text. Legacy presentation parity is investigated separately.
No database writes, migration, model change or provider call. Live API activation
is a separate guarded delivery after exact review and CI, preserving deployed
INGEST changes and all retained data. No fresh page created by tests.

## Validation

Reproduce failure before correction, then prove long proposal plus connected
review roundtrips unchanged with its exact captured output. Preserve rejection
of changed output, invalid labels and unbound origins. Run native collaboration
and completion suites, inspect cumulative diff, independent Bugbot and CI.
Preserve the original diagnostic and failed turn; do not rewrite history.
