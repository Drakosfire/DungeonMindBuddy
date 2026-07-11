"""Acceptance manifest loading and corpus inventory (PR006)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

MANIFEST_SCHEMA = "dmb_world_materialization_acceptance_manifest_v1"

SourceDomain = Literal[
    "recap",
    "pc_hub",
    "worldbuilding",
    "campaign_hub",
    "mechanical",
    "authored",
]

SESSION_RE = re.compile(r"Session\s+(\d+)", re.IGNORECASE)


class AcceptanceManifestError(Exception):
    """Structured manifest or inventory failure."""

    def __init__(self, message: str, *, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.errors = list(errors or [])


@dataclass(frozen=True)
class SourceItem:
    path: str
    domain: SourceDomain
    required: bool
    sha256: str
    session_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "path": self.path,
            "domain": self.domain,
            "required": self.required,
            "sha256": self.sha256,
        }
        if self.session_number is not None:
            payload["session_number"] = self.session_number
        return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _normalize_relpath(path: Path, repo_root: Path) -> str:
    rel = path.resolve().relative_to(repo_root.resolve())
    return rel.as_posix()


def _resolve_dotted_key(payload: dict[str, Any], key: str) -> Any:
    current: Any = payload
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise AcceptanceManifestError(
                f"corpus index key not found: {key!r} (missing {part!r})"
            )
        current = current[part]
    return current


def load_acceptance_manifest(manifest_path: Path) -> dict[str, Any]:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if raw.get("schema") != MANIFEST_SCHEMA:
        raise AcceptanceManifestError(
            f"unsupported manifest schema: {raw.get('schema')!r}; expected {MANIFEST_SCHEMA!r}"
        )
    return raw


def _path_has_excluded_component(relpath: str, exclude: tuple[str, ...]) -> bool:
    parts = relpath.split("/")
    return any(part in exclude for part in parts)


def _session_from_filename(name: str) -> int | None:
    match = SESSION_RE.search(name)
    if not match:
        return None
    return int(match.group(1))


def _expand_world_root_md_files(root: Path, repo_root: Path, exclude: tuple[str, ...]) -> list[str]:
    if not root.is_dir():
        return []
    paths: list[str] = []
    for path in sorted(root.rglob("*.md")):
        if path.name.startswith("."):
            continue
        rel = _normalize_relpath(path, repo_root)
        if _path_has_excluded_component(rel, exclude):
            continue
        paths.append(rel)
    return paths


def _dedupe_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in sorted(paths):
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def _resolve_recap_paths(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
    corpus_index: dict[str, Any],
) -> tuple[list[SourceItem], list[dict[str, Any]]]:
    recaps_cfg = manifest["recaps"]
    exclude = tuple(recaps_cfg.get("exclude_path_components") or [])
    session_min = int(recaps_cfg["session_min"])
    session_max = int(recaps_cfg["session_max"])
    corpus_root = repo_root / manifest["corpus_root"]

    raw_paths = _resolve_dotted_key(corpus_index, recaps_cfg["index_key"])
    if not isinstance(raw_paths, list):
        raise AcceptanceManifestError("recap index_key must resolve to a list of paths")

    by_session: dict[int, list[str]] = {}
    errors: list[dict[str, Any]] = []

    for entry in raw_paths:
        if not isinstance(entry, str):
            continue
        rel = entry.replace("\\", "/")
        if _path_has_excluded_component(rel, exclude):
            continue
        session = _session_from_filename(Path(rel).name)
        if session is None:
            continue
        if session < session_min or session > session_max:
            continue
        full = corpus_root / rel
        if not full.is_file():
            errors.append(
                {
                    "kind": "missing_recap",
                    "path": f"{manifest['corpus_root'].rstrip('/')}/{rel}",
                    "session_number": session,
                }
            )
            continue
        repo_rel = _normalize_relpath(full, repo_root)
        by_session.setdefault(session, []).append(repo_rel)

    items: list[SourceItem] = []
    for session in range(session_min, session_max + 1):
        matches = sorted(set(by_session.get(session, [])))
        if recaps_cfg.get("require_exactly_one_per_session") and len(matches) != 1:
            errors.append(
                {
                    "kind": "recap_session_count",
                    "session_number": session,
                    "count": len(matches),
                    "paths": matches,
                }
            )
            continue
        if len(matches) == 1:
            path = matches[0]
            items.append(
                SourceItem(
                    path=path,
                    domain="recap",
                    required=True,
                    sha256=sha256_file(repo_root / path),
                    session_number=session,
                )
            )

    return items, errors


def build_inventory(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Resolve manifest into requested/accepted inventory with fail-closed required checks."""
    repo_root = repo_root.resolve()
    errors: list[dict[str, Any]] = []
    source_items: list[SourceItem] = []

    index_path = repo_root / manifest["corpus_index"]
    if not index_path.is_file():
        raise AcceptanceManifestError(
            f"missing corpus index: {manifest['corpus_index']}",
            errors=[{"kind": "missing_corpus_index", "path": manifest["corpus_index"]}],
        )
    corpus_index = json.loads(index_path.read_text(encoding="utf-8"))

    recap_items, recap_errors = _resolve_recap_paths(
        manifest, repo_root=repo_root, corpus_index=corpus_index
    )
    errors.extend(recap_errors)
    source_items.extend(recap_items)

    party = manifest["party"]
    corpus_root = repo_root / manifest["corpus_root"]
    registry_path = repo_root / party["registry"]
    if not registry_path.is_file():
        errors.append({"kind": "missing_party_registry", "path": party["registry"]})
    else:
        for slug in party["required_pc_slugs"]:
            hub_rel = party["hub_template"].format(slug=slug)
            hub_path = corpus_root / hub_rel
            if not hub_path.is_file():
                errors.append(
                    {
                        "kind": "missing_pc_hub",
                        "slug": slug,
                        "path": _normalize_relpath(hub_path, repo_root)
                        if hub_path.exists()
                        else f"{manifest['corpus_root'].rstrip('/')}/{hub_rel}",
                    }
                )
                continue
            repo_rel = _normalize_relpath(hub_path, repo_root)
            source_items.append(
                SourceItem(
                    path=repo_rel,
                    domain="pc_hub",
                    required=True,
                    sha256=sha256_file(hub_path),
                )
            )

    exclude = tuple(manifest["recaps"].get("exclude_path_components") or [])
    for world_root in manifest.get("required_world_roots") or []:
        root_path = repo_root / world_root
        if not root_path.is_dir():
            errors.append({"kind": "missing_world_root", "path": world_root})
            continue
        expanded = _expand_world_root_md_files(root_path, repo_root, exclude)
        if not expanded:
            errors.append({"kind": "empty_world_root", "path": world_root})
        for rel in expanded:
            source_items.append(
                SourceItem(
                    path=rel,
                    domain="worldbuilding",
                    required=True,
                    sha256=sha256_file(repo_root / rel),
                )
            )

    for rel_path in manifest.get("required_campaign_sources") or []:
        path = repo_root / rel_path
        if not path.is_file():
            errors.append({"kind": "missing_campaign_source", "path": rel_path})
            continue
        source_items.append(
            SourceItem(
                path=_normalize_relpath(path, repo_root),
                domain="campaign_hub",
                required=True,
                sha256=sha256_file(path),
            )
        )

    for rel_path in manifest.get("required_mechanical_sources") or []:
        path = repo_root / rel_path
        if not path.is_file():
            errors.append({"kind": "missing_mechanical_source", "path": rel_path})
            continue
        source_items.append(
            SourceItem(
                path=_normalize_relpath(path, repo_root),
                domain="mechanical",
                required=True,
                sha256=sha256_file(path),
            )
        )

    authored_cfg = manifest.get("authored_records") or {}
    authored_absent: list[str] = []
    if authored_cfg.get("include_active_graph_review_contributions"):
        authored_absent.append("active_graph_review_contributions")
    if authored_cfg.get("include_identity_decisions"):
        authored_absent.append("identity_decisions")

    deduped = _dedupe_paths([item.path for item in source_items])
    path_to_item = {item.path: item for item in source_items}
    source_items = [path_to_item[p] for p in deduped]

    failed_required = [e for e in errors if e.get("kind") != "authored_absent"]
    recap_session_numbers = list(range(manifest["recaps"]["session_min"], manifest["recaps"]["session_max"] + 1))

    inventory = {
        "world_id": manifest["world_id"],
        "campaign_scope": manifest["campaign_scope"],
        "recap_session_numbers": recap_session_numbers,
        "recap_count": len([i for i in source_items if i.domain == "recap"]),
        "required_pc_slugs": list(manifest["party"]["required_pc_slugs"]),
        "failed_required": failed_required,
        "requested": [item.to_dict() for item in source_items],
        "accepted": [item.to_dict() for item in source_items if not failed_required],
        "skipped": [],
        "source_items": [item.to_dict() for item in source_items],
        "authored_absent_reportable": authored_absent if authored_cfg.get("absence_is_reportable_not_fatal") else [],
        "manifest_sha256": sha256_bytes(
            (manifest_path or Path()).read_bytes()
            if manifest_path and manifest_path.is_file()
            else json.dumps(manifest, sort_keys=True).encode("utf-8")
        ),
    }

    if failed_required:
        raise AcceptanceManifestError(
            f"acceptance inventory failed with {len(failed_required)} required error(s)",
            errors=failed_required,
        )

    return inventory
