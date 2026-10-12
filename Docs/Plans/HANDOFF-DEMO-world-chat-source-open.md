# HANDOFF — DEMO: open sources from durable World conversation

**Status:** SETTLED, 2026-10-12. UI PR #1091 merged at `39af83580e8d9a4a6367560f34f9ab6d021aa6b7` from reviewed head `3d845240da27658c2c9e08104088622972c2f616`. This handoff grants no active path, runtime or state lease.
**Owner:** DEMO; PRIME controls subsequent activation and merge decisions.
**Producer pins:** SERVER source-open projection #1090 merged at `5614fb1c9156a6a42aed94e2f2422f52df412667` (DTO code `98bc9eb18cda45daffc50d94d32947051c92368b`); SOURCE recap reader #1089 merged at `8fce46de7e33bc352300abdf3ece0369a3ac1e68`. Portable architectural ruling SHA-256: `d1502b6cea6172e170a6008000bf0f60f99ce84635c37adc872bcd4a03f0dea4`.

## Delivered boundary

Ordinary saved World Plan answers now show source-opening actions outside collapsed Details. A genuine `evidence_anchor` target uses the pinned World Graph source-anchor reader and **Open evidence**. A separately projected `related_recap_context` target uses SOURCE's recap-context reader and **Open related recap context**; recap context does not become claim support. The consumer checks the target against its saved claim and frozen World authority, then checks the reader's returned identity before showing text. `source_read_id` and `source_opened` remain producer-read audit data, not user-click state.

The reader keeps multiple choices distinct, initially shows at most three, wraps labels, marks partial passages and limited choices, and offers Close. It distinguishes no related context from unavailable metadata and keeps valid links when another source choice cannot be offered. Switching scope clears the passage; a late read cannot put prior-scope text into the current answer. Old history without targets remains readable without fabricated open actions.

## Evidence and limits

- DEMO's mounted World conversation suite: **186 passed** after the SERVER merge. It covers fresh and reopened history, exact evidence and recap reads, foreign or mismatched target rejection, limited choices, close, and late reads. `tsc -b` and cumulative diff check passed.
- ARCHITECTURE reviewed the UI at head `f75bb6e2d9e0bb024ff6a2c5575edf18f2e42366` and reported PASS. DOGFOOD reported bounded code/test UX PASS at unchanged UI code/test blobs `180effe98f031b2a8c63e962997a712e854e13a6`; PRIME performed independent review before merge. The later commits only integrated producer main and updated handoff pins.
- No live World runtime, provider, database, Graph or corpus write occurred in this UI slice. The tests and reviews do not certify a useful real answer, a live passage-opening journey, or operator acceptance. Do not claim HTTP abort on unmount: the consumer invalidates the UI request epoch and ignores a late React result, while the underlying HTTP request may finish.
- The Stacey continuity challenge remains a separate operator acceptance fixture. Current checked source calls Stacey and Marla bugbears in Session 20; a proposed bugbear conversion would not test a contradiction. PRIME's preparation direction is a verified bugbear-to-half-elf challenge without canonical mutation, pending native retained Session 20 recovery and the operator journey.

Future ordinary-chat Debug, quiet refresh and Agent context-read tooling require their own bounded contracts. They are not implied by this merged UI consumer.
