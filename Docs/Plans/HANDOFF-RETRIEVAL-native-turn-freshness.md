# RETRIEVAL: one native Turn freshness owner

Status: ACTIVE prototype qualification. Root owns this human-authorized slice.
Base: origin/main eb0eb9a093b275e8e8282d6c749309f2bdd687a6.
Branch: codex/retrieval-native-turn-freshness. Topology: serial, one bounded PR.
No provider, runtime, primary database or publication write authority.

Outcome: fresh native components once at Turn construction, followed by the same
cross-component joins. Public standalone validators remain fresh defensive owners.
The historical execution-owner reconstruction lease is adopted as completed
predecessor scope, not a competing implementation. Current PRIME work inspected:
Build UI document reference search/preview, disjoint from this allowlist. Overlap
notice sent; no conflicting active native-Turn implementation found. Open PR
inventory checked on activation date; held Play
and composition work remain outside this slice.

Expected writes: this handoff; HANDOFF-RETRIEVAL-execution-owner-reconstruction.md
(truthful predecessor settlement); src/application_state/agent_conversation/types.py,
native_context.py, native_execution.py; existing native Turn/context/execution and
repository tests. Any expanded contract or path requires a checkpoint.

Hypothesis: public mutable binders defensively reconstruct components already
reconstructed during Turn construction. One root wrap freshness boundary can
remove that repeated work without trusting incoming model instances. Preserve
raw database JSON codecs, historical families, completion checks, lifecycle,
request/provenance commitments, capture identity, replay/CAS and error mapping.
No flags, caches, fallback, global strictness relaxation or new representation.

Qualification: all native constructor/existing-instance/model-copy/JSON/repository
routes preserve canonical context and reconstruct mutable components. Mutated
native schema cannot retype into a historical family. Public binders still refuse
nested corruption. Retained 30-context parity covers all 15 questions twice;
benchmark context assessments remain bound to unchanged model-visible bytes.
Independent exact-diff review and owning boundary suites before adoption.

Measure component construction counts and fixed-order repeated local timings.
Prospective promotion rule: reduced reconstruction count and at least 10% median
local Turn construction improvement on retained rows, with no context/refusal
regression. Otherwise reject/defer; no unchanged paid reruns. Local timing is not
an end-to-end claim. Existing 12.04s baseline remains pinned, writer output excluded.

## Qualification checkpoint

Independent design review found Mapping and schema_ discriminator entry bypasses;
both were corrected and covered by regression tests. Native Turn components now
reconstruct once, and duplicate provenance/fingerprint predicates remain at the
public standalone boundary while Turn uses its existing work/request owners.
All 30 retained contexts (15 questions twice) are canonically identical to parent.
270 pure owner tests pass; repository tests pass 4 with 2 historical migration
checks deselected after reproducing both failures unchanged on parent.
Local construction qualification and limits are pinned in
retrieval-native-turn-freshness-v1/variant2-qualification.json under the retained
artifact root. No end-to-end latency claim. Formal committed-diff review pending.

Final obsolete-path audit removed validate_turn_identity: repository-wide source,
application, script and test search found no remaining caller after Turn adoption.
Its request and lifecycle predicates remain at the shared private owners; used
public standalone wrappers remain defensive, not compatibility fallbacks.

## JSON parser correction

Final-head query CI exposed six regressions in d94e5ef81. A source-qualified
complete parent archive passes all six; the first PYTHONPATH-only parent attempt
was contaminated by test bootstrap and is not inherited-failure evidence.
Pydantic model-wrap materializes JSON arrays and alters strict tuple decoding,
even for historical families routed unchanged through handler(value).
Replace the decorator with one Python-only owning core-schema wrapper; retain
the original JSON decoder and hoist its reference so nested $defs/$ref identity
remains unchanged. This is actual parser-mode dispatch, not a fallback, flag or
new representation. The same freshness method and joins govern Python inputs.
Qualification must now include the six actual CI failures, nested Turn/list
JSON adapters, generated schema identity, populated retained JSON roundtrips,
qualified source paths, and refreshed exact-head review. Earlier PASS artifacts
and CI failures remain historical; they do not authorize delivery of this fix.

Schema qualification refinement: duplicate inline core branches produced missing
nested discriminator annotations and were rejected. A single registered original
definition shared by JSON and Python parser branches preserves all semantic
schema content. Standalone Turn schemas are byte-identical; nested Pair/list
schemas differ only by standard inlining of an otherwise identical Turn $ref.
Offline standard-reference expansion proves equality, without patching runtime
JSON schemas. Nested Python instances must still reconstruct independently.
This preserves the existing wire contract; literal $ref placement is not a new
product contract or a replacement representation. Undefined-ref warnings and
missing discriminators are acceptance failures. Source-qualified parent/current
paths are mandatory for further comparisons.

Corrected single-definition local gate: all 37 actual query/saved-page CI failures
pass through the existing pytest nodes; 273 pure owner tests pass. Independent
focused review passes 30 entry/schema cases and finds no new API/freshness hole.
The prior d94e5ef81 review is superseded, not delivery authority. Retained parity,
construction counts and local timing must be freshly bound to the corrected head.
