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
Old readers reject the additive field: deliver matched code as a unit; this PR
does not deploy or claim compatibility with an older running reader.

Exclusive expected writes: this handoff; prior INGEST delivery handoff for truthful
stage1 settlement; native_corpus.py; native_corpus_source.py; native_source_display.py;
existing tests/test_native_corpus_source_access.py, tests/test_native_source_display.py
and tests/test_surface_native_writer.py. Source paths use their existing directories.
No schemas, routes, UI, registry, prompts, providers, database migration or primary
state write. No #2225 passage-modality or #2374 hosted-explorer behavior imported.

Validation: exact source-pair naming and unavailable/mismatched metadata; one
request-local naming snapshot; source text/scope/selector conservation; frozen
label after metadata change; historical nested bytes/digest/request compatibility;
actual native writer/citation ownership tests. Run affected contracts in locked
environment and exact-SHA local hosted verifier, independent cumulative review,
then one PR. Model quality is not inferred from owner tests; rerun only after an
adopted change invalidates prior producing context. Q16 remains separate until its
rejected completion invariant is established. All later goal stages retained.
