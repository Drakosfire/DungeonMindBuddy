# DOGFOOD: reuse retained context for discussion without another search

ACTIVE, directly authorized by Alan's #4459 continuation. DOGFOOD owns this Buddy
runtime design and implementation. This bounded successor explicitly revises the
predecessor's serial-undispatched start restriction: stacked implementation,
serial merge/delivery. Parent PR4484 exact0d0b2019929f653914484badab26dcbda60d6bb2;
branch codex/dogfood-discussion-context, same isolated checkout. Merge4484 into its
owned serving base first, then this child. No runtime write lease in this slice.

Outcome: an anchored discussion/recap receives the same complete prior dialogue
and already-authorized authored/native reads as page synthesis, without Graph,
related-page or body acquisition. Explicit requests for fresh evidence retain
existing acquisition semantics. No new page or title grammar in this slice.

Contract: new retained admissionV3 enables discussion; V1/V2 remain page-only.
APP reader fence0194 follows this serving lineage's0193. Preserve full chronological
closure, pointer/attempt fences, source identities, current-principal reopening
and exact serialized request replay. Source-scope guidance makes explicit reuse
and no-search intent distinct from requests for fresh evidence. Discussion keeps
its ordinary low effort; extending reuse must not promote it to page-draft medium.

Exclusive writes: this handoff; retained_conversation.py, native_corpus.py,
native_execution.py, writer_evidence_selection.py, types.py, repository.py,
service.py and build_intentional_response.py in the conversation package;
build_jev_harness.py, build_jev_driver.py and plan_jev_writer.py only for this route;
new migration0194 and tests/test_build_retained_conversation.py plus owning
ordinary HTTP test fixture protocol support only when necessary. No provider/model,
Rules, Graph publication, source repository/cache, title parser or frontend edits.
ONBOARD4489 surface_evidence_answer.py remains outside this lease.

Validation: ordinary HTTP recap after early uncited read beyond recent history,
no editor snapshot and changed current page; deny physical source acquisitions;
exact full input and original citation reopening; anchored vs fresh source scope;
legacyV1/V2 discussion admission rejected; V3 codec/replay/old-reader fence;
existing page synthesis compatibility. Run owning exact-SHA contracts and frontend
verifier, inspect cumulative parent→head diff and independently review. This
slice depends on4484 qualification/merge, not on its deployment. Later title and
latency PRs remain separately reviewable and serially delivered. Full4459 acceptance
still requires actual deployed app page/save/reopen and measured long-chat latency.

Current main has a separate0193 variant-portrait migration not in servinga5c;
this serving-fork chain does not silently adopt or overwrite it. Reconcile actual
serving integrations and migration/recovery lineage before any combined cutover.

Owning HTTP diagnostic exposed an earlier acquisition boundary: Graph preparation
starts concurrently with the opening decision unless a literal page request was
recognized. Merely adding retained admission would still perform the forbidden
search. This same route slice must wait for an offered semantic source_need
choice before starting Graph; source_lookup then follows the existing route.
The physical-acquisition-forbidden regression caught this failure (503) and is
retained at /tmp/dogfood-discussion-diagnostic.log. No unrelated Graph change.

Working-tree discussion boundary now PASS (2 checks,31 deselected,35.48s):
8 actual prior HTTP turns, original uncited native/authored reads after current
page changed/discarded, physical acquisition forbidden, full serialized dialogue,
original citation resolution, repeatedV3 prefix fast path and V2-on-discussion
rejected. A second diagnostic failed only because its tamper probe serialized
policy aliases/tuples incorrectly; corrected to the owner's Python/by_alias form.
Both unsuccessful diagnostic logs remain local. Exact-source suites and review
are pending; no deployment claim.
