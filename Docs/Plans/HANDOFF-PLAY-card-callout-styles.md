# PLAY: card callout presentation

Status: COMPLETE — PR#1419 merged at `383fd4620befa3730fee83e468d17bde12bda4b6` and delivered on5202. Implementation/write lease ended. Reconciled2026-10-18.

Current disposition: Independent review and actual5202 Read Aloud presentation verified; no authored content or Run mutation. Remaining work requires its own bounded successor; this document grants no continuing lease.


Base: origin/main 04f6ad479fba1e0a1bbac4a2294f0c909b36adfa. Existing buddy-context-loop checkout, branch codex/play-card-callout-styles. Serial single PR; no new checkout or environment. Current open PRs inspected: no active shared scene-card CSS ownership; older Play work is separate or settled. Architecture supplies independent review before PRIME merge.

Expected writes: this handoff and apps/live-control-ui/src/shared/sceneCard.css only. Contract: existing admitted callout AST and ReadOnlyBodyContent HTML remain authoritative; style callouts inside shared Plan/Play Scene cards without modifying authored content, Run pins, notes, request payloads, or parser behavior. Inspection found both Read Aloud and Rules as semantic asides in the live Play DOM, but their styles require an editor theme ancestor absent from Scene cards.

Failure cases: label blending into prose; paragraphs merging visually; paper/choice color contrast; narrow overflow; styles leaking outside scene cards. Verify existing actual Play content-rendering tests, UI typecheck/build, cumulative diff, and rendered live Run against an isolated static asset preview. Do not write user Run/Plan data. Reuse established 5202 static asset delivery after review; preserve previous hashed assets and index rollback. No API restart or database changes.

Settlement: after merge this lease ends; remaining Play notes-to-Agent work and Cards editing/navigation remain separate.
