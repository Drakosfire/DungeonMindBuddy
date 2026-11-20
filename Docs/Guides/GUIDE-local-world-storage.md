# Local managed-World storage

A managed World is not a database connection selected by the UI. Buddy uses
its configured application-state and DungeonMind connections and selects a
World within those authorities. The Buddy
[World catalog service](../../src/application_state/world_catalog/service.py)
stores managed World metadata in application state; the
[World container service](../../apps/live_control_server/services/world_container_registry.py)
provides Buddy's metadata and product access policy over that catalog.
DungeonMind owns native World identity, graph revisions, source/provenance
admission and governed publication. See the
[World architecture](../Design/ARCHITECTURE-campaign-supergraph.md) for the
ownership boundary.

Buddy's [producer source input service](../../apps/live_control_server/services/source_artifact_registry.py)
stores immutable producer source inputs through application state; that storage
is not itself DungeonMind provenance admission or graph publication. Some
stored `repo://` artifacts and other referenced source files still depend on
files in the selected artifact or source roots. The
[artifact root configuration](../../apps/live_control_server/config.py) requires
an existing readable directory when explicitly configured, and exact files can
be required for component reads. Do not assume that restoring databases alone
restores every file-backed dependency, or that a checkout-local legacy registry
is the current World catalog.

## Backup and recovery

Keep the application-state database, DungeonMind World data, and the file-backed
artifacts and source roots used by the deployment in a consistent, verified
recovery set. Record the selected roots and check the files referenced by the
restored records. Do not substitute placeholders, silently remap a source
identity, or reingest content as a shortcut for recovering the original
artifacts.

Use the [application-state recovery runbook](../Runbooks/RUNBOOK-application-state-authority-recovery.md)
for database backup, restore and explicit legacy metadata adoption. The
[production deployment runbook](../Runbooks/RUNBOOK-buddy-production-deployment.md)
describes verifying the WorldGraph database and associated managed World,
artifact, session and WorldGraph files as a recovery set. For local Play,
follow the [local Play runbook](../Runbooks/RUNBOOK-local-play-dogfood.md)
and use a separate Buddy application-state database.

Tests for the [World catalog and container boundary](../../tests/test_world_container_registry.py)
and [HTTP container behavior](../../tests/test_live_world_containers.py) include
cases where a registered World exists without its source directory. These tests
are focused evidence for that boundary, not a complete restore rehearsal.
