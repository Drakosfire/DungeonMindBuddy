# FOUNDATION — manual authoring managed/native World binding

SETTLED: PR #1655 merged at155c91e30c9ed9fd6ddfee12c67edbb294bd0ea0;
independent Bugbot approved961bc536;95 author and independent checks passed,
1 skipped. Protected API delivery preserved2056 APP rows, all native rows,
89 mechanics product files and22 frozen components. Rehearsal Combat reopened
after restart. Manual selection UI/J3 acceptance remained open.

Original serial PRIME slice from e8eac1f5b77cd99b7c320589c743dba1e5ef2f85,
branch codex/manual-authoring-world-binding in reused buddy-context-loop checkout.
One implementation PR, independent Bugbot exact-head review, PRIME merge and
protected API delivery for 5202. Open PRs inspected; no overlapping backend lane.

Manual GraphObject prepare/confirm currently uses one World identifier for both
registered Build ownership and native graph authority. Registered sources belong
to managed Worlds; native publication must use the server-resolved binding.
Resolve the exact registered source/document and managed/native binding at this
service boundary. Keep original source span proof under managed ownership. Derive
only a transport copy for native source admission; do not weaken the generic
admission adapter or mutate registered artifacts. Registered Build sources are
World scoped: require campaign control namespace equal to their managed World and
reject genuine campaign ownership rather than guessing its meaning. Native
contributions use campaign_scope=None; existing recap publication keeps its
campaign scope and authority semantics.

Seal the managed/native IDs, binding version, document ID/revision and exact
source artifact/hash in the existing signed confirmation. Re-resolve and compare
before confirm/recovery/publication. Missing mapping, changed ownership/binding,
foreign source, changed span/body and stale parent must refuse without appending.
Do not add a public caller-selected native ID, compatibility fallback, migration,
new graph writer, model call or source cap. This backend prerequisite does not
claim the later clean-document selection UI or full J3 acceptance.

Critique: mapping only at prepare leaves confirm able to publish into an obsolete
World; checking only the native ID misses a binding-version change. Rewriting the
stored artifact would corrupt managed ownership. Treat managed World as explicit
request authority and re-prove the whole sealed binding before any native action.
Exact source/run and registered-reader fences remain independent.

Exclusive writes: this handoff; graph_object_authoring_prepare.py,
graph_object_authoring_commit.py and new graph_object_authoring_binding.py under
apps/live_control_server/services; tests/test_graph_object_authoring_world_binding.py
and affected current authoring fixture tests; Docs/Roadmaps/ROADMAP-demo.md and
Docs/Plans/HANDOFF-FOUNDATION-plan-writer-schema.md for predecessor settlement.
No UI, registry, dependency, schema, producer or retained-source edits.

Verify real prepare→confirm with distinct managed/native IDs, immutable artifact,
World-scoped assertions/admission, same-key recovery, mapping/version/ownership
and source drift refusals. Run existing authoring/run-span/recap/route cohorts.
Known inherited merge-guard module imports a removed test helper on base; preserve
that failure rather than restoring legacy tests. Review cumulative diff, then
protected deployment with APP/native/mechanics/frozen component retention checks.
