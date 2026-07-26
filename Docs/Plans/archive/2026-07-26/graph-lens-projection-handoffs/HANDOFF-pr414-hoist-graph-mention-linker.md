---
# Literal Markdown the worker MUST use as the PR-body skeleton.
# The complete checked-in handoff remains authoritative.
pr_body_template: |
  ## Outcome
  Any surface that renders prose beside World Graph nodes can splice `dmb-node:` links into that prose through one surface-neutral module so that CommonMark protection is implemented and proved exactly once.

  ## Merge-ready invariant
  For every Markdown input and node-identity binding set the recap path accepts today, the hoisted linker produces byte-identical projected Markdown, an identical mention list (ids, labels, offsets, order), and identical diagnostics (codes, messages, severities, order); no production caller's source or observable output changes.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Byte-identical projection output vs. base | `markdown_mentions.project_markdown_mentions` | Characterization fixture generated at base SHA, replayed at head | {{TODO: pass/fail/not run + provenance}} |
  | Recap adapter output unchanged | `world_recap_projection.project_world_markdown_mentions` | `uv run pytest tests/test_world_graph_recap_projection.py -q` | {{TODO}} |
  | Neutral module imports no surface types | module import graph | `uv run pytest tests/test_markdown_mentions.py -q -k no_surface_imports` | {{TODO}} |
  | Service caller unchanged | route/service boundary | `git diff --name-only <base>...HEAD` omits the caller | {{TODO}} |
  | Binding order preserved | adapter | Ambiguity/longest-surface ordering tests | {{TODO}} |

  ## Scope and explicit deferrals
  {{TODO: base/head, actual changed paths, paths outside §4, and named successors still false}}

  ## Evidence produced
  ### Automated
  {{TODO}}
  ### Adversarial
  {{TODO}}
  ### Regression
  {{TODO}}
  ### Manual / dogfood
  {{TODO}}

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact missing evidence, operator waiver, and stop condition}}
---

# HANDOFF — Hoist the graph mention linker to a surface-neutral module

