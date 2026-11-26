# Application-state transaction connection pooling

Status ACTIVE. The user lifted the read-only constraint for this bounded slice.

Base: 769632f94868be9f7e992ceff88f41aeb763f5d9. Serial lane on
codex/application-state-pooling in the managed application-state-pooling checkout.
Write set: application-state unit of work and connection factory, focused
application-state PostgreSQL tests, their contract inventory entry, and this handoff. Use the existing SQLAlchemy
dependency and existing disposable evaluator. No schema or hosted changes.

One unit of work remains one PostgreSQL transaction. Pool leases must reset
driver and SQL session state, discard unusable connections, and remain tied to
their connection target and worker process. Raw connection owners remain separate.

Verify pooled rollback, stale claims, lost acknowledgements, session state and
target isolation with local disposable PostgreSQL. Compare all 31 frozen writer
requests, citations and ordered checkpoints. Run two ordinary Jev cohorts on
the same integrated build with the writer intercepted, Gold local and primary
data untouched. Report exact pins and first Jev, writer-ready and transport
latency, Gold coverage and citation reopening.
