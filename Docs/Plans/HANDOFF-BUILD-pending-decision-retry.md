# BUILD: retry an interrupted pending decision

Status: ACTIVE. The user authorized recovery, focused verification, review,
merge and deployment. This serial slice is based on serving commit
`a19d88d9a07e9768a1eca107246e86bf1df4efae` on
`codex/build-placement-app0213-base`.

The retained Elderwyld turn was interrupted after the initial controller
received HTTP 400. Its context and execution use the pending Build codecs;
the retry owner rejects these as unverified before checking provider outcome.
Admit only an exactly bound pending receipt and execution with a verified draft
capture and initial select-controller events. Existing provider outcome,
reviewed-action, proposal, lineage and fresh-capture checks remain authoritative.
Later pending work stays unverified. This slice does not change the model route.

Write set: `src/application_state/agent_conversation/retry.py`,
`tests/test_surface_native_build_ordinary.py`, and this handoff. Verify an
ordinary isolated HTTP turn after a synthetic initial 400, its retry and
idempotent replay, unchanged source and Graph, unknown outcome and later-event
refusal, and stale capability, message and revision rejection. Independently
review the cumulative diff. Browser refresh and live-provider behavior need
separate evidence; neither is established by the server replay.

The production diagnostic separately reported `Unknown model: jev-1.14.0` on
the Vercel TypeSafe endpoint. A minimal independent request using
`typesafe-ai/jev-1.14.0` succeeded. Correcting the route identity and its exact
wire and historical-record contracts is a dependent slice, not a fallback.
