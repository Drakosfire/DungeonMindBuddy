# Restore conversation prose formatting

Status: ACTIVE. Serial follow-up to the merged saved-page navigation change. Scope is this handoff, `SavedCitationAnswer.tsx` and its existing focused test. A restored citation-preview reply joined independent prose segments with one newline, collapsing fresh-response paragraph boundaries. Restore those paragraph boundaries for plain prose while retaining the exact saved text and citation selection; keep Markdown structures spanning segments intact. This reproduces one formatting mismatch, not necessarily every symptom in the user's particular conversation.

Verification: focused saved-citation and Markdown renderer tests passed (53 cases), including separated prose, exact citation reopening, and a table and fenced code spanning segments. No provider calls or primary state changes. A neighboring saved-history test PR was checked and does not overlap these files. Independent review is required before merge.
