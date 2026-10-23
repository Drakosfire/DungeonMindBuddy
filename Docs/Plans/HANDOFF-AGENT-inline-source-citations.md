# AGENT — inline source citations

ACTIVE serial PRIME slice, base 6c8ccbc3c2a87b513186b9c32d741da528a00e92,
branch codex/inline-source-citations, existing buddy-context-loop checkout.
Operator requests small numbered circles after supported statements, source-name
and passage details on hover/focus, click to expand exact evidence, shared across
surfaces. Native-source activation work is preserved in the named Git stash;
it is suspended during this serial slice and must be resumed after settlement.
No overlapping open citation UI PR at the current census.

Outcome: a shared citation marker and disclosure component used by current source
passage/native-section answers and existing inline Graph markers. Presentation
only: immutable citation indexes, World/turn scope, exact receipt/hash validation,
request epoch guards and unavailable behavior remain binding. Loading is click
only; hover/focus must not read evidence. Number citations consistently across
one answer; keep full named attribution in accessible labels and tooltip/panel.
No changes to provider prompts, storage, source access or historical protocols.
Failure cases: duplicate numbering, Markdown/table placement, wrong source index,
late responses after scope changes/close/unmount, inaccessible hover-only details,
and narrow panes. Preserve readable output for answers without citations.

Writes: this handoff; apps/live-control-ui/src/planSurface/components/
{SourceCitation.tsx,SourceCitation.css,SourceCitationEvidence.tsx,
sourceCitationReads.ts,SourceCitation.test.tsx,SurfaceEvidenceAnswer.tsx,
SurfaceEvidenceAnswer.test.tsx,BuildSourcePassageEvidence.tsx,
NativeSourceSectionEvidence.tsx,WorldPlanAgentAnswer.tsx,WorldPlanAgentAnswer.css}.
One Bugbot-reviewed PR; PRIME merge. Verify focused evidence/Markdown tests,
typecheck and narrow-pane rendered behavior. Runtime 5202 remains owned by PRIME;
paired deployment stays with protected runtime procedure and retained-state checks.
