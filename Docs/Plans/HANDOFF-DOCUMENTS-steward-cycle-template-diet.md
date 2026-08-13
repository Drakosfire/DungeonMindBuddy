# HANDOFF — Steward Cycle and handoff template diet

**Created:** 2026-08-12  
**Status:** ACTIVE — one process-structure capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOCUMENTS-steward-cycle-template-diet.md`  
**Conversation:** DungeonBuddy development-process optimization  
**Flow / agent:** `DOCUMENTS`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `a9461a9f5c94699f17970b797450d024e5fb39f6`  
**Predecessor:** PR #572 / foundational steward law  
**PR title:** `DOCUMENTS: replace Jumpstart with Steward Cycle`

## §1 Mission and merge-ready invariant

**Mission:** A fresh design/review steward can run one slice from a canonical Steward Cycle while the HANDOFF template contains only slice-specific authority and the external-agent skill contains only operational mechanics.

**Merge-ready invariant:** Process responsibilities are layered without semantic loss: `AGENTS.md` owns durable law, `Docs/Process/STEWARD-CYCLE.md` owns steward judgment/decomposition/review/re-anchor decisions, the external-agent skill owns exact commands/procedure, and `HANDOFF.template.md` owns only one slice's mission/boundaries/write lease/contracts/evidence/handback/rubric; the legacy Jumpstart remains only as a forwarding stub and active source-governance pointers name Steward Cycle as canonical.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every changed path? | Yes — all changed paths move process responsibilities to the correct layer without changing product/runtime behavior. |
| Most likely failure | Slimming removes a contract the parser or worker actually needs, or the old Jumpstart remains active authority through source indexes. |
| Evidence that detects it | §1–§9 parser-shape inspection, pointer scan, and responsibility matrix review. |
| Easiest boundary to under-test | `review_external_pr.py` assumptions about §4/§5/§7/§9 structure. |
| Stop/split trigger | Any change to review script behavior or product code. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, `.cursor/rules/anchor.mdc` |
| Base revision | `a9461a9f5c94699f17970b797450d024e5fb39f6` |
| Predecessor | PR #572 merged foundational rules |
| Named successor | Lane/preflight automation around worktrees, active handoffs, and review-cycle accounting |
| What remains false | No automatic lane collision scan or handoff initialization yet |
| State-authority sync set | This handoff + active process source indexes changed by the rename |

Parallel lane note: active product PRs may continue; this slice leases only process docs/template/runbook/source-index paths listed in §4.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Owning boundary |
|---|---|---|---|
| Fresh steward asks how to run a slice | Reads large Jumpstart containing policy + procedure + review guidance | Reads Steward Cycle for judgment and follows pointers to mechanics/template | Steward Cycle |
| Steward creates handoff | Copies a template that repeats vocabulary, flows, nano commits, review law | Copies a smaller §1–§9 slice payload | HANDOFF template |
| Reviewer needs commands | Reads skill mixed with invariant/tutorial content and fixed doc-sync set | Reads concise command runbook; state sync derives from handoff/workstream | skill |
| Source-governance agent chooses process doc | INDEX/audit name Jumpstart as active template | Steward Cycle is canonical; Jumpstart is superseded forwarding stub | INDEX + audit |
| Review parser reads handoff | Depends on §1–§9 and Path/bash/rubric shapes | Same parser-critical shapes remain | template compatibility |

Adversarial sequence: template is slimmed → `review_external_pr.py fetch` can no longer extract §4 Path, §5 Path, §7 bash commands, or §9 bullets → review automation silently loses evidence. This blocks merge.

## §4 Files in scope (write lease)

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Process/STEWARD-CYCLE.md` | Canonical steward judgment/process document. |
| Modify | `Docs/Plans/JUMPSTART-docs-relevance-first.md` | Superseded forwarding stub for historical links. |
| Modify | `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md` | Remove universal law/procedure while preserving §1–§9 parser contract. |
| Modify | `.cursor/skills/external-agent-pr-loop/SKILL.md` | Keep mechanics/commands; delegate law and judgment upward. |
| Modify | `Docs/Design/INDEX-design-agent-source-set.md` | Point active process source set to Steward Cycle. |
| Modify | `Docs/Reports/graph-document-audit.md` | Reclassify Jumpstart as superseded and Steward Cycle as active process reference. |
| Create | `Docs/Plans/HANDOFF-DOCUMENTS-steward-cycle-template-diet.md` | Slice authority. |

