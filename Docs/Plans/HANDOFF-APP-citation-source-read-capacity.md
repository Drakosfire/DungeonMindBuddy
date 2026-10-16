# APP: preserve every included source read in a citation

Status ACTIVE under PRIME Mirathorn lifecycle goal. Base main50f6aee329dd38c2d429554f5d55a06ff9891605, branch codex/citation-source-read-capacity, non-serving /tmp/prime-recap-mention-boundaries. Serial; PRIME solo implementation; ARCHITECTURE independently reviews.

## Outcome and owned contract

Align APP PlanWorldGraphCitationV2 source_read_ids validation capacity with the receipt stream it already admits. Current max8 confuses one read batch with the full producing envelope. The ordinary Build Float Goat turn0817b6a2-f774-4022-8798-5bb834755999 derived24actualreadIDs for24canonicalrefs and failed citation_schema. Exact saved draft f570e0008c6708638a781bb788e67bc64b13cff45e1a59f9e8bf5f69e96f184a reproduces locally without provider calls; no model-authored citation metadata was wrong.

ARCHITECTURE confirmed: derive citation capacity from max included V3 source-read events2048 × max receipts per read event8 =16384. These are outer serialized validation bounds, not new execution grants. Repeated valid reads can share an evidence ref, so max64refs cannot bound readIDs. Preserve all receipts; never truncate or select an arbitrary subset.

Preserve sorted unique IDs, exact producing-envelope inclusion, validated source content/hash/revision/evidence binding, scope authorization, per-read/body/aggregate/storage safeguards and all provider lifecycle checks. Existing JSON fields/versions/serialization stay identical. Check SQL constraints before determining no migration; no native Graph contract change.

## Exact lease

- This handoff.
- src/application_state/agent_conversation/types.py
- tests/application_state/test_citation_source_read_capacity.py (new)
- tests/application_state/test_agent_source_admission_v3_postgres.py

Shared constants bind the existing2048V3event field and8receipt field to derived citation capacity without changing their values. No unrelated policy refactor. UI existing string[]/normalizers have no max8; recheck affected consumers. Open1259/1235UI and1244packager are disjoint. Stable5876/8002, DOGFOOD5202/8000, providers, corpus and retained databases untouched during implementation.

## Evidence

First demonstrate the24read regression against untouched base. Then prove24/64/>64read IDs, duplicates/unsorted/unknown/omitted/noncontent/foreignref rejection, derived outer limit+1 rejection, and actualAPP completion with24read IDs plus fresh-process identical readback. Revalidate the exact preserved failed draft locally against its original producing authorization; do not mark the original failed turn completed or replay its provider request. Preserve beginning/end refs and all outcomes for task gold. Inspect cumulative diff, commit/push/open one PR, independent review before merge; runtime adoption/new ordinary turn follow separately.
