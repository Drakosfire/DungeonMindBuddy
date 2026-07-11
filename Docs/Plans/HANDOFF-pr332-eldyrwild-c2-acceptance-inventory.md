# HANDOFF — PR006A: Eldyrwild C2 Acceptance Corpus Inventory

**Status:** ACTIVE — review and correction contract for GitHub PR #332  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Branch:** `campaign-supergraph/pr006a-acceptance-inventory`  
**Predecessor:** PR #329 merged as `99437abb1804f599614126701e0e9a24258fbca6`  
**Abandoned attempts:** PR #330 and #331 were closed unmerged; do not reuse them.  
**Successor:** PR006B — C2 recap source → `GraphContribution` conversion  

> This handoff is the canonical dispatch and review contract for PR #332. It
> supersedes the broken pointer from the abandoned PR #330 handoff. It does not
> authorize extraction, contribution construction, graph publication, validation
> changes, or runtime migration.

## §1 Mission

Publish a deterministic, read-only, **pinned** acceptance-corpus contract for
Eldyrwild / Longmont Campaign 2. It selects and hashes source artifacts,
declares their world/campaign authority, and emits the stable provenance
identifiers that PR006B must consume directly.

## §2 Non-goals

This slice must not parse corpus prose, call an LLM, create `GraphContribution`
objects, advance a graph head, change Kernel or validation behavior, alter
runtime readers, or modify corpus files.

The inventory is an input contract, not a candidate graph or publication result.

## §3 Authority and decisions

Read these before changing the implementation:

1. `Docs/Plans/PR-TRACKER-campaign-supergraph.md` — sequence authority.
2. `Docs/Design/ARCHITECTURE-campaign-supergraph.md` — World Supergraph and
   campaign-scope model.
3. `Docs/Design/DECISION-world-campaign-knowledge-hierarchy.md` — world
   sources use `campaign_scope: null`; Campaign 2 sources use `longmont-c2`.
4. `Docs/Design/CONTRACT-graph-kernel-boundary.md` and
   `src/graph_memory/kernel/contributions.py` — contribution identity inputs.
5. `Docs/Anchors/CORPUS-ANCHOR.md` — canonical prose root and derived-path
   exclusions.

Normative PR006A decisions:

- The acceptance corpus is pinned: all 118 selected files are explicit manifest
  entries. Recursive globs and root discovery are not acceptance selection.
- Every selected source is required. New, renamed, removed, or changed files
  require an intentional manifest + digest update.
- `source_artifact_id` is the corpus-relative, case-preserving POSIX path
  (without `corpus/eldyrwild-markdown/`).
- `source_revision_id` is `sha256:<raw-byte-sha256>`.
- `source_kind` is `source_extraction`; `extraction_profile` is
  `eldyrwild-c2-acceptance-v1`.
- Campaign sources carry `canon_layer: campaign` and
  `campaign_scope: longmont-c2`; world sources carry `canon_layer: world` and
  `campaign_scope: null`.
- PR006B must consume these report fields directly. It must not infer scope or
  provenance from paths.

## §4 Files in scope

| Action | Path | Purpose |
|---|---|---|
| Modify | `config/graph_memory/eldyrwild_c2_acceptance_inventory.json` | Pinned source manifest, authority metadata, and expected digests. |
| Modify | `src/graph_memory/materialization/acceptance_inventory.py` | Strict manifest loader, pinned inventory builder, provenance report, and atomic writer. |
| Modify | `scripts/inventory_eldyrwild_c2_acceptance.py` | Thin CLI error boundary for inventory output. |
| Modify | `tests/test_graph_memory_acceptance_inventory.py` | Unit, CLI-boundary, drift, scope, and real-corpus contract tests. |
| Modify | `Docs/Plans/HANDOFF-pr330-initial-world-supergraph-materialization.md` | Retain its ABANDONED warning and point at this handoff. |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Keep PR006A `DOING`; record pinned-inventory boundary. |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Keep the PR006A → PR006B → PR006C split and pinned-inventory dependency clear. |
| Create | `Docs/Plans/HANDOFF-pr332-eldyrwild-c2-acceptance-inventory.md` | This canonical review and dispatch contract. |

