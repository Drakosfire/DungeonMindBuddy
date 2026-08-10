# HANDOFF — Kernel targeted assertion contradiction without replacement

**Created:** 2026-08-10
**Status:** IMPLEMENTATION COMPLETE — awaiting review
**Canonical handoff path:** `Docs/Plans/HANDOFF-kernel-targeted-assertion-contradiction.md`
**Conversation name:** `Kernel Targeted Assertion Contradiction`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**PR title:** `KERNEL: support governed assertion contradiction without replacement`
**Branch:** `build/kernel-targeted-assertion-contradiction`

**Required predecessor:** PR #542 merge `cde14cd600e7cb20ddbbe0494ff22d3b122f529f`

**BUILD dispatch capture:**

```text
origin/main: b8e4dd214b1171793051ce507c0b93c6d87efa91
#542 merge ancestor: proven
mutation authority: synthetic/temp World Graphs only
```

---

## §0 Mission

Add the smallest generic Kernel capability required to express a human-authored graph correction whose correct result is:

```text
historical assertion remains durable
current support becomes contradicted
no replacement assertion is authored
current graph truth no longer projects the defective relationship
replay reconstructs that exact state
```

This PR adds first-class `contradicts` beside existing `contradicts_and_replaces`, plus public `contradict_edge_assertion_support`.

It does **not** mutate canonical Eldyrwild.

---

## §2 Model

```python
class GraphContributionAssertionCorrection:
    correction_kind: Literal["contradicts_and_replaces", "contradicts"]
    target_contribution_id: str
    target_assertion_id: str
    replacement_assertion_id: str | None
```

`replacement_assertion_id` remains a required field: nonblank for `contradicts_and_replaces`, explicit `null` for `contradicts`.

Lysandra identity/digests must remain unchanged.

---

## §4–§10 Contract summary

* One correction contribution may enumerate every active supporter of one edge assertion.
* Exact support-set equality is mandatory; partial coverage fails closed before mutation.
* Apply moves the complete active set into contradicted lineage; durable edge history remains.
* No replacement assertion is authored.
* Replay via `apply_assertion_corrections` reconstructs Q pinned and unpinned.
* Exact retry is idempotent only when C is revision-bound and target support matches the contradiction contract.

---

## §12 Implementation surfaces

```text
src/graph_memory/kernel/contribution_models.py
src/graph_memory/kernel/contributions.py
src/graph_memory/kernel/contribution_merge.py
src/graph_memory/kernel/__init__.py
tests/test_graph_kernel_contribution_merge.py
tests/test_graph_kernel_contribution_rebuild.py
Docs/Plans/HANDOFF-kernel-targeted-assertion-contradiction.md
```

---

## §15 Canonical fence

No `--allow-live-world`. No Session-24 operator CLI. R_current remains
`rev:b90646fb5b135988bd7842cde858c96e` (`369 / 311 / 58 / 3`).

---

## §21 One-sentence invariant

> Add a replayable governed authority that can say “this exact historical edge is wrong and has no justified replacement,” removing all of its current support without deleting history, inventing new truth, or touching unrelated assertions.
