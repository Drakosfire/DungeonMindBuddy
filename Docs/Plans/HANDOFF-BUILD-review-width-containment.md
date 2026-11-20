# BUILD — contain document and review width

DELIVERED with nested source-grid follow-up: PR #1610 merged as
aeb9e6d94d80e292e3a203625f6349d54f7ddadc, one Bugbot cycle approved
9d422961b28a800ed6e7cbcdfa6c388cfc3b4c7a. Paired delivery preserves retained
state. Actual wide/640/480 requested checks show review host/review/sheet fully
contained. Paper's nested editor-shell still expands to574px and needs the same
explicit shrinking-track invariant; successor owns that remaining defect.

Original serial PRIME slice from c0c6aa2b1687ca20be9ae8905149ba20d21a165f;
branch codex/build-review-width-containment, existing buddy-context-loop checkout.
Architecture critique 01a16550-976e-76a1-b731-968c169a4e9b adopted. Remote/open PR
census checked, no overlapping implementation lane. Operator goal authorizes
shared-surface foundation repairs. #1609 ordinary640px review found inner rows
wrap but an implicit auto grid track grows beyond available Build reader width.

One UI-only containment fix at Build's owning workspace boundary: explicit
minmax(0,1fr) column, min-width:0 for review host/review, border-box/max-width as
required by actual paper/review measurements. Preserve existing dock reservation,
width/padding intent and60vh vertical review scrolling. Do not blanket-reset every
descendant or hide overflow with clipping. No semantic/provider/API/publication,
shared stylesheet, source-content or other-surface changes.

Exclusive writes: this handoff; predecessor HANDOFF-BUILD-shared-publication-styles.md;
Docs/Roadmaps/ROADMAP-demo.md; apps/live-control-ui/src/buildSurface/buildSurface.css.
No new tests mirroring CSS; verify current Build shell/review component tests and
actual wide/640px/narrower rendered ancestor widths, full document/reviewer, focus,
vertical scroll and no clipping. Read-only DOM measurements at ordinary UI are
valid evidence; no injected style/state repair. Exact-head Bugbot, PRIME merge,
guarded paired8000/5202 delivery and protected restart/reopen. Preserve APP/native,
mechanics and frozen sources. No Graph publication until actual semantic review.
