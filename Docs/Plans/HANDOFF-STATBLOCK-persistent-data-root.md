# STATBLOCK — persistent product data root

SOURCE DELIVERED: PR1579 merged2687cf712603370ebde61e05889540df05689fb5
and API8000 runs that revision; UI remains1578. Bugbot independently passed136
backend tests; guarded delivery preserved1487 APP rows and46 prior product files.
The real World-scoped draft and original generation now persist in the configured
root. DMS44 repaired a producer schema failure and original generation resumed.
Candidate review/revise exposed current producer/consumer digest drift; successor
HANDOFF-STATBLOCK-canonical-digest-parity.md owns that repair. Actual mechanics
acceptance and restart proof remain open.

Historical lease: PRIME owns design/implementation/merge and guarded8000 delivery.
Basef3a8dac3ca900cb79e9da77989ae33e9fab8858b; existing buddy-context-loop checkout,
branch codex/statblock-persistent-data-root. Serial one PR. No competing lease.

Before paid generation, inspection found current routes pass disposable code
repo_root to ThreatDraft, candidate cache/recovery, acceptance and publication
journals. The configured persistent DMB_ARTIFACT_DATA_ROOT contains retained
records; current immutable code rollout contains none. Do not create a fresh
accepted asset only to strand its recovery journal on the next code rollout.

One capability: route the entire statblock product lifecycle to the existing
explicit artifact data root, using one shared fail-closed route helper. Default
code-root behavior when the existing setting is unset remains its normal config
semantics; no second lookup/fallback, migration, copying, legacy interpretation,
new format, SQL, provider or Graph authority. Managed World registry resolution
continues using its independent configured root. Configured unavailable/relative
root returns503 before state/provider access, never writes into code checkout.

Exclusive writes: new routes/statblock_storage.py; routes/threat_drafts.py,
statblock_candidates.py and threat_publication{,_identity,_proposals,_commits}.py;
new owning HTTP storage-root test; this contract, predecessor
HANDOFF-STATBLOCK-managed-provenance.md and ROADMAP-demo.md settlement.
Verify actual CRUD→generate/cache→accept/journal→code-root switch→candidate/exact
accepted-ref/recovery reopen with only DMS mocked, same-key no duplicate create,
missing configured-root refusal and no code-root writes. Owning existing route/
generation/acceptance/publication cohorts, Bugbot exact cumulative review, then
guarded API delivery preserving APP rows and retained files. Resume actual
synthetic Build generation/review/accept/reopen and same-artifact API restart.
Association/Combat snapshot capability remains separately bounded.
