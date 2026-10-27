#!/usr/bin/env python3
"""Validate the rendered, provider-free Buddy production Compose contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlsplit


_DIGEST_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:+-]*@sha256:[0-9a-f]{64}$")
_SYNTHETIC_IMAGE = (
    "registry.invalid/dungeonmindbuddy@sha256:" + "0" * 64
)
_PERSISTENT_ROOT_TARGETS = {
    "/var/lib/buddy",
    "/var/lib/dungeonmind/worldgraph",
}
_PERSISTENT_PATHS = {
    "DMB_MANAGED_WORLD_DATA_ROOT": "/var/lib/buddy/managed",
    "DMB_ARTIFACT_DATA_ROOT": "/var/lib/buddy/artifacts",
    "DUNGEONMIND_LIVE_SESSION_DIR": "/var/lib/buddy/sessions",
    "DUNGEONMIND_WORLD_GRAPH_ROOT": "/var/lib/dungeonmind/worldgraph",
}


def _database_identity(value: object) -> tuple[str, int, str, str] | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        database = unquote(parsed.path.lstrip("/")).split("/", 1)[0]
        user = unquote(parsed.username or "").strip().lower()
        host = (parsed.hostname or "").lower()
        port = parsed.port or 5432
    except ValueError:
        return None
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or not host
        or not database
        or not user
        or not 1 <= port <= 65535
    ):
        return None
    return host, port, database, user


def validate_compose_config(
    config: Mapping[str, Any],
    *,
    repository_root: Path,
    allow_synthetic_image: bool = False,
) -> tuple[str, ...]:
    """Return stable error codes only; never echo DSNs or environment values."""

    errors: set[str] = set()
    services = config.get("services")
    if not isinstance(services, Mapping) or set(services) != {"buddy"}:
        return ("compose_must_contain_only_buddy_service",)
    service = services.get("buddy")
    if not isinstance(service, Mapping):
        return ("buddy_service_invalid",)

    image = service.get("image")
    is_synthetic = allow_synthetic_image and image == _SYNTHETIC_IMAGE
    is_published_digest = (
        isinstance(image, str)
        and _DIGEST_IMAGE.fullmatch(image) is not None
        and not image.startswith("registry.invalid/")
    )
    if not (is_published_digest or is_synthetic):
        errors.add("image_ref_must_be_registry_digest")
    if "build" in service:
        errors.add("production_compose_must_not_build")
    if service.get("pull_policy") != "always":
        errors.add("digest_image_must_be_pulled")

    ports = service.get("ports")
    if (
        not isinstance(ports, list)
        or len(ports) != 1
        or not isinstance(ports[0], Mapping)
        or ports[0].get("host_ip") != "127.0.0.1"
        or ports[0].get("target") != 8000
    ):
        errors.add("api_port_must_bind_loopback")

    environment = service.get("environment")
    if not isinstance(environment, Mapping):
        return tuple(sorted(errors | {"service_environment_invalid"}))
    required_values = (
        "DUNGEONMIND_SERVER_API_ORIGIN",
        "AUTH_TRUSTED_FRONTEND_ORIGINS",
        "DMB_HOSTED_WORLD_ACCESS_JSON",
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
    )
    if any(not str(environment.get(name, "")).strip() for name in required_values):
        errors.add("required_environment_missing")
    if environment.get("DMB_DEPLOYMENT_ENVIRONMENT") != "production":
        errors.add("deployment_environment_must_be_production")
    if environment.get("DMB_AUTH_MODE") != "hosted_dms":
        errors.add("auth_mode_must_be_hosted_dms")
    if environment.get("DUNGEONMIND_WORLD_GRAPH_AUTHORITY") != "dungeonmind":
        errors.add("world_graph_authority_must_be_explicit")

    app_state = _database_identity(
        environment.get("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL")
    )
    world_graph = _database_identity(
        environment.get("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL")
    )
    if app_state is None or world_graph is None:
        errors.add("database_urls_must_be_postgresql")
    elif app_state[:3] == world_graph[:3] or app_state[3] == world_graph[3]:
        errors.add("database_authorities_must_have_distinct_database_and_role")

    volumes = service.get("volumes")
    if not isinstance(volumes, list):
        return tuple(sorted(errors | {"persistent_mounts_invalid"}))
    bind_mounts = [
        volume
        for volume in volumes
        if isinstance(volume, Mapping) and volume.get("type") == "bind"
    ]
    targets = {
        volume.get("target")
        for volume in bind_mounts
        if isinstance(volume.get("target"), str)
    }
    if len(bind_mounts) != 2 or targets != _PERSISTENT_ROOT_TARGETS:
        errors.add("buddy_and_worldgraph_mounts_must_be_separate")

    sources: list[Path] = []
    for volume in bind_mounts:
        source = volume.get("source")
        if not isinstance(source, str) or not Path(source).is_absolute():
            errors.add("persistent_mount_source_must_be_absolute")
            continue
        source_path = Path(source).resolve(strict=False)
        repo = repository_root.resolve(strict=False)
        if source_path == repo or repo in source_path.parents:
            errors.add("persistent_mount_must_be_outside_checkout")
        bind = volume.get("bind")
        if not isinstance(bind, Mapping) or bind.get("create_host_path") is not False:
            errors.add("persistent_mount_must_not_create_host_path")
        sources.append(source_path)
    if len(sources) == 2:
        first, second = sources
        if first == second or first in second.parents or second in first.parents:
            errors.add("buddy_and_worldgraph_host_roots_must_not_overlap")

    for name, expected_path in _PERSISTENT_PATHS.items():
        actual = environment.get(name)
        if actual != expected_path:
            errors.add("container_persistent_paths_must_match_mounts")
    recap_root = environment.get("DUNGEONMIND_RECAP_SOURCE_CONTENT_ROOT")
    if (
        not isinstance(recap_root, str)
        or not recap_root
        or Path(recap_root).is_absolute()
        or ".." in Path(recap_root).parts
        or recap_root.startswith("file:")
    ):
        errors.add("recap_root_must_remain_safe_relative_path")

    healthcheck = service.get("healthcheck")
    health_command = healthcheck.get("test") if isinstance(healthcheck, Mapping) else None
    if not isinstance(health_command, list) or "/health/ready" not in " ".join(
        str(part) for part in health_command
    ):
        errors.add("readiness_healthcheck_must_be_preserved")
    return tuple(sorted(errors))


def validate_static_files(repository_root: Path) -> tuple[str, ...]:
    """Check provenance wiring, streaming proxy settings, and launch-gate docs."""

    errors: set[str] = set()
    dockerfile = (repository_root / "Dockerfile.production").read_text(encoding="utf-8")
    compose = (
        repository_root / "deploy/production/compose.production.yaml"
    ).read_text(encoding="utf-8")
    workflow = (
        repository_root / ".github/workflows/hosted-validation.yml"
    ).read_text(encoding="utf-8")
    proxy = (repository_root / "deploy/production/nginx-buddy.conf").read_text(
        encoding="utf-8"
    )
    runbook = (
        repository_root / "Docs/Runbooks/RUNBOOK-HOSTED-deployment-preparation.md"
    ).read_text(encoding="utf-8").lower()
    manifest = (
        repository_root / "Docs/Plans/HOSTED-READINESS-MANIFEST-2026-10-26.md"
    ).read_text(encoding="utf-8").lower()

    if not all(
        token in dockerfile
        for token in (
            "ARG DUNGEONMINDBUDDY_SOURCE_REVISION",
            "org.opencontainers.image.source=",
            "org.opencontainers.image.revision=",
            'RUN test -n "$DUNGEONMINDBUDDY_SOURCE_REVISION"',
        )
    ):
        errors.add("dockerfile_source_revision_labels_missing")
    if (
        "--build-arg DUNGEONMINDBUDDY_SOURCE_REVISION=" not in workflow
        or "org.opencontainers.image.revision" not in workflow
    ):
        errors.add("ci_must_supply_and_verify_source_revision")
    if not all(
        token in compose
        for token in (
            "BUDDY_IMAGE_NAME:?",
            "BUDDY_IMAGE_DIGEST:?",
            "@sha256:",
            "pull_policy: always",
        )
    ):
        errors.add("compose_must_require_a_digest_pinned_release_image")
    if not all(
        token in proxy
        for token in (
            "proxy_buffering off;",
            "proxy_request_buffering off;",
            "proxy_read_timeout 3600s;",
        )
    ):
        errors.add("streaming_proxy_contract_missing")
    for token in (
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
        "DUNGEONMIND_WORLD_GRAPH_FILE_ROOT",
        "registry digest",
        "isolated restore",
        "downgrade fence",
        "world resolver",
    ):
        if token.lower() not in runbook:
            errors.add("runbook_gate_missing")
            break
    for token in (
        "2d14d6a32e4d72d16a94254af16d49921ae91688",
        "53d4bfd70bc599e18494e258f5c2b39acbf93c21",
        "48b3f5181890ee3b3362cd12d9bfb8b41ddd65c1",
        "4ccd39a1e433d81569d86c05273ac33ee8f27ef3",
        "no registry digest",
    ):
        if token not in manifest:
            errors.add("source_manifest_pin_or_image_limit_missing")
            break
    return tuple(sorted(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose-json", required=True, type=Path)
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--allow-synthetic-image",
        action="store_true",
        help="allow the registry.invalid sentinel used only by provider-free CI",
    )
    args = parser.parse_args()
    try:
        rendered = json.loads(args.compose_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("production_compose_json_invalid", file=sys.stderr)
        return 2

    errors = set(
        validate_compose_config(
            rendered,
            repository_root=args.repository_root,
            allow_synthetic_image=args.allow_synthetic_image,
        )
    )
    errors.update(validate_static_files(args.repository_root))
    if errors:
        print("production_contract_check_failed: " + ", ".join(sorted(errors)), file=sys.stderr)
        return 1
    print("production Compose, provenance, proxy, and runbook contract checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
