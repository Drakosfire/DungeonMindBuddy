# AGENT — durable controller/writer role policy

ACTIVE. PRIME implements solo; ARCHITECTURE independently reviews.
Base fc175ee2e10ebb98e3231efa7e6ac79054fc82c9; branch
codex/jev-durable-role-policy; isolated /tmp/prime-recap-mention-boundaries.
Serial producer prerequisite to Build-only Jev prepared-envelope adoption. GE #20
is accepted at dde768f3e632af20b969cc694d8318265ce6ff5c, reviewed head
f9e1a2b5f6b019f49591f904528a2c4f2c76ec00; its implementation lease ended.
Open Ingest/UI/SERVER leases are disjoint from this APP model/test write set.

One capability: an explicit settled V3 execution-policy subtype freezes controller
and writer full provider/model/api-mode identities. Existing provider event shapes
and claim/fence/source validations remain. Exactly two distinct identity tuples;
first authorization must be controller, writer authorization irreversibly ends
acquisition, no controller/acquisition after writer, at most one writer authorization.
Even known_not_sent writer fails the turn rather than permitting another writer
in this bounded policy. Completion can bind only the writer's response-received
attempt; headers alone remain insufficient for valid product completion.
Historical policy bytes/hashes must remain unchanged. No automatic authorization
or budget loosening, runtime selection, provider calls, deployment or data migration.

Exclusive writes: this handoff; src/application_state/agent_conversation/types.py;
tests/application_state/test_agent_controller_writer_policy.py;
Docs/Plans/HANDOFF-AGENT-jev-batched-coverage.md; Docs/Roadmaps/ROADMAP-demo.md.
No other schemas, API/UI/provider/evaluator implementation or lockfiles.

Prove policy roundtrip/digest, old-policy byte parity, supported/forged identities,
controller-first/phase transitions, unresolved/unknown attempts, writer known-not-sent
and second authorization denial, controller completion denial, and real disposable
APP persistence/fresh reload/CAS with preserved source and first-envelope checks.
Use synthetic data only. No fixed call cap on controller acquisition. Exactly one
writer authorization implements the operator's one-writer design, not a spending cap.

After independent review/merge, add the genuine Build prepared-envelope verifier
and role-bound policy assembly through existing parent persistence and Graph/source
broker. That consumer must pin GE, prove actual dispatch bytes and final writer
exposure; ordinary adoption remains unimplemented by this producer alone.
