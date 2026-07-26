---
# Literal Markdown the worker MUST use as the PR-body skeleton.
# The complete checked-in handoff remains authoritative.
pr_body_template: |
  ## Outcome

  The union-supergraph recap projection no longer owns a second Markdown mention
  matcher. Known-entity sidecar spans and alias-store fallback are adapted into
  the surface-neutral CommonMark-safe linker introduced by PR #414, so the
  existing union endpoint cannot splice dmb-node: links inside protected Markdown.

  ## Merge-ready invariant

  For one exact union store, recap document, paragraph-span index, known-entity
  sidecar, and identity context, every union projection field and every mention
  outside CommonMark-protected ranges is byte-for-byte and value-for-value
  identical to the pre-migration projection; a candidate overlapping a protected
  range is left byte-unchanged and omitted from mentions, and
  recap_projection._project_markdown_mentions contains no independent regex
  matcher or direct splicing implementation.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Characterization predates implementation | Git history + committed matrix | base fixture/matrix commit before any production edit | {{TODO: pass/fail + SHAs}} |
  | Existing neutral-linker behavior remains exact | neutral module | original PR #414 characterization suite | {{TODO}} |
  | Non-protected union outputs remain exact | union projection model/service | replay committed base cases with exact full-payload equality | {{TODO}} |
  | Protected alias matches are skipped | neutral linker + union adapter | five CommonMark defect families plus existing protected corpus | {{TODO}} |
  | Protected known-sidecar spans are skipped | located-binding path + union adapter | exact-span cases for code, links, references, autolinks, and destinations | {{TODO}} |
  | Sidecar authority and fail-closed remapping remain exact | union adapter | sidecar-first, unresolved, unique-in-paragraph, and no-global-find tests | {{TODO}} |
  | Alias fallback ordering remains exact | union adapter | longest-first and casefold-equivalent first-win tests | {{TODO}} |
  | Mention identity, offsets, evidence, and redirects remain exact | union projection + identity boundary | projected-slice, evidence-ref, redirect, and diagnostic tests | {{TODO}} |
  | Public endpoint changes only in authorized protected cases | HTTP boundary | focused route fixture comparison | {{TODO}} |
  | Direction and frontend contracts remain untouched | diff boundary | exact changed-path proof; no direction/frontend files | {{TODO}} |
  | Duplicate implementation is gone | source guard | AST/source assertion over `_project_markdown_mentions` | {{TODO}} |

  ## Scope and explicit deferrals
  {{TODO: base/head, characterization commit, actual paths, intentional protected-case diffs, paths outside §4, and successors still false}}

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
  {{TODO: none, or exact missing evidence, baseline failures, waivers, and discovered stop conditions}}
---

# HANDOFF — Migrate the union mention path onto the CommonMark-safe linker

