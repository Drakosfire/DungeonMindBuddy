# PLAN — saved authoring bytes at Play entry

ACTIVE serial PRIME slice on49ccd53c4d64fd7513090062d182e4cd643f56de,
branch codex/plan-saved-authoring-handoff, existing buddy-context-loop checkout.
One independently Bugbot-reviewed implementation PR, PRIME merge and protected
UI delivery on5202. API49ccd53c/APP0057 stays unchanged. Current remote/open-PR
census has no competing Plan writer lane.

Ordinary Sheep rehearsal prepared a scene encounter, manually saved and reopened
original/successor Noke mechanics, explicitly adopted only the successor, and
updated stale preparation prose. The Plan saved successfully, but Start Play
refused it. Read-only committed-revision inspection proves the saved text matches
its checksum. The editor supplied multiple final LF characters; the existing
Tiptap authoring writer collapses them to one before content newline normalization.
Start compares those canonical saved bytes to the pre-normalization local text.

Contract: preserve exact saved revision/hash/World/document/work identity, pending
write, selection epoch, edit generation and local-dirty checks. At the Start Play
byte comparison only, accept either the exact verified saved text or its existing
owned authoring transformation: strip trailing LF, append one LF, normalize CRLF/CR.
Do not normalize both arbitrary sides, trim spaces, fetch mutable latest instead of
verifying, ignore a changed hash, clear drafts or reload the editor. No new API,
legacy execution, repair of retained records or arbitrary limits.

Critique: broadly trimming both bodies could admit material whitespace changes;
matching only the writer's directional transformation preserves that distinction.
A delayed verification must still reject newly edited or switched Plans. Original
exact-byte historical reads remain exact; this is not a migration or compatibility
write path.

Writes: this handoff; Docs/Plans/HANDOFF-AGENT-authored-selection-codec.md factual
settlement; Docs/Roadmaps/ROADMAP-demo.md factual settlement;
apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx and PlanSurfacePage.test.tsx.

Verify ordinary save→Start without reload with multiple final LF and CRLF, exact
pin/session preparation and scene/editor continuity; reject noncanonical text/hash,
changed identity, working copy, stale verification and edits during verification.
Inspect cumulative diff, Bugbot exact head, typecheck/build, protected UI rollout
preserving APP/native/mechanics/frozen extraction bytes. Resume the actual Sheep
scene→encounter→new Play session→reload/restart rehearsal after deployment. The
complete goal and repeated full adventure acceptance remain open.
