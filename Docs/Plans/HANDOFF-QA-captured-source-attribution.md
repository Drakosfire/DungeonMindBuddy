# QA: retain exact-source display names through composition

ACTIVE serial slice under the deferred-fundamentals goal. Base
83877ccab9d0064355225b3d3be40bbe51f11d39; isolated non-serving branch
codex/qa-captured-source-attribution. No other implementation PR in this lane.

Confirmed gap: native body writer rows and citations use the first section label
as source_name. Introduction is a section label, not source identity. The existing
display owner resolves exact recap origin/revision/content against APP metadata,
but that readable label currently reaches only navigation and citation reopening.
Core source metadata alone does not carry the APP source name.

One outcome: capture readable display-only naming at the existing Core-admitted
member acquisition boundary and retain it in the existing catalog commitment.
Current opens always capture a verified nonblank label or explicit unavailable
label. Section titles, scopes, bytes, evidence handles and access checks stay owned
by their existing contracts. No session/played chronology inferred from a name.
Historical absent-field records preserve exact old serialization and request
reconstruction; there is no alternate current producer or live replay lookup.
Old readers reject the additive field: use the existing APP schema-head fence
with no-op revision0148 after0147. No rows/tables change. This is indivisible
delivery safety for the captured field, not another capability or auto-migration.
This PR does not deploy or migrate operator state.

Exclusive expected writes: this handoff; prior INGEST delivery handoff for truthful
stage1 settlement; native_corpus.py; native_corpus_source.py; native_source_display.py;
existing tests/test_native_corpus_source_access.py, tests/test_native_source_display.py
and tests/test_surface_native_writer.py. Source paths use their existing directories.
Amended lease includes src/application_state/migrations/versions/20261110_0148_captured_source_names.py
and tests/application_state/test_cli_schema_head.py for this reader fence.
Exact-base reproduction proved the shared native writer test transports discard
the actual last evidence frame by assuming a Return JSON trailer. Lease includes
only that two-line parser correction in tests/test_native_plan_statements.py and
tests/test_native_plan_assertions.py: skip the exact historical trailer text, not
the final message. Preserve every semantic/source/citation assertion. No runtime
prompt restoration or fixture expectation weakening. Retained firstfailure on
base83877 and head438d documents inheritance; interrupted full contract stays red.
No routes, UI, registry, prompts, providers, data migration or primary
state write. No #2225 passage-modality or #2374 hosted-explorer behavior imported.

Validation: exact source-pair naming and unavailable/mismatched metadata; one
request-local naming snapshot; source text/scope/selector conservation; frozen
label after metadata change; historical nested bytes/digest/request compatibility;
actual native writer/citation ownership tests. Run affected contracts in locked
environment and exact-SHA local hosted verifier, independent cumulative review,
then one PR. Model quality is not inferred from owner tests; rerun only after an
adopted change invalidates prior producing context. Q16 remains separate until its
rejected completion invariant is established. All later goal stages retained.
