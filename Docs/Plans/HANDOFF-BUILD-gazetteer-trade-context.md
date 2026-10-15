# PRIME handoff — source-backed Gazetteer trade detail

**Status:** ACTIVE — bounded extension to the registered Gazetteer extraction profile.
**Base:** Buddy main `fae8838318ff98f1196a09b4c365f4107231af4f`; governance PR #1196 is accepted.
**Branch:** `codex/gazetteer-trade-context`.
**Topology:** serial; incorporate the accepted governance prerequisite, then retarget existing PR #1197 to main.
**Runtime/state ownership:** isolated non-serving checkout `/tmp/prime-mirathorn-governance-current`; disposable application test databases on54329 and ephemeral pgvector container `prime-mirathorn-native-test-20261015` on54332. Remove this owned container after review. Do not start or restart servers, call a provider, publish World knowledge, or edit retained data.

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
- Gold metadata refreshes the exact catalog digest and additive profile inventory; facts and questions remain unchanged.
- Existing gold validator retains its exact source/profile/catalog hash checks without weakening validation.
- This handoff and the predecessor governance handoff to record its accepted merge.
- Gold metadata may refresh implementation hashes and additive profile inventory; frozen facts, questions and evidence remain identical.

No corpus text, source hashes or IDs, raw model response, credentials, database, candidate output, serving configuration, or retained World change may enter the PR.

## Evidence and verification

- Unit tests cover grouped spans, exact source quotation, ambiguity, source binding, conflicts, no-node/no-edge behavior, and idempotency using synthetic source text and identifiers.
- The deterministic profile was exercised locally against the saved source and grouped span index using a synthetic candidate. This demonstrates exact span selection and openability only; the full preserved extraction candidate is now available locally and must be replayed before acceptance; prior synthetic execution alone does not prove its outcome.
- Run the focused Python suite, gold validator, Ruff, compileall, and cumulative `git diff --check`.
- Request independent ARCHITECTURE review on the exact PR head. World publication and ordinary-Agent acceptance remain separate lifecycle gates.

## Current preserved-candidate replay

The exact saved Build revision2 source remains unchanged. Replaying its preserved
v1.6 candidate through1.10 leaves35nodes/14edges and preserves scene exclusions.
The existing Mirathorn description already contains the route detail; the pass
adds its exact line38 quotation to the existing source citation (`quote_added`).
The governance edge receives its exact governance/title evidence. Outputs remain
local at `/tmp/prime-mirathorn-trade-replay-20261015`. No retained publication or
ordinary-Agent success is claimed.
