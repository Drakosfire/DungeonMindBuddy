# WRITER: remove Buddy token ceilings

Status: ACTIVE. The operator explicitly instructed “remove the token limits”.
PRIME owns this serial, independently deliverable slice at main
7afaab5cb23f605a70d45529dc9143c2b293999d on
codex/native-writer-provider-default-output in the existing context-loop checkout.
Draft2172 remains unfinished and consumes this change after merge/rebase. PRIME
transfers its overlapping writer/context/role-path lease to this slice until then.
No running service or data mutation lease is implied.

## Outcome and invariant

New ordinary Buddy native answers and connected-authoring writer requests omit
Buddy's fixed max_output_tokens. Native writer preparation must not reject input
against the artificial128k writer allowance. The provider enforces its actual
model capacity; failures and actual usage remain visible. Remove aggregate token
ceilings on new Play policies; retain non-token execution controls. Preserve exact
acknowledged dispatch/input/output, source/Run scope, grounding, claim fences and
actual provider identity. Never turn incomplete output into an accepted answer.

The existing output_token_reserve field records zero reservation for a new request
without an application output cap; do not send0 as an SDK max_output_tokens value.
Existing native writer budget context_limit_tokens=None means provider-owned
capacity, not an arbitrary replacement ceiling. Retained128k/4096 budgets and
actual historical SDK payloads retain their original exact readers/hashes. No
new registry, receipt family or provenance authority. A forward-reader fence
accompanies changed accepted values; it rewrites no documents or retained rows.

## Scope and validation

One coherent cap-removal change, serial before2172. Exact expected writes:
- This handoff;2172 handoff only to record serial lease/dependency.
- services plan_source_turn, plan_jev_writer, agent_turn_service,
  native_play_graph_owner, hermes_graph_agent, build_document_proposal,
  build_image_writer (under apps/live_control_server).
- application_state/agent_conversation native_execution, native_writer,
  build_decision_context, types (under src); necessary forward-reader fence.
- Focused native writer accounting/SDK, proposal/image preparation, Plan/Play policy
  and existing owning tests/fixtures; pin additions before editing another contract.

Prove actual mocked official SDK requests omit the parameter, retain input binding
and real usage, and accept supported outputs longer than the old4096 ceiling.
Prove changed payloads/roles/scopes fail and incomplete/provider-failed responses
remain failures. Read real retained old budget/request fixtures unchanged. Exercise
ordinary SQL admission and reader-fence upgrade on disposable databases. Inspect
cumulative diff, independent Bugbot and CI before merge/delivery. Paired runtime
integration must preserve deployed INGEST extras and retained state. No fresh
provider experiment is required merely to verify parameter omission.

## Exact test/fence lease and current decisions

- tests/test_native_writer_token_accounting.py
- tests/test_surface_native_writer.py (optional explicit SDK-fixture output cap)
- tests/test_surface_native_execution.py (attempt limits remain; token caps optional)
- tests/test_play_graph_authority.py and tests/test_native_play_source_capacity.py
- tests/test_plan_jev_writer.py and tests/test_plan_jev_harness.py
- tests/test_hermes_graph_agent.py
- tests/test_native_writer_provider_default.py (actual SDK omission/regression cases)
- tests/application_state/test_surface_native_writers.py
- src/application_state/migrations/versions/20261106_0121_provider_token_limits.py

No other active migration0121 owner was found in the inspected main/lease paths.
Recheck remote and open PR migration paths before delivery. Retained historical
4096/128k records keep their original defaults; new composition explicitly chooses
zero output reservation and provider-owned capacity. Existing shared-context input
commitments still bind actual initial Jev requests; they do not supply a substitute
writer ceiling. Fresh Plan/Play also carry no APP token window; the configured provider owns
capacity. Provider capacity failures remain failures. Existing Play attempt/Graph operation limits remain unchanged.

Additional exact test lease: tests/test_play_authored_source_references.py, to prove
nullable token ceilings preserve actual selected-source SQL admission and SDK joins.

Owning regression test lease also includes tests/test_build_document_proposal.py
and tests/test_build_jev_image.py. The changes alter current native requests only;
retained positive-cap packets keep exact native producer validation. SDK output
parameter omission is verified against the installed GE/OpenAI provider.

Worker codec boundary correction: apps/live_control_server/services/
hermes_graph_agent_contract.py and tests/test_hermes_graph_agent_contract.py carry
the already-defined zero APP output reservation over IPC; a finite historical context capacity remains positive; fresh requests carry
None for provider-owned capacity. No zero output ceiling is sent to any provider. This is necessary
for the same cap-removal outcome, not another execution path or capability.

Exact current Plan HTTP proof lease: tests/test_agent_native_corpus_sources.py,
existing ordinary native Plan test asserts actual SDK cap omission.

Independent review97dbc6806 held the remaining global byte-as-token input ceiling
and mixed capped/uncapped policies. The owning correction also leases
src/application_state/agent_conversation/native_context.py and
apps/live_control_server/services/plan_jev_dispatch.py. Global APP context allowance
is now None; current provider enforces capacity. Existing byte-size guards remain
byte-size guards. Captured initial-input/IPC fields carry None without a substitute
token ceiling. New writer policy chooses exactly(None,0), historical policy exactly
(128000,4096); Play aggregate ceilings are both absent or both finite. SQL admits
only the matching typed owner states. Additional exact model test lease:
tests/test_surface_native_context.py, to preserve positive historical accounting.
