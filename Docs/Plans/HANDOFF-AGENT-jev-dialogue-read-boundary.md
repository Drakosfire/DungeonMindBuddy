# AGENT — separate conversation references from retrieval coverage

SETTLED #1604 at 8dc5c44fb3c80be8a5d1037b0be30fe979f76c4a, running 8000/5202.
Bugbot approved 0c6173f18c7a4c5fff9169e2a302b9baee9e95b9 in one cycle, no findings;
75 independent tests passed. Real corpus-grounded runs took 10.431s, 9.556s and
14.929s (clean conversation). Exact named source reopened after restart with all
1676 APP rows, native rows, 79 mechanics files and 11 frozen components unchanged.
Fresh run used four Jev calls and followed a peripheral NPC; citation prose also
mislabeled notes as a recap despite the correct session link. Reliable latency and
wording quality remain open; no full-goal acceptance.

Historical serial PRIME successor from10c4422025024d8b950ef91b11caa2fce0613b20,
branch codex/jev-dialogue-read-boundary, existing buddy-context-loop checkout.
Operator goal authorizes Jev prompt refinement, deduplicated reads and actual
swamp/Edge corpus grounding. Open PR census shows no overlapping active lane.

Architecture critique01a164ea-de32-7cd3-a53a-ec66e002ef5a identifies candidate-level
instruction ambiguity and a host-state distinction: examined_subjects means
attempted acquisitions (including failures), never successful source coverage.
Keep that distinction explicit. This slice does not ask Jev to judge successful
coverage: candidate votes judge additional relevant acquisition; the fallback
judges only whether further discovery is useful. Actual receipts and the final
writer remain the only acquired-evidence and answer-sufficiency authority.
No new host coverage field is needed for that bounded decision. If a later design
asks Jev to judge successful coverage, it must add validated receipt-derived state.

Remove the global assumption that offered candidates are unhelpful from the same
batch that votes on them. Every candidate question states dialogue can resolve
references but cannot satisfy a current corpus request; attempted subjects suppress
duplicate acquisition, not establish facts. Relevant unattempted candidates should
be selected when the user requests evidence. Exclude peripheral candidates and
preserve discovery/terminal-gap behavior. No keyword router, caps, retry, public
schema, source authority or image-intent changes.

Lease: this handoff; src/application_state/agent_conversation/jev_retrieval_contract.py
(instruction text only); tests/test_jev_retrieval_contract.py and
tests/test_plan_jev_driver.py; predecessor HANDOFF-AGENT-writer-source-authority.md
and Docs/Roadmaps/ROADMAP-demo.md for truthful1603 settlement.
One exact-head Bugbot-reviewed PR, PRIME merge and guarded8000/5202 delivery.
Core617635c and APP0045 remain unchanged.

Verification: actual typed SDK wire with assistant false coverage and user reference
resolution; current-attempt object/source receipts and exact final provider inclusion;
failed/refused reads preserve gaps and are not retried; mixed-topic/shared-anchor
reads deduplicate; stale/foreign scope still refuses; include votes retain priority.
Live ordinary original swamp/Edge request must acquire actual relevant source
receipts and final citations, not merely produce a fast Plan-only reply. Measure
service and per-call timings separately; full repeated10s/adventure acceptance stays open.