**Created:** 2026-07-26, America/Denver.
**Status:** ACTIVE — dispatch exactly one behavior-hardening capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr420-migrate-union-mention-path.md`
**Implementation base:** `d832a088f1aa62b171f69d59dfa57d17cb5308f8` — merge of PR #419, the atomic doc-sync after PR #416.
**Suggested branch:** `agent/pr420-migrate-union-mention-path`
**Content slug:** `migrate-union-mention-path`

> **Dispatch gate:** Do not edit production code until the worker has read this handoff in full, confirmed the current `origin/main`, inventoried every union mention caller and test, and committed the required pre-change characterization/migration matrix by itself.
>
> This is a deliberate behavior change under the existing union-supergraph projection endpoint. It is not a pure move, not a UI migration, and not a direction-contract change.
>
> This checked-in handoff is the complete authority for the slice. The worker must not compress, replace, or reinterpret it before implementation. The PR description must use the frontmatter skeleton and remain a truthful merge contract; it cannot substitute for this handoff.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Union projection** | `RecapGraphProjection` produced from `UnionSupergraphStore` by `src/graph_memory/projection/recap_projection.py` and exposed by the existing union-supergraph preview route. |
| **Neutral linker** | `graph_memory.projection.markdown_mentions.project_markdown_mentions`, introduced by PR #414, which owns CommonMark protection, surface ambiguity handling, link splicing, and projected offsets without importing graph or surface types. |
| **Known-entity sidecar** | Paragraph-keyed, offset-bearing mention rows supplied by GraphIngest. These rows are authoritative for known nodes and are remapped to exact full-document spans before projection. |
| **Alias fallback** | `UnionSupergraphStore.aliases` matching used only for novel/non-sidecar nodes after known sidecar node IDs are excluded. |
| **Located binding** | A neutral identity binding with an already-resolved exact source span: `surface`, `node_id`, `start_offset`, and `end_offset`. It carries no union, recap, graph-view, evidence, or surface type. |
| **Protected range** | Markdown syntax that must remain byte-unchanged: fenced code, inline code, inline/reference links and images, reference definitions/titles, autolinks, and their destinations. |
| **Authorized difference** | A pre-change link/mention is absent at head because its original candidate span overlaps a protected range. No other output drift is authorized. |
| **Sidecar-only semantics** | Once a node appears in the known-entity sidecar input, alias fallback does not chip another occurrence for that node, even if its sidecar span is unresolved or protected. |
| **First-win alias semantics** | For casefold-equivalent alias keys in the store, the existing stable longest-first iteration chooses the first alias owner; this slice must not reinterpret that input as neutral-linker ambiguity. |
| **Stop condition** | A discovered fact that requires another public contract, changes known-entity authority, changes identity redirect semantics, or forces direction/UI work into this PR. |

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | Product surface changed? | Failure model changed? | Independently testable/revertible? | Decision |
|---|---|---|---|---|---|---|
| Apply CommonMark protection to union alias-store mention matching | Yes | Existing endpoint behavior only | No new screen | Yes | Yes | **Include** |
| Apply the same protection to authoritative known-sidecar exact spans | Yes, but inseparable from one union mention operation | Existing endpoint behavior only | No | Yes | Yes | **Include** under the same invariant |
| Add a surface-neutral located-binding input to the neutral linker | No alone | Additive Python API | No | Enables one matcher | Yes | **Include** as the minimum neutral capability |
| Preserve known-sidecar remap diagnostics and no-global-find behavior | No alone | No | No | Prevents authority regression | Yes | **Include** as mandatory preservation |
| Preserve alias longest-first and first-win behavior | No alone | No | No | Prevents unrelated mention drift | Yes | **Include** as mandatory preservation |
| Remove union-owned regex matching and direct splicing | No alone | No | No | Removes duplicate implementation | Yes | **Include** as required demolition |
| Normalize union direction vocabulary | Yes | Yes — separate union wire contract | Existing consumers | Yes | Yes | Successor: `normalize-union-direction-vocabulary` |
| Migrate Recap/Ingest UI to World Graph recap | Yes | Yes | Yes | Yes | Yes | Successor: PR380B |
| Change known-entity extraction or mention-sidecar generation | Yes | Yes — extraction contract | Indirectly | Yes | Yes | **Reject** from this slice |
| Change identity redirects or `mention_targets_resolved` accounting | Yes | Yes — diagnostics/identity behavior | No | Yes | Yes | **Reject** from this slice |
| Replace the scanner with a Markdown-parser dependency | Yes | Tooling/runtime change | No | Yes | Yes | **Reject**; disproportionate and not authorized |
| Version or rename the union response schema | Yes | Yes | Potentially | Yes | Yes | **Stop condition** requiring operator decision |

**Selected capability:** make the existing union-supergraph mention producer a thin adapter over the PR #414 neutral linker, including exact sidecar spans, while authorizing only the protection-driven disappearance of links that previously corrupted or nested inside Markdown syntax.

**Why sidecar and alias matching belong in one slice:** they compete for ranges in one returned Markdown document and must be spliced exactly once to produce valid projected offsets. Migrating only alias fallback would leave a second unprotected splicing path for sidecar spans; migrating sidecar spans separately would require temporary dual offset ownership. One invariant can govern both because the only newly forbidden output is a link whose original source span overlaps a neutral-linker protected range.

**Named successors, still false after this slice:**

- `normalize-union-direction-vocabulary` — close the separate union wire direction family and update its consumers/fixtures.
- PR380B — migrate Recap/Ingest UI and shared object navigation to the World Graph recap route.
- Any correction to union identity-resolution counters or diagnostics beyond mechanical mapping.

## §1 Mission, invariant, and pre-dispatch critique

### Mission

```text
The union-supergraph projection produces dmb-node links through the same
CommonMark-safe neutral linker as the World Graph recap path, without changing
known-entity authority, alias fallback semantics, identity resolution, evidence,
or any non-mention projection field.
```

### Merge-ready invariant

```text
For one exact union store, recap document, paragraph-span index, known-entity
sidecar, and identity context, every union projection field and every mention
outside CommonMark-protected ranges is byte-for-byte and value-for-value
identical to the pre-migration projection; a candidate overlapping a protected
range is left byte-unchanged and omitted from mentions, and
recap_projection._project_markdown_mentions contains no independent regex matcher
or direct splicing implementation.
```

### Mission falsification test

This is not one slice if implementation must also:

- change `UnionSupergraphEdge.direction`, `UnionSupergraphAdjacencyItem.direction`, or any frontend direction type/fixture;
- change which known-entity sidecar rows are generated or admitted;
- make sidecar resolution fall back to a global document search;
- allow alias fallback for a node represented in the sidecar merely because its sidecar occurrence is protected or unresolved;
- change identity redirects, merged-away filtering, or the meaning/count of `mention_targets_resolved`;
- change mention IDs, evidence-ref policy, response keys, aliases, casing, defaults, or schema version;
- add a UI feature, route, endpoint, cache, telemetry, or product migration;
- modify graph storage or contribution data;
- introduce a general plugin/registry/parser framework.

If any of those becomes necessary, stop and report the smallest split rather than expanding this PR.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every changed path? | Yes. Both sidecar and alias candidates become inputs to one neutral projection operation; the only authorized output difference is protected-range suppression. |
| Why is a direct `project_markdown_mentions(markdown, aliases)` replacement wrong? | The union path gives known sidecar spans priority, excludes those node IDs from fallback, emits union-owned remap diagnostics, attaches node evidence refs, and preserves first-win alias behavior. The existing neutral binding API alone cannot express authoritative exact spans. |
| Highest-risk behavior defect | A protected sidecar occurrence is skipped, then alias fallback links a different occurrence for the same known node, silently weakening sidecar authority. Known sidecar node exclusion must be computed from input rows before protection/remap outcomes and preserved exactly. |
| Highest-risk ordering defect | Feeding all store aliases directly to the neutral ambiguity logic changes casefold-equivalent alias keys from current stable first-win to fail-closed ambiguity. The adapter must preserve current first-win deduplication before constructing neutral bindings. |
| Highest-risk offset defect | Splicing sidecar and alias matches in separate passes causes second-pass coordinates and returned mention offsets to describe different strings. All accepted candidates must be combined and spliced once by the neutral module. |
| Highest-risk protection defect | Protection is applied only to alias regex matches while exact sidecar spans still splice inside links/code, leaving the duplicate bug class alive. Located bindings must use the same protected-range set. |
| Highest-risk scope defect | Touching union direction fields or frontend fixtures because they are adjacent in the same payload. They are explicitly a separate public-contract slice. |
| What compatibility difference is intentional? | Only a link/mention whose original candidate span overlaps protected Markdown disappears; the source bytes stay unchanged. |
| What fact forces a stop? | Need for a graph-specific type in the neutral module; need to alter sidecar generation; inability to preserve first-win semantics; response/schema versioning; or any direction/frontend production path needed for implementation. |

## §2 Context, authority, and exact boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/DECISION-graph-lens-projection-boundary.md`, decision 1 and sequencing entry `migrate-union-mention-path` |
| Repository rules | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, `.cursor/skills/external-agent-pr-loop/SKILL.md`, `.cursor/rules/dungeonbuddy-git-workflow.mdc`; all Python through `uv run` |
| Base revision | `d832a088f1aa62b171f69d59dfa57d17cb5308f8` |
| Predecessor capability | PR #414 (`5c19d433`): surface-neutral linker with the five CommonMark fixes and characterization coverage |
| Most recent contract hygiene | PR #416 (`6410e047`): World Graph nested-view derivation and World-only direction normalization |
| Current duplicate | `src/graph_memory/projection/recap_projection.py::_project_markdown_mentions` |
| Existing route | `GET /api/live/graph-preview/union-supergraph/projection` |
| Exact inputs | `UnionSupergraphStore`, markdown, identity context, optional paragraph text index, optional known-entity sidecar, and optional diagnostics sink |
| Exact mention outputs | projected Markdown, `RecapProjectionMention[]`, and the existing identity-resolution count |
| Other outputs that must remain exact | campaign/session/graph identity, focus, node views, adjacency, suggested expansions, source spans, union identity diagnostics/order, applied assertion IDs, response field names/types/defaults |
| Intentional change | Protection removes candidate links/mentions that overlap protected Markdown ranges |
| Named successor | `normalize-union-direction-vocabulary` |
| Explicit non-goals | UI migration, direction vocabulary, graph facts, identity decisions, evidence authority, extraction matcher, storage, schema version, cache/telemetry |

