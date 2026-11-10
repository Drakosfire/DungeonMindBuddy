# REFERENCE — native Play receipt validation

Status: ACTIVE PRIME serial UI repair, source base 8d8c805e999c5a4c33589da4718f78f5960c4dcc, branch codex/play-native-history-size. Parent2363 is merged/delivered; no unmerged dependency.

The original live Play reply now reads200 from API candidate dea8520d8dc9bb3212eafba59769dce5f1f3cca1, but browser recovery rejects its436376-byte native receipt. Exact diagnostic confirms work, receipt, completion, provenance, authored-reference and all individual digest checks pass. Only the old131072-byte whole-receipt limit fails. That legacy packet bound is not the native receipt contract.

Outcome: shared native Play validation adopts native shape/owner/manifest/receipt checks without the unrelated old packet byte ceiling. Keep the legacy ceiling for legacy receipts and every note/payload/World/provenance/digest check. No prompt, provider, source, generation, backend, schema or migration change. Preserve original failed attempt and current UI draft.

Exclusive writes:
- apps/live-control-ui/src/rulesLookup/playContextProtocol.ts
- apps/live-control-ui/src/rulesLookup/playContextProtocol.test.ts
- this handoff
- HANDOFF-REFERENCE-play-history-read.md only to settle merged/delivered2363 and distinguish this newly found client gap.

Independent open Index/native-demo/storage/CI lanes do not overlap. ADVERSARY coordination remains off. Existing checkout/dependencies and global frontend verification lock; no new environment.

Validate a legitimate native receipt above the legacy threshold, retained digest/note/manifest/foreign-owner refusals, original captured wire against exact source, focused protocol and conversation recovery tests, required exact-source frontend qualification and baseline comparison. Independent exact-head Bugbot then PRIME merge and owned UI delivery; the delivered API/schema147 and both PostgreSQL identities remain unchanged. Verify Check saved request, native citation, reload and restore prior conversation through ordinary controls, without inference replay or page/Run writes.

Working verification:82 protocol tests pass (six new large-native integrity cases); original436376-byte retained response passes every existing validator after the fix. Targeted recovery integration:8pass/6fail, all six failed IDs already present in the retained exactbecc5c4c7 discovered baseline; no new failures. Private original diagnostic and before/after logs retained.
