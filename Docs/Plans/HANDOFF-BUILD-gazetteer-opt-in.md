# BUILD — explicit gazetteer extraction selection

Status BLOCKED successor to server profile #1157 reviewed merge.
PRIME implementation; ARCHITECTURE review; DOGFOOD rendered inspection.
Branch codex/build-gazetteer-opt-in; lane /tmp/buddy-gazetteer-opt-in.
Design base a79c6f47970b95be5b1354bcc0123379ca08b157.
Topology serial consumer; no launch of unsupported server profile before gate.

Exact proposed write lease: this handoff; BuildIngestToolbar.tsx;
useBuildExtraction.ts; useBuildExtraction.test.tsx; BuildIngestToolbar.test.tsx,
all production/tests under apps/live-control-ui/src/buildSurface.

Closed explicit profile choice: existing pilot default, gazetteer opt-in for
Mirathorn. Preserve exact saved envelope/document/revision/hash and recorded
old-run profile on reopen; selecting profile cannot alter an in-flight request.
No source edits, automatic extraction/publication, World overrides or credentials.
Verify submitted exact pair, pilot unchanged, switches/document navigation, stale
responses and stored run identity. Pin exact server merge before activation.
