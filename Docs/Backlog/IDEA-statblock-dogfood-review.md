# Idea: dogfood and review statblocks end to end

**Status:** IDEA — assessment, not an implementation assignment.
**Captured:** 2026-11-24
**Owner:** Buddy statblock authoring and Combat.
**Sequencing:** The [product roadmap](../Roadmaps/ROADMAP-demo.md) owns sequencing.

Conduct a deep, representative statblock dogfood and product/technical review:
create or bring in a statblock, inspect and edit its mechanics, validate, preview,
save and reopen the exact revision, create a reviewed variant where supported,
and use the intended saved mechanics in Combat. Assess usability, fidelity,
identity and revision handling, failure and recovery, and the boundaries between
generated and manually authored content. Identify which steps actually work in
the tested environment and record gaps and evidence without claiming full
qualification from component tests alone.

Check current movement-mode and effect-reference editing against the preserved
design and tests in [closed #869](https://github.com/Drakosfire/DungeonMindBuddy/pull/869);
do not assume its old implementation is needed or shipped. The existing
[disposable legacy statblock rehearsal](MAINTENANCE.md) and
[issue #3573](https://github.com/Drakosfire/DungeonMindBuddy/issues/3573)
remain a narrower operational follow-up, not evidence that this broader review
is complete.

Use disposable state and representative fixtures. Separate findings into
independently reviewable improvements after the review; this note does not
authorize provider calls, production changes, or implementation.
