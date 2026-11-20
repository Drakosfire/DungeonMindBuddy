# BUILD: count the native writer input with prepared offline accounting

Status: DELIVERED. PR2151 merged at
`63587a57d2f949715ea8552e8041cc635931a9cd` after independent review and all
seven CI gates. Runtime candidate `beb93d88d1c2412746de1ccb84d241b5ec675f8f`
delivered it on 5202 alongside merged PR2150. The original request reached a
supported answer (turn `cab3e214-ee53-4515-8084-457abb0ce237`); original failures
and retained user data remain intact. The replay took 88.434 seconds and six
retrieval rounds, so retrieval efficiency and operator acceptance remain open.
This predecessor grants no active write or runtime lease. The serial Play
source-reference successor is bounded by HANDOFF-PLAY-retained-source-references.md.

Outcome: current native Build writers reuse the already prepared offline o200k
counter, multiplier2 and4096 accounting margin accepted by their controller.
Count the complete actual SDK request, including instructions and output schema,
and label the result estimated_token_count, never a guaranteed bound. Preserve
the128000 token allowance and4096 output reserve. Remove duplicate byte-as-token
checks for this current contract. Historical accepted records keep exact readers;
Plan/Play's distinct existing contracts are not silently changed.

Evidence: the retained replay's exact220269-byte SDK request reproduces its228909
local estimate. A single provider input-count diagnostic returned52261 input tokens
(56357 with output reserve), while the offline complete-wire count was54020.
This proves the byte estimate is unsuitable here; it does not prove answer quality.
The original failed attempt and private diagnostic remain intact. No fresh ingestion,
publication, model change, new tokenizer, search path or provenance authority.

Ownership: Core continues to own source access; APP owns exact producing-input,
work and evidence admission; the trusted prepared host counter owns estimation,
as for controller calls. APP validates the frozen accounting kind/estimator/version,
role, request digest and allowance. It does not invent a second tokenizer or claim
that an estimate is an exact provider count. New native budgets require a no-op
reader fence before delivery; upgrade rewrites no user rows.

Write lease: this handoff; native_execution.py, native_writer.py,
build_decision_context.py in src/application_state/agent_conversation;
apps/live_control_server/services/plan_source_turn.py, plan_jev_writer.py,
build_jev_writer.py, build_failure_diagnostic.py and build_jev_harness.py (the
existing failure classifier only; missing counting is context preparation, not
an entered provider failure);
new migration20261106_0119; tests/test_native_writer_token_accounting.py and
tests/test_surface_native_build_ordinary.py fixture adoption;
tests/test_native_writer_projection.py adaptation to the actual moved capacity
owner (retain heavy historical refusal, compact acceptance and exact facts); one new test selector
in .github/workflows/world-ownership-core.yml. Existing INGEST/held REFERENCE
selectors and timeouts remain untouched. Existing native
source/writer tests remain validation consumers. No active INGEST PR among the
50 inspected open lanes changes these writer/accounting or migration paths.
REFERENCE2104 remains held. Broader References and retrieval optimization remain open.

Validation: actual official SDK bytes; complete instruction/schema accounting;
trusted prepared counter missing/mismatched/failed => no dispatch; genuine overflow
=> no dispatch; no byte fallback or new provider counting call; changed input/work,
wrong role/kind/estimator and stale claims remain rejected; retained old records
round-trip; ordinary HTTP answer/proposal/image writers use the same native admission.
Retain a synthetic large-input regression and the private captured-request estimate.
Review exact cumulative diff, independent Bugbot and owning CI before protected
delivery. Then one qualified ordinary replay, preserving all failed attempts and
state, must establish supported delivery; do not declare success from estimates alone.


CI correction: query-and-answer at945194354 reported684 passed and one projection
regression test failure. That test mocked authorize_native_writer, thereby removing
the guard moved into that owner. Exercise the real shared helper and stop at its
APP append seam; preserve both the historical overflow rejection and full compact
fact/evidence closure. Original CI log remains in private runtime evidence. No
runtime implementation, budget, grounding or provider-role change for this repair.
