# AGENT — citation tooltip viewport

ACTIVE serial PRIME follow-up to merged #1638 (8d351fb9afaae8310ff1da36fe3b87c822ceba81),
branch codex/citation-tooltip-viewport, existing buddy-context-loop checkout.
Rendered 650x731 verification found the absolute tooltip clipped at the transcript
edge and extending horizontal overflow. Fix placement using a viewport-clamped
portal; keep named keyboard/hover attribution and click-only exact evidence.
Write lease: this handoff; apps/live-control-ui/src/planSurface/components/
{SourceCitation.tsx,SourceCitation.css,SourceCitation.test.tsx}.
One Bugbot-reviewed PR, PRIME merge and guarded UI-only5202 rollout. Verify actual
narrow-pane tooltip bounds, no tooltip-induced overflow, focus attribution and
click expansion. No API, provider, storage, source access or active retrieval edits.
Prior #1638 reviewed head f5b8cdc8cde968f570335dd28ef70969442d552f, two Bugbot cycles;
300 author tests passed; protected UI rollout preserved1843 APP rows,85 mechanics
files and17 frozen sources. Source activation remains preserved in Git stash.
