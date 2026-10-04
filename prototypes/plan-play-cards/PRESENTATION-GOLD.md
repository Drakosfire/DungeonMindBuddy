# Source-aware presentation candidate target

Operator goal: fast construction, easy styling and interaction through reviewable agent edits. Preserve design v1 as default; adapt its strengths to imported source design and media. This is a development target, not independently reviewed gold or evidence of unseen-adventure generalization.

## Candidate corpus and acceptance loop

Conks and Sheep are tuning material. Retain their pinned source/unit/assembly/interpretation manifests separately from render config and played writing. Freeze each candidate with source, dataset, config and renderer versions. Operator acceptance is per observed task; independent source review remains required. Orbital is a synthetic genre stress theme, not Starfinder source fidelity.

| Task | Gold expectation | Evidence needed |
| --- | --- | --- |
| Read an opening | Paragraph hierarchy/emphasis and conditional speech remain legible; no repeated diagnostics interrupt prose | Source PDF comparison and operator reading trial |
| Find a place/person | Nonlinear exploration, coherent sourced profile, explicit testimony/inference | Exact refs plus operator navigation trial |
| Find media | Map/image retains identity, caption, audience and source relationship | Source asset manifest and displayed image |
| Restyle | Small editable JSON; preview, Apply, cancel/revert, refresh; writing/content untouched | Rendered before/after and persistence/isolation checks |
| Construct a card | Structured prose, dialogue, GM material, choices and media usable without custom renderer code | Timed construction trial and source mapping review |
| Edit with agent | Captured target/basis, inert proposal, deliberate Apply, stale result rejected | Owning-boundary integration tests; local prototype alone cannot pass |
| Recover | Previous source/config/writing accessible; backup/restore round trip | Actual export/import and verified content equality |

For each iteration record failures, time/steps, fidelity, readability and corrections. Retention counts do not score semantic correctness. No aesthetic pass can hide disclosure or mechanics failure. Current gaps: source typography/emphasis flattened in OCR, source-specific callouts incomplete, no native agent presentation tool, downloaded-file transport unverified, no unseen-adventure evaluation. Typed media construction and local-file restore were subsequently implemented and checked in iterations 2–4.

## First useful iteration

Style button on private boards edits a bounded token config: paper/ink/chrome/workspace/accent/muted colors, built-in body/heading fonts, size/leading/padding/radius/reading width. No arbitrary CSS, URLs or remote font execution. Presets supply editable starting points, not source-style extraction. Default styling stays byte-preserved in design-v1. Local config is stored with the play backup but does not alter source bytes, evidence or played decisions.

Local proposals capture board ID, source pin and exact config basis. Preview is inert with respect to persistence; Apply validates current basis. Cancel/close restores persisted config. Restore design v1 removes the override. Production config revision, concurrency and durability are not claimed by browser storage.

## Buddy-owned contract handback

The existing World Plan proposal contract edits Markdown at a captured selection/caret against World+document revision/hash and editor draft basis, with review/Apply before ordinary Save. It currently has no theme/media configuration target. A future presentation contract needs: World+document ownership; committed content and config revisions/hashes; stable block/media targets; typed valid theme fields and audience-preserving media references; idempotent action identity; inert proposal/preview; exact-basis stale checks and late-result fencing; explicit Apply to draft; Save commit; conflict/recovery and export/import. Do not encode styling changes as fabricated Markdown, graph IDs or hidden production schema extensions. ARCHITECTURE/PRIME must settle ownership before native integration.

## Iteration 2 — block construction

Compose blocks builds a selected lens from typed paragraph/heading/list/read-aloud/GM-note/media blocks. Original source projection and exact citations remain accessible; authored adaptation is never recast as a source claim. Media is limited to selected source assets and retains GM/player-review labeling. Preview and Apply capture board/source/card/lens/current-composition basis. Restoring the source removes only the composition overlay. JSON and Add block are an initial construction interface; fast/easy operator authoring is not yet proven. Native agent edits and source-format extraction remain unfinished.

The synthetic Observatory fixture pins expected heading/emphasis/list/callout structure with no imported source claims. Model tests reject unsupported media, audience-field invention and stale target/basis, escape HTML, and verify gold structure. Browser preview→Apply→refresh→Restore was exercised and temporary synthetic adaptation removed. Source PDFs/datasets and writing remain separate. Selected previously PDF-audited boxed/italic/conditional dialogue gets a reading treatment; this is source-aware adaptation, not reproduction of every source font or ornament.

