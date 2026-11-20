# DOGFOOD — Scene lens reader

Status: ACTIVE. Operator authorized reusable UX primitives and prototype exploration; PRIME directed this bounded slice after pinning the ConversationDock touch repair at b79c162c03a65a80eda3f4b744ba4f7f81bd4e8a.

Base: d7e32dbc0fee4d658c61221bfc21f13fe9bb4660. Branch: codex/dogfood-scene-lens-reader. Checkout: /home/drakosfire/.codex/worktrees/dogfood-scene-reader/DungeonMindBuddy.

Topology: parallel-independent. No dependency on PR #986. Checked open lanes #986 conversation layout, #970 Graph reader activation, #979 Plan Graph default, #985 recap target and #987 provider finalization. This slice changes none of their paths or runtime behavior.

Exclusive expected write set: four NEW files apps/live-control-ui/src/ui/SceneLensReader{.tsx,.css,.test.tsx,.stories.tsx}; this handoff; owned screenshots under Docs/Plans/evidence/dogfood-scene-lens-reader/. No shared registry, page, parser, controller, API, Graph, persistence or global token edits.

Invariant: show one caller-supplied reading lens while retaining caller-supplied full-scene access and stable choice/note slots. No invented section, missing-section warning or inferred chronology. The caller owns authored content, stable identifiers, notes and side effects. Null denotes full scene; missing/ambiguous lens identifiers safely display the supplied full scene without callbacks. Lens changes do not mutate scene data. No production adoption in this slice.

Verification: tests exercise controlled selection, keyboard navigation, complete-content fallback, absent/ambiguous sections and choice/note DOM retention. Ladle fixtures exercise parchment/quiet paint, partial sections and full-only content. Review desktop and narrow presentation; disclose inherited compiler failures. No model requests or production database writes.

Runtime ownership: isolated Ladle fixtures may use 5203 only after checking availability. Production 5202/8000, databases and provider calls remain PRIME/SERVER-owned. Stop owned fixtures after inspection.

Design references remain in the task-local surface-design-kit library: Mobbin is the interaction reference; DungeonMind and the successful play prototype inform paper, slate and sage styling. No third-party images are published with this PR.

Completion: inspect cumulative diff, commit, push and open one PR, attach it and send the exact head to PRIME for independent review. Merge requires separate authority.

Author verification, 2026-10-07: 8 focused tests pass; isolated Ladle build passes for four stories. Browser checks covered desktop parchment/quiet paint, 390px wrapping (document scrollWidth = viewport = 390), disclosure visibility, full scene content, and note values surviving lens changes. Screenshots are owned fixture captures, not production adoption evidence. Normal virtual pointer tabs measured 32px; CSS specifies 44px for coarse pointers, but real coarse-pointer hardware was not exercised. Full UI typecheck reports the unchanged ThreatPublicationPanel.tsx:553 TS2503 JSX namespace error, also observed in the predecessor/base work. Fixture location and previous/next buttons illustrate caller-owned slots; they perform no Graph or navigation action. Notes exist only in fixture state and are not durable play storage.

Independent review at8698917 HOLD found prose-only tabpanel skipped by Tab. Correction makes the supplied lens panel focusable and adds a real Tab-sequence test: selected lens ↔ named content panel. Nine focused tests pass. Fresh main6aa5d19c and GitHub MERGEABLE were verified; no unrelated main changes are merged into this existing branch. This corrects the review blocker, not a production adoption claim.

Validation correction: provisional f4d8a78 was pushed before the full result was inspected; its required lens-to-panel assertion passed, but an extra collapsed-Choices tab assertion failed. The corrected test directly proves forward and reverse panel navigation, and all nine tests now pass. No claim is made about JSDOM disclosure-child tabbing.
