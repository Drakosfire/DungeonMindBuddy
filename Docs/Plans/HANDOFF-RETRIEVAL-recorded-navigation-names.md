# RETRIEVAL: preserve multiple recorded navigation names

Status: ACTIVE under the user retrieval goal. Root owns backend implementation;
PRIME owns merge/delivery. Branch codex/navigation-recorded-names.
Topology: stacked on #2218 head9b1a8a79f9cdbfcb2b4574583d38c9c1d971a42e;
merge/rebase order #2214 -> #2216 -> #2218 -> this slice. Checked open UI lanes
#2219/#2222; no UI changes or overlapping write lease.

## Confirmed boundary

native_graph_reads._navigation_labels computes a set of scoped admitted name
values, then discards every value when the set has more than one entry. The
controller sees Unnamed object instead. Retained four-case ledgers show the party
has13 distinct recorded names and111 incident assertions; Stafl has2 names and
61 assertions. Q01 admits379 assertions across10 temporal qualifier groups.
Evidence: selection-breadth-audit-v1/object-expansion.json plus the pinned raw
native-qualification-packing-v1 ledgers. These counts do not prove irrelevance.

Hypothesis: showing the complete set as multiple recorded names enables better
selection than opaque unnamed aliases without adding a pass or changing reads.
Never choose a canonical identity/name, infer aliases, merge objects, promote a
name to fact or broaden scope. Keep missing names unnamed and existing unique/
duplicate-name behavior. Preserve exact scoped Core reads, complete_only policy,
local ordinal disambiguation and host IDs outside model-visible navigation.

## Exclusive write lease

apps/live_control_server/services/native_graph_reads.py;
tests/test_native_plan_assertions.py; tests/test_native_plan_statements.py;
this handoff. No query/receipt schema change, migration, prompt instruction,
provider/model setting, source selection policy or publication change.
Historical labels remain frozen in their stored query; new requests compute new
labels and query hashes. One current label producer; no legacy runtime fallback.

## Experiment and acceptance

Only changed variable: a multi-name object's navigation label shows all distinct
admitted scoped names in deterministic sorted JSON with an explicit multiple-name
label and existing local object ordinal. All names remain navigation metadata.

Verify owning discovery and actual controller SDK input, distinguishing duplicate
entities, missing names, conflicting names, partial entity reads, foreign-campaign
names, case/Unicode/literal IDs and reversed input order. Independent subagent
review must challenge privacy/scope and identity ambiguity before paid execution.

Then use the existing consolidated workflow: Q01/Q09 shardA, Q14/Q15 shardB,
two workers, one ordinary turn each; compare retained #2218 controls. Same corpus,
original APP125->130 state, model/provider/low effort/fast tier, prompts and output
allowance. Gold assessment-only. No per-question scripts or changed ingestion.
Record selected objects, incident assertion counts, session qualifiers, actual
input volume, retrieval intervals, tokens/cost and fact-level coverage.

Accept as promising only with reduced assertion/input breadth in at least3cases,
no lost control-covered fact and no new unsupported, attribution or citation
regression; Q01/Q14 stay complete. Acquisition differences limit causality; all
four cases must be retained, not just successes. Stop/reject on scope/privacy or
quality regression or no breadth benefit. No unchanged retry until pass. A
promising candidate needs predeclared repeated full15 validation before adoption.

Primary/live unchanged. Rejected #2220/#2221 remain pinned historical experiments,
not defaults. Frozen full benchmark remains6complete/9partial until new evidence.