## §5 Explicitly out of scope

- `corpus/**`, `artifacts/**`, `out/**`, `apps/**`, `evals/**`
- `src/graph_memory/kernel/**`, `world_supergraph/**`, and
  `union_supergraph/**`
- Any code, artifact, or validation behavior from PR #330 or PR #331
- LLM calls, extraction, graph contributions, graph-head publication, projection,
  Plan/Play migration, and source-prose mutation

## §6 Implementation contract

### Pinned set and drift

The manifest carries:

```text
expected.source_count
expected.path_set_sha256
expected.content_set_sha256
```

`path_set_sha256` is SHA-256 of newline-joined, sorted
`source_artifact_id` values plus a final newline. `content_set_sha256` is
SHA-256 of newline-joined, sorted `<source_artifact_id>\t<raw-byte-sha256>`
records plus a final newline. The builder fails closed if either expected value
or the expected count differs.

The families must remain separate:

```text
canonical_recaps        campaign / longmont-c2 / canonical_play
party_registry          campaign / longmont-c2 / campaign_registry
pc_hubs                 campaign / longmont-c2 / campaign_reference
required_world_hubs     world    / null        / world_reference
campaign_support        campaign / longmont-c2 / campaign_reference
world_support           world    / null        / world_reference
```

There are 118 pinned sources: 23 recaps, 1 registry, 25 PC-package files,
2 required world hubs, 23 campaign-support files, and 44 world-support files.

### Report identity

Each source record includes:

```text
path                         # repo-relative POSIX display path
source_artifact_id           # corpus-relative canonical POSIX path
source_revision_id           # sha256:<raw-byte-sha256>
canon_layer
campaign_scope
source_authority
source_kind
extraction_profile
sha256
size_bytes
```

### Path and output safety

Reject absolute paths, `..`, duplicate selections, duplicate physical sources,
all symlink components, and files escaping the corpus root. The writer must
write with temporary-file-plus-replace and reject an output that overwrites the
manifest or is inside the corpus root.

## §7 Verification

Run every command from the repository root:

```bash
uv run pytest tests/test_graph_memory_acceptance_inventory.py -q

uv run python scripts/inventory_eldyrwild_c2_acceptance.py \
  --repo-root . \
  --manifest config/graph_memory/eldyrwild_c2_acceptance_inventory.json \
  --output /tmp/eldyrwild-c2-inventory-a.json

uv run python scripts/inventory_eldyrwild_c2_acceptance.py \
  --repo-root . \
  --manifest config/graph_memory/eldyrwild_c2_acceptance_inventory.json \
  --output /tmp/eldyrwild-c2-inventory-b.json

cmp /tmp/eldyrwild-c2-inventory-a.json /tmp/eldyrwild-c2-inventory-b.json
sha256sum /tmp/eldyrwild-c2-inventory-a.json /tmp/eldyrwild-c2-inventory-b.json

uv run ruff check \
  src/graph_memory/materialization/acceptance_inventory.py \
  tests/test_graph_memory_acceptance_inventory.py \
  scripts/inventory_eldyrwild_c2_acceptance.py

git diff --check origin/main...HEAD
git diff --stat origin/main...HEAD
```

## §8 PR reporting contract

The PR body must report the current head SHA, test result, source/family counts,
path-set and content-set digests, repeated-output digest, exact changed-file
list, and current diff statistics. It must state that PR006A remains `DOING`
and PR006B remains blocked.

## §9 Acceptance rubric

- [ ] The canonical `HANDOFF-pr332-*` exists in the repository — §7 diff/stat.
- [ ] All 118 sources are explicit and no acceptance glob remains — focused tests.
- [ ] Count, path-set digest, and content-set digest fail closed on drift — focused tests.
- [ ] World and campaign families carry the correct scope and authority metadata — focused tests.
- [ ] Every report record supplies the direct PR006B provenance mapping — focused tests.
- [ ] Symlinks, traversal, physical duplicates, and manifest/output overwrite paths fail closed — focused tests.
- [ ] Two generated reports are byte-identical — §7 repeated CLI commands.
- [ ] No extraction, contribution, publication, validation, runtime, or projection behavior is added — diff review.
