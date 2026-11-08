# RETRIEVAL: exact assertion qualification packing

Status: ACTIVE; root adopts independent invariant critique before implementation.
Root is designing steward and backend owner under the active retrieval goal.
PRIME owns merge/delivery; primary/live state stays unchanged.
Branch codex/native-qualification-packing; exact parent #2218 head
9b1a8a79f9cdbfcb2b4574583d38c9c1d971a42e. Stacked topology and merge order:
#2214 -> #2216 -> #2218 -> this slice. No UI changes or ingestion changes.

## Evidence and hypothesis

The rejected #2220 experiment remains unmerged at a3a10bb502b5cb14532599c24196334cd0b18016.
Its retained actual SDK packets show 205119--433342 repeated UTF-8 JSON bytes in
exactly identical assertion metadata objects. Q09 has 565 assertions but only129
unique metadata objects; its assertion frame is619530 bytes versus50608 source
body bytes. Evidence: plan-writer-effort-v1/actual-writer-packet-sizes.json and
assertion-metadata-repetition.json in the existing retained evidence root.
Those numbers are a theoretical dictionary saving before references/format cost,
not token counts or a proven latency gain.

Hypothesis: a deterministic exact-object dictionary for assertion qualifications
reduces model input and assembly work without losing meaning or citations. Change
only model presentation, never the admitted records or source authority. All
claims, order, handles, uncertainty, chronology, domain meaning and source quotes
remain exact. No selection heuristic, truncation, extra call or fallback.

## Adopted owner contract

One current producer emits qualifications once and explicit references per
assertion. Dictionary identities are local addresses, not authoritative facts.
The host rederives the complete expected packet from admitted receipt/execution
records before accepting a producing request. Any altered qualification, reference,
missing/extra entry, duplicate, reorder or mixed presentation must be rejected
unless exactly equal to the canonical rederived packet.

Retained inline semantic inputs must remain verifiable by their exact historical
codec, selected from actual producing format, not by retry/fallback. No current
dispatch option may produce the obsolete inline form. Existing output schema and
source reopening owners must see fully resolved semantics without changing handles.
Review whether output_frame should resolve dictionary references or retain the
original host qualification rows; preserve current typed qualification projection.
Use a distinct closed top-level assertion_qualifications field for packed frames;
historical inline frames have the original exact five-key shape. Reconstruct
inline semantics from the host for output validation, not from untrusted refs.
Add revision131 reader fencing, as older readers cannot verify packed requests.

## Proposed write boundary

src/application_state/agent_conversation/native_evidence_view.py;
src/application_state/agent_conversation/native_writer.py;
tests/test_surface_native_writer.py; affected actual ordinary SDK tests only;
this handoff. Any required migration/fence or changed output-schema contract must
be named and added by root before implementation, not silently absorbed.
Root explicitly adds src/application_state/migrations/versions/
20261108_0131_native_qualification_dictionary.py and owning migration tests to
this exclusive lease. No table or publication contract changes. The fence and
producer/reader contract are indivisible: deploying only one would break reads.

## Validation and stopping rules

First, offline replay the same retained packets through the owner projection.
Prove exact expanded equality including order and local citation handles; test
tampered metadata/ref/dictionary, ambiguous formats and retained historical inputs.
Check actual ordinary Plan and Build dispatch and citation reopening boundaries.
Obtain independent cumulative review before new paid calls.

Initial changed-behavior cohort Q01/Q09 and Q14/Q15, two workers, one ordinary turn
each, against retained #2218 low controls. Fixed corpus, same model/provider/low
effort/fast tier, prompt instructions and output allowance; Gold excluded.
Before dispatch require lower bytes and actual tokenizer count on all4 retained
packets, at least25% median input reduction, and exact semantic equality.
Live acceptance requires no lost control-covered facts, no new unsupported claims,
and no attribution/citation/control regression. Record changed acquisition as a
causal limitation. Promising results require full15 predeclared repetitions before
adoption. Reject on semantic loss, irreducible complexity or quality regression;
no unchanged reruns. Preserve rejected code and evidence without active fallback.

Retrieval timing is accepted request to writer authorization, excluding prose.
Use existing trace precision, distinguish concurrent from warm/cold, and retain
unknown billed cost. Four cases cannot establish tail latency or goal completion.