**Read authoritative inputs in this order before editing:**

1. `Docs/Design/DECISION-graph-lens-projection-boundary.md`
2. This handoff in full
3. `src/graph_memory/projection/markdown_mentions.py`
4. `src/graph_memory/projection/recap_projection.py`
5. `src/graph_memory/union_supergraph/model.py`
6. `src/graph_memory/union_supergraph/projection_identity.py`
7. `apps/live_control_server/services/union_supergraph_projection_adapter.py`
8. `apps/live_control_server/routes/graph_preview.py`
9. `tests/test_markdown_mentions.py`
10. `tests/test_graph_memory_projection_contract.py`
11. `tests/test_graph_memory_pc_mention_matcher.py`
12. `tests/test_graph_memory_union_projection_identity_redirects.py`
13. `tests/test_live_union_supergraph_projection_adapter.py`
14. `tests/test_live_union_supergraph_projection_api.py`
15. repository workflow/review rules

### Authority precedence

1. Accepted graph-lens projection decision
2. This checked-in handoff
3. Existing union projection wire/model contracts and owning tests
4. PR #414 neutral-linker public contract and characterization fixture
5. Current `main` implementation
6. PR descriptions/review handbacks
7. Chat summaries

### Base movement rule

Before implementation:

```bash
git fetch origin
git rev-parse origin/main
git diff --name-only d832a088f1aa62b171f69d59dfa57d17cb5308f8..origin/main
```

Inspect drift touching any §4 path, the union projection route/service, known-entity sidecar contract, or neutral linker. Re-anchor and report any material drift before generating the characterization fixture. Docs-only drift may be recorded without stopping.

### Mandatory caller and behavior inventory

Run before editing:

```bash
git grep -n -E '_project_markdown_mentions|_known_mention_spans_in_markdown|project_markdown_mentions|splice_node_link_spans|dmb-node:' -- \
  src/graph_memory \
  apps/live_control_server \
  tests
```

Classify each relevant hit as:

- neutral mention producer;
- union mention adapter;
- exact known-sidecar source;
- alias fallback source;
- identity redirect post-processing;
- direct splicer consumer that does not locate mentions;
- endpoint/service consumer;
- owning test/fixture.

The PR handback must include the inventory. A second union-owned alias regex or unprotected exact-span splicing path remaining after implementation is merge-blocking.

## §3 Observable paths and adversarial sequences

