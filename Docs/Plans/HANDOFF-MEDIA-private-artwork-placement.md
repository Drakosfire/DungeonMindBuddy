# MEDIA — place retained artwork privately

ACTIVE: PRIME activates this serial slice under the standing authoring/preparation/play goal after independent Sol-low invariant critique approved the direction. Base a8c47bc8fa7994a77cc1b9188ed9ca862348fe0b; branch codex/private-artwork-placement; reuse buddy-context-loop checkout and dependencies. Open PRs 1868/1855/1853 (ingestion), 1828 (hosting) and 1764 (held capability work) inspected without overlapping media writes.

## Invariant
Private staged assets already have durable owner-authorized originals. Public CDN publication is independent of placement. Admit only staged or ready, revalidate exact asset and access generation immediately before insertion, and preserve document identity/version/editability/caret/abort guards. Store only the existing dmb-media:UUID reference. Staged rendering reads the authenticated no-store original, checks identity and immutable metadata/MIME/length correspondence, owns a Blob URL and clears it on replacement, unmount or authentication change. Reject uploading/unknown/malformed/foreign/unauthorized results. Ready rendering retains HTTPS imagedelivery.net validation; no fallback authority. Media belongs to the owner, not a fabricated World association. Read-only Runs may display references but cannot place or write.

## Exclusive lease and resources
This handoff; truthful predecessor settlement in HANDOFF-MEDIA-original-image-download.md; apps/live-control-ui/src/media/{MediaImageWizard,DocumentImageStudio,useSavedMediaImage,OriginalImageDownload} and their tests; a shared originalImageBlob helper and focused media integration test; existing documentMediaBridge.test.ts if needed; guidedTour/{definition.ts,ImageObservations.tsx} wording only. No API, schema, provider, publication, source, persistence format or provenance changes. UI5202 protected reviewed delivery owned by PRIME; API8000 and primary DBs retained unchanged. Ordinary saved future-document changes are separately accounted; no old Run or draft replacement.

## Verification
Provider-free staged click/drag, ready rendering, rejected states, identity/auth generation failure, late replacement, malformed original, object URL cleanup, actual document bridge serialization/reload and read-only/draft guards. Typecheck/build; cumulative exact-head independent Bugbot review, CI, merge and protected UI-only delivery. Ordinary use must prove saved UUID-only reference and authenticated decoded private image without CDN Save; older library artwork remains an existing example, not newly generated tour credit. Preserve pending public-upload question without retry or upload. Full walkthrough and operator acceptance remain open.

## Predecessor settlement
PR1872 merged b66c35c1241925106fc17c5d167e0a1cc620522a and delivered reviewed head 4258d5fc2820eef1ed03d5e5345102b9a340d76a. Both Conks and Sheep original downloads matched retained SHA256 bytes. This slice adds placement; it does not repeat generation or publication.
