# INGEST: retain registered extraction failure evidence

Original repair COMPLETED: PR1179 merged
4de42fa3bfc1115d909f82b40392e539cf98a0e3 from independently reviewed
a43b99d172a66e952087315a9c6be0f44cad27d9; one review cycle. Original three-path
write lease released. Base f1ef5ba5a0bc3c40eabff44af3afbf1101012f84.
This repaired the registered controller ignoring supplied exception responses;
it did not add semantic review, publication or provider replay.

## Current storage contract

Retain supplied raw response strings (including empty) exactly as UTF8 through
the existing APP `ingest.component_payload` owner. The production controller no
longer creates duplicate private files. This replaces the original private-file,
mode0600, fsync and repo-URI requirements; Git history retains that implementation.

Use the existing RAW_MODEL_RESPONSE component kind/key and SHA256, retaining the
source/profile/model/run basis. The component URI is an opaque
`urn:dmb:ingest-output:<run_id>:<kind>` label, not a resolver, path or publication
authority. Reads use the current exact run/kind/digest database binding. Retained
older references already use that owner; there is no file fallback or migration.

Mark FAILED only after evidence durability. No promotable candidate or automatic
provider replay. A missing response does not invent a component. The optional
versioned SUCCESS bundle from advisory review uses the same owner before candidate
registration and lifecycle advancement; validate its strict JSON and source/profile
identity first. Consolidation diagnostics also use this database owner with strict
JSON serialization. No arbitrary repr serialization or NaN values.

Database failure raises a controlled storage error without echoing private bytes
or claiming retention/success. Evidence remains private run data, not a corpus
discovery source, public response body or publication approval. Separate bounded
provider-attempt and outer execution captures retain their existing owners.

## Owning proof

Use synthetic registered controller success/failure with disposable APP databases:
exact Unicode/empty response and digest, unchanged source, failed state without
candidate, absent-response behavior, fresh-process bound database reopen, unavailable
private files, strict serialization, and actual database failure before lifecycle
advancement. Inspect the cumulative diff and obtain independent exact-head review.
Tests do not establish semantic benchmark, publication, serving or operator acceptance.
