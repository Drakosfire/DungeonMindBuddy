# WWN renderer test classification

ACTIVE: user requested repairing frontend verification and deploying Trace. Current main `53924014d46c006b12a05366f72281e94ce1d290` includes `StatblockRenderer.wwn.test.tsx` from #4757 without a classification, causing the automatic inventory check on #4764 to fail. This small parent slice owns `ci/test-classification.json` and this brief only. Classify the existing Vitest file with the adjacent fast renderer tests; do not alter selection, test content, or security gates.

Topology: serial prerequisite on `codex/ci-wwn-test-classification`; after it merges, rebase the Trace activity repair #4764 onto the merged parent and reverify/review it. Validate inventory and existing inventory guards; independently review exact head. No runtime or deployment state changes.
