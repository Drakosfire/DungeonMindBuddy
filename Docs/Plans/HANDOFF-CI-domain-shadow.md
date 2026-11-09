# CI: conservative domain prediction in shadow mode

Status: ACTIVE private verification/design candidate under coordinator's permission
 to inspect whether shadow can stand alone without weakened gates/dependencies.
Branch codex/ci-shadow-standalone-proof; base current-main
5d63a5c742e60a3e5338847f3fecc02f12a9efc7; isolated verification checkout.
This is a local reviewable tree, not a replacement/publication/merge of PR2299.
Published PR2299 stays frozen at844025e4, stacked onad540, and HOLD on its red stack.

Candidate topology parallel-independent: current main plus only shadow-owned
files and one inventory entry. No B fast-gate command/workflow/test is a code
or verification dependency. All existing main workflows/commands/test coverage
must remain byte-identical; PR2298 and its failing discovered suite stay intact.
No selector consumer, selection activation, skip/continue-on-error or qualification
claim. Fresh complete-tree independent review and coordinator topology disposition
are required before updating any published PR; no ready/merge action here.

Expected exclusive writes: scripts/ci_domain_shadow.py; ci/domain-selection-v1.json;
tests/test_ci_domain_shadow.py; .github/workflows/domain-shadow.yml; this handoff;
ci/test-classification.json one new shadow guard entry only, copied onto current
main classification with no removed entries. Published C classification lease stays
frozen while its owner prepares this private proof; no concurrent writer. Other
stage3/qualification files and their published branches remain untouched. No product/graph/ADV source edits.

Version1 predicts docs-only and one explicitly scoped presentation CSS path.
All declared runtime domains close conservatively to full regression; unknown,
shared auth/schema/migrations/factories/dependencies/CI paths, deletion/rename,
invalid mapping/source/diff and explicit override fall back to full. Paths for
future narrow runtime selection are not proven and therefore never narrowed.
Reports publish base/merge-base/source SHA, changes, reasons and suites with
shadow-only and gating_enabled=false. They cannot suppress any PR gate or set
qualification/main readiness. Rollback is absence/disablement of this reporting
workflow; no branch protection change.

Verify rename/deletion/mixed/error/monotonicity, dependency closure, unknown and
shared fallback, explicit override and source binding. Replay synthetic fault
origins (tenant/CAS/publication/draft) to require full fallback. This tests mapping
coverage only; it is not actual injected-product fault detection. Full real fault
injection/replay and measured zero misses, full qualification and owner response
remain mandatory proof before any stage5 selector consumer/rollout. Main graph
qualification stays HOLD; candidate proof never satisfies it.

2026-11-09 bounded evidence extension under coordinator's explicit actual historical
replay/controlled-fault authorization: adopt scripts/ci_shadow_evidence.py in this
exclusive lease, plus existing shadow tests/workflow/handoff. Re-anchored main f6e174e;
open PRs2297/2276/2262/2219 and ingest lanes inspected, no overlapping expected
writes. Replay actual pinned historical commit diffs, not invented paths. Exercise
process-local tenant/CAS/content-publication/draft faults against unchanged owner
assertions and disposable APP template/clone fixtures; no product file edits,
external outreach or native/ADV writes. Fresh process baseline after injections
proves mutation removal. These bounded backend samples do not establish frontend
or native publication fault detection, zero misses generally, main qualification,
or stage5 readiness. Existing full gates and shadow-only mode remain unchanged.
