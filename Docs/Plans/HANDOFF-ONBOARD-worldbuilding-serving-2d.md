# ONBOARD: carry Worldbuilding recovery onto the serving release

Status: ACTIVE under the owner's Sizzek delivery goal and explicit authority to
review, merge, and deploy. This serial integration follows merged Buddy #4548
(`667e60eff36350aa378924e40eb5c1ebd00fc4f0`). The exact serving parent is
`2d4361fb05e0b6bbb4e652535b77acd7b30ad1fb`, currently running with schema
`20261123_0204` and guest build `review=1;page=1;home=b4fe79bc-412c-43cc-a5c7-ad97ccaa5543`.
The serving parent is not main; a main-only image would discard serving changes.

Outcome: integrate the merged recovery capability onto that serving parent,
preserving all serving-only behavior and migrations. This slice is a serving
integration, not new extraction semantics. Its expected write set is this
handoff and the files changed by #4548, with any conflicts resolved in favor of
retaining both serving behavior and the reviewed capability. Pin the parent as a
remote base and review the cumulative base-to-head diff. No live runtime, port,
database, or production file is leased during implementation or verification.
Production activation is a subsequent step under the owner's explicit release
authority and the shared deployment lock, after checking the serving parent has
not changed and the candidate retains the guest flags and schema compatibility.

Topology: serial; #4548 was merged first, then this serving integration PR targets
the pinned 2d serving base. Verify the exact head using the frontend hosted
verifier, focused frontend recovery tests, isolated backend recovery and hosted
ownership tests, appropriate backend contracts and independent Bugbot review.
Compare full-discovery frontend failures with the recorded serving baseline and
retain inherited red results. Do not claim full release qualification unless the
full diagnostic actually passes. Build and verify the exact candidate image and
same-schema rollback before activation.
