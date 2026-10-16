# Build reviewed-source discovery

- Status: ACTIVE; PRIME implements solo; ARCHITECTURE reviews independently.
- Authority: Mirathorn lifecycle goal and reviewed Core #126 contract.
- Base: Buddy `314e866587e18beec8d420a4e5f734bdc6857ba9`.
- Branch: `codex/build-source-discovery`; checkout `/tmp/prime-recap-mention-boundaries`.
- Topology: serial successor to merged #1252, using Core `b64e10b71c25814fadde8a2a76bba8f700d3d7d0`. Disjoint from open DOGFOOD #1235/#1237/#1244/#1251 (inspected before activation).

## Outcome and boundary

Give a governed Build conversation a deterministic, bounded discovery roster from the exact saved source and frozen World Graph revision. Resolve the existing source catalog entry by exact artifact identity, workspace reference and full body hash; never mint a revision, choose latest, create source admission, or alter the graph. Absent source admission is explicitly distinct from complete empty discovery. Ambiguous or inconsistent catalog identity fails before inference.

The initial roster contains at most 64 reviewed observations with exact subject/assertion identifiers, bounded excerpts and qualifications. Preserve eligible count, continuation and coverage; partial does not mean exhaustive. Existing object expansion and passage reads establish claim authority. Discovery entries and their excerpts grant no claim, source-read or citation permission. Grouping by source does not imply Council membership. Plan behavior stays unchanged. Retry reconstructs against the frozen graph/source basis; final provider payload verification includes the exact roster.

## Exclusive write set

- This handoff.
- `pyproject.toml`, `uv.lock` (accepted Core pin only).
- `apps/live_control_server/services/build_source_discovery.py`.
- `apps/live_control_server/routes/agent.py`.
- `apps/live_control_server/services/agent_turn_service.py`.
- `tests/test_build_source_discovery.py`.
- `tests/test_agent_build_governed_graph.py`.

## Proof and holds

Exercise real Core source discovery through the consumer, exact source/hash/workspace/World checks, absent/ambiguous/cross-source cases, truncation/coverage, frozen revision, and governed provider-envelope delivery without claim or source-pin promotion. Preserve Plan regressions. Review cumulative diff and open one PR, then independent review before merge. No serving changes, model calls, private corpus export, or retained writes in implementation. Retained read proof already found 38 observations/26 subjects across five pages, wrong revision empty, withdrawn Council description absent, with read-only connections and zero provider calls. Live runtime adoption and a new ordinary question follow separately after merge.
