# CLEANUP: retire historical NPC audit snapshots

Status: ACTIVE. Cleanup steward adopts this bounded slice under the standing
cleanup goal's implementation, review and merge authority. Serial one PR on
`codex/retire-npc-dated-reports`, base `5fd10acc0d67127ea89bfb67de67fc1cb22e64bd`, reused isolated checkout.
No unmerged dependency, provider, database, deployment or operator-state writes.

## Exclusive write lease

- this handoff
- `evals/npc_corpus_recall_audit/README.md` (new lab/recovery guide)
- three JSON files under `evals/npc_corpus_recall_audit/artifacts/runs/2026-05-07/` (delete)

## Invariant and failure cases

Preserve exact historical results through pinned Git links, hashes and lengths.
Do not alter the generator, last-report mirror, corpus, registries or tests.
The three payloads total58130bytes; one matches the retained last mirror. Unique
older versions remain recoverable in Git, not a separate archive directory.
Do not imply the current corpus reproduces historical results or that the lab
is production runtime. Document that the CLI writes its last mirror even when
`--output` is supplied; no misleading side-effect-free command is introduced.

Current/open-head searches found only the generator, its test and an archived
handoff referencing the generator.58previous heads plus newly updated4175 were
checked.210registered worktrees,209with targets, have no target changes/errors.
Remote recovery of all three exact payloads passed. Generic directory readers
and current ownership must be checked before deletion; named active eval leases
from the preceding audit cover unrelated labs. Preserve all neighboring state.

## Verification

Run both NPC audit and corpus-index test modules before/after with fresh locked
exact-source environments; retain any inherited failure without weakening tests.
Verify remote hashes, current maintained links, exact cumulative five-path diff,
net tracked-byte change and official exact-head hosted/build/validator evidence.
Independent exact-head review is required before merge. No new full frontend
diagnostic, operator-use confirmation, physical disk or image-size claim.
Predecessor4176 merged5fd10acc with identical paired67pass1fail; inherited C1S4
comparison failure remains explicitly owned by4177, outside this write lease.
