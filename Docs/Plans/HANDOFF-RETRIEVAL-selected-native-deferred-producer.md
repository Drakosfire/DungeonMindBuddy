# RETRIEVAL: defer Graph for selected native source work

Status: ACTIVE under the user's over-retrieval goal. Serial successor to reader
#4967, merged as `50e66dd286a673da5fcef8074600d82fc99275d4` and live in Actions
run `46007729329`. Branch `codex/retrieval-selected-native-producer` is based on
that serving revision. Root owns the checkout and lane; recheck serving lineage,
open PRs and production identity before merge or deployment.

## Scope and invariant

For ordinary fresh Build requests with a nonempty bundle consisting entirely of
exact native source references pinned to the current knowledge revision, pin the
deployed selected-source deferred Graph
commitment before the controller. Use the existing semantic source-need decision:
only an admitted anchored discussion may answer from the exact selected reads
without Graph settlement. If the request asks for new evidence, its scope is
uncertain, a Graph object is selected, or work requires a different capability,
retain or settle the existing Graph route. No source reference itself proves
exclusive intent. Exact source/version, principal and World access checks remain
with existing owners; absent or stale evidence fails closed. Mixed objects, older still-valid source selections, reviewed work and historical
records keep their current route. The current-revision restriction follows the
deployed reader; supporting older selections without Graph work requires a new
reader contract and remains part of the broader objective. The existing
App page catalog is still eagerly acquired in this Graph-only slice; defer it
in a later serial reader/producer change, never by labeling it empty.

Write lease: `apps/live_control_server/services/agent_turn_service.py` and
`build_jev_driver.py` and `build_jev_harness.py` for producer routing, the
existing three-choice source question and the discussion-only deferral; `tests/test_surface_native_build_ordinary.py` and targeted
existing unit/fixture tests; this handoff and the reader handoff for truthful
predecessor status. Do not change provider models, persistent schema or source
access owners. Reuse the existing exclusively owned benchmark App clone and
shared Core; no full contents scans or additional clones.

The selected-source surface policy cannot accept the pending-Build-only
`current_saved_page` choice. It must therefore keep the existing three-choice
question; emitting the four-choice retained-citation variant here could make a
valid model choice fail execution. Its older wording is imperfect for citations,
so measure its actual routing with a new live replay. A better question needs
its own reader-first contract; do not silently change persisted prompt shapes.

Validation: focused actual HTTP and App boundary tests must cover exact
source-only answer and reopened citation, Graph query not prepared, one selected
source read, explicit fresh/mixed work preserving Graph settlement, Graph-object
fallback, missing/stale/foreign source and revoked access, interruption before
and after provider authorization, completed Turn readback and reader rollback.
Replay development and independently held-out cases with exact provider-wire
review; report App catalog, Graph discovery and source materialization
separately, mark unobserved paths unknown, and record latency without audit wait
as a speed claim. Inspect cumulative diff and obtain independent exact-head
review. Deploy via the authorized Actions workflow only after these gates and
verify the selected-source and fresh-source behavior in the signed-in app.
