# RETRIEVAL: Creative-only source limitation

Status: ACTIVE under the user's over-retrieval and response-quality goal. Parallel
independent of benchmark PR #4584: this slice does not modify its evaluator or
use its database. Branch `codex/creative-source-free-limitation` in the attached
`dogfood-lore-review` checkout is based on serving source
`6595a93e9b4c360a578bf9125876b1cccd6857be`, whose current remote branch is
`codex/trace-serving-base-6595`. The benchmark handoff records the topology.
Write lease: this brief, `src/application_state/agent_conversation/native_completion.py`,
and focused existing completion/Build source-free tests. No schema, prompts,
provider routing, citation binding, acquisition policy or frontend changes.

The signed-in synthetic naming smoke returned a proposal-only creative answer.
The raw writer output contained no limitations, but the host appended a partial
retrieval warning because unprepared native evidence is marked partial. Do not
add that host-generated warning to a valid pending Build proposal-only response
when admitted work explicitly says the supplied context is sufficient. Preserve
writer-supplied limitations, required-source and mixed factual safeguards,
missing-detail reporting, source/citation validation, and all other surfaces.
Do not use absence of source data or the model's proposal label alone to waive a
needed factual warning. The narrow guard must rely on the validated work decision
and completed segment types, and never change input evidence status.

Verify the actual completion boundary using focused synthetic cases: anchored
creative proposal without a footer; source-required, uncertain, mixed/factual,
empty and explicit limitation cases retain their protections; invalid or forged
citations remain rejected. Check the exact cumulative diff and seek independent
exact-head review. The source owner, pinned live identity and relevant open
leases must be rechecked before release. A serving overlay must be based on the
then-current serving source, published and cut over through GitHub Actions with
current rollback pins; signed-in post-deployment smoke is required. Benchmark
qualification and the broader over-retrieval goal remain open.

## Working verification

The synthetic writer/acceptance boundary reproduced the unwanted warning before
the change (one failure, explicit-limitation control passed). With the guard,
four focused cases passed: anchored proposal without an added warning, the
same with a writer-supplied warning preserved, source-lookup work retaining its
warning, and a mixed proposal with an unbound citation rejected. Completed
replies were reconstructed from their stored rows. These tests use in-memory
fixtures and mock transports, with the synthetic fixture's old controller model
alias aligned locally; they do not prove live behavior or benchmark rates.

An additional pre-existing mixed-review test did not run: its autouse fixture
required a retained CI App owner and failed before database access. No new clone
was created. The fixture error is not a product failure or passing evidence.
Additional focused synthetic cases passed for an empty answer retaining its
missing-detail and partial limitations, a valid mixed saved-page claim/proposal
retaining its exact source binding and explicit limitation, and stored-row plus
ordinary replay of a reply accepted under the old warning behavior. The test
constructs that historical reply with the prior host projection. A focused owner-level check also confirms uncertain work does not qualify as
anchored; it does not exercise an entire uncertain turn. Exact-output
reconstruction compatibility, in-flight cross-release acceptance and independently
reviewed real-source boundaries remain required before release. Recheck live serving parent and produce exact-head
review and post-deployment app evidence before claiming delivery.

A focused synthetic cross-release control now constructs the old warning-bearing
result and submits it to the new pending acceptance owner. It fails closed on
exact output equality before changing the mocked Turn or Rules ledger; an
already accepted old reply separately replays unchanged. This is in-memory
boundary evidence, not proof of real PostgreSQL rollback or deployment drain.
`verify_completion` reconstructs the new projection for old proof bytes, but no
production caller was found in `src/` or `apps/`; its independent contract and
any real in-flight cross-release behavior remain release-review concerns. No
broad dual-projection acceptance was introduced.
