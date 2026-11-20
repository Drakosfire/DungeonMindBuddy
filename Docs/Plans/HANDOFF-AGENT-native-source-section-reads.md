# AGENT — selected native source section receipts

Completed predecessor: #1635 merged8551a91430960259d45705f9cb7465987ba2be48
after one Bugbot cycle at reviewed head2fff325ddbb42ebad3aca27870451671a2ba18f1.
Author149 tests passed with2 skips; independent30 APP tests passed. No serving
activation. Consuming writer-input lease: HANDOFF-AGENT-native-source-writer-input.md.

Original ACTIVE serial PRIME slice; base9360eb9b48d8fb5d80815f3f4f7ab6643e8da128,
branch codex/native-source-section-receipts, existing buddy-context-loop checkout.
Predecessor #1634 catalog materialization merged; parent #1631 design. One Bugbot
reviewed PR, PRIME merge; no ordinary tool/route/provider/writer/citation activation
or serving/retained database change. Census2026-10-22: no overlapping APP read lane.

Outcome: persist selection authorization before returning an exact selected excerpt,
then bind a complete/unavailable receipt to that authorization and the verified
host body material. Sibling sections use the original catalog body; no new source
body IO. Exact retries do not duplicate reservations or text. Cache loss/mismatch
settles as unavailable, never silently reloads a source or substitutes latest.

Writes: this handoff; HANDOFF-AGENT-native-source-catalog.md predecessor settlement;
src/application_state/agent_conversation/{types.py,service.py,plan_jev_decision.py,
native_source_sections.py};
src/application_state/migrations/versions/20261022_0055_native_source_sections.py;
tests/application_state/test_native_source_sections_postgres.py.

Use dedicated authorization/read events in explicit native section capability.
The APP transaction owner derives selection from an earlier complete catalog and
checks provider acknowledgment, frozen scope, unique selection/read identity,
existing per-read/aggregate source character budgets and owner/claim fences before
materializing text. Keep native revision, APP UUID, full hash, selector/catalog,
line/character ranges and excerpt hash distinct and exactly joined. No caller
ranges, partial success, Graph evidence IDs, source-name invention or new caps.
Record zero fresh body IO; preserve measured extraction/verification duration.

Charge exact native selected characters as reservations until complete/unavailable
settlement; unique nonoverlapping catalog siblings count once. Existing Graph
read/exposure accounting stays unchanged, including its conservative charges;
no cross-family union/dedup or actual provider token reduction is claimed here.
Pair writer projection/inclusion with explicit overlap handling in the consumer
slice. Providers cannot proceed with unresolved native section reservations.

Verify actual APP catalog→authorize→read→reload, exact retry, sibling reads without
source IO, identity/range/hash tamper rejection, explicit unavailable settlement,
existing budgets/fences, pending provider refusal, concurrent exactly-once receipt,
Unicode/CRLF exact slices, historical records and migration downgrade protection.
Use disposable synthetic sources; no private corpus publication. Model exposure,
named citation/completion proof, authenticated reopening and rendered Plan/Play
routing remain paired successor gates; these tests do not close the full goal.
