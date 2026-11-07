# RETRIEVAL: preserve frozen Build dialogue in native retrieval

Status: DELIVERED through PR2183, merge 02e5c158d735a81511f1ca68f4caaec8f1fbce8f.
Independent review and all seven checks passed. API integration
86facdc655f53962920a29dd1027169806ab7d93 preserves the deployed INGEST work;
UI unchanged. Ordinary broad turn 8b073e07-7ac0-41ae-9190-523653097696 delivered
supported output in 71.1s, and selected-source contrast bdf9ab43-8807-47f8-a90a-992c49474cc2
delivered in 10.4s. Prior aec78a07-b3db-4f04-9491-0c78922a5aec writer timeout is
preserved. Frozen dialogue was present in every observed retrieval SDK request.
No repeatable material speedup is established. Runtime lease released; keyword
prioritization is the serial successor, not proof of whole-goal completion.
Base: f15f11957268d3e61723b031727a237e55e14358 (remote main, re-anchored 2026-11-07).
Branch: codex/build-native-retrieval-dialogue, existing buddy-context-loop checkout.
Topology: serial after merged/delivered PR2182. No new checkout/environment. Open
INGEST lanes do not own these paths; Play2172 remains held. No runtime write lease
until independent review, CI and exact integration/delivery preparation.

## Outcome and invariant

Build already captures and expands complete conversation pairs before native
retrieval, but _native_completion currently passes dialogue=(). Pass the same
frozen text through the existing role/content dialogue input used by Plan's shared
retrieval driver. Dialogue resolves references; it never grants source access,
revision scope, evidence support, publication or write authority. Do not reread
mutable conversation state, inject client-supplied history, trim text, change the
existing history selection policy, or add another context/provenance store.

Failure cases: no prior pairs must remain empty; exact Unicode/long text and pair
order must survive; completed reply replay must make no additional calls; prior
assistant assertions remain untrusted references and cannot satisfy grounding.
Existing prepared authorization includes the actual dialogue bytes. Current read
and source-revision checks remain unchanged. No new codec/schema is introduced.

## Exclusive expected writes

- This handoff.
- Docs/Plans/HANDOFF-RETRIEVAL-source-candidate-scope.md (predecessor settlement).
- apps/live_control_server/services/build_jev_harness.py.
- tests/test_surface_native_build_ordinary.py (ordinary HTTP regression).

## Verification and resources

Use existing dependencies and disposable APP fixture service54329, never primary
APP54331/Core54330 or benchmark55447 for tests. Core tests use their existing
synthetic fixtures. Capture logs in the established private runtime-evidence root.
Prove the regression before the production change, then validate real HTTP → SDK
wire → durable selected input and supported completion, empty-history/replay,
source citation reopening and unchanged page/Graph head. Inspect cumulative diff,
obtain independent review, push/open the one owning PR and wait for all checks.
No paid provider calls required for this regression. Any later paid comparisons
keep Jev/writer fixed and preserve original failures and the 81-second baseline.
The broader activity, References, efficient retrieval and operator acceptance
requirements remain open; this is a context correction, not a latency claim.
