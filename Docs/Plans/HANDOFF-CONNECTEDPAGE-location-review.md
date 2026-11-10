# CONNECTEDPAGE: reviewable new-location default

ACTIVE PRIME stacked UI slice on codex/connected-page-location-review. Parent
PR2335 exact b4f9be3d617e3331cd51e116d07f7aaf0d3386d9; merge2335 first, rebase
this slice onto its merge, independently qualify final head, then merge/deliver.
Existing context-loop checkout/dependencies; no new environment. User requests
quick review/create with clear mandatory Location choice and required markers.

Exclusive writes: this handoff; UI src/shared/ConnectedPageReviewControl.tsx,
src/buildSurface/BuildConnectedPageControl.test.tsx. Color2335/Composition2334
and Surface/Storage/CI lanes do not overlap these paths. No publication/admission
contract change: new pages still require explicit Create confirmation and the
existing exact intent, storage/recovery and native confirmation owners.

After a complete native identity check with no matching locations, default fresh
manual/agent reviews to visibly named new location. Keep explicit choice when
existing candidates match or the identity check fails; never guess
an existing identity from a label. Keep existing identity choices and exact IDs.
Explain that choice controls a new Graph location versus linking an existing
one. Mark required title/location, set native required on the selector; optional
fields stay optional. Title edits retire an existing selection and re-evaluate that same condition,
visible before submission. Preserve frozen retry identity and restored
review choices. No creation, story edits, provider calls or Graph publication in
verification. UI-only delivery, API447264 unchanged. Do not absorb latency work.

Verify default/required semantics, same-name existing locations never auto-selected,
explicit existing selection reaches intent, title edits reset to new, restored
and frozen retries preserve exact identity, Plan and Build share the control.
Run owning tests, cumulative review, exact-head hosted/build/discovered evidence.
Independent Bugbot review and PRIME standing authority govern delivery. Browser
bridge currently unavailable; DOM/API/asset checks are not rendered proof.
