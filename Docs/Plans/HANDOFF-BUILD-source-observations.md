# BUILD — Review and publish independent source observations

Status MERGED as `b285e4fd1ab61139b66b461730ee7b058a909994`; implementation lease ended. Base `c21feff20156fdd8c3c082cfa083895ceee5eef6`.
Lane `/tmp/prime-recap-mention-boundaries`, branch
`codex/worldbuilding-source-observations`. Topology serial. Transfers completed
source-boundary prerequisite lease; other open UI/MIND/Rules work is disjoint.
ARCHITECTURE independently reviews. No serving/retained/provider execution lease.

Outcome: Gazetteer1.11 emits previewv0.2 top-level source observations, one per
source-defined livestock section on the reviewed place candidate, preserving
shared scope/qualification and complete exact evidence. Review each observation
with accept/reject/defer. Accept requires the subject's create-new/bind-existing
acceptance; resolve native identity only through that node decision. New and bound
places both receive distinct worldbuilding_observation assertions. No invented
species identity, convenient ref dropping, historical mutation or runtime splitting.

Exclusive expected paths:
- src/graph_memory/candidate_graph_preview.py
- src/graph_memory/candidate_graph_to_contribution.py
- src/graph_memory/worldbuilding_write_plan.py
- src/graph_memory/extraction/worldbuilding_definition_observations.py (new)
- src/graph_memory/extraction/worldbuilding_profile_catalog.py
- src/graph_memory/extraction/category_candidate_graph_extractor.py
- src/graph_memory/extraction/graph_ingest_packaging.py
- apps/live_control_server/models/extract_promote.py
- apps/live_control_server/services/candidate_graph_admission.py (explicit observation-aware integrity gate)
- apps/live_control_server/services/extract_promote.py
- tests/test_worldbuilding_source_observations.py (new)
- tests/test_worldbuilding_gazetteer_profile.py (catalog expectation only)
- Docs/Plans/HANDOFF-BUILD-source-observations.md
- Docs/Plans/HANDOFF-BUILD-definition-observations.md (completed predecessor sync)

Verify source-exact producer→stamped preview→sealed/fresh load→independent review
and inert/native publication effects with both subject decisions; reject duplicate,
foreign source, missing evidence and unresolved subjects. Old generic consumers
rejectv0.2 rather than silently omit observations. Existingv0.1/raw sealed bytes
remain unchanged. No schema migration or native vocabulary changes.

Review API must expose observation candidates and decision snapshots. Missing
observation decisions fail closed, so an old UI cannot invisibly accept them.
DOGFOOD owns the visible review projection; coordinate it separately before any
operator-readiness claim. Frozen six-definition inventory remains private.
No helper-only pass implies ordinary Agent or operator acceptance. Full actual
publication/readback/open passages and UI witness remain required before retained
adoption under a newly pinned operational contract. Track exact refs/test/model
cost, inspect cumulative diff, commit/push/PR, independent review, then PRIME merge.

Author evidence:117 affected codec/registered-profile/publication-planner tests
pass, two native-only cases skipped there; a separate uniquely created Core DB
runs all16 owning source-observation tests including new/bound native confirm,
idempotency, canonical-object/relationship preservation and exact-source opening.
The real runner seals and reloads two synthetic definitions and the ordinary
review API exposes both subjects; forged quotes and unknown spans reject.
One inherited schema-shadow warning remains. No external provider calls occurred.
Logs `/tmp/worldbuilding-observations-regression.log` and
`/tmp/worldbuilding-source-observations-native.log`.

Deterministic reprocessing of the preserved Mirathorn candidate matches all six
frozen definition texts/evidence exactly (10/10/10/10/10/17refs), leaving a478char
place description with4refs. This private result is neither a fresh inference/run
nor publication. Evidence `mirathorn-independent-observation-proof.json` under
`experiments/build-governed-preview-20261016`. The historical assertion is untouched.

Independent ARCHITECTURE review passed exact `36fd44101f0ac2fa775c9172c06d8987a17e56c0`:16 native owning tests and20 generic regressions.

Remaining explicit gates: DOGFOOD observation review UI,
operational current-main adoption, reviewed fresh Mirathorn run/publication and
ordinary Agent witness. Separate observations do not guarantee all fit one bounded
object result; topic-selective observation retrieval/paging is a required successor
before claiming Float Goat query readiness. Do not broaden limits or omit refs.
