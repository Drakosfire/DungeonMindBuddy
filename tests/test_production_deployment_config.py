from __future__ import annotations

import unittest
from pathlib import Path

from scripts.verify_production_compose import validate_compose_config, validate_static_files


SYNTHETIC_TEST_DIGEST = "0" * 64


def synthetic_compose() -> dict:
    return {
        "services": {
            "buddy": {
                "image": f"registry.invalid/dungeonmindbuddy@sha256:{SYNTHETIC_TEST_DIGEST}",
                "pull_policy": "always",
                "ports": [
                    {
                        "target": 8000,
                        "published": "18080",
                        "protocol": "tcp",
                        "host_ip": "127.0.0.1",
                    }
                ],
                "environment": {
                    "DMB_DEPLOYMENT_ENVIRONMENT": "production",
                    "DMB_AUTH_MODE": "hosted_dms",
                    "DUNGEONMIND_SERVER_API_ORIGIN": "https://dms.example.test",
                    "AUTH_TRUSTED_FRONTEND_ORIGINS": "https://buddy.dungeonmind.net",
                    "DMB_HOSTED_WORLD_ACCESS_JSON": "{}",
                    "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL": (
                        "postgresql://buddy_app_state:synthetic-only"
                        "@app-state.example.test:5432/dungeonbuddy_application_state"
                    ),
                    "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL": (
                        "postgresql://world_graph:synthetic-only"
                        "@world-graph.example.test:5432/dungeonmind_world_graph"
                    ),
                    "DUNGEONMIND_WORLD_GRAPH_AUTHORITY": "dungeonmind",
                    "DMB_MANAGED_WORLD_DATA_ROOT": "/var/lib/buddy/managed",
                    "DMB_ARTIFACT_DATA_ROOT": "/var/lib/buddy/artifacts",
                    "DUNGEONMIND_LIVE_SESSION_DIR": "/var/lib/buddy/sessions",
                    "DUNGEONMIND_WORLD_GRAPH_ROOT": "/var/lib/dungeonmind/worldgraph",
                    "DUNGEONMIND_RECAP_SOURCE_CONTENT_ROOT": "recaps",
                },
                "volumes": [
                    {
                        "type": "bind",
                        "source": "/srv/synthetic/buddy",
                        "target": "/var/lib/buddy",
                        "bind": {"create_host_path": False},
                    },
                    {
                        "type": "bind",
                        "source": "/srv/synthetic/worldgraph",
                        "target": "/var/lib/dungeonmind/worldgraph",
                        "bind": {"create_host_path": False},
                    },
                ],
                "healthcheck": {
                    "test": [
                        "CMD",
                        "python",
                        "-c",
                        "urllib.request.urlopen('http://127.0.0.1:8000/health/ready')",
                    ]
                },
            }
        }
    }


class ProductionDeploymentConfigTests(unittest.TestCase):
    def test_synthetic_digest_config_passes_without_external_services(self) -> None:
        self.assertEqual(
            validate_compose_config(
                synthetic_compose(),
                repository_root=Path("/checkout"),
                allow_synthetic_image=True,
            ),
            (),
        )

    def test_tag_only_image_is_rejected(self) -> None:
        config = synthetic_compose()
        config["services"]["buddy"]["image"] = "registry.invalid/buddy:latest"
        self.assertIn(
            "image_ref_must_be_registry_digest",
            validate_compose_config(
                config,
                repository_root=Path("/checkout"),
                allow_synthetic_image=True,
            ),
        )

    def test_shared_database_authority_is_rejected(self) -> None:
        config = synthetic_compose()
        config["services"]["buddy"]["environment"][
            "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"
        ] = (
            "postgresql://world_graph:synthetic-only"
            "@app-state.example.test:5432/dungeonbuddy_application_state"
        )
        self.assertIn(
            "database_authorities_must_have_distinct_database_and_role",
            validate_compose_config(config, repository_root=Path("/checkout")),
        )

    def test_overlapping_host_roots_are_rejected(self) -> None:
        config = synthetic_compose()
        config["services"]["buddy"]["volumes"][1]["source"] = (
            "/srv/synthetic/buddy/worldgraph"
        )
        self.assertIn(
            "buddy_and_worldgraph_host_roots_must_not_overlap",
            validate_compose_config(config, repository_root=Path("/checkout")),
        )

    def test_public_api_bind_is_rejected(self) -> None:
        config = synthetic_compose()
        config["services"]["buddy"]["ports"][0]["host_ip"] = "0.0.0.0"
        self.assertIn(
            "api_port_must_bind_loopback",
            validate_compose_config(config, repository_root=Path("/checkout")),
        )

    def test_database_services_and_build_context_are_rejected(self) -> None:
        config = synthetic_compose()
        config["services"]["postgres"] = {}
        self.assertIn(
            "compose_must_contain_only_buddy_service",
            validate_compose_config(config, repository_root=Path("/checkout")),
        )

        config = synthetic_compose()
        config["services"]["buddy"]["build"] = {"context": "../.."}
        self.assertIn(
            "production_compose_must_not_build",
            validate_compose_config(config, repository_root=Path("/checkout")),
        )

    def test_source_and_runbook_contract_files_are_consistent(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        self.assertEqual(validate_static_files(repository_root), ())


if __name__ == "__main__":
    unittest.main()