| Observable path | Current behavior | Required head behavior | Authorized difference? | Owning proof |
|---|---|---|---|---|
| Plain alias occurrence | Alias regex links through `splice_node_link_spans` | Same Markdown, mention IDs/order/offsets/evidence | No | union characterization |
| Repeated aliases | Every non-overlapping occurrence links; offsets describe projected string | Exact same | No | projection contract tests |
| Longer alias overlapping shorter alias | Stable descending-length iteration gives longer surface priority | Exact same | No | adapter ordering test |
| Casefold-equivalent alias keys with different owners | Existing stable iteration gives first matching alias ownership | Preserve first-win; do not emit neutral ambiguity | No | explicit adversarial fixture |
| Known sidecar exact offset | Sidecar span is linked before alias fallback | Same unless protected | Only protected skip | sidecar tests |
| Known sidecar wrong offsets, unique in paragraph | Recovers unique in-paragraph occurrence | Same unless protected | Only protected skip | sidecar tests |
| Known sidecar unresolved/ambiguous paragraph | Emits existing warning and does not global-find | Exact same diagnostic/order; no alias fallback for known node | No | sidecar tests |
| Known sidecar and alias overlap | Sidecar occupies range first | Sidecar remains first; one splice only | No | combined-candidate test |
| Known node has another unprotected occurrence but sidecar occurrence is protected | Existing path may link sidecar in protected syntax | Protected occurrence remains unchanged; other occurrence also remains unlinked because node is sidecar-owned | Yes, protected suppression only | authority adversarial test |
| Alias inside fenced/inline code | Currently linked/corrupted | Byte-unchanged, no mention | Yes | CommonMark matrix |
| Alias inside inline/reference link or image | Currently nested/corrupted | Byte-unchanged, no mention | Yes | CommonMark matrix |
| Alias in reference definition/title | Currently linked/corrupted | Byte-unchanged, no mention | Yes | CommonMark matrix |
| Alias in URI/email autolink | Currently linked/corrupted | Byte-unchanged, no mention | Yes | CommonMark matrix |
| Alias in angle-bracket destination containing spaces | Currently linked/corrupted/missed boundary | Byte-unchanged, no mention | Yes | CommonMark matrix |
| Sidecar exact span in any protected family | Currently spliced because exact spans bypass protection | Byte-unchanged, no mention | Yes | located-binding matrix |
| Existing `[label](dmb-node:old-id)` through active redirect | Post-pass rewrites target and increments redirect count | Exact same | No | identity redirect tests |
| Generated mention for redirected node | Adapter resolves node ID before linking | Exact same durable target; do not change counter semantics | No | identity tests |
| Mention evidence refs | Pulled from final projected node | Exact same list/order | No | projection tests |
| Union identity diagnostics | Sidecar remap and identity diagnostics append in existing order | Exact same, except no new diagnostic for ordinary protected skip | No | full payload fixture |
| Union directions | Existing legacy values remain | Unchanged | No | diff boundary |
| HTTP payload | Current schema/keys | Same keys/types/defaults; only protected markdown/mentions differ | Only protected skip | API test |

### Required adversarial sequences

1. **Protected sidecar, unprotected duplicate occurrence**
   - Sidecar declares the protected occurrence for node A.
   - The same surface appears later in plain prose.
   - Required: neither occurrence is linked; node A remains excluded from alias fallback.
2. **Sidecar range overlaps alias range**
   - Sidecar exact span and alias fallback would both target the same bytes.
   - Required: sidecar mention wins, one link is emitted, and evidence refs come from the final node.
3. **Equal/casefold-equivalent alias keys across different nodes**
   - Store insertion order differs from lexical node-id order.
   - Required: head chooses the same first owner as base and emits no new ambiguity diagnostic.
4. **Long alias and short alias across nodes**
   - Both can match within one phrase.
   - Required: longer alias wins exactly as base.
5. **Known sidecar remap failure with earlier global occurrence**
   - Paragraph text cannot resolve the sidecar span; same surface exists elsewhere.
   - Required: existing unresolved diagnostic; no global link; no alias fallback for the known node.
6. **Multiple candidate classes with earlier splice expansion**
   - Sidecar and alias candidates occur in alternating document order.
   - Required: all returned offsets slice exact `[label](dmb-node:id)` strings after one combined splice.
7. **Identity redirect plus protected source**
   - Candidate targets a merged-away node and occurs in protected syntax.
   - Required: source remains unchanged and no mention/redirect diagnostic is invented for a link that was never produced.
8. **Existing dmb-node link plus new plain mention**
   - Existing link target needs redirect; plain mention targets the survivor.
   - Required: existing link redirect behavior/count remains exact and plain mention links once.

## §4 Files in scope — default-deny allowlist

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Modify | `src/graph_memory/projection/markdown_mentions.py` | Add neutral located-binding input and combine located/free candidates under one protected-range scan and one splice, while preserving existing callers exactly |
| Modify if public export is used | `src/graph_memory/projection/__init__.py` | Export only the new neutral located-binding type if package convention requires it; no union/surface type export |
| Modify | `src/graph_memory/projection/recap_projection.py` | Convert sidecar spans and filtered alias fallback into neutral inputs; mechanically map neutral outputs; delete independent regex matching/direct splicing |
| Add | `tests/fixtures/graph_memory/union_mention_characterization_v1.json` | Commit base outputs and explicit authorized-head matrix before production edits |
| Modify | `tests/test_markdown_mentions.py` | Own neutral located-binding protection, one-splice offsets, and no-surface-import/public-shape tests; retain PR #414 characterization exactly |
| Modify | `tests/test_graph_memory_projection_contract.py` | Own alias-only union projection equality, ordering, repeated mentions, offsets, and evidence refs |
| Modify | `tests/test_graph_memory_pc_mention_matcher.py` | Own known-sidecar priority, remap recovery/failure, protected-sidecar behavior, and sidecar-only semantics |
| Modify | `tests/test_graph_memory_union_projection_identity_redirects.py` | Own redirect behavior, protected redirect case, and unchanged identity diagnostics/counters |
| Modify | `tests/test_live_union_supergraph_projection_adapter.py` | Own manifest/snapshot adapter behavior and full payload comparison where existing fixture infrastructure is required |
| Modify | `tests/test_live_union_supergraph_projection_api.py` | Own existing endpoint response and authorized protected-case wire difference |

