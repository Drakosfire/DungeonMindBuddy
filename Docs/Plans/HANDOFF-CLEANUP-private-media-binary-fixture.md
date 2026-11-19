# CLEANUP: align private artwork round-trip fixture with binary delivery

Status: ACTIVE under the user-authorized cleanup goal, including review and merge.
Base: 84ba5c4191320467cbd80810f5b601d69f9c47f5.
Branch: codex/private-media-binary-fixture, existing cleanup checkout.
Topology: serial after merged #4088; no unmerged behavioral dependency.
Owner: cleanup steward; independent Bugbot review before merge. Follow-up #4074.

Outcome: replace the round-trip test's obsolete JSON/data-URL original response
with the existing authenticated binary contract: metadata plus a PNG response
whose MIME, digest header and byte length agree with the fixture. Use a valid
68-byte one-pixel PNG and derive its metadata SHA256 from those exact bytes.
Preserve real document insertion, UUID-only Markdown/JSON reload and no persisted
URL assertions. Require one pre-insertion metadata verification, then reloaded
metadata/original reads, no writes, no-store
and abort signal; inspect the Blob bytes/type/size and its single URL revocation.
Restore the test URL global after cleanup. No runtime or authorization changes;
this does not establish real-provider delivery or browser image-decoder behavior.

Write lease: apps/live-control-ui/src/media/privateArtworkRoundTrip.test.tsx,
this handoff, and HANDOFF-CLEANUP-neutral-core-host-boundaries.md for truthful
predecessor settlement. All 61 open PR file lists checked at activation; no overlap
on existing leased files. Shared media runtime/fixtures remain read-only.
No servers, providers, operator databases or remote hosts are written.

Verification: focused before/after round-trip and existing useSavedMediaImage
contracts (denied/mismatched bytes, owner/asset changes, pending-read sharing and
URL lifecycle). Baseline: 15 passes/1 failure; corrected pair: 16 passes. An
intermediate binary-fixture run exposed the incorrect two-read assumption; the
final diagnostic preserves the actual pre-insertion verification plus two display
reads. These diagnostics are not final exact-commit evidence.
Exact-head hosted verifier/build/validator and full discovered
diagnostic under the shared frontend lock with verified Projects external scratch.
Require the one original failure to resolve with no renamed/added/omitted cases,
new failures or changed remaining leading messages. Preserve unrelated red results,
two conditional inventory extras and earlier unresolved quote-correction case.
Independent exact-head cumulative source/raw-evidence review before merge.
Original cleanup owner/release gates remain outstanding.
