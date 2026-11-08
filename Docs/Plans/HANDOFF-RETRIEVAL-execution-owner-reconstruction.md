# RETRIEVAL: reconstruct execution at its typed owners

Status: ACTIVE. Root designs/implements/reviews; PRIME merges/delivers.
Branch:codex/retrieval-execution-owner-reconstruction; recorded-names-control.
Topology:stacked on2260 exactc0e0c1b59d4c2c549594c341d2fafdb8548c137c.
2257source merged1a19895; merge order2260 then this slice. Rebase before delivery.
Parent settlement does not claim pending runtime136 delivery.
Exclusive expected writes:this handoff; src/application_state/agent_conversation/native_execution.py;
tests/test_surface_native_execution.py. No ports/primary/live state or other source leases.
Concurrent predecessor2260 owns shared relevance contracts/dispatch/fence137 and
its tests; this slice has no overlap. No new codec version or migration: stored
JSON and canonical request/evidence shapes must remain exactly identical.

Hypothesis:full execution JSON encoding/decoding can be replaced with fresh
recursive Python-data validation once the existing strict Build Capabilities
owner reconstructs its own dictionary. Keep all execution/context/policy checks.
Changed variable:one internal reconstruction path and closed capability field
Python dictionary decoder. JSON wire shape unchanged; strict action config
unchanged. Existing dataclass constructor retains tuple/allowed/unique/boolean
checks. Expected TypeError becomes ValueError so APP validation classification
is preserved. No trusted instance fast path:full execution always dumps a fresh
recursive dictionary, rerunning constructor checks even for mutated nested objects.
No whole-action strictness relaxation, list coercion, try-both fallback or cache.

Prior blanket replacement failed Build because strict dataclass requires instance.
That failure stays retained. Distinct owner design review:
retrieval-current-admission-profile-v1/capability-owner-reconstruction-design-review.json.
Acceptance:current/historical Plan/Build/Play owner suites and canonical roundtrip;
mutable capabilities/policy/events reject, unknown fields/unhashable members are
validation failures, source and request bindings unchanged. Independent cumulative
review. Existing consolidated workflow/evidence only, no per-question script.
Stop on valid-family regression or weakened refusal; no codec fallback. Boundary
performance measured separately only after equivalence; four-second target is
not established by a small parse test. No provider calls. Disposable evaluator55447
only for owning database tests; all retained sources and primary unchanged.

Owning-codec checkpoint: a before-validator that merely passes JSON dictionaries
through changes Pydantic nested strict-tuple handling (12Build owner failures).
Use one explicit owner reconstruction for both modes: JSON array members become
tuples; Python data must already contain tuples. Existing constructor validates
all fields and rejects unknown kwargs/type errors as ValidationError. No broad
coercion or try-both parsing. Preserve initial failure evidence and verify exact
canonical JSON as well as mutable capabilities and full surface owners.

Same-capability checkpoint: the policy self-validation inside execution still
encoded and parsed JSON after the full execution fix. The same capability owner
decoder now permits a fresh recursive Python-data policy reconstruction as well.
Remove that last internal roundtrip in native_execution.py, retaining all policy
validators. No extra path/public contract/fallback. Prior variant head and all
measurements remain evidence; qualify the new changed variant independently.
