# PLAN — visible card boundaries in Document

Status ACTIVE; operator directly requested horizontal card divisions2026-10-18 and now authorizes dogfood execution during travel.
Owner PRIME; independent review ARCHITECTURE.
Base36697f5765d7d58d3901b91674681d2831324fcc; existing buddy-context-loop checkout, codex/plan-card-document-dividers.
Topology parallel-independent from DOGFOOD autosave; exact lease apps/live-control-ui/src/styles.css and this handoff. Settle prior Docs/Plans/HANDOFF-AUTHOR-explicit-source-link-activation.md after merged1414.

## Invariant

Document view visibly marks actual Scene/card beginnings with a horizontal rule. Match only canonical rendered data-dmb-playable-kind=scene, not all headings or arbitrary Markdown horizontal rules. Works for existing v1 Scene-first and v2 Beat-first Plans. Presentation only: no DOM content insertion, parser changes, stored horizontal-rule insertion, scene identity change or reordered text. Read/write fidelity and autosave untouched.

## Acceptance

Render actual first and later scene markers in the Plan Document at desktop and narrow widths; visible full-width divisions without overflow and unchanged authored content. Ordinary section headings remain ordinary. Build existing dependencies, inspect cumulative diff, independent review then PRIME merge/reversible static UI delivery. This does not claim Markdown source entry, Card editing or reordering completed.

## Evidence

Vite build PASS (existing chunk warning). Actual Plan preview5210 shows all5canonical scene IDs with a computed accent rule; ordinary travel h4 has0px border. First/later scene screenshots inspected; narrow layout has no horizontal overflow; viewport restored. No text edits or server writes. CSS-only3declarations; diffcheckPASS; independent review pending.