### Characterization-first commit rule

The first branch commit after any handoff-only setup must add only:

- `tests/fixtures/graph_memory/union_mention_characterization_v1.json`

It must be generated against the unmodified public `build_recap_graph_projection` path at the resolved base SHA. No production source may change before that commit. The PR must report:

- base SHA;
- fixture commit SHA;
- first production-change commit SHA;
- `git log --oneline` proving fixture commit precedes implementation.

A test scaffold may be added in the next commit; do not mix production edits into the fixture commit.

### Bounded-discovery exception

A new test-only helper or fixture path may be proposed only when an owning §7 proof cannot be expressed with the files above. Before adding it, report:

- exact path;
- why existing test fixtures cannot own the proof;
- whether it captures base behavior or new behavior;
- why it is not direction/UI scope.

Do not silently expand production scope. Any production path outside the allowlist is a stop condition requiring re-briefing.

## §5 Explicit denylist, non-goals, and stop conditions

### Do not modify

- `apps/live-control-ui/**`
- `src/graph_memory/union_supergraph/model.py`
- union direction fixtures or TypeScript union response types
- `src/graph_memory/projection/world_projection.py`
- `src/graph_memory/kernel/world_projection.py`
- `src/graph_memory/projection/world_recap_projection.py`
- `apps/live_control_server/services/world_graph_recap_projection.py`
- known-entity extraction/matcher/schema production modules
- graph storage, contribution, merge, identity-decision, or redirect production modules
- `apps/live_control_server/routes/graph_preview.py`
- `apps/live_control_server/services/union_supergraph_projection_adapter.py`
- `apps/live_control_server/services/graph_gold_review.py`
- `apps/live_control_server/services/graph_authoring_overlay_projection.py`

The existing adapter and route should observe the changed projection behavior through `build_recap_graph_projection`; changing them is not expected or authorized.

### Do not implement

- `normalize-union-direction-vocabulary`;
- PR380B or any visual/product migration;
- new response keys, schema version, route, or endpoint;
- new ambiguity policy for union aliases;
- a global-find fallback for sidecar rows;
- changes to `RecapProjectionMention.evidence_ref_ids`;
- changes to mention ID format;
- changes to `mention_targets_resolved` accounting;
- new diagnostics merely because a valid candidate is protected;
- parser/plugin/registry/framework abstraction;
- broad refactors of `recap_projection.py` beyond mention adaptation.

### Automatic stop conditions

Stop and report before continuing if:

- the neutral module needs to import any `graph_memory.*`, `apps.*`, union, recap, node-view, evidence, or identity type;
- preserving sidecar-only semantics requires changing known-entity sidecar generation;
- preserving alias first-win semantics is impossible without changing `UnionSupergraphStore.aliases` contract;
- a production path outside §4 must change;
- implementation requires changing union direction or frontend files;
- an existing public consumer relies on invalid located spans being spliced;
- protected suppression requires a new wire diagnostic or schema decision;
- exact non-protected output cannot be preserved;
- the base fixture reveals output differences unrelated to protection;
- a current `main` change overlaps the same matcher before characterization is committed.

## §6 Exact implementation contract

### A. Characterization and migration matrix

Add `tests/fixtures/graph_memory/union_mention_characterization_v1.json` with:

```json
{
  "schema": "dmb_union_mention_migration_characterization_v1",
  "base_sha": "<resolved base>",
  "generated_via": "graph_memory.projection.recap_projection.build_recap_graph_projection",
  "cases": []
}
```

Each case must record enough input to reconstruct the public projection and must contain:

- `case_id`;
- `category`: `unchanged` or `protected_skip`;
- Markdown;
- union nodes/aliases/evidence needed by the case;
- paragraph text index when used;
- known-entity sidecar when used;
- identity redirect input when used;
- exact serialized base projection fields relevant to the case;
- explicit expected head Markdown/mentions for `protected_skip` cases;
- a short `authorized_difference` string or `null`.

Minimum corpus:

- at least 30 cases;
- at least 10 sidecar cases;
- at least 10 alias-only cases;
- at least one identity-redirect case;
- at least one evidence-ref case;
- at least one casefold-equivalent first-win case;
- at least one sidecar-protected + later-plain-duplicate case;
- every CommonMark defect family named in §3 for alias candidates;
- every applicable protected family for exact sidecar spans.

Reuse/import the existing PR #414 protected-case corpus where practical; do not manually create a weaker parallel list. The fixture must make deliberate differences reviewable rather than calling the whole payload “changed.”

### B. Neutral located-binding API

Add a neutral model equivalent to:

