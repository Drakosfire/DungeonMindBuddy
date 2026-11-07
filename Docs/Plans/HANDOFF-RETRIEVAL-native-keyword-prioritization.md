# RETRIEVAL: reversible native keyword prioritization

Status: ACTIVE. PRIME owns this operator-authorized efficient-retrieval slice.
Base: 02e5c158d735a81511f1ca68f4caaec8f1fbce8f (remote main, 2026-11-07).
Branch: codex/native-keyword-prioritization, existing buddy-context-loop checkout.
Topology: serial after merged/delivered PR2183. Open INGEST lanes do not own these
paths. Play2172 remains held; this adopts its existing shared integration boundary,
not an independent Play implementation. No runtime lease until review/CI and exact
integration delivery preparation. Use existing dependencies; no new environment.

## Outcome and invariant

Select optional literal content keywords in the existing first native retrieval
batch. Reuse the exact acknowledged selection to prioritize matching sections in
the next view. Preserve direct full-source choices, Graph/Rules/saved-page choices,
explicit acquired references and unknown metadata. Reuse the existing broad
expansion to restore all source/section offers. No new planner, search execution,
source authority, publication, model change, output cap or corpus mutation.

Keyword-only votes cannot force another acquisition round. Empty, unmatched or
unavailable hints retain the existing view. Handles bind the literal query and
actual World/revision/attempt scope. Recovery reconstructs hints from admitted
selection events, not a second state store. Historical decisions without keyword
candidates retain their exact wire and selection interpretation. A no-op reader
fence prevents older code from misinterpreting newly recorded metadata choices;
no rows are rewritten. Source and grounding checks stay at their current owners.

Frozen combined first-batch experiment selected keyword hints in 775ms and reduced
155 literal-match sections to 74 mechanically. It is not live latency or coverage
proof. Earlier standalone classification and label experiments remain retained;
no manual gold or claim edits. Qualify this implementation with original and
contrast ordinary runs before claiming useful speedup.

## Exclusive expected writes

- This handoff and Docs/Plans/HANDOFF-RETRIEVAL-build-native-dialogue.md settlement.
- src/application_state/agent_conversation/native_source_keywords.py (pure hints).
- src/application_state/agent_conversation/jev_retrieval_contract.py.
- apps/live_control_server/services/corpus_source_navigation.py.
- apps/live_control_server/services/plan_jev_driver.py.
- src/application_state/migrations/versions/20261107_0123_native_keyword_choices.py.
- tests/test_jev_retrieval_contract.py.
- tests/application_state/test_surface_native_acquisition.py.
- tests/application_state/test_surface_native_decisions.py (optional final fixture
  decision; terminal keyword-only selections must not request another provider).

## Verification and resources

Exercise real SDK authorization/selection -> APP reload -> owning driver -> Core
source read, keyword-only fallback, broad expansion, stale parent/attempt refusal,
empty/unmatched terms and mandatory acquired references. Preserve historical wire
replay. Use disposable APP54329 and synthetic Core fixtures only; primary APP54331,
Core54330 and benchmark55447 remain untouched by tests. Save private experiment
and test evidence in the established runtime-evidence root. Inspect cumulative
base/head diff; independent Bugbot review, all CI, then merge/deliver under standing
PRIME authority. Ordinary performance uses the fixed writer and retained source
pins; compare rounds, reads, context, latency and supported coverage. Whole-goal
activity, References and operator acceptance remain open.
