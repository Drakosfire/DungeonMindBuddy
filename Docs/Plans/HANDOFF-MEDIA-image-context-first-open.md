# MEDIA: diagnose image contextual-menu first opening

Status: SOURCE SETTLED. PR2315 merged as
7ec9bcec9beed23c71f911943062bfc9c94bda51 from independently reviewed
7f64c98f5a9dc06b6bbf50128ed82e3aabfc71ab. Exact hosted/build evidence validates;
full7445/164 adds two passing regressions with no new/changed failures. Source
lease released; runtime activation remains held. Historical allocation follows.
Status at allocation: ACTIVE bounded investigation/fix. PRIME owns the existing
buddy-context-loop checkout on codex/image-context-first-open from verified
main e2d75649b577f679af8f05e24329e4cb3f6121a6. Source retirement PR2312 stays
frozen at ce59f851d10b258a44f2459edd84dddddb2868f4 until qualification resolves.
Serial prerequisite if a confirmed repair is required; merge it before re-anchoring
2312. No runtime, provider, DB or browser-state lease. Recovery hold remains.

Outcome: establish why an explicit Edit image click can leave the menu closed,
then repair the owning boundary if confirmed. The preserved full-suite failure is
media/ImageContextEdit.test.tsx, explicit new-image case: Instructions not found;
raw DOM shows aria-expanded=false. It is not yet classified as inherited or as
a production defect. Do not remove, suppress or weaken that test to qualify2312.

Expected writes: this handoff; apps/live-control-ui/src/media/ImageContextEdit.tsx
and ImageContextEdit.test.tsx. Temporary local diagnostic instrumentation is allowed
only on those files, clearly labeled and removed before source qualification.
Keep original file hashes, commands, traces and failures in established private
Projects/.buddy/evidence. Do not modify Tiptap/framework infrastructure without
checkpointing ownership and scope. Active CI/Surface PRs do not own these paths.

Preserve exact owner-generation/asset fences, draft hydration, request aborts,
read-only controls, current document edits and candidate ownership. No retries,
new storage or duplicated editor. Diagnose mount versus passive reset versus
node-view replacement before choosing a fix. Retain all existing assertion fields
and default timeouts. If the failure is only test readiness, prove that distinction.

Verify a meaningful reproduction and owning lifecycle cases, inspect cumulative
diff, obtain independent Bugbot review, and run exact-head local hosted/build and
discovered verification before merging any repair. Keep inherited red diagnostics
visible. Completed CI optimization is not reopened; this is a specific unresolved
qualification failure. No operator data or image-provider call is necessary.

## Confirmed owning-boundary failure

A bounded instrumented run reproduced the same missing-Instructions failure in
another existing image case on attempt6. Its trace orders the same component's
open callback before its mount reset, then renders closed; it shows no identity
replacement. Keep the trace and temporary diff as diagnostic evidence only.
Temporary logging is removed from the implementation.

The uninstrumented regression clicks the committed control from its parent's
layout phase, before child passive initialization. It fails on the original
component with the same closed-menu symptom; the other11 cases pass. Move only
the asset/authority initialization and listener lifecycle to useLayoutEffect.
Keep resets, cleanup, current-generation checks and defaults otherwise intact.
A second regression verifies asset replacement closes the prior menu and drops
its candidate/instructions before opening the new asset. No framework or editor
infrastructure change is required; the originally leased three files suffice.
