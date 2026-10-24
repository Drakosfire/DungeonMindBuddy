# Reuse exact repeated dialogue without losing occurrences

ACTIVE serial PRIME slice; base baee545074120817cdeb66d54d2253059e1edde4,
branch codex/build-exact-dialogue-reuse in the existing buddy-context-loop checkout.
One capability/PR; open hosted/Combat/Ingest lanes are disjoint. PRIME owns API8000
and UI5202. No operator World mutation or model checks while an operator turn runs.

Current Build captures complete recent exchanges, but exact repeated pairs are
sent repeatedly. Introduce a shared lossless dialogue projection: retain every
occurrence in order with its original metadata; replace only identical user AND
assistant text with an explicit zero-based reference to an earlier literal pair.
Never normalize, merge near matches, drop turn IDs/hashes or turn dialogue into
source/citation authority. Do not broaden the six-row history read or add reads.
Keep full ledger rows and expand aliases for host inclusion/proof operations.
Use the same projection for Build decisions, discussion, page and image writers.
Decode strictly and roundtrip before dispatch; reject forward/cyclic/malformed
references. Document interpretation in each actual model input. Use aliases only
when the complete serialized projection is smaller. No new character/token caps.

Exclusive writes: this handoff; HANDOFF-BUILD-draft-correction-priority.md and
Docs/Roadmaps/ROADMAP-demo.md for settlement; new shared pure dialogue_projection.py
under src/application_state/agent_conversation; Build driver, harness, discussion,
proposal and image writer services; focused codec tests, ordinary Build harness
and affected current-contract tests. No schema/DB/UI/dependency change. Preserve
provider dispatch, current draft, source/selection proof, mixed answer completeness,
chronology and immutable history. The projection is a wire representation, not a
new durable source authority or backwards-compatibility execution path.

Prove Unicode/exact/near-match and repeated nonadjacent pairs, distinct metadata,
strict invalid references, roundtrip, actual SDK→APP duplicated-history follow-up,
writer input, one bounded history read and unchanged source. Measure bytes before/
after on a retained private trace; distinguish that from billed tokens/latency.
Run owner/accounting/tamper cohorts, cumulative diff, independent Bugbot, PRIME
merge and protected API delivery. Full authoring/J1–J6/performance acceptance stays open.

The actual dispatch regression exposed static versus projected system instructions;
the owner now sends the exact prepared instructions validated by its existing gate.
Current-contract fixtures also remove one obsolete history-cutoff expectation and
use valid JSON for the pre-existing writer-reserve admission test. No admission
allowance changes. On one retained private six-exchange synthetic request, one
alias saves only 58 serialized bytes after interpretation overhead; this is not a
latency or billed-token improvement claim. A configured writer check interpreted
the alias-bearing input and retained the unresolved current-page conflict correctly.
