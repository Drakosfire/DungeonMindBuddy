# BUILD — explicit gazetteer extraction selection

Status ACTIVE stacked consumer of #1157 head bc064cff30cc00af8162052d05c09dcb638ca06f;
merge server first. No runtime launch before accepted server adoption.
PRIME implementation; ARCHITECTURE review; DOGFOOD rendered inspection.
Branch codex/build-gazetteer-opt-in; lane /tmp/buddy-gazetteer-opt-in.
Design base a79c6f47970b95be5b1354bcc0123379ca08b157.
Topology stacked consumer; parent codex/build-gazetteer-profile exact bc064cff.
Code review may proceed while final server test-only verification settles.

Exact proposed write lease: this handoff; BuildIngestToolbar.tsx;
useBuildExtraction.ts; useBuildExtraction.test.tsx; BuildGazetteerSelection.test.tsx,
all production/tests under apps/live-control-ui/src/buildSurface.

Closed explicit profile choice: existing pilot default, gazetteer opt-in for
Mirathorn. Preserve exact saved envelope/document/revision/hash and recorded
old-run profile on reopen; selecting profile cannot alter an in-flight request.
No source edits, automatic extraction/publication, World overrides or credentials.
Verify submitted exact pair, pilot unchanged, switches/document navigation, stale
responses and stored run identity. Pin exact server merge before activation.

Scope amendment: existing BuildIngestToolbar.test.tsx fixture now records real
returned pilot profile; preserve all original owning cases. New launch must match
returned composite profile; historical reopen retains run-recorded identity.