## §5 Explicitly out of scope

| Path/capability | Why |
|---|---|
| `scripts/review_external_pr.py` | Parser behavior is preserved, not changed; automation successor owns code. |
| `AGENTS.md` | Foundational law landed in predecessor. |
| `.cursor/rules/*.mdc` | Foundational invariants landed in predecessor. |
| Product roadmaps/trackers | No product sequencing changes. |
| Historical handoffs containing Jumpstart links | Forwarding stub preserves them; no history churn. |

## §6 Implementation contract

Required responsibility split:

```text
AGENTS.md
  durable repository law

Docs/Process/STEWARD-CYCLE.md
  re-anchor → decompose → allocate lane → design → dispatch → review/re-review
  → merge/state-sync judgment → next-slice decision

external-agent-pr-loop/SKILL.md
  exact commands and operational mechanics for external PRs

HANDOFF.template.md
  only facts/contracts specific to one slice
```

Template compatibility requirements:

- headings `## §1` through `## §9` remain;
- §4 contains a markdown table with a column literally named `Path`;
- §5 contains a markdown table with a column literally named `Path`;
- §7 contains a `bash` fence for exact verification commands;
- §9 contains normal markdown list/checklist bullets;
- bounded discovery, conditional contract matrices, baseline failures, and stop conditions remain expressible without reprinting their universal rationale.

Legacy behavior: `JUMPSTART-docs-relevance-first.md` becomes a short superseded pointer; historical links keep resolving.

Failure behavior: any responsibility exists in no layer, is contradictory across layers, or parser-critical template structure disappears → block merge.

## §7 Evidence required to merge

| Guarantee | Owning boundary | Evidence | Expected | Stop condition |
|---|---|---|---|---|
| Steward Cycle owns judgment, not foundational law | document structure | direct review | links to AGENTS/rules; no duplicate universal policy wall | foundational law duplicated wholesale |
| Template keeps parser contract | template | exact structural inspection | §1–§9, §4 Path, §5 Path, §7 bash, §9 bullets present | any required shape missing |
| Skill is mechanics-first | skill | structural review | command/procedure content retained; fixed flow/sync assumptions removed | invariant/tutorial bulk still duplicated or required mechanics lost |
| Jumpstart is no longer active authority | stub + source indexes | pointer scan | canonical pointer is Steward Cycle | INDEX/audit still direct fresh agents to Jumpstart |
| Historical links remain valid | Jumpstart path | direct fetch | stub resolves to canonical process doc | old path deleted |
| Scope exact | PR diff | changed path review | only §4 paths | any script/product path changes |

Verification commands for an implementation environment:

```bash
git diff --check
git diff --name-only a9461a9f5c94699f17970b797450d024e5fb39f6...HEAD
rg -n '^## §[1-9] ' .cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md
rg -n '^\|.*Path.*\|' .cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md
rg -n '```bash|^## §9 ' .cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md
rg -n 'JUMPSTART-docs-relevance-first|STEWARD-CYCLE' Docs/Design/INDEX-design-agent-source-set.md Docs/Reports/graph-document-audit.md Docs/Plans/JUMPSTART-docs-relevance-first.md .cursor/skills/external-agent-pr-loop/SKILL.md
```

## §8 Required review handback

Record Review Cycle N, exact head SHA, responsibility-layer findings, parser-shape findings, pointer findings, changed paths, and total handoff-template line reduction as descriptive evidence (not a target).

## §9 Acceptance rubric

- [ ] `STEWARD-CYCLE.md` is the canonical steward process/judgment document.
- [ ] Jumpstart is a superseded forwarding stub rather than an active competing process template.
- [ ] HANDOFF template preserves §1–§9 parser-critical shapes while removing universal policy/tutorial duplication.
- [ ] External-agent skill is an operational runbook rather than a second process constitution.
- [ ] Active source-governance docs point fresh agents to Steward Cycle.
- [ ] Historical handoff links to Jumpstart remain resolvable through the stub.
- [ ] No automation or product behavior is introduced in this slice.
