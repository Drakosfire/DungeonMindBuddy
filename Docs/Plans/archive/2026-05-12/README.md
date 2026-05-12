# Plans archive — 2026-05-12

Post-merge handoff archive for **PR #16** (L3 question-delta failure diagnostics — per-question `failure_diagnostic` buckets + top-level `failure_diagnostic_summary` on committed tight/natural/C1S13 question-delta JSON; six-path allowlist; merge **`7978cd06151e6104fe064eba2e4c0fed1bb9a8f3`**, review fallback **`4275831033`**) and **PR #17** (candidate scene-beat rebenchmark wiring — beat-enriched session-memory JSONL, opt-in same-beat expansion, C1S13 scene-beat question-delta schema; eleven-path allowlist; merge **`28e98a89e591e7203d0b163d2ab445ac11509995`**, review fallback ids **`4276161552`**, **`4276396966`**, **`4276504774`**, **`4276596681`**).

| Path | Contents |
| ---- | -------- |
| [`handoffs/`](handoffs/) | `HANDOFF-pr16-phase-c-question-delta-failure-diagnostics.md` (completed PR #16 — deterministic failure-mode diagnostics on `cohort_baseline_run.py` + regenerated question-delta baselines; default retrieval unchanged; promotion still blocked by PR #12 `promotion_gate_candidate:none_found`). |
| [`handoffs/`](handoffs/) | `HANDOFF-pr17-scene-beat-rebenchmark-wiring.md` (completed PR #17 — candidate scene-beat lane: `scene_beat_memory.py`, same-beat expansion behind explicit flags, C1S13 scene-beat question-delta output; default retrieval unchanged; temp readout **improved 0 / regressed 0 / unchanged_pass 16 / unchanged_fail 9**). |
