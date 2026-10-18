# INGEST: protect indented candidate source from generated navigation

Status: SETTLED — PR #1404 merged ate72a5cdf0630bf3742ee57e6b2e7e54d4e371c2a
after ARCHITECTURE Cycle1 PASS on74aac5516875ff9fc2c23b1bd135d6f96b9694dd.
API-only delivery and actual browser verification passed. This write lease is closed.
Base: origin/main@239011a4ebe4aa478d38b23da8760366bc88f972.
Branch: codex/ingest-indented-candidate-code; reuse buddy-context-loop checkout.
Topology: serial successor to merged #1401; parallel-independent of DOGFOOD #1403.
No overlapping paths, new worktree, environment, preview or provider experiment.

## Invariant and critique

Actual retained Session29 source contains two four-space-indented blocks. The
candidate projector inserted navigation inside them, but the mounted Markdown
reader correctly treats them as literal code/fallback text, exposing generated
qualified IDs. Do not dedent or reinterpret source code as prose to hide this.
Protect candidate mentions on lines beginning with four spaces or a tab before
insertion; retain original bytes/coordinates and all nodes in the local list.
This conservative candidate-only protection also skips indented list continuations
rather than pretending full CommonMark parsing. Report that limitation through an
explicit diagnostic and truthful mention/unlinked counts. One-to-three-space prose
remains eligible; existing fenced/inline/link/image protection remains untouched.
Do not rewrite literal source dmb-node strings. No vocabulary, schema or public
API change; same read contract, no write/native/provider side effect.

## Exclusive expected write paths

- This handoff
- Docs/Plans/HANDOFF-INGEST-exact-candidate-recap-reader.md (factual settlement)
- apps/live_control_server/services/exact_run_candidate_projection.py
- tests/test_exact_run_candidate_projection.py

All shared Markdown admission/mention engine/UI paths remain read-only. This is
not a general Markdown parser improvement or permission to relax editorial saves.

## Verification and delivery

Owning production-produced synthetic run tests: four-space/tab source unchanged,
no generated links in protected lines, one-to-three-space prose linked, CRLF and
Unicode offsets correct, mixed continuation conservative/diagnosed, literal
source graph links unchanged, all candidates still inspectable, counts honest.
Run existing30owning tests on unique disposable54329DBs, no retained54330/54331.
Re-read exact retained Session29 with readonlyDB and compare raw3component hashes.
Cumulative diff→commit/push/onePR→independent review→guarded merge→API-only adoption,
preserving all records and current UI. Reopen real candidate and verify raw
qualified generated navigation disappears from the two source blocks while
ordinary chips/inspection work. No new provider/correction/Graph publication.


## Verified delivery

41 owning tests independently pass. API PID696264 serves the single reviewed
service-file correction; UI index5d90f904 remains unchanged. Ten retained records
and saved Ingestion artifact hashes match before/after restart. Actual Session29
browser verification:66nodes/65relationships remain available,56real chips,
no generated dmb-node:candidate markup in the visible recap, and Brin local
inspection works. The two source blocks are readable plain original text.
Rawsource/candidate/span digests remain unchanged,48nodes honestly unlinked.
No provider, correction, Graph publication, source/Plan/Run/note or UI write.
Broader source formatting and semantic acceptance remain separate unfinished work.
Private receipts: established jev-evidence-loop-20261016 candidate-indented-code-*;
user-facing screenshot session29-candidate-reader-delivered.png.
