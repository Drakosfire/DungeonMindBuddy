# BUILD — exact-run managed World publication binding

Status: ACTIVE, operator Mirathorn goal; PRIME implementation, ARCHITECTURE review.
Base 8cfba654cb25f2e264a3f64d69b0cd2eac011cef.
Branch codex/build-worldbuilding-publication-binding.
Lane /tmp/buddy-worldbuilding-publication-binding.
Topology parallel-independent of #1153 source admission and #1154 editor repair.

Outcome: worldbuilding fact prepare/confirm uses server-verified registered Build
run/source/document ownership and active managed-to-native World binding, never
DEFAULT_WORLD_ID or caller-selected native IDs. Preserve historical frozen source
revisions after legitimate later edits. Seal managed ID, native ID, binding version,
document/revision/source/candidate basis; rederive and reject drift before confirmation
and recovery. Existing DungeonMind identity/CAS validation remains authoritative.

Exclusive write set: this handoff;
apps/live_control_server/services/worldbuilding_graph_publication.py;
apps/live_control_server/models/extract_promote.py;
tests/test_cutover_worldbuilding_authority_port.py.
No provider, serving, retained database, extraction profile, source admission or
shared dependency changes. Typed response-binding extension only if existing signed
transport cannot express complete basis; historical unbound plans require reprepare.

Verify exact registered ownership with two managed Worlds distinct native targets;
prepare/confirm only intended target, stale/forged/changed binding and damaged source
reject, retry/recovery no duplicate publication, later document edit retains historical
source rather than replacing it. Complete bounded PR and ARCHITECTURE review.
