# BUILD: launch extraction inside the retained artifact root

Status: ACTIVE — PRIME owns the operator-reported Edge extraction blocker.
Base: origin/main@0b5b473babe1f512196d009de61830d6aca964c0.
Branch: codex/build-extraction-artifact-root; reuse buddy-context-loop checkout.
Topology: parallel-independent of DOGFOOD semantic World-scope repair (disjoint
route/tests); one PR. No new checkout, dependency environment or preview server.

## Invariant / critique

On5202 the operator's saved Edge Extract request reached the running API and
failed before provider execution: graph_preview.post_extraction_run built an
absolute output path under the code checkout, while the real worldbuilding
runner correctly resolves artifact_data_root and rejects output outside it.
Pass an artifact-relative output path to the runner. Preserve the runner's escape
check and source/revision/digest guards. Existing GenerationEngine profile branch
must remain unchanged. Do not change the configured data root or move artifacts.

## Exclusive write set

- This handoff
- apps/live_control_server/routes/graph_preview.py
- tests/test_graph_preview_routes.py
- Docs/Plans/HANDOFF-BUILD-play-answer-evidence.md (truthful predecessor settlement only)

Prove the actual HTTP launch crosses the real runner with separate code/data
roots, deterministic fixture provider, retained run/component readback under data,
source unchanged and no output under code. Cover unset-root compatibility and
existing runner escape rejection. Preserve real failure outputs. No provider call
or new operator extraction as part of implementation tests; no World publication.
Run owning tests on disposable APP-STATE only, never retained54330/54331. Stop
owned fixture server when consumers finish. Review cumulative diff, commit/push/PR,
ARCHITECTURE review, PRIME merge and same-port API rollout with retained-state
proof. The operator may retry extraction after delivery; do not claim successful
Edge enrichment until actual saved-run review/admission and traversal are proven.

## User-facing acceptance

The saved multimodal Edge page is source authority for extraction: authored text,
accepted generated text/tables, and associated media must retain source provenance
and draft/canon distinctions. This slice repairs only launch. It does not claim
all facts or media are represented in the graph, or authorize fabricated facts
from artwork. Verify the larger ingestion-to-traversal workflow separately.


## Verification

The new real HTTP/runner regression fails on exact base with the original
artifact-root ValueError; restored fix passes. Complete route and artifact-root
suites:41 passed on disposable54329 with10 inherited Pydantic warnings.
No provider calls; fixture client only. Existing compatibility and explicit
out-of-root rejection tests remain passing. Detailed local logs in existing
.pytest_cache/build-root-{before,boundary}.log. Review/merge/adoption remain open.
