# REFERENCE: retry retained non-writing reviews

Status: ACTIVE. PRIME owns this bounded failure/recovery slice under the active
retrieval and connected-authoring goal. Base/parent: PR2187 exact
 e3aa4dd6351aac86bb27d520b2822395c0448e4a, branch
codex/retained-connected-review-retry in the existing buddy-context-loop checkout.
Topology: stacked; merge/deliver2187 first, re-anchor this child on its merge,
then independent review, all CI, merge and owned API delivery. Parent remains
frozen; this child takes exclusive ownership of the ordinary factory test path.
No new worktree, environment, provider, schema, ingestion or runtime lease.
Other INGEST paths and held Play2172 remain outside this write set.

## Outcome and critique

The retained Corrupted Edge failure54302dde resolved review_connected_page with
answer_from_sources, but retained_discussion_capture accepts only the discuss
label. The normal Retry control consequently refuses before provider admission.
The original capture contains a write capability: it must never be inherited.
Use the already admitted operation to distinguish non-writing retries from work
that requires a fresh authoring target. Do not duplicate the semantic classifier
with a second allowlist of review labels. A retained review may prepare another
review; it cannot save a page or publish a relationship.

Preserve original question, captured draft and references, active conversation
pointer, exact predecessor revision and lineage, known provider outcome, and
fresh no-write successor intent. Writing operations still need a fresh target.
Stale/newer-page, mismatched references/question/revision, reused write capability,
unknown outcome and competing successors must still fail before provider calls.
Do not alter or reset the original failed attempt. Existing API/intent/event
shapes remain; no compatibility execution path or new provenance authority.

## Exclusive expected writes

- This handoff.
- src/application_state/agent_conversation/retry.py: operation-based admission.
- tests/test_surface_native_build_ordinary.py: adopt existing native HTTP/default
  factory, source reads, retained-context admission and lineage/replay fixture;
  exercise connected review with an original captured write capability.
- tests/test_build_turn_retry.py or tests/application_state/test_turn_retry.py
  only if existing owning rejection/lineage cases need additional coverage.
- Docs/Plans/HANDOFF-RETRIEVAL-opened-reference-source-hint.md: settlement only
  after parent merge/delivery evidence is knowable; never pre-mark it delivered.

## Validation and delivery

First retain a failing ordinary connected-review Retry reproduction. Verify the
actual native retained-input GET and ordinary POST/SDK/default factory, preserved
references/draft, successor without write capability, one immutable retry edge,
delivery replay, no page/Graph mutation, and all listed negative cases. Run the
owning retry and ordinary Build suites in disposable APP54329/synthetic Core only.
Primary APP54331, Core54330, UI5202, benchmark55447 and retained failures are not
test fixtures. Independent Bugbot review of exact cumulative parent/head diff,
all CI and protected delivery precede ordinary original-attempt dogfood. This
slice does not claim full authoring, References or operator acceptance.
