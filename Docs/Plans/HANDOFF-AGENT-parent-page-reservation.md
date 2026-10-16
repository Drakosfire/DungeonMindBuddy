# AGENT: recognize parent pages in the Harness operation reservation

Status ACTIVE under PRIME's Mirathorn lifecycle goal. Base and accepted #1220
merge `f4e3ab68025e08abfe229e96add852631f29ce1b`. Serial successor.
PRIME implements solo in `/tmp/prime-recap-mention-boundaries`, branch
`codex/agent-parent-page-reservation`; ARCHITECTURE independently reviews.

## Invariant and observed failure

Fresh ordinary Build question on matched preview f4e3ab68 reached one provider
call (18,798 input/81 output tokens) and one Graph expansion. Worker reservation
recognizes only raw schemas, marks parent overview indeterminate, retires tools,
and its next-provider guard vetoes. Terminal turn is retained; do not replay.
Real reservation + real parent presenter reproduces this with zero provider/Graph
I/O. Parent paging/admission remains authoritative and unchanged.

Recognize parent overview/page only with valid wrapper structure and exact
expected tool, result schema and frozen retrieval-session/World/revision. Preserve
underlying outcome/Core truncation separately from transport pagination. Count a
successful original read once; continuations consume cached transport without
incrementing read counts, including at the read cap. Parent validates tokens and
exact evidence; worker recognition grants no claims. Malformed/foreign wrapper
and uncertain broker outcomes remain indeterminate. Preserve provider/token/
deadline limits, registered denial feedback and existing small raw-result paths.

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-AGENT-parent-graph-presentation.md` (settle #1220 and live finding).
- `apps/live_control_server/services/hermes_graph_agent.py`
- `tests/test_graph_parent_page_reservation.py` (new).

No open PR overlap; gold #1219 is merged and disjoint. One implementation PR.
No providers, retained database/source/Graph writes or serving changes during
implementation. Existing owned preview 5207/8004 stays matched f4e3ab68 on APP
clone; 5202/5876 untouched. Preview execution remains owned by portable handoff
pin a2064010b3013794b1ca5e0f7b3dc6f4b67b1d1e.

## Verification

Prove actual reservation→plugin→pinned SDK→next-provider guard for overview/page,
small raw result and continuations at cap. Prove no repeated read, duplicate page
idempotence, expiry/foreign token denials, malformed scope/tool/schema rejection,
Core truncation retention and broker uncertainty. Include real parent presenter.
Inspect cumulative diff, commit/push/open assigned PR, independent exact-head
review before merge. Ordinary question/passage/restart/operator acceptance still
required after accepted rollout. No uncertain replay.

## Review evidence

51 focused tests pass, including 19 new reservation/SDK cases. Real parent
presenter→reservation→plugin→pinned SDK dispatcher→Responses serializer→next
provider guard succeeds for overview, source page, small result and continuation
at cap. Tests prove single initial read, repeat continuation idempotence, live
transport tools at read cap, source/Core truncation intact, expired/foreign token
feedback, wrapper scope/tool/schema/shape refusal and uncertain broker shutdown.
Broader Harness run: 143 pass, two failures reproduced unchanged on exact base
f4e3ab68: `test_mixed_plugin_capability_policy_loads_both_surfaces` and
`test_parent_graph_broker_blocks_child_fallback_and_returns_parent_packet`.
Logs `/tmp/parent-page-reservation-focused.log`,
`/tmp/parent-page-reservation-regression-v2.log`,
`/tmp/parent-reservation-base-failures.log`. Guard fixture uses production's
Responses transport with opaque reasoning replay disabled; no API inference.
Ruff and cumulative diff checks pass. Ordinary runtime acceptance remains open.
