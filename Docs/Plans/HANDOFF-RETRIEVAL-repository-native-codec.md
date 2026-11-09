# RETRIEVAL: decode stored shared native Turns once

Status: ACTIVE. Root owns design and implementation under the user-authorized
retrieval critical-path goal. Serial topology: one bounded implementation PR,
base 9193d54ca874240ec181a47e8964905028794e05, branch
codex/retrieval-acknowledgement-critical-path. No unmerged dependency.

Expected writes: this handoff; src/application_state/agent_conversation/repository.py;
existing shared-native Turn/repository tests. No concurrent open PR found on this
codec. Reference UI, CI inventory, held composition and ingestion lanes remain
outside this lease. Isolated resources: evaluator55447 owned ack-profile clone,
retained benchmark clones read-only, retrieval-critical-path-next-v1 artifacts.
Primary data and original evaluator remain unchanged; no writer calls for acceptance.

Hypothesis: the shared-native database codec first parses individual native JSON
components, then the fresh Python Turn owner reconstructs them again. Decode the
complete stored shared-native base Turn in JSON mode once, retaining all root
joins, lifecycle checks, strict tuples and exact source/citation bindings. Preserve
stored-corruption error classification at the repository boundary. Historical and
mixed Rules codec ownership is unchanged; no retry/fallback/cache or skip-validation
flag is introduced. Successful-prefix durability and transaction fencing remain.

Qualification: exact canonical equality on all15 context cases twice; Build/Plan/
Play and malformed-row rejection; actual repository owner tests; independent
cumulative review. Existing retained material only for local feasibility. Any
prospective fresh measurement uses consolidated capture-context workflow, fixed
controls and no writer. Report local decoding separately from response-ready
latency. Local gain alone does not satisfy the six-second target.

Initial evidence: 30 retained Plan rows equal; fixed-order local medians26.64 to
17.84ms, not controlled cycle gain. Unmodified temporary prototype changes some
IntegrityError failures to ValidationError and is NOT qualified for adoption.
Raw probes remain preserved, with initial failed schema-check attempt. Small-batch
source-observation proposal remains rejected: loses durable prefix on hard kill.

Stopping decision: reject on context/refusal regression; do not weaken strict
source authority or add an old-code fallback. If verified local improvement lacks
whole-cycle materiality, preserve evidence and continue the seconds-scale goal;
do not call six seconds achieved. Adopt only after review and measured disposition.

## Repository qualification checkpoint

Complete shared-native base records use one JSON Turn decoder. The original
ordered column codec table still owns recognition and error precedence. Recognized
component failures precede composition-summary checks; root failures follow them.
This preserves historical/native cross-family failure classification without a
second parse. Pure tests168 pass (2 inherited serializer warnings). Broader owner
suite291 passed before the final19 error regressions. Actual PostgreSQL tests28
pass; five failures reproduce on the complete pinned parent with the same source-
catalog and old-migration expectations. Both full logs retained. No claim that
those five checks pass. Sandbox stalled pure attempt is not passing evidence;
qualified rerun passed. All30 implemented populated Plan rows canonically equal;
fixed-order local decode medians28.83 to19.30ms, not a whole-cycle speed claim.
