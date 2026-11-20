# QA: replay retained writer evidence as paragraphs

MERGED in #2391 at 168d19f983d08e388f8735b426e56ba829eefbbb. Write lease released.
The previous replay slice merged in #2387 and released its write lease.
This checkout is non-serving. No database, provider, runtime, or primary-state
write lease is needed. The open #2225 composition change owns product files
outside this slice.

The existing writer replay harness gains one cohort-wide body layout option.
It presents each admitted excerpt as an ordered array of paragraphs whose
concatenation is the exact retained text. Existing excerpt handles, model
settings, instructions, and structured output schema stay fixed. The harness
reconstructs and pins the actual SDK wire through its existing dispatch gate.
This option is a provider diagnostic and does not qualify ordinary delivery.

Expected paths are this handoff, the predecessor handoff for settlement,
evals/buddy_benchmark/workflow.py and tests/test_buddy_benchmark_workflow.py.
Verify the full workflow suite locally, including exact paragraph round-trip,
SDK wire binding, and refusal of unknown or combined overrides. Obtain
independent exact-head review before adoption.

The retained Q07 and Q16 captures are partial cases. Mirathorn location and
trade is a passing control outside the QA cohort. A future comparison must
recover the omitted captivity and forced-feeding evidence, preserve correct
actor attribution and grounding, and preserve both Mirathorn facts.
