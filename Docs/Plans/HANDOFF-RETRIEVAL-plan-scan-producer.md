# RETRIEVAL: Plan controller-selected source discovery

Status: ACTIVE. Authority: DungeonOverMind PR #112, pinned
`79c32ae1d396c24221c8e43bddca2464a594ff32`, in
`Docs/Plans/HANDOFF-RETRIEVAL-selective-source-discovery.md`. Base:
`a656f1da7cbc4dba0307fe09c687ae752eb83066`, which contains the compatible
reader and is live via Actions 46041017774. Branch:
`codex/retrieval-plan-scan-producer`.

New current request-owned Plan admission opts into controller-selected source
discovery. The shared builder used by legacy SDK admission remains unchanged.
Existing source authorization, retained event identity and exact citation
checks continue to own every selected search and read. No keyword heuristic or
fixed source cap decides whether a source is necessary.

Qualify creative/context-reuse, required-source, missing-source and
multiple-source cases at the real Plan boundary. A partial acquisition journal
cannot prove zero reads; mock-provider tests do not prove model behavior. Keep
the existing reader image available as rollback after any new-mode turns are
written. Independent exact-head review, compatible serving-parent checks,
Actions delivery and signed-in acceptance remain required. The dedicated
negative-retrieval benchmark and broader index work remain part of the goal.
