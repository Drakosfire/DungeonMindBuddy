---
pr_body_template: |
  ## Handoff pointer
  - Conversation: Kernel Targeted Edge Assertion Correction
  - Flow / agent: BUILD
  - Direction: DESIGN → CODE
  - Handoff: Docs/Plans/HANDOFF-kernel-targeted-edge-assertion-correction.md
  - PR / branch: build/governed-edge-assertion-correction

  ## Verification pointer
  - Base/head: record exact implementation base and head in review handback
  - Changed paths: only §4 allowlist plus any explicitly exercised bounded-discovery path
  - Verification: execute every §7 command and report exact results

  The checked-in handoff, cumulative code diff, nano commits, and independently
  rerun verification are the review contract. The PR description is transport
  metadata only. Document sync is a separate operation.
---

# HANDOFF — governed targeted structural edge-assertion correction

**Created:** 2026-08-09.  
**Status:** BLOCKED ON HANDOFF DOC MERGE — dispatch only after this handoff is merged to `main`.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-kernel-targeted-edge-assertion-correction.md`  
**Conversation name:** `Kernel Targeted Edge Assertion Correction`  
**Flow / agent:** `BUILD`  
**Handoff direction:** `DESIGN → CODE`  
**Design agent:** DungeonBuddy design steward — 2026-08-09  
**Code agent:** fresh BUILD code agent using the same conversation name  
**PR title:** `BUILD: publish governed edge assertion correction`

> **Dispatch gate:** Before the first code change, record the exact `origin/main` SHA, prove it is a descendant of re-anchored main `c6eb77e5751f0d924f0cfc0147d5e919d58c3ae3`, and prove this canonical handoff exists on that base. If the active tracker no longer names targeted assertion correction as next, stop and return to design.
>
> This checked-in handoff is the complete implementation authority for the slice. Do not replace the target correction with whole-contribution supersession, direct snapshot mutation, projection special-casing, source prose edits, or an Eldyrwild-specific reversal rule.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Target assertion support** | The exact pair `(target_contribution_id, target_assertion_id)` whose source contribution currently supplies the one active durable support being corrected. |
| **Correction contribution** | A human-authored `GraphContribution` whose durable body binds one exact target assertion support to one exact accepted replacement edge assertion. |
| **Contradicted support** | Historical support that remains attributable to its original contribution/evidence but is no longer current graph authority because an active governed correction contradicts it. |
| **Replacement assertion** | The new accepted structural edge assertion supplied by the correction contribution. |
| **Structural edge correction** | A correction that changes edge identity/shape — e.g. direction, endpoint, or predicate — and therefore materializes a distinct edge object rather than rewriting the old edge object in place. |
| **Current authority** | An assertion support with `support_state == "supported"` and active contribution support, as already consumed by World Graph projection. |
| **Historical authority** | Immutable prior revisions plus durable contribution/evidence lineage proving what the source or earlier authoring asserted, even when that assertion is no longer current. |

## Agent flow and nano-commit contract

Use `BUILD` for this implementation. Keep the work in nano commits. A recommended story shape is:

1. durable correction/support models and deterministic identity;
2. correction publication + exact-support transition;
3. replay + lifecycle fail-closed guards;
4. adversarial and regression proofs;
5. only if needed, one narrowly justified projection compatibility fix from the bounded-discovery exception.

Do not encode a PR number into the title, branch name, public identifiers, or design authority.

## Review and doc-sync contract

Review the cumulative diff and nano-commit sequence against this handoff. The implementation PR must not update the roadmap/tracker/handoff status as part of a code fix. After merge, document synchronization is a separate operation.

## §1 Mission and merge-ready invariant

**Mission:** Kernel callers can publish one governed structural correction to one durable edge assertion so that a mistaken relationship can be replaced without superseding unrelated assertions from the source contribution.

**Merge-ready invariant:** Against one exact expected parent revision, one active target edge support is atomically moved out of current authority and one human-authored replacement edge assertion becomes current in the same immutable descendant revision, while every unrelated assertion/support/provenance remains unchanged, the original contribution and evidence remain historical authority, stale or ambiguous writes fail closed, exact retry does not duplicate state, and pinned contribution replay reconstructs the same corrected projection.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes**, if this slice is structural **edge** correction only. Generic node/attribute/alias/evidence correction would require different materialization rules and is explicitly split. |
| What adversarial sequence is most likely to falsify it? | A source contribution publishes edge X plus unrelated assertions Y/Z; a correction of X accidentally uses contribution-level supersession and retires Y/Z, or mutates the old edge object so pinned old revisions/replay disagree. |
| Would the proposed §7 evidence actually detect that failure? | **Yes.** The owning synthetic proof fingerprints Y/Z support+provenance before/after, projects both old/new revisions, reruns pinned rebuild, and exercises stale/retry paths. |
| Which owning boundary is easiest to under-test? | Replay and lifecycle interaction: a live correction can look right while `rebuild_from_contributions()` silently resurrects X or loses the correction linkage. |
| What fact would force this slice to stop or split? | If a replay-safe structural edge correction cannot be represented as durable contribution input plus assertion-support lineage without a parallel mutable authority store, or if making it correct requires generic node/attribute correction semantics. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` on re-anchored main after PR #532 |
| Repository rules | Public graph writes cross `graph_memory.kernel`; immutable revisions; expected-parent/CAS publication; contributions/evidence are durable/replayable authority; agents are not privileged writers |
| Design anchor | `377ca60e146df2c9a801ebcb864a9dd9b0183dbe` (PR #531 merge) with docs re-anchor merged as `c6eb77e5751f0d924f0cfc0147d5e919d58c3ae3` |
| Implementation base | Exact `origin/main` SHA after this handoff is merged; must be a descendant of `c6eb77e5751f0d924f0cfc0147d5e919d58c3ae3`, contain this file, and be recorded before implementation |
| Predecessor contract | `GraphContribution` / `GraphContributionAssertion`; `DurableAssertionSupport`; `merge_contribution_to_revision`; `supersede_graph_contribution`; `retract_graph_contribution`; revision-bound contribution replay manifest; active-support projection integrity |
| Exact input consumed | One correction contribution containing exactly one accepted replacement **edge** assertion and exactly one durable correction link to an exact active `(target_contribution_id, target_assertion_id)` |
| Named successor | `eldyrwild-lysandra-threat-direction-correction` |
| What remains false | No Eldyrwild relationship is changed; effective conformance remains `294 represented / 52 residual`; no node/attribute/alias/evidence correction; no generic Graph Review UI authoring; no correction-contribution retraction/supersession lifecycle |
| Explicit non-goals | DungeonMind vocabulary changes; source prose rewrite; global edge reversal; contribution-wide source replacement; identity migration; compound decomposition; UI/routes; conformance-count movement; cleanup unrelated to this Kernel seam |

Read authoritative inputs in order before changing code:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
3. this handoff
4. `src/graph_memory/evidence/assertion_support.py`
5. `src/graph_memory/kernel/contribution_models.py`
6. `src/graph_memory/kernel/contributions.py`
7. `src/graph_memory/kernel/contribution_merge.py`
8. `src/graph_memory/kernel/contribution_rebuild.py`
9. `src/graph_memory/kernel/world_projection.py` — read for consumer behavior; do not edit unless the bounded-discovery gate is triggered
10. `tests/test_graph_kernel_contribution_merge.py`
11. `tests/test_graph_kernel_contribution_rebuild.py`

### Why contribution supersession is not the primitive

Existing `supersede_graph_contribution()` removes one contribution's support from every assertion it supports. The owning test intentionally proves that a source contribution containing X and Y can be superseded by a replacement containing only X, leaving Y unsupported. That is correct **source replacement** behavior and must not be weakened.

This slice therefore introduces assertion-support correction as a distinct governed operation. Do not special-case `supersede_graph_contribution()` to mean two different things.

### Required granularity

The correction target is not merely `assertion_id`. Assertion IDs may have multiple active supporting contributions. This first correction contract is legal only when the target assertion has **exactly one active supporting contribution**, and it must equal `target_contribution_id`.

If the same assertion has multiple active source supporters, fail closed. Resolving independent-source disagreement is a separate adjudication capability; this PR must not silently invalidate all sources or create conflicting canonical edges.

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---:|---|
| Construct durable correction contribution | No typed assertion-level correction linkage | Durable contribution body binds one exact target support to one exact replacement assertion; identity/digest change when linkage changes | Yes | contribution models/factory |
| Publish correction against exact head | Only merge, whole-contribution supersede, or retract exist | Validate target and replacement, transition target support, apply replacement, publish exactly one descendant with expected-parent CAS | Yes | Kernel correction operation + world revision publish |
| Read old pinned revision | Old edge is current | Remains byte/semantically unchanged and still projects old edge | Yes | immutable revision + projection |
| Read corrected revision | No correction semantics | Old edge is non-current; replacement edge is current | Yes | support authority + projection |
| Inspect historical source | Whole-contribution paths preserve ledger but assertion-level correction absent | Original contribution/evidence remains loadable and attributable; correction does not rewrite source bytes | Yes | contribution/evidence store |
| Target assertion has multiple active supporters | Existing support model permits it | Correction fails closed; no support, ledger, revision, or head mutation | Yes | correction validation |
| Target contribution/assertion missing or not active | No assertion-level path | Fail closed before publish | Yes | correction validation |
| Replacement reuses target edge object identity | Existing edge merge may retain structural fields | Fail closed; structural correction must materialize a distinct edge object | Yes | correction validation/materialization |
| Stale expected parent | Existing publication CAS can reject | Fail closed with no head movement and no active correction effect | Yes | world revision publish |
| Exact retry after success | Merge has idempotent contribution behavior; no correction behavior | No second revision, no duplicate support, no duplicate contradicted lineage | Yes | correction operation |
| Pinned rebuild | Replays contribution lifecycle only | Replays correction contribution deterministically and fingerprints equivalent to corrected revision | Yes | contribution rebuild |
| Retract/supersede correction contribution | Existing generic lifecycle APIs would not undo target contradiction | **Fail closed in this slice** with stable diagnostic; do not publish partial lifecycle | Yes | contribution lifecycle API |
| Retract/supersede a contribution currently targeted by an active correction | Existing lifecycle has no correction-aware reversal | **Fail closed in this slice**; correction/source lifecycle composition is deferred | Yes | contribution lifecycle API |

### Ordered failure sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Publish source contribution A with wrong edge X + unrelated Y/Z → correct X | X becomes historical/non-current, X' current, Y/Z support and provenance unchanged | §7 synthetic atomicity proof |
| Prepare correction on parent P → another write advances head → submit correction with expected P | No correction revision; head remains newer revision; target support unchanged | §7 stale-parent proof |
| Submit exact correction C successfully → submit exact C again | Head/revision count unchanged on retry; support lineage contains each ID once | §7 idempotency proof |
| Target X is supported by A and B → attempt correction naming A | Fail closed; neither A nor B is contradicted; replacement not published | §7 multi-support proof |
| Correct X → pinned rebuild corrected revision | Rebuilt fingerprint equals corrected revision; old edge remains non-current and X' current | §7 replay proof |
| Correct X → try retracting correction C | Lifecycle API refuses before publication; corrected head remains authoritative | §7 lifecycle-guard proof |
| Correct X → try superseding/retracting target contribution A | Lifecycle API refuses before publication; no mixed lineage state is produced | §7 lifecycle-guard proof |
| Tamper correction target/replacement linkage in durable contribution file after publish → rebuild pinned corrected revision | Source payload digest mismatch / integrity failure; no invented correction authority | §7 integrity proof |

## §4 Files in scope (allowlist)

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Modify | `src/graph_memory/evidence/assertion_support.py` | Add durable contradicted-contribution lineage while preserving backward-compatible defaults |
| Modify | `src/graph_memory/kernel/contribution_models.py` | Add the typed correction-link model and additive correction field on `GraphContribution` |
| Modify | `src/graph_memory/kernel/contributions.py` | Bind correction linkage into deterministic contribution identity/source payload and construct canonical correction contributions safely |
| Modify | `src/graph_memory/kernel/contribution_merge.py` | Validate/apply one targeted correction, guard incompatible lifecycle operations, and publish one CAS-fenced descendant |
| Modify | `src/graph_memory/kernel/contribution_rebuild.py` | Replay active correction contributions deterministically from revision-bound contribution authority |
| Modify | `src/graph_memory/kernel/__init__.py` | Export the correction model/factory/operation through the legal Kernel public boundary |
| Modify | `tests/test_graph_kernel_contribution_merge.py` | Own atomicity, granularity, stale-parent, retry, lifecycle-guard, and historical-lineage proofs |
| Modify | `tests/test_graph_kernel_contribution_rebuild.py` | Own pinned replay equivalence and tamper/integrity proofs |

**Bounded discovery exception:**

```text
Directory: src/graph_memory/kernel/world_projection.py
Maximum additional paths: 1
Allowed path kinds: the existing World Graph projection implementation only
Decision rule for including one: only if a failing owning-boundary test proves that a correctly persisted `contradicted` edge support is still projected as current despite the existing active-support / unsupported-object rules. Any new projection policy, API, or special-case edge reversal is a stop condition.
```

No other production path is authorized. If another file is required, stop and report why the invariant cannot be proved inside this allowlist.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| Eldyrwild graph data, source corpus, adjudication fixtures, source seals | This PR proves the primitive synthetically; the Lysandra successor owns the first real mutation |
| `apps/**` | No UI/server/product workflow is required to prove Kernel correction semantics |
| DungeonMind dependency/vocabulary/conformance adapters | The target defect is Buddy write/history semantics, not vocabulary admission |
| Generic node correction | Existing node materialization has correction-sensitive fingerprint and in-place object semantics requiring a separate design |
| Attribute/alias/evidence correction | Different graph-object ownership and materialization rules; separate invariant |
| Compound relationship decomposition | Creates multiple assertions and different authority semantics |
| Identity correction/merge/split | Existing identity-decision subsystem owns this |
| Correction contribution retraction/supersession | Requires explicit reversal/composition semantics; this slice fails closed instead |
| Source contribution lifecycle while actively targeted by correction | Same reason; fail closed until a correction-lifecycle successor exists |
| Graph Review correction UI | Human surface authoring is a separate product slice after the Kernel contract exists |
| Roadmap/tracker updates | Separate doc-sync after implementation review/merge |

## §6 Implementation contract and conditional matrices

### Durable correction shape

The exact class/function names may follow repository naming conventions, but the persisted semantics must be equivalent to:

```text
GraphContribution
  source_kind = graph_review_authored_assertion
  authored_by = non-blank human/operator identity
  accepted_assertions = [replacement_edge_assertion]
  assertion_corrections = [
    {
      correction_kind: "contradicts_and_replaces",
      target_contribution_id: <exact durable contribution id>,
      target_assertion_id: <exact canonical assertion id>,
      replacement_assertion_id: <exact canonical accepted assertion id>
    }
  ]
```

`assertion_corrections` must default to `[]` so historical contribution records continue to validate unchanged.

`DurableAssertionSupport` must gain durable contradicted-contribution lineage equivalent to:

```text
contradicted_contribution_ids: list[str] = []
```

When the only active support `(A, X)` is corrected:

```text
X support:
  active_contribution_ids: []
  contradicted_contribution_ids: [A]
  support_state: "contradicted"
  aggregate source/evidence history: retained

X' support:
  active_contribution_ids: [correction contribution C]
  support_state: "supported"
```

Do not relabel A as `superseded` or `retracted`; the source contribution itself remains active because its unrelated assertions remain current.

### Correction contribution validity

The correction operation must reject before publication unless all are true:

- correction contribution is for the requested world;
- `source_kind == "graph_review_authored_assertion"`;
- `authored_by` is non-blank;
- exactly one correction link exists;
- exactly one accepted assertion exists and it is the linked replacement;
- replacement `assertion_kind == "edge"` and `acceptance_state == "accepted"`;
- target contribution exists, is active, and contains the exact target assertion in its accepted assertions;
- target assertion `assertion_kind == "edge"`;
- target support is `supported` with exactly one active contribution, equal to `target_contribution_id`;
- target and replacement assertion IDs are different;
- target/replacement campaign scope, visibility, epistemic kind, and temporal scope are unchanged in this first structural-correction contract;
- replacement materializes a distinct edge object identity; do not reuse the old `edge_id` to attempt in-place structural mutation;
- correction contribution does not also carry contribution supersession, identity decisions, unresolved mentions, or a second accepted fact;
- correction linkage is part of deterministic contribution identity and the lifecycle-neutral revision-bound source digest.

Provenance may cite the original evidence, a human-authored correction artifact, or both according to existing contribution provenance rules, but the correction must never rewrite the original source artifact/evidence payload to make it agree.

### Public operation

```text
Input:
  root
  world_id
  correction contribution containing one exact correction link
  expected_parent_revision_id

Output:
  existing ContributionMergeResult contract (or a strictly additive compatible extension)
  naming the contribution/revision/accepted replacement and stable failure diagnostics

Invariant:
  same as §1

Failure behavior:
  stale parent → no head mutation
  missing/inactive/ambiguous target → no correction mutation
  multiple active target supporters → no correction mutation
  invalid replacement or reused edge object identity → no correction mutation
  contribution/revision integrity error → fail closed

Replay / idempotency:
  same exact correction input after success → no second revision or duplicate lineage
  changed target/replacement/linkage → distinct contribution identity
  pinned replay → derives correction from revision-bound contribution manifest + source digest, never caller-injected semantic authority

Trust boundary:
  Verifies: exact contribution/assertion IDs, target active support, correction shape, provenance integrity, expected parent, durable contribution digest, replacement materialization
  Records or trusts without proving: the human semantic judgment that the replacement fact is correct; that judgment is represented by `graph_review_authored_assertion` authority, not inferred by the Kernel
```

### Commit model

```text
Commit point:
  successful `publish_world_graph_revision` / equivalent existing atomic head advancement

Before commit:
  correction contribution may be durably staged according to existing contribution-write conventions, but it must not become active graph authority

After commit:
  one immutable descendant revision contains both the target-support contradiction and replacement support; replay manifest/digest bind the correction contribution

Truthful result after a post-commit failure:
  if publication is known to have succeeded, do not retry semantic mutation blindly; exact retry must discover/no-op against the already-applied correction rather than publish another descendant
```

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| correction publish | require existing world/head + contribution ledger | one descendant revision | fail closed, no fallback | fail closed | fail closed | expected-parent mismatch blocks | exact retry no-op; changed correction gets distinct identity |
| target lookup | exact contribution + assertion IDs | one active support | fail closed | fail closed | fail closed | inactive/superseded/retracted target blocks | no label/edge-shape fallback |
| old pinned projection | exact old revision | old edge remains | normal projection behavior | existing projection error | existing integrity error | pin is immutable | deterministic |
| corrected projection | exact new revision | replacement current; contradicted old edge non-current | normal projection behavior | existing projection error | existing integrity error | pin is immutable | deterministic |
| pinned rebuild | revision-bound replay manifest/digests | equivalent fingerprint | fail if required contribution missing | fail closed | digest/integrity mismatch | never substitute current head lifecycle | deterministic |
| lifecycle mutation touching active correction relation | existing contribution record/support map | **not supported** | n/a | fail closed | fail closed | refuse before publish | successor required |

No fallback source is permitted for target identity or correction semantics.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Target contribution ID | Exact durable ID | missing/wrong-world/inactive → fail | No |
| Target assertion ID | Exact canonical ID inside target contribution and support map | missing/mismatch → fail | No |
| Replacement assertion ID | Exact canonical ID of the sole accepted replacement assertion | mismatch/rekey ambiguity → fail | No |
| Target edge object ID | Derived from durable target support/assertion only | must not be accepted as substitute for assertion identity | No |
| Replacement edge object ID | Must be distinct for structural correction | reuse of target object → fail | No |
| Label / predicate / endpoint search | Not an identity mechanism | prohibited | No |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| Store correction contribution | GraphContribution with additive correction link | target/replacement/linkage survive exact JSON round trip and source digest | same body → same deterministic identity | old records parse with empty correction list | correction-contribution lifecycle reversal not implemented here |
| Publish correction | immutable World Graph revision + support lineage + replay manifest | corrected revision reloads with same support states/object identities | exact retry publishes nothing new | no rewrite of prior revisions | existing world-head rollback is not a substitute for correction lifecycle and is not expanded here |
| Rebuild corrected revision | contribution ledger + pinned manifest/digests | canonical fingerprint equals pinned corrected revision | deterministic | historical contributions without corrections replay unchanged | active correction remains active; lifecycle composition deferred |

### D. Predecessor-to-consumer mapping

**Grounding source:** current Kernel models/functions at the implementation base; no invented fixture vocabulary.

| Predecessor field / outcome | Real shape and optionality | Consumer field / behavior | Transformation | Proof fixture/test |
|---|---|---|---|---|
| `GraphContribution.accepted_assertions` | list of canonical `GraphContributionAssertion` | correction replacement | exactly one accepted edge assertion referenced by correction link | merge tests |
| `GraphContribution.source_kind` | includes `graph_review_authored_assertion` | correction authority class | must equal human-authored source kind | contract tests |
| `GraphContribution.authored_by` | optional today | correction authorization provenance | required non-blank for correction contribution | validation tests |
| `DurableAssertionSupport.active_contribution_ids` | list; multiple support is legal | target granularity | must contain exactly one ID matching correction target | multi-support failure test |
| `DurableAssertionSupport.support_state` | `supported/unsupported/contradicted/retracted` | current projection authority | corrected target becomes `contradicted` when its only active support is removed | projection + support assertions |
| per-contribution evidence/source maps | active-contribution provenance maps | unchanged unrelated lineage | Y/Z maps remain exact; target active map entry leaves current support while aggregate history/source records remain | atomicity proof |
| contribution replay manifest | ordered contribution IDs + lifecycle status + source digest | pinned replay | correction contribution remains ordinary active replay member whose durable body carries correction link | rebuild test |
| projection active-support rule | only `supported` + active contribution authority is admitted | corrected relationship view | old contradicted edge omitted; replacement admitted | old/new pinned projection proof |

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| One assertion corrected without collateral source loss | Kernel merge/support | adversarial contract | synthetic A contains edge X + unrelated Y/Z; publish correction X→X' | X contradicted, X' supported, Y/Z support/provenance exactly unchanged | any Y/Z support/provenance drift |
| Whole-contribution supersession semantics remain unchanged | Kernel merge | regression | existing supersession tests | prior tests still prove source replacement retires unsupported sibling assertions | modifying supersession semantics to fake correction |
| Multi-source ambiguity fails closed | Kernel correction validation | adversarial | support same X from A+B, attempt correction naming A | no head move, no replacement, neither support invalidated | correction silently picks/invalidates sources |
| Old revision preserves old truth | revision/projection | regression | project parent revision after correction publish | X still current in old pin | old revision/store bytes or projection change |
| Corrected revision projects only corrected structural edge when target had sole support | support/projection | contract | project new revision | X non-current; X' current | both old+new current or neither current |
| Original source/evidence remains historical authority | contribution/evidence store | contract | reload A + evidence after correction | bytes/semantic payload unchanged; source/evidence still resolvable | source rewrite/deletion |
| Stale parent is fenced | world publication | adversarial | advance head between prepare and correction publish | correction not published; newer head unchanged | stale write advances head |
| Exact retry is idempotent | correction operation | adversarial | call exact correction twice | one correction contribution authority, one corrected revision/head transition, no duplicate lineage | second descendant or duplicate IDs |
| Correction linkage is digest-bound | contribution digest/rebuild | integrity | mutate target/replacement link in stored contribution then pinned rebuild | digest/integrity failure | replay accepts tampered semantic authority |
| Pinned rebuild reproduces corrected revision | rebuild | contract | `rebuild_from_contributions(... compare_revision_id=<corrected>)` | equivalent canonical fingerprint success | corrected live head cannot replay exactly |
| Correction lifecycle unsupported paths fail closed | contribution lifecycle APIs | adversarial | try retract/supersede correction contribution and try retract/supersede actively targeted A | no publication; corrected state unchanged | partial lifecycle mutation |
| Historical no-correction contributions remain compatible | model/load/rebuild | regression | existing Kernel contribution/rebuild suite | old contribution fixtures load/replay unchanged | schema migration required for old records |
| No Eldyrwild semantic movement | DungeonMind effective conformance | regression | run current adjudication/effective-conformance tests only; do not publish live graph | anchor remains `294/52`; fixture/source seals unchanged | this PR changes real Eldyrwild graph/conformance state |

Run and record exact results for at least:

```bash
uv sync --locked

uv run ruff check \
  src/graph_memory/evidence/assertion_support.py \
  src/graph_memory/kernel/contribution_models.py \
  src/graph_memory/kernel/contributions.py \
  src/graph_memory/kernel/contribution_merge.py \
  src/graph_memory/kernel/contribution_rebuild.py \
  src/graph_memory/kernel/__init__.py \
  tests/test_graph_kernel_contribution_merge.py \
  tests/test_graph_kernel_contribution_rebuild.py

uv run pytest tests/test_graph_kernel_contribution_merge.py -q
uv run pytest tests/test_graph_kernel_contribution_rebuild.py -q
uv run pytest tests/test_graph_kernel_contribution_merge.py tests/test_graph_kernel_contribution_rebuild.py -q

uv run pytest \
  tests/test_dungeonmind_relationship_adjudication_continuity.py \
  tests/test_dungeonmind_relationship_effective_conformance.py -q

git diff --check
git diff --stat <implementation-base>...HEAD -- \
  src/graph_memory/evidence/assertion_support.py \
  src/graph_memory/kernel/contribution_models.py \
  src/graph_memory/kernel/contributions.py \
  src/graph_memory/kernel/contribution_merge.py \
  src/graph_memory/kernel/contribution_rebuild.py \
  src/graph_memory/kernel/__init__.py \
  tests/test_graph_kernel_contribution_merge.py \
  tests/test_graph_kernel_contribution_rebuild.py

git diff --name-only <implementation-base>...HEAD
```

If the bounded projection exception is used, add that path to the focused `ruff`/diff commands and record the exact failing proof that justified it.

### Minimal live / dogfood proof

`Not applicable — this is intentionally a synthetic Kernel capability slice. The first real-world proof is the named Lysandra successor. Mutating Eldyrwild here is a merge blocker, not extra confidence.`

### Baseline failure protocol

For any required command already failing on the exact implementation base:

- rerun the same command on base and head;
- report base/head counts and exact failing tests;
- do not call the gate green;
- request an explicit operator waiver if the failure blocks acceptance.

## §8 Required review handback

The review handback must include:

1. Exact PR URL or branch/head SHA.
2. §1 Mission and merge-ready invariant copied exactly.
3. Exact implementation base SHA and proof it contains this handoff.
4. §7 evidence ledger with produced results and provenance.
5. Nano-commit list and each discrete fix/proof story.
6. Actual changed paths and focused diff stat.
7. Every required command and exact result.
8. Old/new synthetic revision IDs used by the atomicity proof.
9. Target contribution/assertion/replacement IDs from the synthetic proof.
10. Before/after support payloads for X, Y, and Z showing collateral preservation.
11. Pinned rebuild equivalence result.
12. Stale-parent and exact-retry results.
13. Multi-source fail-closed result.
14. Lifecycle-guard results for both correction contribution and targeted source contribution.
15. Confirmation that Eldyrwild source graph, adjudication fixture, and effective `294/52` state were not mutated.
16. Baseline failures and operator waivers; `none` when none exist.
17. Paths outside §4; `none` or a stop report.
18. Stop conditions encountered and resolution; `none` when none exist.
19. Named successor still false: `eldyrwild-lysandra-threat-direction-correction`.
20. Confirmation that the checked-in handoff was implemented without compressed or omitted constraints.

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true:

- [ ] Exactly one independently useful capability was delivered: governed structural edge-assertion correction.
- [ ] The target is exact `(contribution_id, assertion_id)` authority; there is no label/predicate/edge-ID fallback.
- [ ] A target with multiple active supporting contributions fails closed.
- [ ] The correction contribution is human-authored authority and binds exactly one replacement edge assertion.
- [ ] Correction linkage changes contribution identity/source digest and survives exact round trip.
- [ ] The target source contribution remains active for unrelated assertions and is not falsely marked superseded/retracted.
- [ ] The target assertion's sole source support is durably represented as contradicted historical lineage.
- [ ] The replacement assertion is current in the corrected revision.
- [ ] Unrelated Y/Z support and per-contribution provenance are unchanged.
- [ ] The old pinned revision still projects the old edge.
- [ ] The corrected pinned revision does not project the contradicted old edge and does project the replacement.
- [ ] Exact retry creates no second semantic transition.
- [ ] Stale expected parent creates no correction mutation.
- [ ] Pinned rebuild is canonically equivalent to the corrected revision.
- [ ] Tampering with correction linkage fails revision-bound digest/integrity verification.
- [ ] Existing whole-contribution supersession/retraction behavior remains intact for uncorrected contributions.
- [ ] Lifecycle mutation of a correction contribution or actively corrected target contribution fails closed in this slice.
- [ ] Historical contributions with no correction fields remain backward compatible.
- [ ] No Eldyrwild graph, source, seal, adjudication fixture, or effective conformance count changed.
- [ ] No node/attribute/alias/evidence correction semantics were smuggled into the PR.
- [ ] No path outside §4 changed unless the bounded projection exception was explicitly triggered and proven necessary.
- [ ] The named Lysandra successor remains unimplemented.

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- the only way to correct X is to supersede/retract the whole source contribution;
- correction authority would live only in diagnostics, operation IDs, a mutable side table, or current-head state rather than replayable contribution authority;
- target identity must be inferred from edge shape, labels, predicate matching, or source prose;
- a multi-source target cannot be detected and rejected before mutation;
- replay would need caller-injected semantic judgments or current-head lifecycle instead of the pinned replay manifest/source digest;
- the correction must reuse the old edge object ID while changing structural semantics;
- a direct graph-store edit is proposed instead of a public Kernel operation with expected-parent publication;
- more than one head advancement is required for one correction;
- source artifact/evidence bytes must be rewritten to make the new assertion appear source-derived;
- generic node/attribute/alias/evidence correction is required to make the edge slice work;
- correction contribution retraction/supersession or corrected-source lifecycle must be implemented rather than safely rejected;
- any Eldyrwild-specific edge ID, Lysandra name, cultist name, predicate exception, or global reversal rule appears in production code;
- any real Eldyrwild graph revision is published by this PR;
- a path outside §4 or the bounded projection exception is required;
- the active tracker/architecture moved after this handoff and no longer supports this slice.

Use this stop report shape:

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

## Named successor handoff seed — do not implement here

After this capability is merged and independently reviewed, the next slice is:

```text
eldyrwild-lysandra-threat-direction-correction
```

That successor should consume the adjudicated source-correction finding for the exact defective relationship, publish one human-authored correction through this new Kernel path, preserve the original Session 8 source/evidence as history, and then prove the effective semantic movement:

```text
294 represented / 52 residual
→
295 represented / 51 residual
```

If the first real correction cannot achieve exactly that bounded movement without unrelated semantic change, stop before selecting another residual.
