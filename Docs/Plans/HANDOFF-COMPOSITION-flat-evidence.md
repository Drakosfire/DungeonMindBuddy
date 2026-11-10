# COMPOSITION: lossless flattened evidence presentation

ACTIVE: user authorized deterministic flattening preserving every fact,
qualification and citation handle, independent subagent review, and a Q15
quality/token comparison through existing workflow without retrieval.

Serial single PR, branch codex/flatten-writer-evidence from fetched origin/main.
Write lease: this handoff; src/application_state/agent_conversation/native_evidence_presentation.py;
evals/buddy_benchmark/workflow.py; tests/test_native_evidence_presentation.py;
tests/test_buddy_benchmark_workflow.py; Docs/Guides/ordinary-benchmark-workflow.md.
No other active PR owns these paths. Task artifacts out/writer-flat-evidence-v1.
No primary/retained database, services, dependency pins or source edits.

One capability: deterministic tabular rendering of existing native assertions
and qualifications. Keep all scalar values, empty containers, order, field paths,
and citation handles. Unchanged evidence envelope retains excerpts/question/status.
Host-only layout/readback proof is not model context or another provenance owner.
Unknown/malformed data fails before inference; no summarization or semantic filtering.

Experiment controls: same frozen Q15 source, native GE revision, system prompt,
output schema, reasoning/settings and endpoint snapshot. Existing successful
native full-context result D (nine Gold concepts) is the retained control; use its
same model and route once for the flat candidate. No unchanged baseline replay,
Gold injection, new retrieval or hidden retries. Record full/flat input tokens,
coverage, unsupported claims, attribution/chronology/citations, cost and elapsed
time separately. Candidate quality below control means no production adoption;
one run is exploratory, not reliability or causal speedup proof.

Verify exact readback on real 375-assertion/97-qualification frame, adversarial
generic structures/escaping, fixed system/schema and actual SDK request shape.
Obtain independent exact-head review. Deliver the renderer and experiment tooling
as a bounded PR; an experiment selection is not a second product default.