## Iteration 3 — direct construction trial

Composer now exposes prose/list/caption fields, heading level, selected source media, Add/remove/reorder/undo and collapsed advanced JSON import. Unapplied drafts save separately and reopen without changing the displayed preparation. Apply/restore archive prior presentation state into local backup history; source data and played notes remain separate.

Concrete Sheep task: open compound Situation; emphasize its existing conditional-conflict sentence; add media; select the compound map; caption it; Preview; Apply. Eight control interactions from opening the composer, with no JSON editing. Three existing choices and the conditional retreat link remained accessible; map kept GM/player-review labeling. Reorder and undo were observed. Test adaptation was restored afterwards, with history retained. This is an agent-run interaction witness, not operator speed/ease acceptance or source-style extraction.

## Iteration 4 — live construction pane and recovery

Style and Compose now use a nonmodal docked pane. The canvas adjusts to its width; pointer dragging and arrow keys resize the divider. Valid style configuration and typed composition blocks preview on the canvas before Apply. Closing resets unapplied preview; composition drafts remain distinct from applied preparation. Switching tools clears the prior pane synchronously and ignores its queued close event.

Browser evidence: Style preset changed the live canvas; keyboard resize produced a 460px pane and the dialog was nonmodal. Direct Style→Compose switching retained the docked pane. Typing a synthetic sentence showed “Live preview · not applied” on the canvas; Restore returned the original projection. Private screenshot evidence remains outside Git.

Back up / restore offers downloadable or copyable JSON plus local-file/paste review. It validates board/source revision, preserves unmatched writing, archives the current state before replacement, and restores earlier revisions into their original revision key. Browser paste review/restore roundtripped the existing state. File chooser/download transport has not been independently proven in this iteration. Model tests cover writing, decisions, themes/compositions, invalid targets, and earlier revision handling.

The target remains a candidate: source/operator acceptance and the native World presentation edit contract remain outstanding.

Recovery follow-up: local file chooser loaded the exact private backup; Review enabled explicit Restore, and restoring returned to the canvas. Backup UI now invalidates an earlier review immediately when another file is selected, disables review while reading, and fences late file results against newer typed input and disconnected dialogs. A focused UI-handler test proves those races. Six model/UI test files pass. Downloaded-file transport remains unproven; local-file import and paste restoration are proven separately.

## Iteration 5 — direct styling

The same validated theme configuration now has color wells, built-in font menus, and bounded sliders for text size, line spacing, card padding, corner radius, and reading width. JSON sits in a closed Advanced disclosure and remains interchangeable with the controls. Apply uses the existing board/source/current-config basis guard. The action bar remains visible while the pane scrolls.

Browser evidence: one arrow-key step and one font selection changed the actual canvas to 17px Georgia without JSON editing. Reading width reached 600px; Apply plus refresh retained typography. The first refresh exposed duplicated width constraints (528px instead of 600px); fixed the card-versus-container sizing, then verified 600px after refresh. Restore returned the unconfigured design-v1 baseline. This is usability evidence for observed tasks, not source or operator acceptance.

## Iteration 6 — reviewed source corrections

Audit reconciled the reviewed C045 source package with the Conks candidate. Its two corrections now render as explicit reviewed overlays against exact unchanged OCR-unit text. The derivative captures reviewer, package identity/revision/hash, source-PDF hash and visual-review metadata. Original readback retains the OCR plus the reviewed derivative. The old board revision is archived and remains a previous writing key; the new private candidate is separately pinned. No source package is rewritten or published.

Browser checked the corrected statblock and its disclosure/readback. Model checks reject missing units, mismatched original text/source PDF, missing reviewer and invalid package digest; overlays do not change authored adaptations or contextual multi-span text. Both private boards validate; seven test files and Session29 fixture checks pass. This reconciles those two reviewed corrections only, not full source or gold acceptance.

Completion audit remains partial: design-v1/Session29 and observed construction/style/recovery invariants have direct evidence; source hierarchy/media/identity coverage still needs wider review; native agent presentation integration is outside the current prototype contract; operator task acceptance and downloaded-file transport are not proven. Candidate remains active for those requirements.
