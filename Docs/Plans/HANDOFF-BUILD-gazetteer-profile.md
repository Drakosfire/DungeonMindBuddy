# BUILD — named gazetteer extraction and publication

Status: ACTIVE; #1155 merged a79c6f47970b95be5b1354bcc0123379ca08b157; re-anchored.
Operator Mirathorn goal; PRIME implementation, ARCHITECTURE review.
Branch codex/build-gazetteer-profile; lane /tmp/buddy-gazetteer-profile.
Design base 6c9e4d6dbe96a5f8dcd99d12caa8db55e9605407.
Topology serial publication/profile successor; no overlapping model writes until gate.

Outcome: exact versioned gazetteer profile preserves named livestock definitions,
uses, geography, governance, recurring festivals, qualified history/beliefs, and
unplayed hooks without recap semantics. Existing vocabulary only. Species is a
creature kind definition, not a manufactured individual; products remain qualified
source descriptions unless independent item identity exists. No played episodes,
statblock invention, automatic identity merges, beats or party participation fill.

Closed exact publishable profile catalog preserves Shepherd pilot identity and
validator. Run-recorded profile selects corresponding bounds; unknown versions,
plumbing publication, recap/non-null-session input and profile mismatches reject.
Build opts in explicitly using existing profile transport and exact saved envelope;
old run reopen retains recorded profile. Split UI selector if independently useful.

Proposed paths for activation after gate: new gazetteer profile/catalog and tests;
graph_preview_runner profile registration; routes/graph_preview.py allowed pair;
services/extract_promote.py recorded-profile validator; models/extract_promote.py
closed literal; src/graph_memory/worldbuilding_write_plan.py profile admission;
useBuildExtraction.ts and owning tests only if minimal opt-in is coherent.
Exact allowlist must be verified from current files before activation.

Evidence: synthetic source equivalents through passes->typed preview->reviewed
plan/contribution, durable recorded profile, native endpoint representability,
quotes/modality preserved, no invented individuals/events/statblocks. Actual
Mirathorn source fidelity reviewed separately. No provider/serving/native writes
under this blocked design. Six source spans frozen in private coverage packet.

Activated exact server-profile write set: this handoff;
src/graph_memory/extraction/worldbuilding_gazetteer_profile.py;
src/graph_memory/extraction/worldbuilding_profile_catalog.py;
src/graph_memory/extraction/graph_preview_runner.py;
apps/live_control_server/routes/graph_preview.py;
apps/live_control_server/services/extract_promote.py;
apps/live_control_server/models/extract_promote.py;
src/graph_memory/worldbuilding_write_plan.py;
tests/test_worldbuilding_gazetteer_profile.py.
Build UI explicit selection is a separate bounded consumer after server admission;
existing Build defaults remain pilot. No DOGFOOD file overlap or serving/provider writes.
