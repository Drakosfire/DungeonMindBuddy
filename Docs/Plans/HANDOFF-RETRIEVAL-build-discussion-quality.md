# RETRIEVAL: preserve requested creative constraints in Build discussion

Status: ACTIVE. The user authorized this serial over-retrieval lane and reviewed
merges/deployment. Base `195d44632183caa8b0fd9686ca1a5c5ea8dba584`, branch
`codex/build-discussion-writer-effort`, existing isolated checkout
`negative-heldout-regressions`. The previously held-out H5 creative case failed
and is now a development regression; the other H5 cases remain unexposed. The
old draft #3290 touches Plan evidence compaction elsewhere in the writer file;
it has no active pinned lease and is not a behavioral dependency. Historical
Rules/Plan/session-note handoffs mentioning this file correspond to merged PRs.

Outcome: for admitted Build discussion with no Rules lookup or authoring, use
medium instead of low writer reasoning effort. Preserve existing non-low values
and all other surfaces, barriers, requested operations, retrieval, prompts,
citations and output validation. Do not parse user text or create a second
writer/retry. This is a bounded quality/latency tradeoff, not a guarantee of
creative constraint compliance. The matching serving port is a separate serial
successor after main merge, based on the then-current serving source.

Exclusive write lease: this handoff, `apps/live_control_server/services/plan_jev_writer.py`,
and focused tests in `tests/test_plan_jev_response_assembly.py`. No database,
provider, schema, locks, retrieval policy or production change is allocated to
this implementation. Existing synthetic replay evidence lives in the separately
owned workstream clone; its workers are serial and closed.

Evidence: original H5 creative turn 382 and matched low turn 394 violated the
explicit item-length constraint. Two generic prompt-only candidate replays also
failed. Three low writer-only repeats failed, three medium repeats passed; a
medium actual-turn candidate 385 and matched repeat 397 passed independent
semantic review. Case 391 selected medium and completed a synthetic source-required
ledger answer with independently verified source support. Case 388 was excluded
by the selector and retained a post-capture experiment assertion failure; it is
not a candidate success. The 394/397 local request cycles were 3.65/4.10 s;
individual samples include instrumentation and do not establish a latency rate.
No result proves complete acquisition coverage, held-out success, or production
behavior. Preserve these observations and rerun fresh held-out controls only after
a reviewed implementation.

Validate the actual writer assembly through its GenerationEngine TextRequest for eligible Build
discussion; the temporary candidate turn also captured an actual medium-effort SDK wire. negative controls cover other surfaces, Rules, barriers, authoring,
missing work and non-low prior settings. Review exact cumulative diff and require
independent exact-head review and short checks. Do not run broad local suites.

Focused checks: 14 selector and actual writer-to-TextRequest cases passed. Five
other existing focused cases passed. Two existing assembly assertions fail at
both this working tree and byte-identical unmodified base: `test_actual_ordinary_writer_uses_compiler_in_actual_sdk_bytes[plan_current]`
expects three messages but gets one, and `[build]` expects the generic prompt
but gets Build-specific guidance. They are retained inherited failures, not
evidence for this change. The boundary test stops before SDK serialization;
the separately captured temporary candidate turn observed an actual medium wire.
