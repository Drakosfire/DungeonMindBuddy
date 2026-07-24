---
document_id: dmb-design-merge-ready-invariant-evidence
title: Merge-Ready Invariant and Evidence Contract
document_class: design_decision
status: adopted
version: 0.1
created_at: "2026-07-23"
last_updated_at: "2026-07-23"
---

# Merge-Ready Invariant and Evidence Contract

## Decision

Every implementation handoff and PR description must answer two governing questions:

1. **What is the merge-ready invariant?**
2. **What evidence is required to merge?**

The PR description is the live merge contract. It restates the handoff mission and invariant verbatim, then records required evidence beside evidence actually produced. A summary and undifferentiated test list are not substitutes.

## Merge-ready invariant

The invariant is one sentence describing the property that must remain coherent across every participating layer and observable path. It should name the identities, revisions, authority boundaries, durable state, local/editor state, navigation state, projections, and agent context that matter to the capability.

For stateful surface work, the default shape is:

> For one operation or durable object, every participating server, artifact, local/editor, graph, URL, surface-authority, and agent-context representation identifies the same authorized identity and revision; any mismatch fails safely without unintended mutation and offers an explicit recovery path.

A slice is not ready to dispatch when one invariant cannot govern all claimed behavior. Split it or perform reconnaissance first.

## Evidence required to merge

Each material clause in the invariant must have an owning proof and an explicit stop condition.

| Invariant clause / guarantee | Owning boundary | Required evidence | Produced evidence | Stop condition |
|---|---|---|---|---|
| `<claim>` | `<store/service/route/component/workflow/CLI>` | `<automated, adversarial, regression, manual, or dogfood proof>` | `<result + provenance>` | `<outcome that blocks merge>` |

Evidence classes are complementary:

- **Contract tests** prove pure rules, authorization, schemas, and state transitions.
- **Adversarial integration tests** prove races, stale state, partial success, retries, navigation, and cross-surface misuse.
- **Regression suites** prove shared changes preserve existing consumers.
- **Manual proofs** cover browser history, editor behavior, recovery controls, and visible truthfulness.
- **Dogfood scenarios** prove the capability is understandable and usable in its real operating context.

Missing required evidence remains a visible gap. It may be waived only by an explicit operator decision recorded in the PR description and judgment record.

## Pre-dispatch critique gate

Before implementation launches:

1. critique the proposed invariant;
2. critique whether the proposed evidence would actually prove it;
3. enumerate adversarial sequences that could falsify it;
4. split the slice when proof ownership or failure behavior spans separate invariants;
5. finalize the handoff only after the invariant and evidence ledger survive critique.

## Review and re-review

Review the diff against the invariant, not against the worker's task list. Re-review only the new delta, then re-evaluate the full invariant and evidence ledger. A fix closes a finding only when the new behavior and proof remove the failure sequence rather than relocating it.

## Fix-loop response

When a review exposes a fix loop:

1. **Harden the current seam** until its invariant and evidence ledger are satisfied.
2. **Use the next PR for bounded polish and dogfood**, without adding a new foundational capability.
3. **Pause before the following capability** and critique its invariant and required evidence before writing or dispatching its implementation handoff.

The fix loop is a signal to improve the governing contract, not to accumulate surface-specific patches or pre-plan farther ahead.

## Required PR-description sections

```markdown
## Outcome

## Merge-ready invariant

## Evidence required to merge

| Guarantee | Owning boundary | Required evidence | Result |
|---|---|---|---|

## Scope and explicit deferrals

## Evidence produced

### Automated
### Adversarial
### Regression
### Manual / dogfood

## Gaps, waivers, and stop conditions
```

## Application to the Build workstream

BLD-05a hardens the shared workspace-document authoring seam. Its successor is a bounded polish/dogfood slice. Extraction-control work is not replanned or launched until its proposed invariant and evidence ledger are critiqued against the hardened seam and dogfood findings.