```python
class LocatedMentionBinding(BaseModel):
    surface: str
    node_id: str
    start_offset: int
    end_offset: int
```

Extend the existing neutral operation compatibly:

```python
def project_markdown_mentions(
    markdown: str,
    bindings: Sequence[MentionBinding],
    *,
    located_bindings: Sequence[LocatedMentionBinding] = (),
) -> tuple[str, list[MarkdownMention], list[MarkdownMentionDiagnostic]]:
    ...
```

Required semantics:

- Existing callers that omit `located_bindings` produce byte-identical output, mentions, diagnostics, ordering, and offsets to PR #414.
- Compute protected ranges once for the original Markdown.
- Process located bindings before free-text bindings, in caller order.
- A located binding is admitted only when:
  - `0 <= start_offset < end_offset <= len(markdown)`;
  - `markdown[start_offset:end_offset] == surface`;
  - it does not overlap a protected range;
  - it does not overlap an earlier admitted located binding.
- Invalid, mismatched, protected, or later-overlapping located bindings are skipped fail-closed. Do not emit a new neutral diagnostic: the union adapter already owns remap diagnostics, and protected suppression is ordinary successful behavior.
- Mark admitted located ranges occupied before scanning free-text bindings.
- Run existing free-text ambiguity and longest-surface behavior unchanged for the remaining unoccupied/unprotected ranges.
- Combine all admitted located and free-text matches and invoke `splice_node_link_spans` once.
- Return neutral mentions sorted in source order, with existing mention ID and projected-offset semantics.
- Keep the neutral module graph- and surface-independent.
- Do not add a second public scanner or a union-specific callback to the neutral module.

### C. Union sidecar adaptation

Preserve `_known_mention_spans_in_markdown` as the owner of:

- paragraph-to-document remapping;
- exact-offset validation;
- unique in-paragraph recovery;
- no-global-find failure behavior;
- identity redirect resolution;
- projectability filtering;
- `known_entity_mention_offset_unresolved` diagnostics and message/order.

It may return its existing tuples and be mapped immediately, or return neutral `LocatedMentionBinding` objects directly. It must not import or invoke protected-range internals.

Compute the set of known sidecar node IDs from all admitted input rows with a non-empty canonical ID, exactly as current behavior does, **before** remap/protection outcomes. Alias fallback must exclude those resolved node IDs even when:

- the sidecar row cannot be remapped;
- the sidecar surface is missing/ambiguous in its paragraph;
- the sidecar span overlaps protected Markdown;
- the sidecar node is otherwise absent from emitted mentions.

This preserves sidecar-only authority.

### D. Union alias adaptation

Build free-text `MentionBinding` values from `store.aliases` while preserving current behavior:

- stable sort by descending alias length only;
- resolve each alias target through the current identity context;
- exclude every resolved known-sidecar node ID;
- exclude absent or non-projectable nodes;
- preserve the first item for each casefolded alias key and discard later casefold-equivalent entries before passing bindings to neutral ambiguity handling;
- do not synthesize node labels or `node.aliases` that were not already present in `store.aliases`;
- do not change alias casing in the emitted label; the actual Markdown match remains the mention label.

The first-win dedupe is required because the current union alias map has one effective winner, while the neutral linker’s ambiguity contract intentionally means something different.

### E. One neutral call and mechanical wire mapping

`_project_markdown_mentions` must become a thin adapter:

- handle `None`/empty Markdown exactly as today;
- build/receive the identity context;
- collect sidecar remap diagnostics exactly as today;
- build located bindings and filtered alias bindings;
- call `project_markdown_mentions` exactly once;
- map neutral mentions to `RecapProjectionMention` using:
  - same `mention_id`;
  - same durable/resolved `node_id`;
  - same `label`;
  - same projected offsets;
  - `evidence_ref_ids=list(store.nodes[node_id].evidence_ref_ids)` in existing order;
- mechanically map any neutral diagnostics to `UnionProjectionIdentityDiagnostic` only if they can arise from admitted union bindings; do not alter sidecar diagnostic wording/order;
- return the existing third tuple value without changing its current semantics.

After implementation, `_project_markdown_mentions` must contain:

- no `re.compile`;
- no `.finditer`;
- no direct `splice_node_link_spans` call;
- no protected-range implementation;
- exactly one neutral `project_markdown_mentions` call.

### F. Identity redirect sequencing

Preserve the existing two stages:

1. sidecar/alias targets resolve through `UnionProjectionIdentityContext` before new links are generated;
2. after mention projection, `resolve_projection_markdown_dmb_node_links` rewrites any pre-existing `dmb-node:` targets in source Markdown and reports its existing count/diagnostics.

Do not move redirect rewriting into the neutral linker. Do not change redirect counts, diagnostics, merged-away filtering, or applied assertion IDs.

### G. Exact authorized difference rule

For every fixture case:

- `category=unchanged`: full serialized projection must equal the base fixture exactly.
- `category=protected_skip`: all non-mention projection fields must equal base; Markdown differs only by retaining the original protected source bytes where base inserted a `dmb-node:` link; the corresponding mention row is absent; all other mentions remain exact including order/offsets/evidence.

No unknown difference may be blessed by updating the fixture at head. If implementation reveals a new difference, classify it against §1. If it is not solely protected suppression, stop.

### H. Preserve response and direction contracts

The following remain exact:

