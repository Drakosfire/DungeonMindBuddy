---
# Optional workflow contract: literal Markdown the worker may use for the PR body.
# Keep this summary subordinate to the complete handoff below.
pr_body_template: |
  ## Outcome
  {{TODO: copy §1 Mission exactly}}

  ## Scope and verification
  {{TODO: base/head, actual changed paths, §7 results, provenance, waivers, and deferred successors}}
---

# HANDOFF — {{TODO: one implementation capability}}

**Created:** {{TODO: YYYY-MM-DD}}.
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `{{TODO: repository path}}`

> **Dispatch gate:** Dispatch is prohibited until capability decomposition is complete, one independently useful mission remains, every expected path is known, required contract matrices are resolved, and every acceptance claim has an owning proof.
>
> This checked-in handoff is the complete authority. The worker must not “helpfully” compress, omit, replace, or rewrite it before implementation. A PR-body summary may link here but cannot substitute for it.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Capability** | A coherent behavior or contract that creates one outcome someone can use, depend on, test, or revert. |
| **Independently useful outcome** | An outcome that provides value or establishes a reusable contract even if neighboring work never ships. |
| **Public/durable contract** | A persisted format, identifier, API, event, schema, file representation, caller-facing type, or externally consumed interface that must remain interpretable beyond one call stack. |
| **Observable path** | A user-visible or externally observable route through the behavior, including success, miss, error, retry, persistence, and operator paths. |
| **Owning boundary** | The layer where a guarantee becomes true and therefore must be proved: serializer, store, service, route, component, workflow, CLI, or equivalent. |
| **Invariant** | The single property every changed layer establishes or proves. |
| **Stop condition** | A discovered fact that invalidates the current slice boundaries and requires a report before implementation continues. |

## §1 Mission

One sentence describing one independently useful outcome and its value. The word “and” is allowed only when it does not join separate outcomes.

```text
<caller or user> can <single capability> so that <value>.
```

**Invariant:** `<one property every changed layer establishes or proves>`

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `<architecture, decision, tracker, or issue>` |
| Repository rules | `<dispatch, security, language, or review rules>` |
| Base revision | `<immutable SHA / revision>` |
| Predecessor contract | `<merged PR, canonical schema/type, captured fixture, or none>` |
| Exact input consumed | `<artifact, payload, event, store revision, or caller contract>` |
| Named successor | `<capability intentionally deferred>` |
| What remains false | `<specific behavior not delivered by this slice>` |
| Explicit non-goals | `<policy, API, UI, migration, cleanup, management surface, or diagnostics>` |

Read authoritative inputs in order before changing code:

1. `<architecture / decision authority>`
2. `<active tracker or issue state>`
3. `<predecessor contract / captured fixture>`
4. `<implementation seam>`
5. `<existing owning tests>`

If the base moved, an authority conflicts, or the predecessor shape differs from this handoff, stop and report the consequence before implementation.

## §3 Observable-path inventory

Mandatory for user-facing, multi-entry, stateful, persistence, or multi-source work. Otherwise: `Not applicable — <one-sentence reason>`.

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---:|---|
| `<entry / interaction path>` | `<today>` | `<after this slice>` | Yes / No | `<layer>` |

Inventory success, ordinary miss, error/unavailable, stale context, retry/replay, save/reload, traversal, and operator paths where relevant. A `No` in “Same invariant” is a split trigger unless the row is explicitly removed from this mission.

## §4 Files in scope (allowlist)

Every changed path must appear here. The expected focused diff must be expressible from this table.

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Create / Modify / Delete | `{{TODO: relative/path}}` | `{{TODO}}` |

**Bounded discovery exception:** `Not applicable — <reason>` or complete all fields:

```text
Directory:
Maximum additional paths:
Allowed path kinds:
Decision rule for including one:
```

Unrestricted globs such as `src/**` are prohibited. If another path is needed outside the table or bounded exception, stop and report it; do not add it silently.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `{{TODO}}` | `{{TODO: successor ownership, collision risk, or separate invariant}}` |

Nearby work is not authorization. Dogfood search, notes, classifications, management controls, persistence, reports, or dedicated panels are product capabilities unless §1 names them as the single mission.

## §6 Implementation contract and conditional matrices

Specify behavior, not a code recipe.

```text
Input:
  <types, artifacts, exact predecessor authority>

Output:
  <public result, durable artifact, or observable state>

Invariant:
  <same invariant as §1>

Failure behavior:
  <named failure> → <stable result, unresolved state, or blocked transition>

Replay / idempotency:
  same input →
  changed input →
  retry after partial failure →

Trust boundary:
  Verifies:
  Records or trusts without proving:
```

For irreversible work:

```text
Commit point:
Before commit:
After commit:
Truthful result after a post-commit failure:
```

Each matrix is required when applicable. Use `Not applicable — <one-sentence reason>`; never omit one silently.

### A. State and fallback matrix

