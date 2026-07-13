# Jumpstart Template — Select, Dispatch, Review, and Re-anchor One Slice

> Status: ACTIVE PROCESS TEMPLATE
> Use for: Fresh design/review stewards preparing one implementation slice without prior chat context.
> Canonical repo path: `Docs/Plans/JUMPSTART-docs-relevance-first.md`
> Project adaptation: Fill the project-specific authority, tracker, and command fields before dispatch.

## 0. Pickup prompt

Use this prompt when transferring stewardship:

```text
Reconcile current repository authority and current change state. Identify candidate capabilities, decompose them before dispatch, and select one independently useful implementation outcome. Write one complete PR handoff whose constraints survive without chat context. Review the resulting change skeptically at the owning boundaries, then re-anchor repository state after merge before selecting another slice.
```

The steward owns the full cycle:

```text
authority reconciliation → capability decomposition → one-slice dispatch
→ invariant-based review → finding-led re-review → post-merge re-anchor
```

## 1. Shared vocabulary

Use these definitions in this template and the PR handoff template.

| Term | Definition |
|---|---|
| **Capability** | A coherent behavior or contract that creates one outcome someone can use, depend on, test, or revert. |
| **Independently useful outcome** | An outcome that provides value or establishes a reusable contract even if neighboring work never ships. |
| **Public/durable contract** | A persisted format, identifier, API, event, schema, file representation, caller-facing type, or externally consumed interface that must remain interpretable beyond one call stack. |
| **Observable path** | A user-visible or externally observable route through the behavior, including success, miss, error, retry, persistence, and operator paths. |
| **Owning boundary** | The layer where a guarantee becomes true and therefore must be proved: serializer, store, service, route, component, workflow, CLI, or equivalent. |
| **Invariant** | The single property every changed layer establishes or proves. |
| **Stop condition** | A discovered fact that invalidates the current slice boundaries and requires a report before implementation continues. |

Several files, packages, or architectural layers do not automatically imply several capabilities. One architectural consumer, endpoint, or feature area does not automatically imply one capability.

## 2. Project adaptation and authority reconciliation

Complete this block at pickup:

| Project field | Current authority |
|---|---|
| Repository and default branch | `<repository>` · `<branch>` |
| Architecture / decision authority | `<paths>` |
| Active tracker / roadmap | `<paths or Not applicable: reason>` |
| Dispatch and review rules | `<paths>` |
| Current handoff or predecessor | `<paths or none>` |
| Required build / test commands | `<commands>` |
| Current base revision | `<SHA or immutable revision>` |

Then reconcile evidence in this order:

1. **Repository authority:** current checked-in architecture, contracts, policies, and source code.
2. **Trackers and roadmaps:** current sequencing and active-slice state; they may sequence work but must not silently override architecture.
3. **Current change state:** open PRs, branch heads, merged predecessors, CI, and intervening commits.
4. **Attached or project-source context:** useful input only after mapping it to repository authority.
5. **Prior handoffs and summaries:** historical evidence unless still explicitly active.
6. **Chat-only constraints:** nonexistent for a fresh worker until written into the canonical handoff.

Classify conflicts as `MATCH`, `SOURCE_AHEAD`, `REPOSITORY_AHEAD`, `CONFLICT`, `SOURCE_ONLY`, or `REPOSITORY_ONLY`. Record which authority wins and why. Do not dispatch from a stale summary or an unverified attachment.

## 3. Capability decomposition worksheet

Before selecting a PR, list every candidate outcome—including “supporting” workflows that may actually be separate product behavior.

| Candidate outcome | Independently useful? | Public/durable contract changed? | User surface changed? | Failure model changed? | Ownership layer | Independently testable/revertible? | Decision |
|---|---:|---:|---:|---:|---|---:|---|
| `<outcome>` | Yes / No | Yes / No | Yes / No | Yes / No | `<boundary>` | Yes / No | Keep / Split / Reconnaissance |

Also enumerate affected observable paths before grouping outcomes. Consider, when relevant:

- existing-object resolution and linked-object traversal;
- creation, insertion, search, and selection;
- save/reload, migration, replay, and retry;
- diagnostics and operator or dogfood judgment;
- unavailable, stale, integrity-failure, and ordinary-miss behavior.

Group outcomes only when every changed layer establishes or proves the same invariant. Split when an outcome is independently useful, independently reviewable, independently revertible, or creates a second public/durable contract.

## 4. Dispatch-readiness gate

Do not dispatch until every answer is concrete.

- **Single outcome:** What one independently useful outcome will exist afterward?
- **Remaining falsehood:** What named successor capability remains false?
- **Observable paths:** Which success, miss, failure, retry, and persistence paths change?
- **Second contract check:** Does the slice introduce another durable format, public type, API, event, identifier, or operator workflow?
- **Identity semantics:** Where relevant, are exact ID, alias, normalization, rename, deletion, and fallback rules explicit?
- **State semantics:** Where relevant, are initialization, ready, miss, unavailable, integrity failure, stale context, and retry decisions explicit?
- **Persistence semantics:** Where relevant, are save/reload, migration, replay, compatibility, and idempotency explicit?
- **Predecessor realism:** Is integration grounded by a captured fixture, canonical schema/type, or field-level mapping?
- **Path allowlist:** Can every expected changed path be named, with any bounded discovery exception precisely constrained?
- **Owning proofs:** Does every acceptance claim map to a test, inspection, or manual scenario at the boundary that owns it?
- **Stop conditions:** Does the worker know when to stop instead of expanding?
- **Full authority:** Is the complete mission, boundary, matrix, proof map, rubric, and stop logic checked in—not merely summarized in a PR body or chat?

