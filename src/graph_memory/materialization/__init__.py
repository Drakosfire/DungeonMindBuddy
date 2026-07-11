"""World graph materialization from acceptance manifests and candidate bundles (PR006)."""

from graph_memory.materialization.acceptance_manifest import (
    AcceptanceManifestError,
    build_inventory,
    load_acceptance_manifest,
    sha256_file,
)
from graph_memory.materialization.candidate_bundle import (
    build_deterministic_acceptance_bundle,
    load_candidate_bundle,
    validate_candidate_bundle,
)
from graph_memory.materialization.candidate_to_contribution import (
    bundle_sources_to_contributions,
)
from graph_memory.materialization.reporting import build_materialization_report
from graph_memory.materialization.world_materializer import materialize_world_graph

__all__ = [
    "AcceptanceManifestError",
    "build_deterministic_acceptance_bundle",
    "build_inventory",
    "build_materialization_report",
    "bundle_sources_to_contributions",
    "load_acceptance_manifest",
    "load_candidate_bundle",
    "materialize_world_graph",
    "sha256_file",
    "validate_candidate_bundle",
]
