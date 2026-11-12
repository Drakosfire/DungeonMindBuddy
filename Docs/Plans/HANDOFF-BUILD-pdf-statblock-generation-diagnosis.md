# HANDOFF — Preserve PDF statblock GenerationEngine failure categories

Status: ACTIVE; serial; one unstacked PR.
Base: origin/main@6464347ec6e478699a1f539778b96f2a2a8801f7.
Branch: codex/pdf-statblock-generation-diagnosis-20261112.
Checkout: existing /home/drakosfire/Projects/.codex/pdf-gold-baseline/DungeonMindBuddy; reuse it.

## Outcome

Build already displays safe API error codes after PR #2500. The PDF extraction service still maps nearly every GenerationEngineError to pdf_statblock_generation_unavailable, hiding the normalized failure category that GenerationEngine exposes.

Preserve that provider-neutral FailureCode in the API error code, retaining the existing specialized pdf_statblock_output_invalid code for invalid structured output. Do not return SDK details, raw provider messages, prompts, responses, or host metadata. Do not suppress failures, add retries, change OCR/model execution, or create review drafts after failure. This slice improves diagnosis; it does not claim to repair an unknown provider-side cause.

## Write lease

- This handoff and HANDOFF-BUILD-pdf-statblock-review-diagnostics.md to settle the merged UI slice.
- apps/live_control_server/services/build_pdf_statblock_extraction.py.
- tests/test_build_pdf_statblock_extraction.py.

No frontend, schema, source, OCR, review-storage, DungeonMind publication, or provider configuration changes.

## Verification

- Provider-free tests cover every GenerationEngine FailureCode, confirm the structured-output specialization remains, and prove no provider diagnostic text leaks.
- The route contract confirms a specific safe code is returned and no review is saved on generation failure.
- The focused failure-code and route checks pass (17 tests). The full extraction test file now passes (23 tests) after removing two local async test harness stalls while preserving the route function assertions and guarded provider-wire checks. The local Python runtime stalled in OpenAI's host-only `asyncio.to_thread(get_platform)` helper and Starlette `TestClient`'s cross-thread portal before route assertions could complete. The provider-wire tests inline only the OpenAI platform metadata lookup; route tests call the route function directly, without TestClient/ASGI transport. Thus these tests do not prove FastAPI thread-pool/ASGI integration. No production workaround or provider call was introduced.
- Command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -p no:cacheprovider -q tests/test_build_pdf_statblock_extraction.py` — 23 passed in 2.16s.
- No live model call or database mutation in this slice. A separate ordinary Build retry on the same retained region is still required to capture the actual failure category and fix the underlying rejection.
- Independent exact-head Bugbot review and required repository checks apply before merge.

## Dependencies

Depends on merged PR #2500 (691096d1d04f3d4397fdd75af35f39d58016cedb), which exposes safe server codes in Build. Buddy owns the API classification; GenerationEngine owns its normalized failure taxonomy; DungeonMind remains the authority for source identity, admission and Graph publication.
