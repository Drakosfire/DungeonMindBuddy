# CLEANUP: reproduce statblock models without changing admission

Status: ACTIVE. Cleanup steward adopts original52/#4156 under the standing
cleanup goal's design, implementation, independent review and merge authority.
Serial one PR; base `2afb8ff5b428225727a21eec4818765203224606`, branch
`codex/statblock-model-regeneration`, reused isolated checkout. No unmerged
dependency, deployment, provider, database or operator-state write.

## Exclusive write lease

- this handoff
- `apps/live_control_server/integrations/dungeonmind_statblocks/README.md`
- `apps/live_control_server/integrations/dungeonmind_statblocks/generated/models.py`
- `tests/test_sbw06a_server_revise_transcripts.py`
- completed `Docs/Plans/HANDOFF-CLEANUP-statblock-schema-identity.md` for retirement

Initial scope collided with#3716's client tests. Preserve that lane: client tests
stay read-only; use the existing schema-provenance module for generation contract
assertions. Revised current open-PR scope has no changed-path overlap, including
complete102paths of unchanged#3824. Check pinned handoffs before implementation.

## Contract and bounded outcome

Canonical OpenAPI requires nullable movement/ruleset/proficiency; current models
already preserve omission refusal. Generator0.35 incorrectly emits defaults;
upstream0.46 fixes required-nullable handling. Its single proficiency wrapper
must be explicitly collapsed to the existing constrained scalar, with exact
shape/count guards. Keep existing enum/discriminator normalizations and byte
comparison. Regenerate only stale description metadata absent from the current
schema; no admission, scalar-interface, raw capture, schema or fingerprint change.
Fail/split if semantic changes extend beyond this bounded recipe.

Replace the failing README procedure with a reproducible pinned recipe using
Projects task scratch/caches. Add required/null/omitted/negative/integer round-trip
checks in the existing provenance module, not a new inventory entry. Preserve all
fixture hashes and historical identity checks.

## Verification and settlement

Run the actual documented generation and compare complete body, plus a repeated
run for deterministic bytes. Verify model delta is description-only and parse/
dump all captured request/response DTOs. Run full affected provenance/create/
capture/client contracts in a fresh locked exact-SHA environment. Verify schema/
model header/fingerprint, no capture changes, docs links, cumulative diff,
exact-head hosted/build/validator and independent review before merge. No full
frontend diagnostic or release qualification claim.

#4159 merged e0f9fb079273eeb88e31b057269d3f02ef09a88f corrected current identity
and historical captures, with75backend and1411selected frontend checks passing.
Its completed transition brief retires here with Git history retained. #4156 is
not complete until this slice's actual regeneration/compatibility evidence exists
and review/merge settle the result. The separate legacy scaffold#4163 inventory
ownership gate and all other original residuals are unaffected.
