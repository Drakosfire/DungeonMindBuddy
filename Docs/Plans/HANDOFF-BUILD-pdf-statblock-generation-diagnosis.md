# HANDOFF — Preserve PDF statblock GenerationEngine failure categories

Status: SETTLED — PR #2505 merged as `84e146d96c06e68219b08afb5f19022b3862e8fe`.

The post-merge ordinary Build retry on the retained Conks statblock region still
failed with `pdf_statblock_generation_provider_error`. No review was saved or
published. The category is now visible, but it does not identify the underlying
provider rejection.

## Delivered by #2505

Buddy now preserves GenerationEngine's provider-neutral `FailureCode` in the
PDF extraction API error code, retaining the specialized
`pdf_statblock_output_invalid` code for invalid structured output. It does not
return SDK details, raw provider messages, prompts, responses, or host metadata,
and it does not suppress failures or create review drafts after a failure.

## Merged scope

- This handoff and HANDOFF-BUILD-pdf-statblock-review-diagnostics.md to settle the merged UI slice.
- apps/live_control_server/services/build_pdf_statblock_extraction.py.
- tests/test_build_pdf_statblock_extraction.py.

No frontend, schema, source, OCR, review-storage, DungeonMind publication, or provider configuration changes.

## Verification

- Provider-free tests cover every GenerationEngine FailureCode, confirm the structured-output specialization remains, and prove no provider diagnostic text leaks.
- The route contract confirms a specific safe code is returned and no review is saved on generation failure.
- The focused failure-code and route checks pass (17 tests). The full extraction test file now passes (23 tests) after removing two local async test harness stalls while preserving the route function assertions and guarded provider-wire checks. The local Python runtime stalled in OpenAI's host-only `asyncio.to_thread(get_platform)` helper and Starlette `TestClient`'s cross-thread portal before route assertions could complete. The provider-wire tests inline only the OpenAI platform metadata lookup; route tests call the route function directly, without TestClient/ASGI transport. Thus these tests do not prove FastAPI thread-pool/ASGI integration. No production workaround or provider call was introduced.
- Command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -p no:cacheprovider -q tests/test_build_pdf_statblock_extraction.py` — 23 passed in 2.16s.
- After #2505 merged, the same retained Conks page-16 region was retried through
  ordinary Build. It failed with `pdf_statblock_generation_provider_error`;
  no review was saved or published. The API category is specific enough to
  distinguish provider generation failure, but it does not expose the upstream
  HTTP status or request ID needed to identify the rejection.
- PR #2505 received independent Bugbot review and merged. The safe transport
  diagnostic dependency update is tracked by
  `HANDOFF-BUILD-adopt-ge-safe-provider-diagnostics.md`.

## Dependencies

Depends on merged PR #2500 (691096d1d04f3d4397fdd75af35f39d58016cedb), which exposes safe server codes in Build. Buddy owns the API classification; GenerationEngine owns its normalized failure taxonomy; DungeonMind remains the authority for source identity, admission and Graph publication. The observed `pdf_statblock_generation_provider_error` remains unresolved; adopting GenerationEngine #38 is diagnostic follow-up, not a claim that the provider failure is fixed.
