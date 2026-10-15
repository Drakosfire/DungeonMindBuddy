# PRIME handoff — source-backed Gazetteer trade detail

**Status:** ACTIVE — bounded extension to the registered Gazetteer extraction profile.  
**Base:** Buddy PR #1196 head `0c9dad0845d8e4fbe7c991d0116a2e5cb736a370`.  
**Branch:** `codex/gazetteer-trade-context`.  
**Runtime/state ownership:** none. Do not start or restart servers, call a provider, publish World knowledge, or edit retained data.

## Outcome

Add an immutable Build profile version that extends the existing Gazetteer governance and prepared-scene behavior. In a unique `Economy and Trade` section, identify one unambiguous trade-access statement, copy its route detail onto the one existing city-location candidate, and attach the exact openable source evidence.

The pass creates or renames no nodes, creates no relationships, invents no routes or endpoints, and never publishes. It fails closed if the title, section, statement, city location, or source binding is ambiguous.

## Admission rules

- Expand grouped source spans into physical lines for section and sentence matching while retaining the original span ID.
- Require one city title, one level-3 `Economy and Trade` section, one supported trade-access statement, and one existing location whose label matches the title.
- Require the new source span to belong to the same source artifact and revision already cited by the location, with openable source evidence.
- Append the detail and citation idempotently. Preserve semantic state, existing evidence, all other candidates, previous profile behavior, and source identities.

## Write set

- New extraction-profile module and synthetic unit tests.
- Profile catalog, GenerationEngine and route allow-lists, Build default profile, and version tests.
- Gold data is unchanged. Its catalog hash remains a historical snapshot; listed profile modules remain pinned and catalog growth is covered by contract tests.
- Gold validator and contract tests that preserve the frozen evaluation data while allowing additive profile registrations.
- This handoff.

No corpus text, source hashes or IDs, raw model response, credentials, database, candidate output, serving configuration, or retained World change may enter the PR.

## Evidence and verification

- Unit tests cover grouped spans, exact source quotation, ambiguity, source binding, conflicts, no-node/no-edge behavior, and idempotency using synthetic source text and identifiers.
- The deterministic profile was exercised locally against the saved source and grouped span index using a synthetic candidate. This demonstrates exact span selection and openability only; the full preserved extraction candidate is unavailable here, so its replay and final candidate counts are not claimed.
- Run the focused Python suite, gold validator, Ruff, compileall, and cumulative `git diff --check`.
- Request independent ARCHITECTURE review on the exact PR head. World publication and ordinary-Agent acceptance remain separate lifecycle gates.
