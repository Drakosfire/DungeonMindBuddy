# INGEST: preserve directed relationship meaning and modality

Status: COMPLETE implementation, independently approved at head
`3d78104952f742b355da197638f4b96cef32b634` and merged via PR2045 as
`e7c0ec84508d212c7dc211c7c270393534e7b375`. All seven CI checks passed.
Runtime delivery remains PRIME-owned; no fresh model or publication quality
is established by this merge.
Base: `e4773b18c559e14f95e39c84dc3fcca582784add`.
PR2044 merged disjoint producer retirement after activation; this lane was
fast-forwarded to fetched main before final validation and review.
Branch: `codex/recap-directed-edge-faithfulness`.
Checkout: `/home/drakosfire/Projects/.codex/249d/DungeonMindBuddy`.

Outcome: recap edge guidance requires source support for the full directed
from_node_id → relationship_type → to_node_id assertion. A source-faithful label
or valid quote does not make a reversed, misbound or overconfident tuple valid.
Plans/promises must not become completed positive relationships merely because
the catalog lacks an equivalent qualified predicate.

Observed failures: retained Session 5 actual output includes wrong endpoints and
promise-to-completed-travel promotion. Existing recap edge guidance discusses
broad referents and relationship support but does not explicitly connect tuple
direction and predicate modality to source truth. This is a prompt-level
intervention, not a proven causal cure for every observed model error.

Topology: serial successor to merged PR2043, based on fetched origin/main.
Later common object/thread guidance is a separate successor. Merged PR2044
producer retirement and PRIME’s diagnostics investigation are disjoint; no
routing or runtime state edits are included.

Expected write set:
- src/graph_memory/extraction/recap_extraction_profile.py
- tests/test_recap_source_faithfulness_profile.py
- Docs/Plans/HANDOFF-INGEST-recap-directed-edge-faithfulness.md
- Docs/Plans/HANDOFF-INGEST-inline-heading-planning.md, truthful predecessor
  merge settlement only. Runtime delivery remains independently owned by PRIME.

Implementation: consolidate the existing edge_pass specific guidance into one
coherent instruction covering direct evidence, broad referents, direction,
predicate meaning and omission when no faithful catalog expression exists.
Preserve the common recap faithfulness block and existing shared prompt builder,
catalog, exact-node contract and observation_edges-only response schema.
Do not add a semantic postprocessor, suffix repair, hard-coded source identities,
new predicate, deferred_items edge response, producer, representation or fallback.
Do not weaken recall by recommending blanket omission: retain every supported
edge whose listed endpoints and catalog predicate faithfully express the source.

Validation at owner: ordinary rendered edge prompt contains the consolidated
rules once, preserves source packet and exact catalog, requires existing schema,
and does not inject recap-only rules into Worldbuilding. Neutral active/passive
attack and possession, promised/completed travel, intended possession, unbound
victim and broad referent cases establish distinct expected tuples for later
model assessment. Prompt tests prove instruction delivery only; they must not
pretend a fixture model proves semantic compliance. Preserve original failures.

Actual model verification follows coordinated isolated runtime qualification,
using the approved standard DeepSeek configuration and retained sources. Capture
raw output, prompt/config pins and compare directed tuples, unsupported extras,
recall and host conservation separately. Publication acceptance additionally
requires governed receipts and inspection of actual published assertions.
No provider/database/publication/primary effects are authorized by this code slice.

Completion: cumulative diff review, owning checks, commit, push, PR to PRIME.
Merge and runtime delivery remain separate. Record exact pins and review results.

## Implementation evidence

The ordinary prompt regression reproduced one failure with three passing controls
before the owner correction. The existing recap edge guidance was replaced in
place; no second rule block or schema change was added. Focused profile, category
extractor and source-quote checks pass: 43 tests. Ruff and cumulative diff checks
pass. Ten retained neutral cases define later model judgments; these checks do
not establish actual model compliance or publication quality.