Required when multiple states, dependencies, sources, or sibling paths exist.

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| `<path>` | `<defer / fail / fallback>` | `<primary source>` | `<unresolved / named fallback>` | `<behavior>` | `<fail closed / behavior>` | `<behavior>` | `<allowed conditions>` |

Name every fallback source. Audit every sibling path sharing the same trust boundary.

### B. Identity matrix

Required when IDs, labels, aliases, normalization, merge, rename, deletion, or rebinding affect resolution.

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Exact ID | `<rule>` | `<rule>` | Yes / No: `<source>` |
| Alias / label | `<unique-only / prohibited / other>` | `<rule>` | Yes / No |
| Normalized key | `<rule or prohibited>` | `<rule>` | Yes / No |
| Rename / deletion / rebind | `<stable identity behavior>` | `<rule>` | Yes / No |

First-win matching should normally be prohibited. Display labels must not silently substitute for durable identity.

### C. Persistence and replay matrix

Required when data survives restart, save/reload, retries, replay, compatibility, or migration.

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| `<write / load / replay>` | `<format / revision>` | `<exact property>` | `<rule>` | `<rule>` | `<rule>` |

A new persisted format or durable identifier is not an incidental adapter detail. If independently useful or revertible from §1, stop and propose a successor slice.

### D. Predecessor-to-consumer mapping

Required when adapting an existing API, event, schema, file, fixture, or error payload.

**Grounding source:** `<exact captured fixture | canonical schema/type | field-level mapping>`

| Predecessor field / outcome | Real shape and optionality | Consumer field / behavior | Transformation | Proof fixture/test |
|---|---|---|---|---|
| `<field>` | `<type, identifier shape, nullability, error payload>` | `<destination>` | `<mapping>` | `<path/test>` |

Invented “close enough” fixture vocabulary is not acceptable proof.

## §7 Verification ownership map and commands

Every behavioral guarantee must be exercised at its owning boundary. Lower-level helper coverage is necessary when useful but cannot prove a higher-level claim.

| Guarantee | Owning boundary | Command or manual scenario | Expected evidence |
|---|---|---|---|
| `<guarantee>` | `<serializer/store/service/route/component/workflow/CLI>` | `<exact command or scenario>` | `<observable result>` |

Run every applicable command and record exact results:

```bash
<focused owning-boundary test>
<contract or exact round-trip test>
<integration / failure-injection test>
<repository-specific build, formatting, or lint command>
git diff --check
git diff --stat <base>...HEAD -- <§4 paths>
git diff --name-only <base>...HEAD
```

### Minimal live proof

`Not applicable — <reason>` or:

```text
Existing surface used:
Smallest scenario:
Expected observation:
Evidence captured:
```

If live proof requires new search, persistence, notes, classifications, management controls, reports, or a dedicated panel, stop for split review.

### Baseline failure protocol

For any required command already failing on base:

- run or cite the same command on base and head;
- record whether head introduces additional failures;
- do not call the gate green;
- name the explicit operator waiver required if it remains an acceptance gate.

## §8 Required handback

The PR body or implementation handback must include:

1. Base SHA/revision and head SHA/revision.
2. Actual changed paths and focused diff stat limited to §4.
3. Every §7 command/scenario and exact result.
4. Provenance of each result: author-local, independently rerun local, or CI.
5. Live/manual evidence when applicable.
6. Baseline failures with base/head comparison.
7. Explicit operator waivers; `none` when none exist.
8. Paths outside §4; `none` or a stop report.
9. Stop conditions encountered and resolution; `none` when none exist.
10. Successor capabilities deferred and still false.
11. Confirmation that the authoritative handoff was implemented without compression or omitted constraints.

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true and each behavioral bullet names its §7 proof.

- [ ] Exactly one independently useful capability from §1 was delivered — proved by `<§7 proof>`.
- [ ] The declared invariant holds across every observable path in §3 — proved by `<§7 proofs>`.
- [ ] No second public/durable contract was silently introduced — proved by `<diff inspection + contract tests>`.
- [ ] State, fallback, identity, persistence, and predecessor behavior follow every applicable §6 matrix — proved by `<§7 proofs>`.
- [ ] Real predecessor vocabulary and shapes are used — proved by `<captured fixture / schema / mapping test>`.
- [ ] No path outside §4 changed — proved by `<changed-path command>`.
- [ ] Baseline failures are reported truthfully and any required waiver is explicit — proved by `<base/head evidence>`.
- [ ] Minimal live proof did not grow into an unacknowledged product surface — proved by `<scenario or Not applicable reason>`.
- [ ] The named successor remains unimplemented and unclaimed.

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- a second independently useful outcome;
- a new public/durable contract not owned by §1;
- unresolved identity, state, fallback, persistence, replay, or compatibility semantics;
- a predecessor contract that differs materially from the authoritative fixture/schema/mapping;
- a required path outside §4 or its bounded discovery exception;
- a new product or operator surface disguised as verification;
- an irreversible operation outside the declared commit model;
- a repository rule or architecture conflict;
- a base/head failure that requires an operator waiver before acceptance.

```text
Stop condition:
Why the current mission cannot absorb it:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```