> **COMPLETED — 2026-07-26.** Shipped via [PR #414](https://github.com/Drakosfire/DungeonMindBuddy/pull/414)
> (`main` merge commit `5c19d433c9e103573ea6bd72ae1f34483862569f`).
> **Three review rounds** (all GitHub `COMMENTED` under self-review fallback; treat banners as the verdict):
> 1. APPROVE (`pullrequestreview-4781008821`, head `0d3265b4`) — pure-move invariant held on first independent re-verify.
> 2. REQUEST CHANGES (`pullrequestreview-4781999189`) — blocker: `MarkdownMentionDiagnostic.severity: str = "info"` made a required public field optional.
> 3. MERGE (`pullrequestreview-4782060618`, corrective head `eaf441d0`) — severity required again; public-contract test asserts `code`/`message`/`severity` required; corrective delta limited to model + tests.
> Archived and renamed from `HANDOFF-pr413-…` to `HANDOFF-pr414-…` per `AGENTS.md`.
> **Follow-ups:** `derive-recap-views-normalize-direction` (shipped as PR #416); `migrate-union-mention-path`; PR380B. **Archived for historical reference; do not re-dispatch.**

**Created:** 2026-07-25.
**Status:** DONE — merged as GitHub **PR #414** (`5c19d433c9e103573ea6bd72ae1f34483862569f`).
**Canonical handoff path:** `Docs/Plans/archive/2026-07-26/graph-lens-projection-handoffs/HANDOFF-pr414-hoist-graph-mention-linker.md`

> **Numbering:** Successors below use **content slugs**, not guessed GitHub PR numbers. The old handoff vocabulary "PR #414" / "PR #415" meant those successor slices, not this PR.

> **Dispatch gate:** Dispatch is prohibited until capability decomposition is complete, one independently useful mission remains, the merge-ready invariant and required evidence survive critique, every expected path is known, required contract matrices are resolved, and every acceptance claim has an owning proof.
>
> This checked-in handoff is the complete authority. The worker must not compress, omit, replace, or rewrite it before implementation. The PR description must use the frontmatter skeleton and remain a truthful merge contract; it cannot substitute for the handoff.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Capability** | A coherent behavior or contract that creates one outcome someone can use, depend on, test, or revert. |
| **Independently useful outcome** | An outcome that provides value or establishes a reusable contract even if neighboring work never ships. |
| **Public/durable contract** | A persisted format, identifier, API, event, schema, file representation, caller-facing type, or externally consumed interface that must remain interpretable beyond one call stack. |
| **Observable path** | A user-visible or externally observable route through the behavior, including success, miss, error, retry, persistence, and operator paths. |
| **Owning boundary** | The layer where a guarantee becomes true and therefore must be proved: serializer, store, service, route, component, workflow, CLI, or equivalent. |
| **Invariant** | The single property every changed layer and observable path establishes or proves. |
| **Evidence ledger** | The mapping from each invariant clause to its owning boundary, required proof, produced result, provenance, and merge-blocking stop condition. |
| **Stop condition** | A discovered fact that invalidates the current slice boundaries or required proof and must be reported before implementation continues. |
| **Binding** | A `(surface, node_id)` pair: a literal text form that, when found in prose, denotes a durable graph node. |
| **Surface form** | The literal text matched in prose — a node label or one of its aliases. |

## §1 Mission and merge-ready invariant

```text
Any surface that renders prose beside World Graph nodes can splice `dmb-node:` links
into that prose through one surface-neutral module so that CommonMark protection is
implemented and proved exactly once.
```

**Merge-ready invariant:** `For every Markdown input and node-identity binding set the recap path accepts today, the hoisted linker produces byte-identical projected Markdown, an identical mention list (ids, labels, offsets, order), and identical diagnostics (codes, messages, severities, order); no production caller's source or observable output changes.`

This is a **pure move with a characterization-test invariant.** No behavior change of any kind is authorized. If you believe a current behavior is wrong, that is a stop condition, not a fix.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. There is exactly one production caller (`apps/live_control_server/services/world_graph_recap_projection.py:117`) and one public function (`project_world_markdown_mentions`). Byte-identity of that function's three return values governs every path. |
| What adversarial sequence is most likely to falsify it? | **Binding iteration order.** Today `_surface_owners` and the `unique_surfaces` loop both iterate `for node in nodes: for raw in (node.label, *node.aliases)`. Ambiguity detection picks `sample` as the *first* surface in that order, and `unique_surfaces` is sorted by `(-len, casefold, node_id)` with a first-wins dedupe on casefold. A refactor that builds bindings from a `set`, a `dict`, or a re-sorted collection changes which literal casing is reported in the ambiguity diagnostic message and which surface wins a tie — silently, with most tests still green. |
| Would the proposed §7 evidence actually detect that failure? | Yes, but only via the characterization fixture (§7 row 1), which pins exact diagnostic *message strings* and exact mention order — not just counts. The existing four unit tests alone would **not** catch a casing flip in the ambiguity sample. This is why the fixture is mandatory and why it must be generated at base before any refactoring. |
| Which owning boundary is easiest to under-test? | The adapter in `world_recap_projection.py`. It is tempting to test only the new neutral module and assume the adapter is trivial. The adapter is where binding order is constructed, i.e. exactly where the most likely defect lives. |
| What fact would force this slice to stop or split? | Discovering that `splice_node_link_spans` cannot move without touching `graph_gold_review.py` or `graph_authoring_overlay_projection.py`; or discovering an import cycle that cannot be resolved without moving additional symbols; or finding that the characterization fixture cannot reproduce byte-identity because behavior depends on unpinned iteration order (e.g. `set` ordering) already present at base. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/DECISION-graph-lens-projection-boundary.md` (decision 1 and its Sequencing table) |
| Repository rules | `.cursor/rules/external-agent-pr-loop.mdc`, `AGENTS.md`, `.cursor/rules/dungeonbuddy-git-workflow.mdc`, `QUICK-REFERENCE-DungeonMind.mdc` (**all Python via `uv run`**) |
| Base revision | `origin/main` at dispatch = `3195251a543ef0ebe0a551e7ea8015aa0f1d64b2` (docs-only commit on top of `7a22e6c8`, the PR #412 merge — the `src/` and `tests/` trees are byte-identical to `7a22e6c8`). Branch from `origin/main`; all diff commands below use `$(git merge-base origin/main HEAD)` so a later docs-only commit on `main` does not invalidate them. |
| Predecessor contract | PR #412 / PR380A — `world_recap_projection.project_world_markdown_mentions` and its five CommonMark protection fixes |
| Exact input consumed | `markdown: str` plus `list[WorldGraphProjectionNodeView]`; produced by `apps/live_control_server/services/world_graph_recap_projection.py` |
| Named successor | `derive-recap-views-normalize-direction` (derive recap views from generic views; normalize `direction` at the kernel boundary); `migrate-union-mention-path` (migrate `recap_projection._project_markdown_mentions` onto the hoisted linker) |
| What remains false | The union-supergraph mention path remains unprotected. The `WorldGraphRecap*` models remain hand-copied. `adapt_relationship_direction` still translates per-surface. No new surface consumes the hoisted module yet. |
| Explicit non-goals | Any behavior change; any frontend change; any new CommonMark protection; any wire-schema change; any plugin/registry abstraction |

Read authoritative inputs in order before changing code:

1. `Docs/Design/DECISION-graph-lens-projection-boundary.md`
2. `src/graph_memory/projection/world_recap_projection.py` lines 274–728 (the region being moved) — read the **whole** region before editing; the helpers are mutually dependent
3. `src/graph_memory/projection/recap_projection.py` lines 372–416 (`splice_node_link_spans`)
4. `apps/live_control_server/services/world_graph_recap_projection.py` line 117 (the single production caller)
5. `tests/test_world_graph_recap_projection.py` lines 119–231 (the four owning tests)

If the base moved, an authority conflicts, the predecessor shape differs, or the invariant cannot be preserved, stop and report the consequence before implementation.

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---:|---|
| Unique surface in plain prose | Spliced to `[label](dmb-node:id)` | Byte-identical | Yes | `markdown_mentions` |
| Surface owned by ≥2 nodes | Left unlinked; one `ambiguous_mention_surface` diagnostic per surface key | Byte-identical, including the literal `sample` casing in the message | Yes | `markdown_mentions` |
| Overlapping surfaces (longest wins) | Longest unique surface wins; shorter overlapping match dropped | Byte-identical | Yes | `markdown_mentions` |
| Surface inside protected Markdown | Untouched; no mention emitted | Byte-identical | Yes | `markdown_mentions` |
| Recap service call | `project_world_markdown_mentions(markdown, nodes)` returns recap types | Same signature, same types, byte-identical values | Yes | `world_recap_projection` adapter |
| `POST /api/live/world-graph/recap-projection` | camelCase payload with mentions and diagnostics | Byte-identical response | Yes | route |

Ordered failure sequences that must be exercised:

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Node A label `Caelynn` → Node B alias `caelynn` → project prose containing `CAELYNN` | Exactly one ambiguity diagnostic whose message quotes the **first** surface in node-iteration order, with its original casing; no splice | §7 row 1 + row 5 |
| Node with alias longer than another node's label, both matching at the same offset | Longer surface wins; shorter is dropped, not double-spliced | §7 row 1 + row 5 |
| Same surface text appearing both inside a fenced code block and in plain prose | Prose occurrence spliced; code occurrence untouched; mention offsets computed against post-splice text | §7 row 1 |
| Node whose label is empty/whitespace, plus a valid alias | Empty surface skipped without diagnostic; alias still binds | §7 row 1 |

## §4 Files in scope (allowlist)

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Create | `src/graph_memory/projection/markdown_mentions.py` | The surface-neutral module: neutral models, `splice_node_link_spans`, the CommonMark scanner, `project_markdown_mentions` |
| Modify | `src/graph_memory/projection/world_recap_projection.py` | Delete the moved region; `project_world_markdown_mentions` becomes a thin binding-builder + result-mapper preserving its exact signature |
| Modify | `src/graph_memory/projection/recap_projection.py` | Import `splice_node_link_spans` from the new module and re-export it so existing callers are untouched |
| Modify | `src/graph_memory/projection/__init__.py` | Export the new neutral names; keep every existing export working |
| Create | `tests/test_markdown_mentions.py` | Owning-boundary tests for the neutral module, the no-surface-imports test, and the characterization replay |
| Create | `tests/fixtures/markdown_mention_characterization_v1.json` | Base-generated golden: inputs → exact projected Markdown, mentions, diagnostics |
| Modify | `tests/test_world_graph_recap_projection.py` | Move the four linker tests out; retain adapter-level coverage asserting the recap types and binding order |

**Bounded discovery exception:** `Not applicable — every path is enumerable from the single production caller and the four owning tests.`

Unrestricted globs such as `src/**` are prohibited. If another path is needed outside the table, stop and report it; do not add it silently.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `apps/live_control_server/services/world_graph_recap_projection.py` | **Its absence from the diff is the proof** that the public signature was preserved. Touching it invalidates the invariant. |
| `apps/live_control_server/services/graph_gold_review.py` | Imports `splice_node_link_spans` from `recap_projection`; the re-export keeps it unchanged. Updating its import is a successor cleanup. |
| `apps/live_control_server/services/graph_authoring_overlay_projection.py` | Same as above. |
| `recap_projection._project_markdown_mentions` and `_known_mention_spans_in_markdown` | The unprotected second implementation. Migrating it is `migrate-union-mention-path` and carries a real behavior change. Do **not** "fix it while you're there." |
| `WorldGraphRecap*` models, `_adapt_*`, `adapt_world_node_to_recap_view` | `derive-recap-views-normalize-direction`. Separate invariant (derivation, not identity). |
| `adapt_relationship_direction` | `derive-recap-views-normalize-direction` — normalization moves to the kernel boundary. |
| `_protected_ranges` behavior — adding, removing, or "improving" any CommonMark case | Five review rounds produced the current set. Any change breaks byte-identity and is a stop condition. |
| `apps/live-control-ui/**` | `dmb-node:` consumers are already generic. No frontend change is in scope. |
| `Docs/Design/DECISION-graph-lens-projection-boundary.md` | Authority document; the worker does not edit its own authority. |

Nearby work is not authorization.

## §6 Implementation contract and conditional matrices

```text
Input:
  markdown: str
  bindings: Sequence[MentionBinding]  # ordered; duplicates permitted and significant

Output:
  (projected_markdown: str,
   mentions: list[MarkdownMention],
   diagnostics: list[MarkdownMentionDiagnostic])

Invariant:
  Same as §1 — byte-identical to base for every input the recap path accepts.

Failure behavior:
  empty markdown              -> return input unchanged, [], []
  empty bindings              -> return input unchanged, [], []
  blank/whitespace surface    -> skipped silently, no diagnostic (matches base)
  surface owned by >1 node    -> unlinked + one ambiguous_mention_surface diagnostic per key

Replay / idempotency:
  same input        -> identical output (pure function, no I/O, no randomness)
  changed input     -> recomputed; no cached state
  retry after failure -> not applicable; function is total and side-effect free

Trust boundary:
  Verifies: that a matched span lies outside every protected Markdown range;
            that a surface maps to exactly one node before linking.
  Records or trusts without proving: that caller-supplied node_ids are durable and
            resolvable; mentions are navigation-only and carry no evidence authority.
```

### Required public shape

```python
class MentionBinding(BaseModel):
    surface: str
    node_id: str

class MarkdownMention(BaseModel):
    mention_id: str      # f"mention:{node_id}:{original_start}" — preserve exactly
    node_id: str
    label: str
    start_offset: int | None = None
    end_offset: int | None = None

class MarkdownMentionDiagnostic(BaseModel):
    code: str
    message: str
    severity: str

AMBIGUOUS_MENTION_DIAGNOSTIC = "ambiguous_mention_surface"

def project_markdown_mentions(
    markdown: str,
    bindings: Sequence[MentionBinding],
) -> tuple[str, list[MarkdownMention], list[MarkdownMentionDiagnostic]]: ...
```

`mention_id` uses the **original** (pre-splice) start offset while `start_offset`/`end_offset` are **post-splice**. That asymmetry exists at base; preserve it exactly.

### A. State and fallback matrix

`Not applicable — the function is pure with a single source of truth (its arguments); there are no dependencies, no loading state, and no fallback sources.`

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Exact `node_id` | Passed through verbatim into the `dmb-node:` href and `mention_id` | n/a | No |
| Alias / label surface | Case-insensitive match; linked **only** when the casefolded surface is owned by exactly one `node_id` | Left unlinked; one diagnostic per casefolded key, quoting the first surface in binding order with original casing | No |
| Normalized key | `str.casefold()` for ownership and dedupe only; never for display or href | n/a | No |
| Overlapping matches | Longest surface first, then `casefold`, then `node_id`; first-wins dedupe on casefolded key; occupied ranges block later overlaps | n/a | No |

First-win matching across *different* nodes is prohibited — that is exactly what the ambiguity diagnostic exists to prevent. Display labels must not substitute for durable identity.

### C. Persistence and replay matrix

`Not applicable — nothing is persisted. The characterization fixture is test data, not a runtime durable format.`

### D. Predecessor-to-consumer mapping

**Grounding source:** `src/graph_memory/projection/world_recap_projection.py` at base `origin/main` (source identical to `7a22e6c8`), lines 610–728.

| Predecessor field / outcome | Real shape and optionality | Consumer field / behavior | Transformation | Proof fixture/test |
|---|---|---|---|---|
| `nodes: list[WorldGraphProjectionNodeView]` | required; `label: str`, `aliases: list[str]` | `bindings: Sequence[MentionBinding]` | `for node in nodes: for raw in (node.label, *node.aliases)` — **order-preserving, duplicates kept, no set/dict deduplication** | `tests/test_markdown_mentions.py::test_binding_order_preserves_ambiguity_sample_casing` |
| `WorldGraphRecapMention` | `mention_id`, `node_id`, `label`, `start_offset`, `end_offset`, `evidence_ref_ids=[]` | `MarkdownMention` + adapter | Adapter re-adds `evidence_ref_ids=[]`; all other fields copied verbatim | `tests/test_world_graph_recap_projection.py` (retained adapter tests) |
| `WorldGraphProjectionDiagnostic` | `code`, `message`, `severity="warning"` | `MarkdownMentionDiagnostic` + adapter | Field-for-field; message string byte-identical | characterization fixture |

The binding-order row is the highest-risk mapping in this slice. Treat it as the primary review target.

## §7 Evidence required to merge

| # | Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---:|---|---|---|---|---|---|
| 1 | Byte-identical projection output vs. base | `markdown_mentions.project_markdown_mentions` | contract / characterization | `uv run pytest tests/test_markdown_mentions.py -q` replaying the base-generated fixture | Every case matches exactly: projected string, mention tuples in order, diagnostic strings in order | Any single byte differs |
| 2 | Recap adapter and route output unchanged | `world_recap_projection` + route | regression | `uv run pytest tests/test_world_graph_recap_projection.py -q` | All pass, including revision-pin service and route tests | Any failure |
| 3 | Neutral module imports no surface types | module import graph | contract | `uv run pytest tests/test_markdown_mentions.py -q -k no_surface_imports` | `markdown_mentions` imports nothing from `world_projection`, `world_recap_projection`, `recap_projection`, `node_view`, `focus_overlay` | Any surface import present |
| 4 | Production caller untouched | service boundary | contract | `git diff --name-only $(git merge-base origin/main HEAD)...HEAD` | Output omits `apps/live_control_server/services/world_graph_recap_projection.py` | Caller appears in the diff |
| 5 | Binding order preserved | `world_recap_projection` adapter | adversarial | `uv run pytest tests/test_markdown_mentions.py -q -k "binding_order or ambiguity"` | Ambiguity message quotes the first surface in node-iteration order with original casing; longest-surface tie-break unchanged | Casing or winner differs from base |
| 6 | No import cycle introduced | package | contract | `uv run python -c "import graph_memory.projection as p; print(sorted(p.__all__))"` | Imports cleanly; `__all__` is a superset of base | ImportError or a removed export |
| 7 | Package-wide regression | projection package | regression | `uv run pytest tests/ -q -k "projection or recap or mention"` | No new failures vs. base | Any new failure |
| 8 | Lint clean | repo | regression | `uv run ruff check src/graph_memory/projection tests/test_markdown_mentions.py tests/test_world_graph_recap_projection.py` | Clean | Any error |

Run every command and record exact results:

```bash
uv run pytest tests/test_markdown_mentions.py -q
uv run pytest tests/test_world_graph_recap_projection.py -q
uv run pytest tests/ -q -k "projection or recap or mention"
uv run ruff check src/graph_memory/projection tests/test_markdown_mentions.py tests/test_world_graph_recap_projection.py
uv run python -c "import graph_memory.projection as p; print(sorted(p.__all__))"
git diff --check
git diff --stat $(git merge-base origin/main HEAD)...HEAD
git diff --name-only $(git merge-base origin/main HEAD)...HEAD
```

### Mandatory ordering: generate the characterization fixture FIRST

This is not optional and not reorderable.

1. Branch from `origin/main`. **Change no source yet.**
2. Write a generator that calls the **unmodified** `project_world_markdown_mentions` over the corpus below and serializes, per case: the input Markdown, the input node label/alias structure, the projected Markdown, every mention as `(mention_id, node_id, label, start_offset, end_offset)` in order, and every diagnostic as `(code, message, severity)` in order.
3. Commit the fixture as its own commit, before any refactoring, with a message naming the base SHA. The reviewer will verify the fixture predates the refactor in history.
4. Only then perform the move.

**Fixture corpus — minimum required cases.** Include every adversarial case already present in `tests/test_world_graph_recap_projection.py::test_protected_markdown_and_code_ranges_untouched` (do not retype them from memory; read them from the file), plus:

- plain unique surface; repeated unique surface; surface at string start and string end
- ambiguous surface with differing casing across two nodes, prose using a third casing
- overlapping surfaces where the longer belongs to a different node
- node with empty-string label and a valid alias; node with whitespace-only alias
- surface adjacent to punctuation, and surface embedded in a longer word (must not match)
- surface inside: inline code span, multiline code span, fenced block, existing inline link label, existing link destination, shortcut reference link, nested link label, URI autolink (lower and upper case scheme), email autolink, reference definition with zero whitespace, next-line destination, unindented title, multiline title, angle-bracket destination containing spaces
- empty markdown; empty bindings; markdown with no matches

### Minimal live / dogfood proof

`Not applicable — this slice changes no observable behavior; the characterization fixture is a stronger proof than a dogfood run, and a dogfood run could not detect a byte-level regression.`

### Baseline failure protocol

For any required command already failing on base: run the same command on base and head, record whether head introduces additional failures, do not call the gate green, and name the operator waiver required if it remains an acceptance gate.

## §8 Required PR description and handback

The PR description must use the frontmatter skeleton and include:

1. §1 Mission copied exactly.
2. §1 merge-ready invariant copied exactly.
3. The §7 evidence ledger: required evidence, produced result, and provenance.
4. Base SHA (output of `git merge-base origin/main HEAD`) and head SHA.
5. Actual changed paths and focused diff stat limited to §4.
6. Every §7 command and its exact result (exit code, pass/fail counts, failing test names).
7. Provenance of each result: author-local, independently rerun local, CI, or manual.
8. Baseline failures with base/head comparison.
9. Explicit operator waivers; `none` when none exist.
10. Paths outside §4; `none` or a stop report.
11. Stop conditions encountered and resolution; `none` when none exist.
12. The commit SHA of the characterization fixture, demonstrating it predates the refactor.
13. Successor capabilities deferred and still false (`derive-recap-views-normalize-direction`, `migrate-union-mention-path`, PR380B).
14. Confirmation that this handoff was implemented without compressed or omitted constraints.

A generic "Summary / Test plan" PR body does not satisfy this section.

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability from §1 was delivered — proved by §7 rows 1 and 4.
- [ ] Byte-identity holds across every observable path and adversarial sequence in §3 — proved by §7 rows 1, 2, 5.
- [ ] The characterization fixture was generated at base and committed **before** the refactor — proved by commit order in `git log`.
- [ ] The neutral module's public signature contains no graph, recap, or surface type — proved by §7 row 3 and diff inspection.
- [ ] Binding construction preserves node-iteration order with duplicates — proved by §7 row 5 and §6.D.
- [ ] The single production caller is byte-unchanged — proved by §7 row 4.
- [ ] No second public/durable contract was silently introduced; the recap wire schema is untouched — proved by diff inspection.
- [ ] No CommonMark protection case was added, removed, or altered — proved by §7 row 1 and diff inspection of `_protected_ranges` and its helpers.
- [ ] No path outside §4 changed — proved by §7 row 4's `--name-only` output.
- [ ] Baseline failures are reported truthfully and any required waiver is explicit.
- [ ] The named successors (`derive-recap-views-normalize-direction`, `migrate-union-mention-path`) remain unimplemented and unclaimed — in particular `recap_projection._project_markdown_mentions` still lacks protection and this PR does not claim otherwise.

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- that base behavior depends on unpinned iteration order, so byte-identity cannot be characterized deterministically;
- that `splice_node_link_spans` cannot move without editing a §5 service file;
- an import cycle requiring additional symbol moves;
- a CommonMark case that appears wrong (report it as a `migrate-union-mention-path` candidate; do not fix it);
- any second independently useful outcome;
- a required path outside §4.

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```
