# INGEST: retain registered extraction failure evidence

Status DONE for this bounded repair. PR1179 merged
4de42fa3bfc1115d909f82b40392e539cf98a0e3 from independently reviewed
a43b99d172a66e952087315a9c6be0f44cad27d9; one review cycle. Write lease released.
Base f1ef5ba5a0bc3c40eabff44af3afbf1101012f84. Independent of DOGFOOD1178
(disjoint paths/state). Prerequisite split from BLOCKED advisory-review design:
existing registered controller ignores CategoryGraphExtractionError's returned
raw_model_response while legacy packaging retains it. No new review stage here.

Exact three-path write lease:
- this handoff
- src/graph_memory/extraction/graph_preview_runner.py
- tests/test_registered_extraction_failure_evidence.py

Persist a supplied raw response string (including empty) EXACTLY as UTF8 in a
private0600 atomically replaced file beneath the already owned run outputdir.
Use existing RAW_MODEL_RESPONSE component kind/key, repo URI and SHA256. Retain
source/profile/model/run basis; mark FAILED only after evidence durability. No
promotable candidate; no new schema, source/candidate edits, inference, retry,
fallback, native/publication or serving change. Error diagnostics/logs must not
newly contain raw body. None retains old absent-component behavior.

Storage failure raises a controlled evidence-storage error without claiming
retention or auto-replaying provider requests. No false completed run/candidate.
The component is private run evidence, not a corpus discovery source or public
response body. Future completed-pass bundles require separate producer review;
this fix only preserves the existing exception's supplied payload.

Owning registered-source tests with unique disposable APP DBs: Unicode and empty
raw preservation/hash/0600, failed state/no candidate and unchanged source; None
no artifact; fresh-process registry/component reopen; simulated storage failure
must not advertise retained evidence or reviewable result. Cleanup fixture DBs.
Inspect cumulative diff, commit/push/PR; independent exact-head review before
merge. Goal remains full rich Mirathorn lifecycle, not merely this prerequisite.

## Settlement

Independent exact-head five-test pass used real disposable APP databases and
fresh-process registry/component reads; no provider/retained/serving changes.
Combined commit statuses were empty, not a CI-green claim. This preserves only
raw text supplied by the exception. Earlier completed-pass journaling/semantic
review and full Mirathorn lifecycle remain separate unfinished work. Later
consumers must re-anchor on the merge and preserve private evidence semantics.
