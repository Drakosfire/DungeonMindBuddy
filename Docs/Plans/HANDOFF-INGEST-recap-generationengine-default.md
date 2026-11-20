# INGEST: ordinary recap GenerationEngine execution

Status: MERGED as #1207 at `98dfb01ff9ba88364b0f329521beb7ba7bb2f01c`, following ARCHITECTURE PASS on `cbd778cf37d3b6384725281338649499a10d3e1b` (60 independent tests). Implementation/model-control lease closed and returned to DOGFOOD. Fresh extraction/source-fidelity acceptance remains in progress under PRIME.
Base: `75152c52f430dfb0c6c8dcbc6d6ead65263ce6b2` (#1206).
Lane: `codex/recap-generationengine-default`, `/tmp/prime-mirathorn-governance-current`.
Topology: serial; solo PRIME implementation, independent ARCHITECTURE review.

## Contract

Ordinary recap extraction uses the existing GenerationEngine/OpenRouter DeepSeek
V4.1 Flash adapter, rather than silently defaulting to direct OpenAI. Provider/model
mismatch rejects before inference; injected clients remain explicit test seams.
Record private source/context hashes, returned attempts and usage/failure ledger.
Failure to retain required evidence cannot leave the run reviewable. Candidate
extraction is distinct from retained World publication. No unchanged model replay.

## Exclusive write set

- This handoff and `Docs/Plans/HANDOFF-INGEST-party-fill-source-binding.md` (settle merged lease).
- `apps/live_control_server/services/graph_preview_runner.py`
- `apps/live_control_server/routes/recap_ingest.py`
- `tests/test_recap_generationengine_default.py`
- `tests/test_live_recap_ingest_graph_preview_api.py` (owning API fixtures adopt configured route and exact admitted citations).
- `tests/test_bounded_recap_execution.py`
- `src/graph_memory/extraction/bounded_recap_execution.py` (derive profile-sized technical pass budget; preserve per-call/run deadlines).

UI model-control hunk lease transferred from DOGFOOD to PRIME by explicit
coordination (DOGFOOD acknowledged); #1191
is frozen at `553a24acbb4f0cadf0e2ceb00fe5206e8306898` until this slice merges:
`apps/live-control-ui/src/modules/IngestionModule.tsx` and `.test.tsx`.
Only obsolete Mini selection/request labels change; #1191 welcome/layout ownership
stays with DOGFOOD. Build #1183 is disjoint and continues independently.

## Evidence and state

Prove ordinary route→service→GE request and private evidence/ledger with a fake
worker, including failed attempts and ledger persistence failure. No credential
contents/public corpus output. No serving port, database migration or retained
World change in this code slice. Private run outputs remain under artifact root.
Exact-head review precedes the changed-pipeline live experiment and deployment.
