# Existing corpus statblock import

PRIME owns the corpus inventory in branch codex/statblock-corpus-inventory
from 1b5e87418, reusing the Buddy checkout. This first slice writes this handoff
and scripts/audit_corpus_statblocks.py. The import and delivery slices are serial
successors. This slice needs Git and Python only and makes no live writes.

Run `python scripts/audit_corpus_statblocks.py --revision 1b5e87418` to reproduce
the candidate list with the exact commit and SHA-256 of each file. This is an
offline inventory of Markdown in the two tracked Elderwyld trees. Its signals
are review hints and grant no source or mechanics authority. Separate evidence
is needed for image-only originals, untracked material and live database rows.

The inventory finds 55 candidate files, 26 in normalized Markdown and 29 in the
unprocessed tree. The existing two-folder browse index finds 12 of the 26.
The wider list includes six PC sheets, distinct Lysandra CR 2 and CR 4 variants,
two Dustwalker paths, token sheets, an embedded JSON seed and overlapping raw
exports. Files do not correspond one-to-one with mechanics definitions. The
browse index also drops the Meat Worm's CR 1/2 from its display metadata.
Neither inventory establishes playable or already-imported coverage.

## Delivery sequence

1. Settle the manifest against exact sources and existing accepted mechanics.
   Record each candidate as a distinct statblock, source variant, duplicate,
   supporting material or unresolved. Keep separate encounter variants even
   when their names match. Track PC sheets separately from creature mechanics.
2. Compare conversion of representative structured JSON, Markdown, and OCR
   exports using known expected mechanics. Prefer deterministic copying of
   explicit fields. Report missing or uncertain values rather than inventing
   rules or collapsing differences. Measure exact AC, HP, movement, action
   text, uses and recharge fidelity before expanding to the full set.
3. Use the existing source revision owner and the exact DungeonMindServer
   mechanics validation and acceptance path. Preserve source bytes and field
   witnesses, stable operation identities and existing actor associations.
   Rehearse on disposable state, verify repeat import is idempotent and report
   unresolved records. Verify each accepted revision can reopen in Build and
   be selected in Play before delivering to the live World.

Inventory validation reproduced 26 + 29 candidate files from the pinned tree.
The existing corpus index service test passed. Three existing endpoint tests
returned 503 in the local test environment. This slice adds no route or
runtime changes, and those endpoint checks are not treated as passing.
