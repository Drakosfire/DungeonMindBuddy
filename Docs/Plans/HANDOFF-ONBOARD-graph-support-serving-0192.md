# ONBOARD: Graph assertion support on the 0192 serving lineage

Status: ACTIVE. The owner authorized the Sizzek lane, independent Bugbot review,
merge and deployment. Serial integration from
`codex/build-plan-semantic-hosted-0192` at `7dded9c90cd607d8a3e71ed06d78ea046ecba208`
to `codex/onboard-graph-support-serving-0192`. PR #4477 is already merged into
that branch; production still serves its parent `a5c7599c3c32731785de4562ced073cadf392e07`.
The prior owner-review image has not been activated: its workflow failed SSH
authentication before the activator, and the temporary release record was removed.

Carry only #4489's reviewed assertion-ID deduplication and its owning tests onto
the merged guest-review lineage. The fix preserves each selected read's citations
and qualifications; it must not weaken foreign, omitted or duplicate-handle
checks. Main merged #4489 as `a9676c1b05d2fcd4f1bfe3b4f1500352e72b9e49` after
Bugbot review of head `d3f311db77ddbba1656e403be18c19bf3f252046`. Its real
Sizzek failure diagnosis remains provisional: the synthetic duplicate-read
reproduction matches the exception, but the retained live trace does not prove
that exact cause. No final answer or guest publication is claimed.

Exclusive expected writes: this handoff, `src/application_state/agent_conversation/
surface_evidence_answer.py` for the reviewed assertion projection only, and
`tests/test_surface_native_completion.py` for the carried regression tests. No
schema, provider, production configuration, World or release-content write lease.
No open PR was found targeting the serving branch at activation; recheck live
image, current base and active work before merge or deployment.

Compare exact cumulative diff to both parent and reviewed main, run the owning
backend and required exact-head hosted frontend verifier, document inherited
failures against the exact parent, and obtain Bugbot review. Image build and
activation require a newly verified compatible rollback and working authorized
deployment path. The guest preparation/promotion gates and digest-bound owner
content review remain separate and are not satisfied by this integration.
