# Source ingestion and evidence: contributor map

Buddy turns source material into reviewable work for a World. The exact entry
point and available actions depend on the source and surface; this map is not
an assertion that every path is complete or deployed. Start with the
[source-to-World interaction contract](../Design/DESIGN-source-to-world-authoring-interaction-contract.md)
for the accepted ownership and confirmation boundary, then inspect the owning
route and tests for the path being changed.

## Follow the boundary

1. **Select and preserve source.** Buddy manages source interaction and
   producer inputs. Its [source artifact service](../../apps/live_control_server/services/source_artifact_registry.py)
   uses the [application-state source service](../../src/application_state/source/service.py)
   to persist immutable Markdown revisions with content digests. A stored
   producer input is not DungeonMind source admission or a published World fact.
2. **Extract and review.** Source-specific workflows create material for
   review. For example, [recap routes](../../apps/live_control_server/routes/recap_ingest.py)
   and [Worldbuilding execution](../../apps/live_control_server/services/worldbuilding_ge_execution.py)
   are different implementation entry points. Read the relevant current code
   rather than assuming a historical diagram describes both paths. Extraction
   output and evidence need review; an extracted candidate is not automatically
   durable World truth.
3. **Admit and publish through the owning boundary.** DungeonMind owns source
   identity and provenance admission, World revisions and governed publication.
   Buddy provides the product interaction; WorldKeeper coordinates supported
   semantic changes. See the interaction contract for the specific boundary and
   its implementation limits. Source grounding alone does not establish an
   explicit source-occurrence or mention link.
4. **Inspect what actually happened.** Publication and coverage are distinct
   from extraction. The [publication coverage service](../../apps/live_control_server/services/worldbuilding_publication_coverage.py)
   and its [tests](../../tests/test_worldbuilding_publication_coverage.py) are
   starting points for that path, not proof of an end-to-end deployment.

For storage and recovery across application state, DungeonMind and file-backed
artifacts, use the [local World storage guide](GUIDE-local-world-storage.md)
and its linked recovery runbooks. Do not replace missing source artifacts or
reingest as a substitute for a verified restore.

## Where to verify a change

Choose tests for the actual boundary and source path; examples include
[source-body durability](../../tests/test_worldbuilding_source_body_durability.py),
[source catalog admission](../../tests/test_worldbuilding_source_catalog_admission.py),
[source section handling](../../tests/test_worldbuilding_source_sections.py),
and the publication coverage tests above. These are navigation leads, not an
exhaustive suite or a substitute for the exact-source verification required by
[AGENTS.md](../../AGENTS.md#review-and-verification). Follow database isolation
and provider-use constraints in the applicable handoff and repository policy.

## Evidence and history

The [accepted ingestion working baseline and retrieval history](../Reports/REPORT-ingestion-baseline-and-retrieval-history-2026-11-07.md)
records the owner's C1 sessions 1–10 decision, known defects, sanitized receipt,
and limits on reproducibility. It also links the retained retrieval experiments
and explains why routing, answer quality, and publication are different claims.
That dated baseline is evidence for its stated scope, not a current release or
universal model-quality guarantee. The [lab guide](../../evals/README.md)
routes to further experiments and their inputs.

Earlier ingestion designs are useful context, but check their status and date
before relying on a statement about “today.” Current code, the applicable
contract and fresh evidence govern the particular path being changed.
