# MEDIA: shared saved-image projection

Status: COMPLETE — PR#1421 merged at `3dfa43f946837d4ffb1a1a1d3c84b33d497e0b31` and delivered on5202. Implementation/write lease ended. Reconciled2026-10-18.

Current disposition: Independent Architecture source/render review; actual ready images in Plan Cards and Live on5202; transient reader controls left saved Plan and Run unchanged. This is projection, not Live editing. Remaining work requires its own bounded successor; this document grants no continuing lease.


Invariant: admitted saved media occurrences render actual authorized ready images in the shared static card reader used by Plan/Live; editing retains current MediaImageNode behavior and exact asset/presentation Markdown contract. Extract the existing authenticated readyasset/CDN resolution hook for shared reuse. Keep static occurrence presentation and transient read-only expand/collapse separate from writable editor transactions. Same asset used twice remains two independent occurrences. Unavailable asset preserves alt/reference and surrounding prose; invalidmetadata or unsafe delivery URL never renders as an image. No image generation, save-asset, document mutation, schema/API or new media-type contract.

Exclusive expected paths: this handoff; apps/live-control-ui/src/media/useSavedMediaImage.ts (new), SavedMediaImage.tsx (new); apps/live-control-ui/src/tiptap/extensions/MediaImageNode.tsx; apps/live-control-ui/src/markdownReader/ReadOnlyBodyContent.tsx and .test.tsx. Existing media CSS reused. Extend lease explicitly if evidence requires another path; no unrelated editor/controller changes.

Implementation approach: static reader continues safe generateHTML for supported AST, then mounts read-only saved-image presenters into the generated media occurrence slots, using React portals scoped to that rendered snapshot. Do not grant mutation through reader controls or weaken unsafe-node admission. Metadata lookup is keyed/fenced by asset identity, resolves existing ready imagedelivery.net HTTPS delivery only, and ignores late responses after replacement/unmount. Editor uses same resolver but retains existing resize/drag/persisted-collapse logic.

Verify actual Markdown-to-AST-to-shared-reader with repeated saved asset references, distinct width/collapse, surrounding callout/table/prose and Graph refs; independent transient expand, source immutability, invalid asset/metadata/URL and replacement races. Existing editor manipulation and reader/SceneCard tests, typecheck/build, cumulative diff and independent review. Render existing saved media on real card/Live projection with desktop/narrow proof; use existing ready assets without provider spend. Preserve all real documents/notes/Run state; if preview activates a disposableRun, capture/guardedly restore activepointer. 5202 asset delivery afterreview, rollback retained. No API restart.

Operator has chosen Run-local versioned Live edits with Plan unchanged, existing scenes first. That future server/editing contract is separate; this slice restores display only and is not whole-goal completion. This lease ends after accepted merge/delivery.
