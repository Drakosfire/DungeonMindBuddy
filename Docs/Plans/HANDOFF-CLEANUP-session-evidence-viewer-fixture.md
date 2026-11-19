# CLEANUP: valid pinned-session viewer fixture

Status: ACTIVE. Authorized by the standing cleanup goal with independent review
and merge authority. Base: 5432c6d2d14be6422532fbbeddb0c9d1ab684f6a.
Topology: serial after #4094; no unmerged dependency. Existing isolated cleanup
checkout; no runtime ports, providers, databases or operator data.

## Invariant and scope

The read-only viewer must render a digest-verified immutable session packet with
an admitted UUID run reference. The existing test uses `run-a`, rejected by the
current navigation guard before rendering. Preserve strict admission, packet and
entry digest verification, exact world/run/revision reads and no reflections
editor. Correct the viewer fixture only; do not relax runtime validation or alter
picker storage/race fixtures unnecessarily. Restore any stubbed globals and URL
state. Check a deliberately invalid run remains rejected at the owning boundary.

Write lease: apps/live-control-ui/src/playSurface/review/SessionEvidencePicker.test.tsx
and this brief. All 61 current open head objects were inspected for changes to
that test, SessionEvidenceViewer, sessionEvidenceCitation and sessionEvidenceHref;
none overlaps. Runtime contracts remain read-only owners outside this lease.

## Verification

Record baseline and corrected focused picker/viewer/citation tests under the
shared frontend resource lock with external task-owned source/scratch. Verify
rendered read-only text, exact requested identity and admitted entry target, and
retain invalid-reference rejection. Then run exact-head repo hosted verifier,
build, validator and full discovered diagnostic. Compare exact test IDs/results
with cc0637c513ff7a57cb026ef98cc1295afb61024a: only the intended failure may resolve,
with no omitted cases, new failures or unexplained changed remaining messages.
Inherited failures, conditional inventory differences and unresolved quote variant
stay red under #4074. Inspect cumulative diff and obtain independent exact-head
review before merge. This does not establish backend or release qualification.
