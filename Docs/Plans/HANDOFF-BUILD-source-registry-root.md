# BUILD — native source admission managed registry root

Status: ACTIVE; operator Mirathorn goal. PRIME implementation; ARCHITECTURE review.
Base: 14596b15eff7f587b67ece69157deeda02a20e40.
Branch: codex/build-source-registry-root. Lane: /tmp/buddy-build-source-registry-root.
Topology: parallel-independent of DOGFOOD #1151 reader; no shared paths.

Outcome: native Build source admission reads managed World ownership from the
configured managed registry root, while committed document bytes remain in the
workspace repository root. Invalid managed configuration fails closed.

Exclusive write set: this handoff;
apps/live_control_server/integrations/dungeonmind/native_world_source_admission.py;
tests/test_demo_j1_native_world_source_admission.py.
No provider, serving, retained database, native identity mapping or publication
contract changes. Native managed-ID-to-space-ID assumptions remain a separate gap.
Verify distinct document/registry roots through actual source admission/status,
exact bytes and replay; preserve same-root tests and invalid-root rejection.
Finish PR, independent review and PRIME merge before runtime adoption.
