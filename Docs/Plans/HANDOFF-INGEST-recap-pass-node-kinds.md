# INGEST: bound recap pass node kinds

Status: CLOSED. PR2065 merged/delivered c125b91ba9cc297d883dacfe98fcbf48af6909e6; exclusive lease released. Actual S7 run70fcd7d0-9b96-4141-855c-5adb5e3544af produced zero foreign kinds,7attempts0retries; this proves the scoped boundary, not full quality. Successor: HANDOFF-INGEST-recap-object-authority.md. ADV owns design and implementation under the user's ingestion-through-publication assignment; PRIME reviews and owns merge/delivery.

## Lane and topology

Serial successor to merged source-form PR2064 (c3d7a0063980878bb1765713e357f838a03f2309), delivered in fetched base 9855ef2ea9c5507247e6fb35c96c4744774b8b88. Branch codex/recap-pass-node-kinds; checkout /home/drakosfire/Projects/.codex/249d/DungeonMindBuddy. No unmerged behavioral dependency. Open ingestion PR paths inspected, including1148/1235; this lease does not overlap their extractor/UI edits. PRIME informed before implementation. No ports, services, providers, databases or publication writes allocated.

## Invariant and evidence

Actual isolated S7 run810d1eb6-fdf9-4397-b949-dc30ab8b80bc emitted11characters and1location from thread_pass. Preserve the run and source-only Gold. Each declared pass must accept only its owned node kinds through the existing allowed_node_types response-schema mechanism. Wrong-role records must receive existing conformance handling, not silent post-filtering or identity merging. Type conformance does not prove source entailment or remove within-pass duplicates.

Actor owns character/creature; location owns location; collective owns faction/organization/group; object owns item. Thread retains existing supported semantic vocabulary: event, clue, thread, mystery, warning, promise, debt, rumor and unknown_important. Dedicated optional encounter/job owns combat_encounter/quest. Preserve dispositions' existing optional kind contract. Shared recap node passes apply to both recap profiles. Worldbuilding is unchanged.

## Exclusive write lease

- src/graph_memory/extraction/recap_extraction_profile.py
- tests/test_recap_pass_node_kinds.py (new)
- Docs/Plans/HANDOFF-INGEST-source-form-authority.md (predecessor settlement only)
- This handoff.

No profile identity change, new validator, producer, representation, fallback or native gate. Beat source-excerpt authority is intentional and unchanged. Full objective remains C1S1–10 Gold/isolated publication, then agreed worldbuilding, then benchmarking. Semantic holds remain separate work.

## Validation

Exercise actual pass-spec provider JSON schemas with valid and wrong-role payloads, preserving dispositions and all supported thread kinds. Run adjacent schema, recap prompt and worldbuilding profile tests; inspect cumulative diff and report inherited failures honestly. These tests prove schema enforcement, not actual model quality. Submit committed/pushed PR to PRIME before any delivered-runtime comparison.

Validation completed: regression before fix failed all5 pass role-rejection cases (pass-node-kinds-red-v2.log); after fix30 focused schema/recap/worldbuilding checks and74 bounded execution checks pass. Ruff and cumulative diff whitespace checks pass. Logs retained under /tmp/pr2026-audit-8779. No actual provider dispatch or publication acceptance claimed.