- `RecapGraphProjection` field set and aliases;
- route and service signatures;
- snake_case JSON shape;
- `UnionSupergraphStore` and node/edge models;
- adjacency/suggested-expansion direction values;
- frontend union types and fixtures;
- evidence/source-span/focus behavior;
- known-entity sidecar schema and digest metadata.

## §7 Verification plan and evidence ledger

All Python commands run from repository root using `uv run`.

| # | Guarantee | Owning boundary | Required evidence | Merge-blocking result |
|---|---|---|---|---|
| 1 | Fixture predates implementation | Git history | fixture-only commit then source commit | Fixture generated after/mixed with source edits |
| 2 | Original neutral linker behavior is unchanged | neutral linker | complete PR #414 characterization suite | Any existing case drifts |
| 3 | Located bindings use the same protected ranges | neutral linker | focused located-binding matrix | Any protected span is linked |
| 4 | All candidates are spliced once | neutral linker | alternating located/free offset test + source guard | Offset mismatch or second splice path |
| 5 | Unchanged union cases remain exact | union projection | full serialized fixture replay | Any non-protected drift |
| 6 | Protected alias cases change only as authorized | union projection | CommonMark migration matrix | Extra/missing unrelated change |
| 7 | Protected sidecar cases change only as authorized | union projection | exact-span CommonMark matrix | Protected sidecar still links or fallback links elsewhere |
| 8 | Sidecar remap authority remains exact | union adapter | existing and new remap tests | Global find, changed diagnostic, changed priority |
| 9 | Alias ordering remains exact | union adapter | longest-first + casefold first-win tests | New ambiguity or owner/order drift |
| 10 | Mention fields remain exact | projection model | ID/label/node/order/offset/evidence assertions | Any non-authorized drift |
| 11 | Identity redirect behavior remains exact | identity boundary | redirect suite + protected redirect adversary | Count/diagnostic/target drift |
| 12 | Existing endpoint owns authorized behavior | HTTP route | route fixture comparison | Schema/status/unrelated payload drift |
| 13 | Duplicate union matcher is removed | source boundary | AST/source test | Regex/finditer/direct splice remains |
| 14 | Direction/frontend remain untouched | diff boundary | changed-path proof + literal inventory | Any direction/frontend production path |
| 15 | Broader union projection has no new failures | repository tests | broader filtered suite + baseline protocol | New failure |
| 16 | Diff is clean and bounded | Git/Ruff | allowlist, stat, diff-check, lint | Extra path or static error |

### Required commands

```bash
# Base, scope, and commit order
git fetch origin
git rev-parse origin/main
git merge-base origin/main HEAD
git diff --name-only $(git merge-base origin/main HEAD)...HEAD
git diff --stat $(git merge-base origin/main HEAD)...HEAD
git diff --check
git log --oneline --decorate $(git merge-base origin/main HEAD)..HEAD

# Caller / duplicate-implementation inventory
git grep -n -E '_project_markdown_mentions|_known_mention_spans_in_markdown|project_markdown_mentions|splice_node_link_spans|dmb-node:' -- \
  src/graph_memory \
  apps/live_control_server \
  tests

# Neutral linker, including original PR #414 characterization
uv run pytest tests/test_markdown_mentions.py -q

# Union projection model + sidecar + identity owning suites
uv run pytest \
  tests/test_graph_memory_projection_contract.py \
  tests/test_graph_memory_pc_mention_matcher.py \
  tests/test_graph_memory_union_projection_identity_redirects.py \
  -q

# Service and route boundary
uv run pytest \
  tests/test_live_union_supergraph_projection_adapter.py \
  tests/test_live_union_supergraph_projection_api.py \
  -q

# Cross-boundary focused selection
uv run pytest \
  tests/test_markdown_mentions.py \
  tests/test_graph_memory_projection_contract.py \
  tests/test_graph_memory_pc_mention_matcher.py \
  tests/test_graph_memory_union_projection_identity_redirects.py \
  tests/test_live_union_supergraph_projection_adapter.py \
  tests/test_live_union_supergraph_projection_api.py \
  -q -k "mention or markdown or projection or redirect"

# Broader union regression; baseline protocol applies
uv run pytest tests/ -q -k "union_supergraph and (mention or projection)"

# Static checks
uv run ruff check \
  src/graph_memory/projection/markdown_mentions.py \
  src/graph_memory/projection/recap_projection.py \
  src/graph_memory/projection/__init__.py \
  tests/test_markdown_mentions.py \
  tests/test_graph_memory_projection_contract.py \
  tests/test_graph_memory_pc_mention_matcher.py \
  tests/test_graph_memory_union_projection_identity_redirects.py \
  tests/test_live_union_supergraph_projection_adapter.py \
  tests/test_live_union_supergraph_projection_api.py
```

If `src/graph_memory/projection/__init__.py` is unchanged, omit it from the Ruff command and record that no package export was needed.

### Required exact assertions

At minimum, automated evidence must prove:

