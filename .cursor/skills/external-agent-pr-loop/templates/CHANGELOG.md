# HANDOFF template changelog

`template_version` in `HANDOFF.template.md` frontmatter records the contract
generation a handoff was authored against. Filled handoffs keep the value they
were copied with; bump it here, not in a handoff.

Bump **major** when a section is added, removed, or renumbered (reviewers and
workers key off §1–§9). Bump **minor** for wording, added guardrails, or
tightened rules that do not move a section.

## 2.0 — 2026-07-25

Same §1–§9 structure and `pr_body_template`; the contract language changed.

- Added **Operating model**: the agentic premise (workers see this file, not the
  author's chat) plus six one-line rules — one capability, contract over recipe,
  allowlist as interface, prove at the owning boundary, evidence over narrative,
  stop over improvise.
- Converted the dispatch gate from a prose paragraph to a falsifiable checklist.
- Collapsed §8 from thirteen numbered requirements into a field → source → rule
  table; the frontmatter skeleton already carries the shape.
- Added corpus-PII redaction for PR-body evidence
  (`.cursor/rules/corpus-pii-and-llm-payloads.mdc`) — PR bodies are external.
- Added §7 evidence hygiene: exit status and assertion-relevant output, not
  full logs.
- Added §4 note to list this handoff and any tracker/plan doc the slice updates,
  so doc edits do not read as out-of-allowlist paths.
- Tightened definitions, matrices, and rubric wording; removed repeated
  admonitions that agents skim past.

## 1.0 — before 2026-07-23

Original §1–§9 template introduced alongside
`Docs/Design/DESIGN-merge-ready-invariant-evidence.md`: mission, merge-ready
invariant, pre-dispatch critique, observable-path inventory, §4 allowlist,
out-of-scope table, implementation matrices, evidence ledger, PR-description
requirements, acceptance rubric, stop conditions.
