# PROMPTS: semantic native Plan work

Status: ACTIVE. Independent design critique approved the Plan-only boundary,
exact historical codec and existing support owners. PRIME owns the exclusive
implementation write lease below; no runtime write lease is active. Serial
successor to merged/delivered #2200. Base: fetched main
6b9c38e400543d1a8084a086b82f6cae6fcbedd5; branch
codex/native-plan-semantic-work in the existing buddy-context-loop checkout.

## Outcome and boundary

Current native Plan replies and authoring present saved Plan, session notes,
working draft, edit intent, dialogue and selected-reference meaning without host
IDs, hashes, revision counters or execution envelopes. Input-local block selectors
also appear in the finite output schema. Keep exact text, source kind/title,
meaningful ending time, uncertainty and authoring destination. No model/provider,
capacity, retrieval, publication or persistent data changes.

Keep native_writer.model_work_frame as the exact host reconstruction. Present a
pure Plan-only view at PlanJevWriter; locked verify_input_records compares the
actual serialized view against a reconstruction from actual records. Historical
work bytes remain an exact separate codec, never a fallback after a new mismatch.
The existing producing_plan_authored_records and authored block owner retain
source identities, session entries, hashes, revisions and quote checks. Resolve
local aliases through those existing blocks; do not construct another ledger,
source authority, provenance decision or persistent mapping. A no-op reader fence
130 protects readers unable to reconstruct this new input/output meaning.

Build's draft/proposal/image/relationship work, Rules prompting, held Play and
citation PR2191 are outside this slice. ADVERSARY is unblocked independently;
its frozen Q09/Q14 failures remain assessment authority. No paid rerun or new
checkout/environment is required for implementation.

## Planned exclusive write set

- This handoff and HANDOFF-PROMPTS-native-writer-evidence.md (settle #2200).
- src/application_state/agent_conversation/native_plan_work_view.py
- src/application_state/agent_conversation/native_writer.py
- src/application_state/agent_conversation/native_completion.py
- src/application_state/agent_conversation/surface_evidence_answer.py
- apps/live_control_server/services/plan_jev_writer.py
- src/application_state/migrations/versions/20261108_0130_native_plan_work_view.py
- tests/test_surface_native_work_input.py
- tests/test_surface_native_authored_output.py
- tests/test_native_writer_projection.py (only actual current Plan producer assertions)

No shared runtime/resource lease. Tests use disposable generated databases on
54329; primary APP/Core and operator drafts remain untouched. Other open lanes
(INGEST, SURFACE, held reference/Play) were inspected and are disjoint from this
write set. Re-anchor before expanding paths or activation.

## Verification and delivery

Prove actual SDK input plus APP reconstruction and finite output enum parity;
Plan/session selectors resolve to the exact existing saved text and entry owners.
Cover saved versus dirty draft, same-as-saved reuse, blank blocks, multiple session
entries, duplicate/foreign aliases, Plan material rejected as session support,
source/role/date changes, mixed old/new or malformed frames, duplicate frames,
user literals containing host-looking strings and exact historical reopening.
Exercise both discussion and current-page authoring and Rules composition.
Run relevant existing ownership suites, inspect cumulative diff, obtain independent
exact-head review, commit/push/open PR, CI, then merge and guarded delivery under
standing PRIME authority. Fence delivery requires independent composition/recipe
review and retained-state conservation. Ordinary dogfood and full goal acceptance
remain open; this slice alone proves neither whole-prompt cleanliness nor latency.
