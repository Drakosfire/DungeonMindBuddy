# AGENT — batched revision-bound evidence acquisition

Status: ACTIVE. PRIME solo implementation under the operator's MIND-first goal;
ARCHITECTURE independently reviews. Serial successor to merged Jev live reader
Buddy #1268 and MIND #131 (637364c647da475d766cfba0b7eebed66d1182f4).
Base Buddy c6eacbbba94efdf8f6a0c1fad43b5a0c6bf709d1; branch
codex/jev-batched-acquisition; isolated /tmp/prime-recap-mention-boundaries.

One capability: combine independent actions within an already selected retrieval
wave using existing bounded observation-selection and source-anchor APIs. Preserve
per-action source support and exact qualifications; dependent heading continuation
waits for its parent read. No speculative actions, provider calls, API/schema change,
serving rollout, retained World/history write or cross-operation cache.

Write lease: this handoff; evals/graph_memory_layer/jev_evidence_loop.py;
evals/graph_memory_layer/jev_live_evidence.py;
evals/graph_memory_layer/run_jev_live_evidence.py;
tests/test_jev_live_evidence.py; pyproject.toml; uv.lock;
Docs/Plans/HANDOFF-AGENT-jev-live-evidence-writer.md;
Docs/Roadmaps/ROADMAP-demo.md. Open #1266/#1259/#1244/#1235 Ingest leases are
disjoint. Older paused rules dependency leases do not activate dependency writes.
The dependency lease transfers from the merged exact-source consumer to this slice.

Verification: synthetic owning-reader tests prove bounded combined selection,
shared-anchor reuse, action ownership, incomplete/foreign evidence rejection and
failure before decisions/writing. Replay fixed Float/Council actions read-only;
compare full unit hashes, actions, anchors and component time against accepted
serial measurements. Preserve failures. No new model calls in this slice.
Ordinary Agent adoption and complete Mirathorn acceptance remain later work.
