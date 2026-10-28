"""Trusted native reads, including governed V7 receipt verification."""

from dungeonmind.application.graph_snapshot_v7 import (
    VersionedUnionGraphSnapshotReaderV7,
)
from dungeonmind.infrastructure.postgres import (
    PostgresDatabase,
    PostgresRepositoryBundle,
)
from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_v3_descriptor,
)


def build_graph_reader() -> VersionedUnionGraphSnapshotReaderV7:
    return VersionedUnionGraphSnapshotReaderV7(
        profile_registry=StaticSemanticProfileRegistry([load_builtin_v3_descriptor()])
    )


def open_repository_bundle(database_url: str) -> PostgresRepositoryBundle:
    return PostgresRepositoryBundle(
        PostgresDatabase(database_url), v7_graph_reader=build_graph_reader()
    )