- fixture `base_sha` equals the actual characterization base;
- fixture commit precedes the first production edit;
- original 68+ neutral characterization cases remain exact;
- neutral public API still imports no graph/surface modules;
- located binding plain prose links with exact projected offsets;
- located binding in each protected family is skipped;
- invalid/mismatched located binding fails closed without new diagnostic;
- located binding occupies its range before free-text matching;
- alternating sidecar/alias mentions all slice exact returned link strings;
- alias-only unchanged cases equal base payload exactly;
- known-sidecar unchanged cases equal base payload exactly;
- unresolved sidecar emits the exact existing diagnostic and never global-finds;
- a protected sidecar node does not alias-link a later plain occurrence;
- longest alias remains the winner;
- casefold-equivalent alias keys retain base first owner and produce no ambiguity diagnostic;
- mention evidence refs equal the final node evidence refs exactly;
- existing `dmb-node:` redirect behavior/count remains exact;
- generated mention IDs/labels/node IDs/order remain exact outside protected cases;
- no direct regex/finditer/splicer remains in `_project_markdown_mentions`;
- union direction literals/fields and frontend files are absent from the diff;
- HTTP response status/schema/field set remain exact;
- protected-case payload differs only in Markdown and corresponding mention rows.

### Baseline failure protocol

If any required command is nonzero:

1. run the exact command at the merge base in a clean worktree;
2. record base/head exit codes and counts separately;
3. compare exact failing test IDs and error classes/messages;
4. prove zero new failures;
5. never call a nonzero command green;
6. obtain an explicit operator waiver if a hard acceptance gate remains red.

A baseline waiver for another PR or another command does not automatically apply here.

### Manual/dogfood proof

No new product screen is authorized. Manual proof is limited to the existing union endpoint and does not replace automated route evidence.

Use a deterministic test fixture or existing verified run containing:

- one plain alias occurrence that should link;
- one alias or sidecar occurrence inside protected Markdown that must remain unchanged;
- at least one known-sidecar node;
- one existing `dmb-node:` link if a redirect fixture is available.

Request:

```http
GET /api/live/graph-preview/union-supergraph/projection
```

Record exact request identity, store/run artifact, response status, and the relevant Markdown/mention slices. Do not use or paste campaign-private prose into the handback when a synthetic fixture proves the same contract.

## §8 Required implementation handback and PR-body ledger

The PR description must remain synchronized with the handoff and include:

- exact base SHA, head SHA, merge-base SHA;
- fixture commit SHA and first production commit SHA, with commit-order proof;
- actual changed-path list and any bounded-discovery exception;
- caller/implementation inventory;
- count of characterization cases by category and input source;
- exact intentional protected-case differences;
- proof that every unchanged case is full-payload equal to base;
- neutral public API change and why it remains surface-neutral;
- sidecar authority and alias first-win mapping rules actually implemented;
- every §7 command, exit code, counts, and provenance;
- baseline failure comparison and explicit waivers, if any;
- source guard proving no duplicate matcher/direct splice remains;
- confirmation that union direction/frontend paths are absent;
- stop conditions encountered;
- named successors still false:
  - `normalize-union-direction-vocabulary`;
  - PR380B;
  - identity counter/diagnostic corrections.

Do not say “behavior unchanged.” The correct statement is:

```text
Behavior is exact outside protected Markdown; protected candidates are now
left unchanged and omitted from mentions by design.
```

## §9 Reviewer rubric

A reviewer should request changes if any answer below is “no.”

### Invariant and behavior

- Does one exact input produce full-payload equality to base for every unchanged characterization case?
- Are all deliberate differences limited to candidates overlapping protected Markdown ranges?
- Do protected source bytes remain exactly unchanged?
- Are corresponding protected mention rows absent rather than relocated?
- Are all remaining mention IDs, labels, node IDs, order, offsets, and evidence refs exact?

### Sidecar authority

- Are known sidecar rows still remapped and diagnosed by the union adapter rather than the neutral module?
- Is global document search still forbidden after remap failure?
- Are known sidecar node IDs excluded from alias fallback even when unresolved or protected?
- Does sidecar priority win when sidecar and alias candidates overlap?

### Alias compatibility

- Does alias input still come only from `store.aliases`?
- Is stable descending-length behavior preserved?
- Are casefold-equivalent aliases deduped first-win before neutral ambiguity handling?
- Is no new union ambiguity policy introduced?

### Neutral capability

- Is located-binding support graph/surface-neutral?
- Does it reuse one protected-range scan and one splice?
- Do original PR #414 characterization cases remain exact?
- Are invalid located bindings skipped fail-closed without expanding diagnostics?

### Demolition and scope

- Does `_project_markdown_mentions` contain no regex matcher, `.finditer`, protected-range scanner, or direct splicer call?
- Is there exactly one neutral linker call for union mention generation?
- Are route/service signatures and response schema unchanged?
- Are union direction, frontend, World Graph, extraction, storage, and identity production files absent from the diff?
- Was the fixture committed before implementation?
- Is every nonzero gate reported honestly under the baseline protocol?

## Successor refinement — not part of this handoff

`normalize-union-direction-vocabulary` remains a separate public-contract slice.

Its future handoff must independently inventory and decide the wire contract across:

- `UnionSupergraphEdge.direction`;
- `UnionSupergraphAdjacencyItem.direction`;
- projected `GraphProjectionAdjacencyCandidate.direction` and suggested expansions;
- TypeScript `UnionSupergraphProjectionResponse` and its consumers;
- Plan/Graph Review fixtures, especially `unionSupergraphFixture.ts`;
- persisted/raw versus presentation vocabulary boundaries.

It must choose and prove one closed union presentation vocabulary, define compatibility/versioning for current consumers, and remove translations at the correct boundary. It does not depend on mention migration and must not share this PR, its fixture, or its merge-ready invariant.
