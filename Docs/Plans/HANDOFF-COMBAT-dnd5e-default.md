# Combat D&D 5e configuration

ACTIVE under the user's Combat default-system and passing-merge assignment.
Root owns fc67 on codex/combat-dnd5e-default based on
7d94acd0f265d98d82b557b4edd747c64f26fe82. Serial successor to #4280, reviewed
at 2d03d0a45f40affd52941371c1fac956738a4987 and merged at the base.

Persist the D&D 5e selection as an explicit immutable configuration when
the standalone roster creates the default encounter or keeps the sample.
Reuse the existing tracker field set. Existing generic records and callers
that omit the ruleset keep their existing configuration. Custom systems
continue through the current profile writer.

Write lease: this handoff, src/application_state/combat_encounters/rulesets.py,
the CombatRosterModule and its owning test, and tests/test_live_combat_encounters.py.
Review neighboring #3668 and #3716 as read-only owners. No migration,
provider, host, deployment or live data writes.

Verify through normal HTTP create, exact committed reread and sampled roster
creation, preservation of generic creation and the explicit unsaved sample.
Run exact source frontend and backend checks and independent review.
Production publication follows this slice.
