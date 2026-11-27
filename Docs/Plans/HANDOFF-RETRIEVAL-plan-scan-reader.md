# RETRIEVAL: Plan source-discovery reader

Status: ACTIVE reader-only slice. Authority: the reviewed assignment at
DungeonOverMind PR #112, pinned `c20c52f43eba53b3dac28758c0f8243292760676`,
`Docs/Plans/HANDOFF-RETRIEVAL-selective-source-discovery.md`. Base:
`6bc8b1d07cce3df64e04d2def2108904244cba9f`; branch:
`codex/retrieval-plan-scan-reader`. A separate producer is blocked on reviewed,
deployed reader compatibility. Existing producers emit no new mode.

The reader recognizes the host-only controller-selected mode without changing
historical action bytes. Automatic search grants remain mandatory for legacy
request-owned turns and prohibited for the new mode. New-mode searches require
the existing acknowledged selection and source authorization; a missing search
observation is never silently repeated. Existing Plan batch codecs and closure
remain governed by their original readonly-work predicate. The mode is restricted
to current request-owned Plan admission and cannot enter model-facing input.

Focused verification covers legacy and new serialization, request admission,
opening authorization, forged automatic and unselected search rejection,
interrupted search and batch closure. Synthetic unique-World HTTP controls use
the retained owned App clone, in-memory Core and mocked providers to exercise
creative/no-scan, selected source/citation/reopen and legacy source behavior.
These are reader checks, not a live benchmark or evidence that the producer is
active. Independent exact-head review and applicable release checks remain
required; after producer activation, rollback must retain a compatible reader.
