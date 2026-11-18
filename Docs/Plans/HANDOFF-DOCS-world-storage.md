# DOCS: local World storage and recovery map

Status: MERGED / HISTORICAL. Buddy PR #3989, merge `29beef5ee9fc5b3ea5eab5314628e97c4b8b23e5`. The lane is closed; this record does not authorize new work.

Base: Buddy main `b416410d5ecc3031a2c2db56a8aa31e0e5c480f6`. Branch: `codex/docs-world-storage`.

## Outcome and boundary

Correct stale checkout-owned registry claims in the local World storage guide.
Distinguish Buddy APP catalog and producer source inputs from DungeonMind World
and provenance authority, and preserve the need to recover referenced files.
Link existing recovery runbooks rather than inventing recovery commands. Mark
the merged #3987 handoff historical. No runtime, schema, production data,
service, port or database changes are authorized.

Expected write lease: `Docs/Guides/GUIDE-local-world-storage.md`, `Docs/README.md`,
`Docs/Plans/HANDOFF-DOCS-checker-navigation.md`, and this handoff.

## Verification

Compare each storage claim with current World catalog, source input and artifact
root code, owning tests and recovery runbooks; check links, inspect the full
diff, run `git diff --check` and the maintained entry-point checker, then follow
the exact-head review standard. No restore or live-data mutation is implied.
