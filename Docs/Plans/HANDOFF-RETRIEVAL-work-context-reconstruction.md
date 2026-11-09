# RETRIEVAL: fresh work-context reconstruction

Status: ACTIVE. Root owns design and implementation under the retrieval goal.

## Slice and topology

Serial slice based on `da00448bfd14e7809a2744435e1b03bc0feafaf2`, branch
`codex/retrieval-work-context-reconstruction`, in the recorded-names-control
checkout. PRIME owns merge and delivery. The final pre-branch fetch included
merged #2268 at that base. Its Plan runtime paths were inspected; this slice
does not edit them. This is a main-based successor, not an unmerged stack.
The work-context owner is byte-identical between the previously inspected
`5c49a30f37b11ac3b5706f553f0505b3b9a571cb` and the actual base, so the retained
old-code comparison remains valid. The 139 owner tests ran on this actual base
plus the bounded change, including the merged Plan additions.

Expected write lease:

- This handoff.
- `src/application_state/agent_conversation/native_context.py`.
- `tests/test_surface_native_context.py`.

## Hypothesis and invariant

The work/provenance join can reconstruct fresh values from complete Python-mode
dictionaries instead of serializing them to JSON and immediately parsing them.
Keep every existing commitment and surface-owner check. Never trust the original
model instance or introduce a cache, skip flag, fallback, or parallel reader.

This changes internal reconstruction only. Database wire decoding, Build action
capabilities, provider requests, accounting, model settings and source selection
are unchanged. In particular, direct Python decoding of raw database Build
execution dictionaries is **not** authorized by this design.

Evidence: the frozen original/current comparison passed all 60 context captures;
remaining admission costs are material, but this local change has only a small
expected benefit. Simplification is independently useful; do not count it as a
validated whole-cycle speedup or as meeting the four-second target.

## Verification and stopping rule

Run the existing three-surface context/execution tests, including malformed
nested-instance mutations. Compare returned canonical contexts against the old
codec on retained optimized captures, with fixed local repetition order. Use
independent subagent review of the cumulative diff. No new paid calls, database
writes, ingestion, publication, migrations or live runtime changes.

Accept only if all actual supported families retain canonical output and nested
mutation rejection. Otherwise fix this owner or reject the slice; do not add a
surface-specific fast path. Open one bounded PR after verification. Broader
admission redesign and historical ingestion-script retirement remain outside
this lease.
