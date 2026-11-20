# INGEST: Review recap names before extraction

Status: ACTIVE. Reconciliation of PR #2087 for the AW benchmark goal. User direction authorizes generic deterministic name checking before model extraction, explicit edits, and original source retention. This reconciliation advances AW02 and AW04.

Topology: serial in #2087. Candidate base is main at 6b3c31b1f7ee982c494c63c77b5b79d9a65f7fa0. Checkout is `~/Projects/.codex/aw-ingest-name-review/DungeonMindBuddy`. The previous branch head, 687b26a2b83b5fe424801245b1cd199c1d183630, retains the historical scope and qualification. Actor injection, reader projection repair, and workflow changes are outside this reconciliation.

Write set: this handoff, the recap ingest route, recap review and catalog services, recap Process service, its runner lineage, the deterministic name matcher, and the Ingest UI review, API transport and owning tests. Use the existing APP source/run and native read owners. Use disposable AW Postgres at 32787 with per-test clones. Evidence stays on Projects. Provider calls and primary mutations are outside local verification.

The server validates the World and session, derives each correction from the reviewed exact occurrence and current admitted catalog, and retains accepted decisions as host-only run lineage. For reviewed edits it preserves the original APP source and passes the corrected artifact to extraction. Validate missing and stale review rejection before dispatch, exact source readback, possessive and keep choices, no-suggestion reuse, and frontend authorization and lifecycle. Use local owning backend and frontend contracts, then independent review against the exact candidate head.
