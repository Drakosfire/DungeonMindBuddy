# BUILD — admit saved source to verified native World

Status: ACTIVE, operator Mirathorn lifecycle authority. PRIME implementation;
ARCHITECTURE independent review. Base 8cfba654cb25f2e264a3f64d69b0cd2eac011cef.
Branch codex/build-source-native-binding; /tmp/buddy-build-source-native-binding.
Topology serial source-admission successor to merged #1152; independent of reader.

Invariant: the saved document retains its managed World identity, while all native
repository operations use the native World resolved by the existing verified
managed binding. Never initialize a native space merely named after a managed ID.
Resolve active binding before status/admission repository access. Seal native target
and binding version into admission identity; verify the same basis at replay and
before publication/recovery. Changed/missing/inactive bindings fail closed.
Source bytes, document revision and origin remain exact. No fallback to default IDs.

Exclusive write set: this handoff;
apps/live_control_server/integrations/dungeonmind/native_world_source_admission.py;
tests/test_demo_j1_native_world_source_admission.py;
tests/integration/test_demo_j1_native_world_source_admission_postgres.py.
No provider, serving, retained database, extraction-profile or fact-publication writes.

Prove two managed Worlds with different native IDs, source admission and replay
only in intended native space, truthful managed world_id/native space_id status,
absent/inactive/changed bindings and zero wrong-space writes. Preserve exact bytes,
source opening and durable PostgreSQL evidence. Update fixtures to real managed
bindings rather than bypassing the production resolver. Inspect cumulative diff,
commit/push/open one PR, request ARCHITECTURE review, merge once gates pass.
