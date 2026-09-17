#!/usr/bin/env python3
"""Fail-closed zero-model replay of the accepted current-corpus candidates.

Replays the exact frozen 44-candidate cohort through current production
source-admission → candidate-admission → governed confirm, then exercises
ordinary Buddy product reads. Never extracts, regenerates, or mutates the
historical accepted World.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

WORLD_ID = "dogfood-current-corpus-replay-v1"
DATABASE_NAME = "dmb_current_corpus_replay_v1"
EXPECTED_HOST = "127.0.0.1"
EXPECTED_PORT = 54330
OPERATOR = "current-corpus-candidate-replay-v1"
OUTPUT_REL = Path("out/graph_memory/current_corpus_candidate_replay_v1")

HISTORICAL_WORLD_ID = "dogfood-current-corpus-acceptance-v1"
HISTORICAL_DATABASE_NAME = "dmb_current_corpus_acceptance_v1"
ACCEPTED_RUN_ID = "execute-2026-09-16T020204Z-6e3b812a"
ACCEPTED_MANIFEST_COUNT = 44
ACCEPTED_MANIFEST_DIGEST = (
    "d21477c395f7093540491ca17c109a83bdf7e8a4e9f04517f5ef91f5d3d30e5c"
)
ACCEPTED_MANIFEST_SCHEMA = "dmb_current_corpus_admission_manifest_v1"
PREDECESSOR_MERGE = "074d4f66f94d4b391a7aaf485b69030a20d576e4"
PREDECESSOR_MODEL_ID = "gpt-5.4-mini"
PREDECESSOR_MODEL_POLICY_DIGEST = (
    "477b9f1541a675dbe1751b9e46c376208cd7a5052207c1059b6c62e981ca2212"
)
MIREWARD_PREFERRED_ID = "node:location:mireward"
C1S10_KEY = ("longmont-c1", "session-10")
C2S22_KEY = ("longmont-c2", "session-22")
PROVENANCE_FAIL_CODES = frozenset(
    {
        "stored_provenance_invalid",
        "missing-source",
        "scope-unknown-for-in-scope-recap",
        "evidence_source_domain_mismatch",
        "source_not_admitted",
        "source_identity_conflict",
    }
)


class ReplayStop(RuntimeError):
    """First owning-boundary failure; never a partial PASS."""

    def __init__(
        self,
        message: str,
        *,
        boundary: str,
        campaign_id: str | None = None,
        session_id: str | None = None,
        last_good_head: str | None = None,
        diagnostics: Sequence[str] = (),
        candidate_preserved: str = "not-produced",
    ) -> None:
        super().__init__(message)
        self.boundary = boundary
        self.campaign_id = campaign_id
        self.session_id = session_id
        self.last_good_head = last_good_head
        self.diagnostics = tuple(diagnostics)
        self.candidate_preserved = candidate_preserved


@dataclass(frozen=True)
class ManifestEntry:
    ordinal: int
    campaign_id: str
    campaign_number: int
    session: int
    session_id: str
    normalized_path: str
    normalized_sha256: str
    original_path: str
    original_sha256: str
    source_artifact_id: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def key(self) -> tuple[str, str]:
        return (self.campaign_id, self.session_id)


@dataclass(frozen=True)
class FrozenManifest:
    schema: str
    entries: tuple[ManifestEntry, ...]
    digest: str

    @property
    def count(self) -> int:
        return len(self.entries)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "digest": self.digest,
            "count": self.count,
            "entries": [entry.as_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class LedgerRow:
    ordinal: int
    campaign_id: str
    session_id: str
    candidate_locator: str
    candidate_digest: str
    source_artifact_id: str
    source_revision_id: str
    original_path: str
    original_sha256: str
    normalized_path: str
    normalized_sha256: str
    payload: Mapping[str, Any]

    @property
    def key(self) -> tuple[str, str]:
        return (self.campaign_id, self.session_id)


@dataclass
class ReplaySeams:
    """Injectable production call boundaries for deterministic tests."""

    probe_world: Callable[[str], Any] | None = None
    prepare_genesis: Callable[..., Any] | None = None
    confirm_genesis: Callable[..., Any] | None = None
    load_source_artifact: Callable[..., Any] | None = None
    load_mutation_context: Callable[..., Any] | None = None
    prepare_admission: Callable[..., Any] | None = None
    confirm_admission: Callable[..., Any] | None = None
    current_head: Callable[[str], str] | None = None
    read_revision_parent: Callable[[str, str], str | None] | None = None
    project_campaign: Callable[..., Any] | None = None
    get_object: Callable[..., Any] | None = None
    get_complete_object: Callable[..., Any] | None = None
    get_neighborhood: Callable[..., Any] | None = None
    get_evidence: Callable[..., Any] | None = None
    read_source: Callable[..., Any] | None = None


@dataclass
class ReplayState:
    run_id: str
    mode: str
    git_head: str
    dsn: str
    accepted_run_id: str = ACCEPTED_RUN_ID
    accepted_artifact_root: str | None = None
    world_id: str = WORLD_ID
    database_name: str = DATABASE_NAME
    predecessor_merge: str = PREDECESSOR_MERGE
    frozen_model_id: str = PREDECESSOR_MODEL_ID
    frozen_model_policy_digest: str = PREDECESSOR_MODEL_POLICY_DIGEST
    manifest: FrozenManifest | None = None
    model_calls: int = 0
    candidate_regenerations: int = 0
    candidate_rewrites: int = 0
    graph_writes: int = 0
    genesis_d0: str | None = None
    last_good_head: str | None = None
    terminal_head: str | None = None
    replay_acceptance: str = "HOLD"
    product_loadability: str = "NOT_MEASURED"
    operator_dogfood: str = "NOT_MEASURED"
    replay_ledger: list[dict[str, Any]] = field(default_factory=list)
    product_smoke: dict[str, Any] | None = None
    stop: dict[str, Any] | None = None
    output_dir: Path | None = None


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_obj(value: object) -> str:
    return _sha256_text(_canonical_json(value))


def git_head(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()


def git_worktree_clean(repo_root: Path) -> bool:
    status = subprocess.check_output(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        text=True,
    )
    return not status.strip()


def _require_contained(path: Path, root: Path, *, boundary: str) -> Path:
    resolved = path.resolve()
    base = root.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ReplayStop(
            f"path escapes allowed root {base}: {resolved}",
            boundary=boundary,
        ) from exc
    return resolved


def _manifest_entry_from_mapping(raw: Mapping[str, Any]) -> ManifestEntry:
    return ManifestEntry(
        ordinal=int(raw["ordinal"]),
        campaign_id=str(raw["campaign_id"]),
        campaign_number=int(raw["campaign_number"]),
        session=int(raw["session"]),
        session_id=str(raw["session_id"]),
        normalized_path=str(raw["normalized_path"]),
        normalized_sha256=str(raw["normalized_sha256"]),
        original_path=str(raw["original_path"]),
        original_sha256=str(raw["original_sha256"]),
        source_artifact_id=str(raw["source_artifact_id"]),
    )


def _recompute_manifest_digest(entries: Sequence[ManifestEntry], schema: str) -> str:
    payload = {
        "schema": schema,
        "entries": [entry.as_dict() for entry in entries],
    }
    return _digest_obj(payload)


def assert_runtime_dsn(dsn: str) -> tuple[str, int, str]:
    parsed = urlparse(dsn)
    host = parsed.hostname or ""
    port = int(parsed.port or 0)
    database = (parsed.path or "").lstrip("/")
    if host not in {EXPECTED_HOST, "localhost"}:
        raise ReplayStop(
            f"DSN host must be loopback {EXPECTED_HOST}, got {host!r}",
            boundary="runtime_guard",
        )
    if host == "localhost":
        host = EXPECTED_HOST
    if port != EXPECTED_PORT:
        raise ReplayStop(
            f"DSN port must be {EXPECTED_PORT}, got {port}",
            boundary="runtime_guard",
        )
    if database == HISTORICAL_DATABASE_NAME:
        raise ReplayStop(
            f"historical database {HISTORICAL_DATABASE_NAME!r} is forbidden",
            boundary="runtime_guard",
        )
    if database != DATABASE_NAME:
        raise ReplayStop(
            f"DSN database must be {DATABASE_NAME}, got {database!r}",
            boundary="runtime_guard",
        )
    return host, port, database


def _default_dsn() -> str:
    import os

    return (
        os.environ.get("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "").strip()
        or f"postgresql://dungeonmind:dungeonmind-dev@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}"
    )


def _forbid_historical_world(world_id: str) -> None:
    if world_id == HISTORICAL_WORLD_ID:
        raise ReplayStop(
            f"historical World {HISTORICAL_WORLD_ID!r} is forbidden",
            boundary="runtime_guard",
        )
    if world_id != WORLD_ID:
        raise ReplayStop(
            f"World id must be {WORLD_ID!r}, got {world_id!r}",
            boundary="runtime_guard",
        )


def _probe_world(world_id: str, *, dsn: str, seams: ReplaySeams) -> Any:
    _forbid_historical_world(world_id)
    if seams.probe_world is not None:
        return seams.probe_world(world_id)
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )

    return DungeonMindWorldGraphInitializationAdapter(database_url=dsn).probe(world_id)


def _assert_pristine(world_id: str, *, dsn: str, seams: ReplaySeams) -> None:
    try:
        state = _probe_world(world_id, dsn=dsn, seams=seams)
    except ReplayStop:
        raise
    except Exception as exc:
        raise ReplayStop(
            "replay World probe failed; operator must create a migrated "
            f"pristine database {DATABASE_NAME!r} on {EXPECTED_HOST}:{EXPECTED_PORT}: {exc}",
            boundary="recap_genesis_probe",
        ) from exc
    status = getattr(state, "state", None) or (
        state.get("state") if isinstance(state, Mapping) else None
    )
    if status != "uninitialized":
        raise ReplayStop(
            f"World {world_id!r} is not pristine (state={status!r}); "
            "operator must recreate the replay database. No reset/resume.",
            boundary="recap_genesis_probe",
        )


def verify_entry_source_bytes(
    repo_root: Path,
    entry: ManifestEntry,
    *,
    boundary: str = "replay_artifact_drift",
) -> None:
    original = _require_contained(
        repo_root / entry.original_path,
        repo_root,
        boundary="replay_artifact_unavailable",
    )
    if not original.is_file():
        raise ReplayStop(
            f"frozen original source missing: {entry.original_path}",
            boundary="replay_artifact_unavailable",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
        )
    actual = _sha256_file(original)
    if actual != entry.original_sha256:
        raise ReplayStop(
            f"original source bytes drifted for {entry.campaign_id} {entry.session_id}",
            boundary=boundary,
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
        )
    normalized = _require_contained(
        repo_root / entry.normalized_path,
        repo_root,
        boundary="replay_artifact_unavailable",
    )
    if not normalized.is_file() or _sha256_file(normalized) != entry.normalized_sha256:
        raise ReplayStop(
            f"normalized lineage bytes drifted for {entry.campaign_id} {entry.session_id}",
            boundary=boundary,
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
        )


def _resolve_candidate_path(locator: str, artifact_root: Path) -> Path:
    artifact = artifact_root.resolve()
    raw = Path(locator)
    tries: list[Path] = []
    if raw.is_absolute():
        tries.append(raw.resolve())
    else:
        tries.append((artifact / raw.name).resolve())
        tries.append((artifact / "candidates" / raw.name).resolve())
        parts = raw.parts
        if artifact.name in parts:
            idx = parts.index(artifact.name)
            tries.append(artifact.joinpath(*parts[idx + 1 :]).resolve())
    existing_escape = None
    for path in tries:
        try:
            path.relative_to(artifact)
        except ValueError:
            if path.exists():
                existing_escape = path
            continue
        if path.is_file():
            return path
    if existing_escape is not None:
        raise ReplayStop(
            f"candidate locator escapes artifact root: {locator}",
            boundary="replay_artifact_unavailable",
        )
    raise ReplayStop(
        f"candidate file missing for locator {locator}",
        boundary="replay_artifact_unavailable",
    )


def load_accepted_cohort(
    *,
    artifact_root: Path,
    repo_root: Path,
    expected_count: int = ACCEPTED_MANIFEST_COUNT,
    expected_digest: str = ACCEPTED_MANIFEST_DIGEST,
) -> tuple[FrozenManifest, tuple[LedgerRow, ...]]:
    root = artifact_root.resolve()
    if not root.is_dir():
        raise ReplayStop(
            f"accepted artifact root missing: {root}",
            boundary="replay_artifact_unavailable",
        )
    manifest_path = root / "manifest.json"
    ledger_path = root / "session_ledger.json"
    if not manifest_path.is_file():
        raise ReplayStop(
            "accepted manifest.json missing",
            boundary="replay_artifact_unavailable",
        )
    if not ledger_path.is_file():
        raise ReplayStop(
            "accepted session_ledger.json missing",
            boundary="replay_artifact_unavailable",
        )

    manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    stored_digest = str(manifest_raw.get("digest") or "")
    stored_count = int(manifest_raw.get("count") or 0)
    schema = str(manifest_raw.get("schema") or ACCEPTED_MANIFEST_SCHEMA)
    raw_entries = list(manifest_raw.get("entries") or [])
    if stored_count != expected_count or len(raw_entries) != expected_count:
        raise ReplayStop(
            f"manifest count mismatch: stored={stored_count} "
            f"entries={len(raw_entries)} expected={expected_count}",
            boundary="replay_artifact_drift",
        )
    if stored_digest != expected_digest:
        raise ReplayStop(
            f"manifest digest mismatch: stored={stored_digest} expected={expected_digest}",
            boundary="replay_artifact_drift",
        )
    entries = tuple(_manifest_entry_from_mapping(item) for item in raw_entries)
    recomputed = _recompute_manifest_digest(entries, schema)
    if recomputed != stored_digest:
        raise ReplayStop(
            "manifest digest does not match canonical recomputation",
            boundary="replay_artifact_drift",
        )
    ordinals = [entry.ordinal for entry in entries]
    if ordinals != list(range(1, expected_count + 1)):
        raise ReplayStop(
            f"manifest ordinals are not strict 1..{expected_count}: {ordinals}",
            boundary="replay_artifact_drift",
        )
    keys = [entry.key for entry in entries]
    if len(set(keys)) != len(keys):
        raise ReplayStop(
            "manifest contains duplicate campaign/session rows",
            boundary="replay_artifact_drift",
        )

    ledger_raw = json.loads(ledger_path.read_text(encoding="utf-8"))
    sessions = list(ledger_raw.get("sessions") or [])
    if len(sessions) != expected_count:
        raise ReplayStop(
            f"session ledger count mismatch: {len(sessions)} expected {expected_count}",
            boundary="replay_artifact_drift",
        )

    ledger_rows: list[LedgerRow] = []
    seen_keys: set[tuple[str, str]] = set()
    seen_locators: set[str] = set()
    from apps.live_control_server.services.candidate_graph_admission import (
        canonical_candidate_digest,
    )

    for index, (entry, row) in enumerate(zip(entries, sessions, strict=True), start=1):
        campaign_id = str(row.get("campaign_id") or "")
        session_id = str(row.get("session_id") or "")
        ordinal = int(row.get("ordinal") or 0)
        if ordinal != entry.ordinal or ordinal != index:
            raise ReplayStop(
            f"ledger row out of order at ordinal {index}: {campaign_id}/{session_id}",
                boundary="replay_artifact_drift",
                campaign_id=campaign_id or entry.campaign_id,
                session_id=session_id or entry.session_id,
            )
        key = (campaign_id, session_id)
        if key != entry.key:
            raise ReplayStop(
                "ledger campaign/session disagree with frozen manifest",
                boundary="replay_artifact_drift",
                campaign_id=campaign_id,
                session_id=session_id,
            )
        if key in seen_keys:
            raise ReplayStop(
                f"duplicate ledger row {campaign_id}/{session_id}",
                boundary="replay_artifact_drift",
                campaign_id=campaign_id,
                session_id=session_id,
            )
        seen_keys.add(key)
        for field_name in (
            "source_artifact_id",
            "original_path",
            "original_sha256",
            "normalized_path",
            "normalized_sha256",
        ):
            if str(row.get(field_name) or "") != str(getattr(entry, field_name)):
                raise ReplayStop(
                    f"ledger {field_name} disagrees with frozen manifest "
                    f"for {campaign_id}/{session_id}",
                    boundary="replay_artifact_drift",
                    campaign_id=campaign_id,
                    session_id=session_id,
                )
        locator = str(row.get("candidate_locator") or "")
        if not locator:
            raise ReplayStop(
                f"ledger missing candidate_locator for {campaign_id}/{session_id}",
                boundary="replay_artifact_unavailable",
                campaign_id=campaign_id,
                session_id=session_id,
            )
        if locator in seen_locators:
            raise ReplayStop(
                f"duplicate candidate locator {locator}",
                boundary="replay_artifact_drift",
                campaign_id=campaign_id,
                session_id=session_id,
            )
        seen_locators.add(locator)
        candidate_path = _resolve_candidate_path(locator, root)
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        digest = canonical_candidate_digest(candidate)
        sealed = str(row.get("candidate_digest") or "")
        if digest != sealed:
            raise ReplayStop(
                f"canonical candidate digest mismatch for {campaign_id}/{session_id}",
                boundary="replay_artifact_drift",
                campaign_id=campaign_id,
                session_id=session_id,
            )
        verify_entry_source_bytes(repo_root, entry)
        ledger_rows.append(
            LedgerRow(
                ordinal=ordinal,
                campaign_id=campaign_id,
                session_id=session_id,
                candidate_locator=locator,
                candidate_digest=digest,
                source_artifact_id=entry.source_artifact_id,
                source_revision_id=str(row.get("source_revision_id") or ""),
                original_path=entry.original_path,
                original_sha256=entry.original_sha256,
                normalized_path=entry.normalized_path,
                normalized_sha256=entry.normalized_sha256,
                payload=row,
            )
        )

    if len(seen_keys) != expected_count:
        raise ReplayStop(
            "ledger is missing unique chronological rows",
            boundary="replay_artifact_drift",
        )
    return (
        FrozenManifest(schema=schema, entries=entries, digest=stored_digest),
        tuple(ledger_rows),
    )


def _run_genesis(
    *,
    repo_root: Path,
    dsn: str,
    seams: ReplaySeams,
) -> str:
    from apps.live_control_server.models.recap_world_genesis import (
        RecapWorldGenesisConfirmRequest,
        RecapWorldGenesisPrepareRequest,
    )
    from apps.live_control_server.services.recap_world_genesis import (
        confirm_recap_world_genesis,
        prepare_recap_world_genesis,
    )

    prepare_req = RecapWorldGenesisPrepareRequest(
        world_id=WORLD_ID,
        campaign_id="longmont-c1",
        baseline_roster_key="1",
        requested_by=OPERATOR,
    )
    if seams.prepare_genesis is not None:
        plan = seams.prepare_genesis(prepare_req, repo=repo_root, dsn=dsn)
    else:
        from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
            DungeonMindWorldGraphInitializationAdapter,
        )

        authority = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
        plan = prepare_recap_world_genesis(prepare_req, repo=repo_root, authority=authority)

    if seams.confirm_genesis is not None:
        receipt = seams.confirm_genesis(plan, repo=repo_root, dsn=dsn)
    else:
        from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
            DungeonMindWorldGraphInitializationAdapter,
        )

        authority = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
        receipt = confirm_recap_world_genesis(
            RecapWorldGenesisConfirmRequest(plan=plan, confirming_principal=OPERATOR),
            repo=repo_root,
            authority=authority,
        )

    d0 = str(getattr(receipt, "published_revision_id", "") or "")
    parent = getattr(receipt, "parent_revision_id", None)
    if not d0:
        raise ReplayStop(
            "genesis receipt missing published_revision_id",
            boundary="production_genesis",
        )
    if parent is not None:
        raise ReplayStop(
            f"genesis D0 must have null parent, got {parent!r}",
            boundary="production_genesis",
        )
    pcs = tuple(getattr(receipt, "pc_object_ids", ()) or getattr(plan, "pc_object_ids", ()) or ())
    if len(pcs) != 6:
        raise ReplayStop(
            f"genesis must materialize six PC anchors, got {len(pcs)}",
            boundary="production_genesis",
        )
    return d0


def _load_canonical_source_artifact(
    *,
    repo_root: Path,
    entry: ManifestEntry,
    seams: ReplaySeams,
):
    if seams.load_source_artifact is not None:
        artifact = seams.load_source_artifact(repo_root=repo_root, entry=entry)
    else:
        from apps.live_control_server.services.source_artifact_registry import (
            create_recap_source_artifact,
        )

        artifact = create_recap_source_artifact(
            repo_root,
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            recap_path=repo_root / entry.original_path,
            expected_content_sha256=entry.original_sha256,
        )
    artifact_id = str(getattr(artifact, "source_artifact_id", "") or "")
    if artifact_id != entry.source_artifact_id:
        raise ReplayStop(
            "canonical source_artifact_id disagrees with frozen manifest/ledger",
            boundary="exact_source_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
        )
    existing_world = getattr(artifact, "world_id", None)
    if existing_world not in {None, "", WORLD_ID}:
        raise ReplayStop(
            f"canonical source artifact world_id {existing_world!r} is not the replay World",
            boundary="exact_source_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
        )
    if existing_world != WORLD_ID:
        if hasattr(artifact, "model_copy"):
            artifact = artifact.model_copy(update={"world_id": WORLD_ID})
        else:
            setattr(artifact, "world_id", WORLD_ID)
    return artifact


def _source_admission_authority(*, dsn: str):
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )

    return DungeonMindWorldGraphSourceAdmissionAdapter(database_url=dsn)


def _admit_and_confirm(
    *,
    repo_root: Path,
    dsn: str,
    entry: ManifestEntry,
    candidate_graph: dict[str, Any],
    source_artifact: Any,
    source_uri: str,
    source_revision_id: str,
    prior_head: str,
    seams: ReplaySeams,
) -> dict[str, Any]:
    from apps.live_control_server.models.candidate_graph_admission import (
        CandidateAdmissionIntegrityError,
        CandidateAdmissionNotConfirmableError,
    )
    from apps.live_control_server.services.candidate_graph_admission import (
        canonical_candidate_digest,
        confirm_candidate_graph_admission,
        prepare_candidate_graph_admission,
    )

    frozen = json.loads(json.dumps(candidate_graph))
    digest = canonical_candidate_digest(candidate_graph)

    if seams.load_mutation_context is not None:
        context = seams.load_mutation_context(WORLD_ID, dsn=dsn, prior_head=prior_head)
    else:
        from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
            load_production_mutation_context,
        )

        context = load_production_mutation_context(WORLD_ID, database_url=dsn)
    context_rev = str(getattr(context, "revision_id", "") or "")
    if context_rev != prior_head:
        raise ReplayStop(
            f"mutation context parent {context_rev!r} != prior head {prior_head!r}",
            boundary="governed_write_seam",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        )

    source_admission = None if seams.prepare_admission is not None else _source_admission_authority(dsn=dsn)
    prepare_kwargs = dict(
        candidate_graph=candidate_graph,
        source_uri=source_uri,
        source_revision_id=source_revision_id,
        prepared_by=OPERATOR,
        world_id=WORLD_ID,
        source_artifact_id=entry.source_artifact_id,
        source_artifact=source_artifact,
        campaign_scope=entry.campaign_id,
        repo_root=repo_root,
        mutation_context=context,
        source_admission=source_admission,
    )
    try:
        if seams.prepare_admission is not None:
            prepared = seams.prepare_admission(**prepare_kwargs)
        else:
            prepared = prepare_candidate_graph_admission(**prepare_kwargs)
    except CandidateAdmissionIntegrityError as exc:
        raise ReplayStop(
            f"candidate integrity failure at admission: {exc}",
            boundary="candidate_document_integrity",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            diagnostics=[str(item) for item in getattr(exc, "diagnostics", ())],
            candidate_preserved="yes",
        ) from exc
    except CandidateAdmissionNotConfirmableError as exc:
        raise ReplayStop(
            f"admission is nonconfirmable; stopping before governed confirm: {exc}",
            boundary="candidate_graph_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        ) from exc
    except ReplayStop:
        raise
    except Exception as exc:
        raise ReplayStop(
            f"source admission / candidate prepare failed: {exc}",
            boundary="exact_source_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
            diagnostics=[type(exc).__name__],
        ) from exc

    if candidate_graph != frozen:
        raise ReplayStop(
            "runner or admission mutated candidate semantics",
            boundary="exact_candidate_forwarding",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="no",
        )

    package = prepared.review_package
    if seams.prepare_admission is None:
        from dataclasses import replace

        from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
            bind_identity_ledger_to_package,
        )

        package = bind_identity_ledger_to_package(package, context)
        prepared = replace(
            prepared,
            review_package=package,
            proposal_digest=str(package["proposal_digest"]),
        )

    binding = dict((package.get("effect") or {}).get("candidate_admission") or {})
    if binding.get("candidate_digest") != digest:
        raise ReplayStop(
            "admission digest disagrees with exact candidate",
            boundary="candidate_graph_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        )
    confirmable = bool(getattr(prepared, "confirmable", False) or binding.get("confirmable"))
    dispositions = list(binding.get("dispositions") or [])
    if not confirmable:
        raise ReplayStop(
            "admission is nonconfirmable; stopping before governed confirm",
            boundary="candidate_graph_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            diagnostics=[f"{d.get('item_id')}:{d.get('reason')}" for d in dispositions],
            candidate_preserved="yes",
        )

    source_proof = dict((package.get("effect") or {}).get("source_admission") or {})
    if not source_proof.get("source_artifact_id") or not source_proof.get("source_revision_id"):
        raise ReplayStop(
            "confirmable package is missing sealed source admission",
            boundary="exact_source_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        )

    accepted = list((package.get("effect") or {}).get("accepted_proposals") or [])
    assertion_ids = [
        str(item.get("assertion_id") or "").strip()
        for item in accepted
        if isinstance(item, Mapping) and str(item.get("assertion_id") or "").strip()
    ]
    if not assertion_ids:
        raise ReplayStop(
            "confirmable package has no accepted assertion_ids",
            boundary="candidate_graph_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        )

    if seams.current_head is not None:
        live_head = seams.current_head(WORLD_ID)
    else:
        from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
            DungeonMindWorldGraphAuthorityAdapter,
        )

        live_head = DungeonMindWorldGraphAuthorityAdapter(
            database_url=dsn
        ).current_head(WORLD_ID).revision_id
    if live_head != prior_head:
        raise ReplayStop(
            f"stale parent: live head {live_head!r} != sealed parent {prior_head!r}",
            boundary="governed_write_seam",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        )

    def _governed_confirm() -> Any:
        if seams.confirm_admission is not None:
            return seams.confirm_admission(
                review_package=package,
                candidate_graph=candidate_graph,
                prior_head=prior_head,
                assertion_ids=assertion_ids,
                dsn=dsn,
            )
        from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
            confirm_extract_promote_via_dungeonmind,
        )
        from apps.live_control_server.models.extract_promote import (
            ExtractPromoteConfirmRequest,
        )

        request = ExtractPromoteConfirmRequest(
            review_package=package,
            assertion_ids=assertion_ids,
        )
        return confirm_extract_promote_via_dungeonmind(
            request,
            database_url=dsn,
            confirming_principal=OPERATOR,
            assertion_ids=tuple(assertion_ids),
            repo_root=repo_root,
        )

    try:
        if seams.confirm_admission is not None:
            payload = _governed_confirm()
        else:
            payload = confirm_candidate_graph_admission(
                review_package=package,
                candidate_graph=candidate_graph,
                governed_confirm=_governed_confirm,
                source_admission=source_admission,
            )
    except CandidateAdmissionNotConfirmableError as exc:
        raise ReplayStop(
            f"admission became nonconfirmable at confirm: {exc}",
            boundary="candidate_graph_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        ) from exc
    except Exception as exc:
        code = getattr(exc, "code", type(exc).__name__)
        if str(code) in {"stale_parent", "governed_write_stale_parent"} or "stale" in str(exc).lower():
            raise ReplayStop(
                f"stale parent during confirm: {exc}",
                boundary="governed_write_seam",
                campaign_id=entry.campaign_id,
                session_id=entry.session_id,
                last_good_head=prior_head,
                candidate_preserved="yes",
            ) from exc
        raise ReplayStop(
            f"governed write failed: {exc}",
            boundary="dungeonmind_write",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
            diagnostics=[str(code)],
        ) from exc

    if candidate_graph != frozen:
        raise ReplayStop(
            "candidate mutated across confirm",
            boundary="exact_candidate_forwarding",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="no",
        )

    if hasattr(payload, "published_revision_id"):
        child = str(payload.published_revision_id)
        parent = getattr(payload, "parent_revision_id", prior_head)
    elif isinstance(payload, Mapping):
        child = str(
            payload.get("committed_revision_id")
            or payload.get("published_revision_id")
            or ""
        )
        parent = payload.get("parent_revision_id", prior_head)
    else:
        child = str(payload)
        parent = prior_head
    if not child:
        raise ReplayStop(
            "confirm returned no child revision",
            boundary="receipt_verification",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        )
    if str(parent or "") != prior_head:
        raise ReplayStop(
            f"receipt parent {parent!r} != prior head {prior_head!r}",
            boundary="receipt_verification",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        )

    if seams.current_head is not None:
        head_after = seams.current_head(WORLD_ID)
    else:
        from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
            DungeonMindWorldGraphAuthorityAdapter,
        )

        head_after = DungeonMindWorldGraphAuthorityAdapter(
            database_url=dsn
        ).current_head(WORLD_ID).revision_id
    if head_after != child:
        raise ReplayStop(
            f"current head {head_after!r} != receipt child {child!r}",
            boundary="receipt_verification",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        )

    if seams.read_revision_parent is not None:
        recorded_parent = seams.read_revision_parent(WORLD_ID, child)
        if recorded_parent != prior_head:
            raise ReplayStop(
                f"child revision parent {recorded_parent!r} != prior head {prior_head!r}",
                boundary="receipt_verification",
                campaign_id=entry.campaign_id,
                session_id=entry.session_id,
                last_good_head=prior_head,
                candidate_preserved="yes",
            )
    elif seams.confirm_admission is None:
        from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
            DungeonMindWorldGraphAuthorityAdapter,
        )

        recorded_parent = DungeonMindWorldGraphAuthorityAdapter(
            database_url=dsn
        ).read_revision(WORLD_ID, child).parent_revision_id
        if recorded_parent != prior_head:
            raise ReplayStop(
                f"child revision parent {recorded_parent!r} != prior head {prior_head!r}",
                boundary="receipt_verification",
                campaign_id=entry.campaign_id,
                session_id=entry.session_id,
                last_good_head=prior_head,
                candidate_preserved="yes",
            )

    return {
        "candidate_digest": digest,
        "confirmable": True,
        "dispositions": dispositions,
        "accepted_proposal_count": len(assertion_ids),
        "parent_revision_id": prior_head,
        "child_revision_id": child,
        "proposal_id": str(package.get("proposal_id") or ""),
        "proposal_digest": str(package.get("proposal_digest") or ""),
        "source_admission": {
            "source_artifact_id": source_proof.get("source_artifact_id"),
            "buddy_source_revision_id": source_proof.get("buddy_source_revision_id"),
            "source_revision_id": source_proof.get("source_revision_id"),
            "content_sha256": source_proof.get("content_sha256"),
            "source_domain": getattr(source_artifact, "source_domain", None),
            "campaign_id": entry.campaign_id,
            "session_id": entry.session_id,
        },
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _new_run_id(prefix: str) -> str:
    import uuid

    return f"{prefix}-{_now_iso().replace(':', '')}-{uuid.uuid4().hex[:8]}"


def _stop_payload(state: ReplayState, stop: ReplayStop, remaining: Sequence[str]) -> dict[str, Any]:
    return {
        "message": str(stop),
        "boundary": stop.boundary,
        "campaign_id": stop.campaign_id,
        "session_id": stop.session_id,
        "last_verified_good_head": stop.last_good_head or state.last_good_head,
        "candidate_preserved": stop.candidate_preserved,
        "diagnostics": list(stop.diagnostics),
        "model_calls": state.model_calls,
        "sessions_not_attempted": list(remaining),
    }


def _remaining_sessions(
    entries: Sequence[ManifestEntry],
    stop: ReplayStop,
) -> list[str]:
    remaining: list[str] = []
    seen_fail = False
    for entry in entries:
        key = f"{entry.campaign_id}/{entry.session_id}"
        if stop.campaign_id == entry.campaign_id and stop.session_id == entry.session_id:
            seen_fail = True
            remaining.append(key)
            continue
        if seen_fail:
            remaining.append(key)
    return remaining


def _report_payload(state: ReplayState) -> dict[str, Any]:
    manifest = state.manifest.as_dict() if state.manifest else None
    return {
        "schema": "dmb_current_corpus_candidate_replay_report_v1",
        "replay_acceptance": state.replay_acceptance,
        "product_loadability": state.product_loadability,
        "operator_dogfood": state.operator_dogfood,
        "mode": state.mode,
        "run_id": state.run_id,
        "git_head": state.git_head,
        "predecessor_merge": state.predecessor_merge,
        "accepted_run_id": state.accepted_run_id,
        "accepted_artifact_root": state.accepted_artifact_root,
        "frozen_model_id": state.frozen_model_id,
        "frozen_model_policy_digest": state.frozen_model_policy_digest,
        "world_id": state.world_id,
        "database_name": state.database_name,
        "dsn_host_port": f"{EXPECTED_HOST}:{EXPECTED_PORT}",
        "manifest": manifest,
        "genesis_d0": state.genesis_d0,
        "last_good_head": state.last_good_head,
        "terminal_head": state.terminal_head,
        "model_calls": state.model_calls,
        "candidate_regenerations": state.candidate_regenerations,
        "candidate_rewrites": state.candidate_rewrites,
        "graph_writes": state.graph_writes,
        "replay_ledger": state.replay_ledger,
        "product_smoke": state.product_smoke,
        "stop": state.stop,
        "historical_accepted_world_untouched": True,
        "claims_that_remain_false": [
            "semantic truthfulness / recall / precision",
            "Agent usefulness",
            "semantic model selection",
            "historical accepted World repaired",
            "historical backfill safety",
        ],
        "generated_at": _now_iso(),
    }


_DIRECT_READ_SERVICES: dict[tuple[str, str], Any] = {}


def _direct_read_services(dsn: str):
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        build_direct_world_graph_read_services,
    )

    key = (dsn, WORLD_ID)
    services = _DIRECT_READ_SERVICES.get(key)
    if services is None:
        services = build_direct_world_graph_read_services(dsn, WORLD_ID)
        _DIRECT_READ_SERVICES[key] = services
    return services


def _project_campaign(
    *,
    dsn: str,
    campaign_id: str,
    revision_pin: str,
    seams: ReplaySeams,
):
    if seams.project_campaign is not None:
        return seams.project_campaign(
            world_id=WORLD_ID,
            campaign_id=campaign_id,
            revision_pin=revision_pin,
            dsn=dsn,
        )
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        project_world_graph_direct,
    )
    from graph_memory.projection.world_projection import WorldGraphProjectionRequest

    return project_world_graph_direct(
        _direct_read_services(dsn),
        WorldGraphProjectionRequest(
            schema_="dmb_world_graph_projection_request_v1",
            world_id=WORLD_ID,
            campaign_id=campaign_id,
            revision_pin=revision_pin,
            scope_mode="campaign",
            admissibility="gm",
        ),
    )


def _projection_diagnostics(projection: Any) -> list[str]:
    rows = list(getattr(projection, "diagnostics", None) or [])
    out: list[str] = []
    for item in rows:
        if isinstance(item, Mapping):
            code = str(item.get("code") or "")
            message = str(item.get("message") or "")
        else:
            code = str(getattr(item, "code", "") or "")
            message = str(getattr(item, "message", "") or "")
        out.append(f"{code}:{message}" if code else message)
        if code in PROVENANCE_FAIL_CODES or any(
            token in f"{code} {message}".lower()
            for token in ("stored_provenance_invalid", "missing-source", "scope-unknown")
        ):
            raise ReplayStop(
                f"campaign projection rejected a recap-backed object: {code or message}",
                boundary="product_loadability",
                diagnostics=out,
            )
    return out


def _snapshot_revision(result: Any) -> str | None:
    snapshot = getattr(result, "snapshot", None)
    if snapshot is None and isinstance(result, Mapping):
        snapshot = result.get("snapshot")
    if snapshot is None:
        return None
    if isinstance(snapshot, Mapping):
        return str(snapshot.get("revision_id") or "") or None
    return str(getattr(snapshot, "revision_id", "") or "") or None


def _round_trip_object(
    *,
    dsn: str,
    campaign_id: str,
    revision_pin: str,
    node_id: str,
    seams: ReplaySeams,
) -> dict[str, Any]:
    if seams.get_object is not None:
        found = seams.get_object(
            world_id=WORLD_ID,
            campaign_id=campaign_id,
            revision_pin=revision_pin,
            node_id=node_id,
            dsn=dsn,
        )
    else:
        from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
            get_object_direct,
        )
        from graph_memory.retrieval.models import (
            RETRIEVAL_OBJECT_REQUEST_SCHEMA,
            WorldGraphObjectRequest,
        )

        found = get_object_direct(
            _direct_read_services(dsn),
            WorldGraphObjectRequest.model_validate(
                {
                    "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
                    "worldId": WORLD_ID,
                    "campaignId": campaign_id,
                    "revisionPin": revision_pin,
                    "scopeMode": "campaign",
                    "nodeId": node_id,
                }
            ),
        )
    outcome = getattr(found, "outcome", None) or (
        found.get("outcome") if isinstance(found, Mapping) else None
    )
    resolved = getattr(found, "resolved_node_id", None) or (
        found.get("resolved_node_id") if isinstance(found, Mapping) else None
    )
    if str(outcome or "") in {"empty", "unavailable"} or (
        resolved not in {None, node_id} and str(resolved) != node_id
    ):
        raise ReplayStop(
            f"exact-object could not reopen emitted id {node_id!r}",
            boundary="product_loadability",
            campaign_id=campaign_id,
        )

    if seams.get_complete_object is not None:
        complete = seams.get_complete_object(
            world_id=WORLD_ID,
            campaign_id=campaign_id,
            revision_pin=revision_pin,
            node_id=node_id,
            dsn=dsn,
        )
    else:
        from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
            get_complete_object_direct,
        )
        from apps.live_control_server.models.world_graph_object_projection import (
            OBJECT_PROJECTION_REQUEST_SCHEMA,
            WorldGraphObjectProjectionRequest,
        )

        complete = get_complete_object_direct(
            _direct_read_services(dsn),
            WorldGraphObjectProjectionRequest.model_validate(
                {
                    "schema": OBJECT_PROJECTION_REQUEST_SCHEMA,
                    "worldId": WORLD_ID,
                    "campaignId": campaign_id,
                    "revisionPin": revision_pin,
                    "nodeId": node_id,
                    "admissibility": "gm",
                }
            ),
        )
    complete_found = getattr(complete, "found", None)
    if complete_found is False:
        raise ReplayStop(
            f"complete-object could not reopen emitted id {node_id!r}",
            boundary="product_loadability",
            campaign_id=campaign_id,
        )

    if seams.get_neighborhood is not None:
        neighborhood = seams.get_neighborhood(
            world_id=WORLD_ID,
            campaign_id=campaign_id,
            revision_pin=revision_pin,
            node_id=node_id,
            dsn=dsn,
        )
    else:
        from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
            get_neighborhood_direct,
        )
        from graph_memory.retrieval.models import (
            RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
            WorldGraphNeighborhoodRequest,
        )

        neighborhood = get_neighborhood_direct(
            _direct_read_services(dsn),
            WorldGraphNeighborhoodRequest.model_validate(
                {
                    "schema": RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
                    "worldId": WORLD_ID,
                    "campaignId": campaign_id,
                    "revisionPin": revision_pin,
                    "scopeMode": "campaign",
                    "seedNodeIds": [node_id],
                }
            ),
        )
    missing = []
    coverage = getattr(neighborhood, "coverage", None)
    if coverage is not None:
        missing = list(getattr(coverage, "missing_seed_node_ids", None) or [])
    neighborhood_nodes = [
        getattr(item, "node_id", None) or (item.get("node_id") if isinstance(item, Mapping) else None)
        for item in (getattr(neighborhood, "nodes", None) or [])
    ]
    if node_id in missing or (
        str(getattr(neighborhood, "outcome", "") or "") == "empty"
        and node_id not in neighborhood_nodes
    ):
        raise ReplayStop(
            f"neighborhood treated emitted id {node_id!r} as missing",
            boundary="product_loadability",
            campaign_id=campaign_id,
        )

    if seams.get_evidence is not None:
        evidence = seams.get_evidence(
            world_id=WORLD_ID,
            campaign_id=campaign_id,
            revision_pin=revision_pin,
            node_id=node_id,
            dsn=dsn,
        )
    else:
        from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
            get_evidence_direct,
        )
        from graph_memory.retrieval.models import (
            RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
            WorldGraphEvidenceRequest,
        )

        evidence = get_evidence_direct(
            _direct_read_services(dsn),
            WorldGraphEvidenceRequest.model_validate(
                {
                    "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                    "worldId": WORLD_ID,
                    "campaignId": campaign_id,
                    "revisionPin": revision_pin,
                    "scopeMode": "campaign",
                    "target": {"kind": "node", "id": node_id},
                }
            ),
        )
    evidence_outcome = str(getattr(evidence, "outcome", "") or "")
    if evidence_outcome in {"unavailable"}:
        raise ReplayStop(
            f"evidence treated emitted id {node_id!r} as missing",
            boundary="product_loadability",
            campaign_id=campaign_id,
        )
    snapshot_rev = _snapshot_revision(found) or _snapshot_revision(complete)
    if snapshot_rev and snapshot_rev != revision_pin:
        raise ReplayStop(
            f"product read at pin {revision_pin!r} leaked revision {snapshot_rev!r}",
            boundary="product_loadability",
            campaign_id=campaign_id,
        )
    return {
        "node_id": node_id,
        "exact_outcome": str(outcome or ""),
        "complete_found": bool(complete_found if complete_found is not None else True),
        "evidence_outcome": evidence_outcome,
        "source_anchors": list(getattr(evidence, "source_anchors", None) or []),
        "evidence": evidence,
    }


def _read_source_anchor(
    *,
    dsn: str,
    campaign_id: str,
    revision_pin: str,
    anchor_id: str,
    repo_root: Path,
    seams: ReplaySeams,
):
    if seams.read_source is not None:
        return seams.read_source(
            world_id=WORLD_ID,
            campaign_id=campaign_id,
            revision_pin=revision_pin,
            anchor_id=anchor_id,
            dsn=dsn,
        )
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        read_source_anchor_direct,
    )
    from graph_memory.retrieval.models import (
        RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
        WorldGraphSourceAnchorReadRequest,
    )

    return read_source_anchor_direct(
        _direct_read_services(dsn),
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "worldId": WORLD_ID,
                "campaignId": campaign_id,
                "revisionPin": revision_pin,
                "scopeMode": "campaign",
                "anchorId": anchor_id,
            }
        ),
        repo_root=repo_root,
    )


def _select_emitted_id(projection: Any, *, preferred: str, label: str) -> str:
    nodes = list(getattr(projection, "nodes", None) or [])
    ids = [
        str(getattr(node, "node_id", None) or (node.get("node_id") if isinstance(node, Mapping) else ""))
        for node in nodes
    ]
    if preferred in ids:
        return preferred
    matches: list[str] = []
    needle = label.lower()
    for node in nodes:
        node_id = str(
            getattr(node, "node_id", None)
            or (node.get("node_id") if isinstance(node, Mapping) else "")
        )
        node_label = str(
            getattr(node, "label", None)
            or (node.get("label") if isinstance(node, Mapping) else "")
        ).lower()
        aliases = [
            str(item).lower()
            for item in (
                getattr(node, "aliases", None)
                or (node.get("aliases") if isinstance(node, Mapping) else [])
                or []
            )
        ]
        if node_label == needle or needle in aliases:
            matches.append(node_id)
    unique = sorted(set(matches))
    if len(unique) == 1:
        return unique[0]
    raise ReplayStop(
        f"product projection did not emit a unique {label!r} identity",
        boundary="product_loadability",
        diagnostics=[f"preferred={preferred}", f"matches={unique}"],
    )


def _anchor_id(anchor: Any) -> str:
    if isinstance(anchor, Mapping):
        return str(anchor.get("anchor_id") or anchor.get("anchorId") or "")
    return str(getattr(anchor, "anchor_id", "") or "")


def _source_read_diagnostics(read: Any) -> list[str]:
    rows = list(getattr(read, "diagnostics", None) or [])
    if not rows and isinstance(read, Mapping):
        rows = list(read.get("diagnostics") or [])
    out: list[str] = []
    for item in rows:
        if isinstance(item, Mapping):
            code = str(item.get("code") or "")
            message = str(item.get("message") or "")
        else:
            code = str(getattr(item, "code", "") or "")
            message = str(getattr(item, "message", "") or "")
        if code or message:
            out.append(f"{code}:{message}" if code else message)
    return out


def _require_source_navigation(
    *,
    dsn: str,
    campaign_id: str,
    revision_pin: str,
    round_trip: Mapping[str, Any],
    repo_root: Path,
    seams: ReplaySeams,
    require_anchor: bool,
) -> dict[str, Any]:
    anchors = list(round_trip.get("source_anchors") or [])
    if not anchors:
        evidence = round_trip.get("evidence")
        anchors = list(getattr(evidence, "source_anchors", None) or [])
    if not anchors:
        if require_anchor:
            raise ReplayStop(
                "evidence/source read is unresolved; no source anchors emitted",
                boundary="product_loadability",
                campaign_id=campaign_id,
            )
        return {"status": "empty_evidence_ok"}
    last_failure: dict[str, Any] | None = None
    for anchor in anchors:
        anchor_id = _anchor_id(anchor)
        if not anchor_id:
            if require_anchor:
                raise ReplayStop(
                    "evidence emitted a source anchor without an opaque anchor id",
                    boundary="product_loadability",
                    campaign_id=campaign_id,
                )
            last_failure = {"status": "unreadable", "reason": "missing_anchor_id"}
            continue
        read = _read_source_anchor(
            dsn=dsn,
            campaign_id=campaign_id,
            revision_pin=revision_pin,
            anchor_id=anchor_id,
            repo_root=repo_root,
            seams=seams,
        )
        outcome = str(
            getattr(read, "outcome", None)
            or (read.get("outcome") if isinstance(read, Mapping) else "")
            or ""
        )
        digest = getattr(read, "content_sha256", None) or (
            read.get("content_sha256") if isinstance(read, Mapping) else None
        )
        locator_kind = getattr(read, "locator_kind", None) or (
            read.get("locator_kind") if isinstance(read, Mapping) else None
        )
        snapshot_rev = _snapshot_revision(read)
        diagnostics = _source_read_diagnostics(read)
        if snapshot_rev and snapshot_rev != revision_pin:
            raise ReplayStop(
                f"source-read at pin {revision_pin!r} leaked revision {snapshot_rev!r}",
                boundary="product_loadability",
                campaign_id=campaign_id,
            )
        digest_text = str(digest or "").strip()
        if outcome in {"enough", "truncated"} and digest_text:
            return {
                "anchor_id": anchor_id,
                "outcome": outcome,
                "content_sha256": digest_text,
                "locator_kind": locator_kind,
                "revision_id": snapshot_rev or revision_pin,
            }
        last_failure = {
            "status": "unreadable",
            "anchor_id": anchor_id,
            "outcome": outcome,
            "content_sha256": digest_text or None,
            "locator_kind": locator_kind,
            "diagnostics": diagnostics,
            "revision_id": snapshot_rev or revision_pin,
        }
        if require_anchor:
            raise ReplayStop(
                (
                    f"source-read dead-ended for anchor {anchor_id}: "
                    f"outcome={outcome!r} digest={digest_text or None!r}"
                ),
                boundary="product_loadability",
                campaign_id=campaign_id,
                diagnostics=diagnostics
                or [
                    f"outcome={outcome}",
                    f"locator_kind={locator_kind}",
                    "digest verification required",
                ],
            )
    if require_anchor:
        raise ReplayStop(
            "evidence/source read is unresolved; no source anchors emitted",
            boundary="product_loadability",
            campaign_id=campaign_id,
        )
    return last_failure or {"status": "unreadable"}


def _is_ancestor(
    *,
    descendant: str,
    ancestor: str,
    seams: ReplaySeams,
    dsn: str,
) -> bool:
    cursor: str | None = descendant
    seen: set[str] = set()
    while cursor:
        if cursor == ancestor:
            return True
        if cursor in seen:
            raise ReplayStop(
                f"revision parent cycle while proving ancestry of {ancestor}",
                boundary="product_loadability",
            )
        seen.add(cursor)
        if seams.read_revision_parent is not None:
            cursor = seams.read_revision_parent(WORLD_ID, cursor)
        else:
            from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
                DungeonMindWorldGraphAuthorityAdapter,
            )

            cursor = DungeonMindWorldGraphAuthorityAdapter(
                database_url=dsn
            ).read_revision(WORLD_ID, cursor).parent_revision_id
    return False


def _projection_summary(projection: Any, *, campaign_id: str) -> dict[str, Any]:
    summary = getattr(projection, "summary", None)
    snapshot = getattr(projection, "snapshot", None)
    return {
        "campaign_id": campaign_id,
        "revision_id": getattr(snapshot, "revision_id", None),
        "head_revision_id": getattr(snapshot, "head_revision_id", None),
        "node_count": getattr(summary, "node_count", len(getattr(projection, "nodes", []) or [])),
        "relationship_count": getattr(
            summary, "relationship_count", len(getattr(projection, "relationships", []) or [])
        ),
        "diagnostics": _projection_diagnostics(projection),
        "node_ids": [
            str(getattr(node, "node_id", None) or node.get("node_id"))
            for node in (getattr(projection, "nodes", None) or [])
        ],
    }


def run_product_smoke(
    *,
    repo_root: Path,
    dsn: str,
    terminal_head: str,
    replay_ledger: Sequence[Mapping[str, Any]],
    seams: ReplaySeams | None = None,
    genesis_d0: str | None = None,
) -> dict[str, Any]:
    seams = seams or ReplaySeams()
    c1 = _project_campaign(
        dsn=dsn, campaign_id="longmont-c1", revision_pin=terminal_head, seams=seams
    )
    c2 = _project_campaign(
        dsn=dsn, campaign_id="longmont-c2", revision_pin=terminal_head, seams=seams
    )
    c1_summary = _projection_summary(c1, campaign_id="longmont-c1")
    c2_summary = _projection_summary(c2, campaign_id="longmont-c2")
    print(
        "product-smoke projections "
        f"c1_nodes={c1_summary['node_count']} c2_nodes={c2_summary['node_count']}",
        file=sys.stderr,
        flush=True,
    )

    by_key = {
        (str(row["campaign_id"]), str(row["session_id"])): row
        for row in replay_ledger
    }
    try:
        c2s22 = by_key[C2S22_KEY]
        c1s10 = by_key[C1S10_KEY]
    except KeyError as exc:
        raise ReplayStop(
            "replay ledger is missing C2S22 or C1S10 child revisions",
            boundary="product_loadability",
        ) from exc
    mireward_rev = str(c2s22.get("receipt_child_revision") or "")
    c1s10_rev = str(c1s10.get("receipt_child_revision") or "")
    if not mireward_rev or not c1s10_rev:
        raise ReplayStop(
            "replay ledger missing child revisions for Mireward/C1S10 pins",
            boundary="product_loadability",
        )
    if not _is_ancestor(
        descendant=terminal_head, ancestor=c1s10_rev, seams=seams, dsn=dsn
    ):
        raise ReplayStop(
            "C1S10 replay revision is not an ancestor of terminal head",
            boundary="product_loadability",
        )

    mireward_projection = _project_campaign(
        dsn=dsn, campaign_id="longmont-c2", revision_pin=mireward_rev, seams=seams
    )
    _projection_diagnostics(mireward_projection)
    mireward_id = _select_emitted_id(
        mireward_projection, preferred=MIREWARD_PREFERRED_ID, label="Mireward"
    )
    mireward_round = _round_trip_object(
        dsn=dsn,
        campaign_id="longmont-c2",
        revision_pin=mireward_rev,
        node_id=mireward_id,
        seams=seams,
    )
    mireward_source = _require_source_navigation(
        dsn=dsn,
        campaign_id="longmont-c2",
        revision_pin=mireward_rev,
        round_trip=mireward_round,
        repo_root=repo_root,
        seams=seams,
        require_anchor=True,
    )

    pin_projection = _project_campaign(
        dsn=dsn, campaign_id="longmont-c1", revision_pin=c1s10_rev, seams=seams
    )
    pin_summary = _projection_summary(pin_projection, campaign_id="longmont-c1")
    if pin_summary["revision_id"] not in {None, c1s10_rev}:
        raise ReplayStop(
            f"C1S10 pin leaked revision {pin_summary['revision_id']!r}",
            boundary="product_loadability",
        )
    if pin_summary["revision_id"] == terminal_head and c1s10_rev != terminal_head:
        raise ReplayStop(
            "C1S10 historical pin fell forward to terminal head",
            boundary="product_loadability",
        )
    pin_id = _select_emitted_id(pin_projection, preferred="node:character:torbin", label="Torbin")
    pin_round = _round_trip_object(
        dsn=dsn,
        campaign_id="longmont-c1",
        revision_pin=c1s10_rev,
        node_id=pin_id,
        seams=seams,
    )
    if _snapshot_revision(pin_round.get("evidence")) == terminal_head and c1s10_rev != terminal_head:
        raise ReplayStop(
            "C1S10 object read fell forward to terminal head",
            boundary="product_loadability",
        )

    round_trips: list[dict[str, Any]] = []
    campaign_anchors: dict[str, dict[str, Any]] = {}
    for campaign_id, _projection, summary in (
        ("longmont-c1", c1, c1_summary),
        ("longmont-c2", c2, c2_summary),
    ):
        total_nodes = len(summary["node_ids"])
        for index, node_id in enumerate(summary["node_ids"], start=1):
            if index == 1 or index % 25 == 0 or index == total_nodes:
                print(
                    f"product-smoke {campaign_id} {index}/{total_nodes} {node_id}",
                    file=sys.stderr,
                    flush=True,
                )
            result = _round_trip_object(
                dsn=dsn,
                campaign_id=campaign_id,
                revision_pin=terminal_head,
                node_id=node_id,
                seams=seams,
            )
            round_trips.append(
                {"campaign_id": campaign_id, **{k: v for k, v in result.items() if k != "evidence"}}
            )
            if campaign_id not in campaign_anchors and result.get("source_anchors"):
                nav = _require_source_navigation(
                    dsn=dsn,
                    campaign_id=campaign_id,
                    revision_pin=terminal_head,
                    round_trip=result,
                    repo_root=repo_root,
                    seams=seams,
                    require_anchor=False,
                )
                if nav.get("content_sha256"):
                    campaign_anchors[campaign_id] = nav
        if campaign_id not in campaign_anchors:
            raise ReplayStop(
                f"campaign {campaign_id} emitted no digest-verified recap source read",
                boundary="product_loadability",
                campaign_id=campaign_id,
            )

    return {
        "terminal_head": terminal_head,
        "genesis_d0": genesis_d0,
        "campaign_projections": {"longmont-c1": c1_summary, "longmont-c2": c2_summary},
        "emitted_id_round_trips": {
            "attempted": len(round_trips),
            "passed": len(round_trips),
        },
        "campaign_source_reads": campaign_anchors,
        "mireward": {
            "node_id": mireward_id,
            "revision_id": mireward_rev,
            "source": mireward_source,
        },
        "c1s10_benchmark_pin": {
            "revision_id": c1s10_rev,
            "is_ancestor_of_terminal": True,
            "object_id": pin_id,
        },
        "product_loadability": "PASS",
    }


def run_preflight(
    *,
    accepted_artifact_root: Path,
    repo_root: Path | None = None,
    dsn: str | None = None,
    seams: ReplaySeams | None = None,
    expected_count: int = ACCEPTED_MANIFEST_COUNT,
    expected_digest: str = ACCEPTED_MANIFEST_DIGEST,
    require_clean_worktree: bool = False,
) -> ReplayState:
    """Zero model calls; zero graph mutation."""
    from src.bootstrap_env import load_dungeonmindbuddy_dotenv

    load_dungeonmindbuddy_dotenv()
    root = (repo_root or REPO_ROOT).resolve()
    seams = seams or ReplaySeams()
    run_id = _new_run_id("preflight")
    out = root / OUTPUT_REL / run_id
    out.mkdir(parents=True, exist_ok=True)
    head = git_head(root)
    if require_clean_worktree and not git_worktree_clean(root):
        raise ReplayStop(
            "worktree is dirty; expected clean checkout for replay",
            boundary="replay_artifact_unavailable",
        )
    dsn_value = dsn or _default_dsn()
    assert_runtime_dsn(dsn_value)
    manifest, _ledger = load_accepted_cohort(
        artifact_root=accepted_artifact_root,
        repo_root=root,
        expected_count=expected_count,
        expected_digest=expected_digest,
    )
    _assert_pristine(WORLD_ID, dsn=dsn_value, seams=seams)
    state = ReplayState(
        run_id=run_id,
        mode="preflight",
        git_head=head,
        dsn=dsn_value,
        accepted_artifact_root=str(accepted_artifact_root.resolve()),
        manifest=manifest,
        output_dir=out,
    )
    _write_json(out / "preflight_report.json", _report_payload(state))
    return state


def run_execute(
    *,
    accepted_artifact_root: Path,
    repo_root: Path | None = None,
    dsn: str | None = None,
    seams: ReplaySeams | None = None,
    expected_count: int = ACCEPTED_MANIFEST_COUNT,
    expected_digest: str = ACCEPTED_MANIFEST_DIGEST,
    require_clean_worktree: bool = False,
) -> ReplayState:
    """Fresh pristine replay; stop on first failure. Never resumes."""
    from src.bootstrap_env import load_dungeonmindbuddy_dotenv

    load_dungeonmindbuddy_dotenv()
    root = (repo_root or REPO_ROOT).resolve()
    seams = seams or ReplaySeams()
    run_id = _new_run_id("execute")
    out = root / OUTPUT_REL / run_id
    out.mkdir(parents=True, exist_ok=True)
    head = git_head(root)
    if require_clean_worktree and not git_worktree_clean(root):
        raise ReplayStop(
            "worktree is dirty; expected clean checkout for replay",
            boundary="replay_artifact_unavailable",
        )
    dsn_value = dsn or _default_dsn()
    assert_runtime_dsn(dsn_value)
    manifest, ledger = load_accepted_cohort(
        artifact_root=accepted_artifact_root,
        repo_root=root,
        expected_count=expected_count,
        expected_digest=expected_digest,
    )
    _assert_pristine(WORLD_ID, dsn=dsn_value, seams=seams)
    _write_json(out / "manifest.json", manifest.as_dict())

    state = ReplayState(
        run_id=run_id,
        mode="execute",
        git_head=head,
        dsn=dsn_value,
        accepted_artifact_root=str(accepted_artifact_root.resolve()),
        manifest=manifest,
        output_dir=out,
    )
    by_key = {entry.key: entry for entry in manifest.entries}

    try:
        d0 = _run_genesis(repo_root=root, dsn=dsn_value, seams=seams)
        state.genesis_d0 = d0
        state.last_good_head = d0
        state.graph_writes += 1
        prior_head = d0
        for row in ledger:
            entry = by_key[row.key]
            verify_entry_source_bytes(root, entry)
            candidate_path = _resolve_candidate_path(row.candidate_locator, accepted_artifact_root)
            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            from apps.live_control_server.services.candidate_graph_admission import (
                canonical_candidate_digest,
            )

            digest = canonical_candidate_digest(candidate)
            if digest != row.candidate_digest:
                raise ReplayStop(
                    "candidate digest drifted between preflight and replay row",
                    boundary="replay_artifact_drift",
                    campaign_id=entry.campaign_id,
                    session_id=entry.session_id,
                    last_good_head=prior_head,
                )
            artifact = _load_canonical_source_artifact(
                repo_root=root, entry=entry, seams=seams
            )
            source_uri = str(getattr(artifact, "uri", "") or f"repo://{entry.original_path}")
            source_revision_id = (
                row.source_revision_id
                or f"sha256:{getattr(artifact, 'content_sha256', entry.original_sha256)}"
            )
            admit = _admit_and_confirm(
                repo_root=root,
                dsn=dsn_value,
                entry=entry,
                candidate_graph=candidate,
                source_artifact=artifact,
                source_uri=source_uri,
                source_revision_id=source_revision_id,
                prior_head=prior_head,
                seams=seams,
            )
            state.graph_writes += 1
            prior_head = admit["child_revision_id"]
            state.last_good_head = prior_head
            state.replay_ledger.append(
                {
                    "ordinal": entry.ordinal,
                    "campaign_id": entry.campaign_id,
                    "session_id": entry.session_id,
                    "predecessor_candidate_digest": row.candidate_digest,
                    "candidate_locator": row.candidate_locator,
                    "candidate_digest": digest,
                    "source_artifact_id": entry.source_artifact_id,
                    "source_admission": admit["source_admission"],
                    "sealed_parent_revision": admit["parent_revision_id"],
                    "proposal_id": admit["proposal_id"],
                    "proposal_digest": admit["proposal_digest"],
                    "receipt_child_revision": admit["child_revision_id"],
                    "verified_current_head": admit["child_revision_id"],
                    "accepted_proposal_count": admit["accepted_proposal_count"],
                    "admission_dispositions": admit["dispositions"],
                }
            )
            _write_json(out / "replay_ledger.json", {"sessions": state.replay_ledger})

        state.terminal_head = prior_head
        state.replay_acceptance = "PASS"
    except ReplayStop as stop:
        state.replay_acceptance = "HOLD"
        state.product_loadability = "NOT_MEASURED"
        state.operator_dogfood = "NOT_MEASURED"
        remaining = _remaining_sessions(manifest.entries, stop)
        state.stop = _stop_payload(state, stop, remaining)
    finally:
        _write_json(out / "replay_report.json", _report_payload(state))
    return state


def run_product_smoke_from_run(
    *,
    completed_replay_run_root: Path,
    repo_root: Path | None = None,
    dsn: str | None = None,
    seams: ReplaySeams | None = None,
) -> ReplayState:
    root = (repo_root or REPO_ROOT).resolve()
    seams = seams or ReplaySeams()
    run_root = completed_replay_run_root.resolve()
    report_path = run_root / "replay_report.json"
    ledger_path = run_root / "replay_ledger.json"
    if not report_path.is_file():
        raise ReplayStop(
            "completed replay report missing; cannot product-smoke a partial run",
            boundary="product_loadability",
        )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("replay_acceptance") != "PASS" or not report.get("terminal_head"):
        raise ReplayStop(
            "product-smoke refuses a non-PASS / incomplete replay",
            boundary="product_loadability",
        )
    if report.get("stop"):
        raise ReplayStop(
            "product-smoke refuses a STOP replay; no resume-as-PASS",
            boundary="product_loadability",
        )
    ledger_sessions = list(
        (json.loads(ledger_path.read_text(encoding="utf-8")).get("sessions") if ledger_path.is_file() else None)
        or report.get("replay_ledger")
        or []
    )
    dsn_value = dsn or str(report.get("dsn") or "") or _default_dsn()
    from src.bootstrap_env import load_dungeonmindbuddy_dotenv

    load_dungeonmindbuddy_dotenv()
    assert_runtime_dsn(dsn_value)
    state = ReplayState(
        run_id=str(report.get("run_id") or run_root.name),
        mode="product-smoke",
        git_head=str(report.get("git_head") or git_head(root)),
        dsn=dsn_value,
        accepted_artifact_root=report.get("accepted_artifact_root"),
        genesis_d0=report.get("genesis_d0"),
        terminal_head=report.get("terminal_head"),
        last_good_head=report.get("terminal_head"),
        replay_acceptance="PASS",
        replay_ledger=list(ledger_sessions),
        output_dir=run_root,
        model_calls=int(report.get("model_calls") or 0),
        graph_writes=int(report.get("graph_writes") or 0),
    )
    if state.manifest is None and report.get("manifest"):
        raw = report["manifest"]
        state.manifest = FrozenManifest(
            schema=str(raw.get("schema") or ACCEPTED_MANIFEST_SCHEMA),
            entries=tuple(_manifest_entry_from_mapping(item) for item in raw.get("entries") or []),
            digest=str(raw.get("digest") or ""),
        )
    try:
        state.product_smoke = run_product_smoke(
            repo_root=root,
            dsn=dsn_value,
            terminal_head=str(state.terminal_head),
            replay_ledger=state.replay_ledger,
            seams=seams,
            genesis_d0=state.genesis_d0,
        )
        state.product_loadability = "PASS"
    except ReplayStop as stop:
        state.product_loadability = "NOT_READY"
        state.operator_dogfood = "NOT_MEASURED"
        state.stop = _stop_payload(state, stop, [])
        state.product_smoke = {
            "product_loadability": "NOT_READY",
            "stop": state.stop,
        }
    _write_json(run_root / "product_smoke_report.json", _report_payload(state))
    _write_json(run_root / "replay_report.json", _report_payload(state))
    return state


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Zero-model replay of accepted current-corpus candidates"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", metavar="ACCEPTED_RUN_ROOT")
    mode.add_argument("--execute", metavar="ACCEPTED_RUN_ROOT")
    mode.add_argument("--product-smoke", metavar="COMPLETED_REPLAY_RUN_ROOT")
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--require-clean-worktree", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.preflight:
            state = run_preflight(
                accepted_artifact_root=Path(args.preflight),
                dsn=args.dsn,
                require_clean_worktree=args.require_clean_worktree,
            )
            print(
                json.dumps(
                    {
                        "mode": "preflight",
                        "git_head": state.git_head,
                        "manifest_count": state.manifest.count if state.manifest else 0,
                        "manifest_digest": state.manifest.digest if state.manifest else None,
                        "model_calls": state.model_calls,
                        "graph_writes": state.graph_writes,
                        "world_id": state.world_id,
                        "database_name": state.database_name,
                        "output_dir": str(state.output_dir),
                    },
                    indent=2,
                )
            )
            return 0
        if args.execute:
            state = run_execute(
                accepted_artifact_root=Path(args.execute),
                dsn=args.dsn,
                require_clean_worktree=args.require_clean_worktree,
            )
            print(
                json.dumps(
                    {
                        "mode": "execute",
                        "replay_acceptance": state.replay_acceptance,
                        "git_head": state.git_head,
                        "model_calls": state.model_calls,
                        "graph_writes": state.graph_writes,
                        "genesis_d0": state.genesis_d0,
                        "terminal_head": state.terminal_head,
                        "stop": state.stop,
                        "output_dir": str(state.output_dir),
                    },
                    indent=2,
                )
            )
            return 0 if state.replay_acceptance == "PASS" else 1
        state = run_product_smoke_from_run(
            completed_replay_run_root=Path(args.product_smoke),
            dsn=args.dsn,
        )
        print(
            json.dumps(
                {
                    "mode": "product-smoke",
                    "replay_acceptance": state.replay_acceptance,
                    "product_loadability": state.product_loadability,
                    "product_smoke": state.product_smoke,
                    "stop": state.stop,
                },
                indent=2,
            )
        )
        return 0 if state.product_loadability == "PASS" else 1
    except ReplayStop as stop:
        print(
            json.dumps(
                {
                    "status": "STOP",
                    "boundary": stop.boundary,
                    "message": str(stop),
                    "campaign_id": stop.campaign_id,
                    "session_id": stop.session_id,
                    "diagnostics": list(stop.diagnostics),
                    "model_calls": 0,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