Any unresolved answer means: split, perform reconnaissance/design work, or resolve architecture first.

## 5. Slice-selection algorithm

1. List candidate outcomes and observable paths.
2. Group only outcomes governed by one invariant.
3. Separate independently useful, independently revertible, or independently consumable contracts.
4. Treat unresolved architecture as reconnaissance or design work, not implementation guesswork.
5. Select one implementation capability and state what remains false.
6. Name successors without implementing or claiming them.
7. Write the complete PR handoff from the canonical template.

Size, changed-file count, and layer count are warning signals—not decision rules. Cross-layer work may remain unified when each layer implements or proves one invariant.

## 6. Contract resolution before dispatch

Use compact matrices in the PR handoff when applicable. `Not applicable` requires a one-sentence reason.

### Identity

State whether resolution is exact ID only, exact ID then alias, unique alias/label, normalized key, or another explicit rule. First-win matching should normally be prohibited. Display labels must not silently replace durable identity. Define rename, deletion, rebinding, ambiguity, and fallback behavior.

### State and fallback

For each observable path, resolve loading/initialization, exact success, ordinary miss, unavailable dependency, integrity failure, stale/superseded context, and retry/replay. Name the primary source and any fallback. Distinguish unresolved, deferred, fail-closed, and retryable outcomes.

Audit every sibling path sharing the same trust boundary; a rule for initial load may also govern selection, traversal, refresh, and reopen.

### Persistence and replay

Treat new persisted syntax, references, schemas, or representations as contracts—not adapter details. Define round trips, compatibility, migration, replay, idempotency, and independent rollback. A second independently useful durable contract is a split trigger.

### Predecessor mapping

Require one of: an exact captured response fixture, a canonical schema/type definition, or a field-level predecessor-to-consumer mapping. Invented “close enough” names, identifier shapes, optionality, or error payloads are not integration proof.

## 7. Review protocol

Review the invariant across paths before reviewing files one by one.

1. Restate the mission, invariant, named successor, and expected changed paths.
2. Enumerate every entry path governed by the invariant.
3. Compare actual diff to the mission and allowlist; unexpected paths are scope findings.
4. Look for hidden second contracts: persistence, identifiers, caller types, management surfaces, reports, or diagnostics.
5. Verify identity, state/fallback, and persistence matrices against every sibling path.
6. Confirm predecessor fixtures and mappings use real vocabulary, shapes, optionality, and error semantics.
7. Trace each acceptance claim to its owning proof. Lower-level helper tests cannot prove higher-level guarantees.
8. Exercise exact round trips, failure injection, and replay where applicable.
9. Distinguish the smallest live proof from new product behavior. Search, notes, classifications, controls, reports, or a dedicated panel are product capabilities, not “just dogfood.”
10. Compare required gates on base and head when base is already failing. Do not call a failing gate green.

Typical owning proofs:

| Guarantee | Owning proof |
|---|---|
| Serialization / durable format | Exact serialization or save/reload round-trip test |
| UI behavior | Component/integration test or explicit browser smoke |
| Service contract | Route, endpoint, or consumer contract test |
| Atomicity | Failure-injection test at the commit boundary |
| Predecessor compatibility | Captured-contract fixture or canonical mapping test |
| Live usability | Recorded minimal manual scenario on an existing surface |

## 8. Re-review protocol

Begin from a finding ledger, not from the latest patch alone.

| Prior finding | Claimed fix | Owning files/tests | Verified? | New consequence? |
|---|---|---|---:|---|
| `<finding>` | `<claim>` | `<paths / commands>` | Yes / No | `<result>` |

For each finding, retest the full invariant across all governed paths. Do not verify only the literal line changed in response to review. Add newly exposed consequences to the ledger before issuing another verdict.

## 9. Baseline failures and verification truth

When a required command fails on base:

1. Run or cite the same command on base and head.
2. Record whether head adds failures, removes failures, or leaves the baseline unchanged.
3. Do not report the gate as passing.
4. Require an explicit operator waiver if the failing command remains an acceptance gate.
5. Separate author-reported local results, independently rerun local results, and visible CI results.

## 10. Post-merge re-anchor

Before selecting or dispatching another slice, refresh:

- merged head SHA or immutable revision;
- active tracker and roadmap state;
- predecessor contract and actual delivered behavior;
- deferred successors and stop findings;
- current open PR and collision state;
- whether the next named slice still passes capability decomposition.

Do not chain-dispatch from pre-merge assumptions or stale handoff prose.

## 11. Anti-patterns

| Bad | Better |
|---|---|
| “One dashboard consumes it, so migration, favorites persistence, search, and review notes are one slice.” | Decompose by independently useful outcomes and contracts. |
| “Add a notes panel so we can dogfood the migration.” | Prove migration through the smallest existing surface; dispatch notes management separately. |
| “Store the new reference string inside the adapter.” | Treat the persisted reference format as a public/durable contract with round-trip and rollback semantics. |
| “Fall back normally on errors.” | Fill the state/fallback matrix for each governed path and source. |
| “The PR summary contains the important constraints.” | Check the complete authority into the handoff; summaries may link but not replace it. |
| “The mock returns approximately the predecessor fields.” | Use a captured fixture, canonical schema/type, or exact field mapping. |
| “Frontend plus backend is too large.” | Keep them together when both establish and prove one invariant; split only on capability boundaries. |
