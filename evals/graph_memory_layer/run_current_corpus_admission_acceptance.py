#!/usr/bin/env python3
"""Fail-closed structural acceptance over current production memory seams.

This harness freezes the current normalized-recap lineage, initializes one
pristine acceptance World via recap genesis, then chronologically runs each
original recap through production extraction → Candidate Graph Admission →
exact-parent governed write. It never repairs, sanitizes, skips, or resumes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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

WORLD_ID = "dogfood-current-corpus-acceptance-v1"
DATABASE_NAME = "dmb_current_corpus_acceptance_v1"
EXPECTED_HOST = "127.0.0.1"
EXPECTED_PORT = 54329
OPERATOR = "current-corpus-admission-acceptance"
OUTPUT_REL = Path("out/graph_memory/current_corpus_admission_acceptance_v1")

REQUIRED_NORMALIZATION_SCHEMA = "dmb_recap_normalized_v1"
ALLOWED_CAMPAIGNS = frozenset({"longmont-c1", "longmont-c2"})


class AcceptanceStop(RuntimeError):
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


@dataclass
class AcceptanceSeams:
    """Injectable production call boundaries for deterministic tests."""

    probe_world: Callable[[str], Any] | None = None
    prepare_genesis: Callable[..., Any] | None = None
    confirm_genesis: Callable[..., Any] | None = None
    extract_session: Callable[..., Any] | None = None
    load_mutation_context: Callable[..., Any] | None = None
    prepare_admission: Callable[..., Any] | None = None
    confirm_admission: Callable[..., Any] | None = None
    current_head: Callable[[str], str] | None = None
    read_revision_parent: Callable[[str, str], str | None] | None = None


@dataclass
class AcceptanceState:
    run_id: str
    mode: str
    git_head: str
    model_policy_digest: str
    resolved_model_id: str
    dsn: str
    world_id: str = WORLD_ID
    database_name: str = DATABASE_NAME
    manifest: FrozenManifest | None = None
    model_calls: int = 0
    graph_writes: int = 0
    genesis_d0: str | None = None
    last_good_head: str | None = None
    terminal_head: str | None = None
    structural_acceptance: str = "HOLD"
    session_ledger: list[dict[str, Any]] = field(default_factory=list)
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
    return (
        subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
        )
        .strip()
    )


def git_worktree_clean(repo_root: Path) -> bool:
    status = subprocess.check_output(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        text=True,
    )
    return not status.strip()


def model_policy_digest(repo_root: Path | None = None) -> str:
    from src.model_policy import buddy_model_policy_path

    path = buddy_model_policy_path()
    return _sha256_file(path)


def resolved_production_model_id() -> str:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        resolve_category_graph_model,
    )

    return resolve_category_graph_model(None)


def parse_flat_frontmatter(markdown: str) -> dict[str, str | int | None]:
    from src.ingestion.frontmatter import (
        FrontmatterParseError,
        _parse_frontmatter_block,
        split_frontmatter,
    )

    block, _body = split_frontmatter(markdown)
    if block is None:
        raise FrontmatterParseError("missing frontmatter")
    return _parse_frontmatter_block(block)


def _discover_sessions(corpus: Path, campaign_number: int) -> list[int]:
    from src.corpus.session_recap_paths import session_recaps_prefix

    norm_dir = corpus / session_recaps_prefix(campaign_number) / "_normalized"
    if not norm_dir.is_dir():
        raise AcceptanceStop(
            f"missing normalized directory for campaign {campaign_number}",
            boundary="acceptance_preflight",
        )
    sessions: set[int] = set()
    for path in norm_dir.glob("Session *.md"):
        match = re.match(r"Session\s+(\d+)\s+-", path.name, re.I)
        if match:
            sessions.add(int(match.group(1)))
    ordered = sorted(sessions)
    if not ordered:
        raise AcceptanceStop(
            f"no normalized recaps for campaign {campaign_number}",
            boundary="acceptance_preflight",
        )
    expected = list(range(1, ordered[-1] + 1))
    if ordered != expected:
        missing = sorted(set(expected) - set(ordered))
        raise AcceptanceStop(
            f"non-contiguous sessions for campaign {campaign_number}: missing {missing}",
            boundary="acceptance_preflight",
        )
    return ordered


def _require_repo_contained(path: Path, repo_root: Path) -> Path:
    resolved = path.resolve()
    root = repo_root.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AcceptanceStop(
            f"path escapes repository: {resolved}",
            boundary="acceptance_preflight",
        ) from exc
    return resolved


def freeze_current_corpus_manifest(repo_root: Path) -> FrozenManifest:
    """Freeze one exact current-corpus cohort before any model call."""
    from src.corpus.session_recap_paths import (
        campaign_id_from_number,
        pick_normalized_basename_from_disk,
        session_recaps_prefix,
    )
    from src.graph_memory.evidence.source_artifact import build_recap_source_artifact_id
    from src.live_play.recap_stage_paths import corpus_root as default_corpus_root

    corpus = default_corpus_root()
    if not corpus.is_dir():
        # Allow tests to point corpus via repo_root layout.
        corpus = repo_root / "corpus" / "eldyrwild-markdown"
    corpus = _require_repo_contained(corpus, repo_root)

    entries: list[ManifestEntry] = []
    ordinal = 0
    seen_keys: set[tuple[str, int]] = set()

    for campaign_number in (1, 2):
        campaign_id = campaign_id_from_number(campaign_number)
        for session in _discover_sessions(corpus, campaign_number):
            key = (campaign_id, session)
            if key in seen_keys:
                raise AcceptanceStop(
                    f"duplicate logical recap {campaign_id} session {session}",
                    boundary="acceptance_preflight",
                )
            seen_keys.add(key)

            picked = pick_normalized_basename_from_disk(
                corpus, campaign_number=campaign_number, session=session
            )
            if picked is None:
                raise AcceptanceStop(
                    f"ambiguous or missing normalized recap {campaign_id} S{session}",
                    boundary="acceptance_preflight",
                )
            normalized_path = (
                corpus
                / session_recaps_prefix(campaign_number)
                / "_normalized"
                / f"{picked}.md"
            )
            normalized_path = _require_repo_contained(normalized_path, repo_root)
            if not normalized_path.is_file():
                raise AcceptanceStop(
                    f"normalized recap missing: {normalized_path}",
                    boundary="acceptance_preflight",
                )

            markdown = normalized_path.read_text(encoding="utf-8")
            fm = parse_flat_frontmatter(markdown)
            if str(fm.get("normalization_schema") or "") != REQUIRED_NORMALIZATION_SCHEMA:
                raise AcceptanceStop(
                    f"bad normalization_schema for {normalized_path.name}",
                    boundary="acceptance_preflight",
                )
            if str(fm.get("document_class") or "") != "play":
                raise AcceptanceStop(
                    f"document_class must be play for {normalized_path.name}",
                    boundary="acceptance_preflight",
                )
            if str(fm.get("canon_layer") or "") != "campaign":
                raise AcceptanceStop(
                    f"canon_layer must be campaign for {normalized_path.name}",
                    boundary="acceptance_preflight",
                )
            if str(fm.get("source_class") or "") != "observed_session_recap":
                raise AcceptanceStop(
                    f"source_class must be observed_session_recap for {normalized_path.name}",
                    boundary="acceptance_preflight",
                )
            if str(fm.get("temporal_scope") or "") != "session_specific":
                raise AcceptanceStop(
                    f"temporal_scope must be session_specific for {normalized_path.name}",
                    boundary="acceptance_preflight",
                )
            if str(fm.get("campaign_id") or "") != campaign_id:
                raise AcceptanceStop(
                    f"campaign_id disagreement for {normalized_path.name}",
                    boundary="acceptance_preflight",
                )
            session_vals = (
                fm.get("session"),
                fm.get("origin_session"),
                fm.get("last_updated_session"),
            )
            if session_vals != (session, session, session):
                raise AcceptanceStop(
                    f"session identity disagreement for {normalized_path.name}: {session_vals}",
                    boundary="acceptance_preflight",
                )
            normalized_from = str(fm.get("normalized_from") or "").strip()
            if not normalized_from:
                raise AcceptanceStop(
                    f"missing normalized_from for {normalized_path.name}",
                    boundary="acceptance_preflight",
                )
            original_path = _require_repo_contained(corpus / normalized_from, repo_root)
            if not original_path.is_file():
                raise AcceptanceStop(
                    f"original source missing for {normalized_path.name}: {original_path}",
                    boundary="acceptance_preflight",
                )

            original_sha = _sha256_file(original_path)
            session_id = f"session-{session}"
            source_artifact_id = build_recap_source_artifact_id(
                campaign_id=campaign_id,
                session_id=session_id,
                content_sha256=original_sha,
            )
            ordinal += 1
            entries.append(
                ManifestEntry(
                    ordinal=ordinal,
                    campaign_id=campaign_id,
                    campaign_number=campaign_number,
                    session=session,
                    session_id=session_id,
                    normalized_path=str(normalized_path.relative_to(repo_root)),
                    normalized_sha256=_sha256_file(normalized_path),
                    original_path=str(original_path.relative_to(repo_root)),
                    original_sha256=original_sha,
                    source_artifact_id=source_artifact_id,
                )
            )

    payload = {
        "schema": "dmb_current_corpus_admission_manifest_v1",
        "entries": [entry.as_dict() for entry in entries],
    }
    digest = _digest_obj(payload)
    return FrozenManifest(
        schema="dmb_current_corpus_admission_manifest_v1",
        entries=tuple(entries),
        digest=digest,
    )


def assert_runtime_dsn(dsn: str) -> tuple[str, int, str]:
    parsed = urlparse(dsn)
    host = parsed.hostname or ""
    port = int(parsed.port or 0)
    database = (parsed.path or "").lstrip("/")
    if host not in {EXPECTED_HOST, "localhost"}:
        raise AcceptanceStop(
            f"DSN host must be loopback {EXPECTED_HOST}, got {host!r}",
            boundary="runtime_guard",
        )
    if host == "localhost":
        host = EXPECTED_HOST
    if port != EXPECTED_PORT:
        raise AcceptanceStop(
            f"DSN port must be {EXPECTED_PORT}, got {port}",
            boundary="runtime_guard",
        )
    if database != DATABASE_NAME:
        raise AcceptanceStop(
            f"DSN database must be {DATABASE_NAME}, got {database!r}",
            boundary="runtime_guard",
        )
    return host, port, database


def verify_entry_source_bytes(repo_root: Path, entry: ManifestEntry) -> None:
    original = repo_root / entry.original_path
    if not original.is_file():
        raise AcceptanceStop(
            f"frozen original source missing before extraction: {entry.original_path}",
            boundary="manifest_source_guard",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
        )
    actual = _sha256_file(original)
    if actual != entry.original_sha256:
        raise AcceptanceStop(
            f"original source bytes drifted for {entry.campaign_id} {entry.session_id}",
            boundary="manifest_source_guard",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
        )
    normalized = repo_root / entry.normalized_path
    if not normalized.is_file() or _sha256_file(normalized) != entry.normalized_sha256:
        raise AcceptanceStop(
            f"normalized lineage bytes drifted for {entry.campaign_id} {entry.session_id}",
            boundary="manifest_source_guard",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
        )


def _default_dsn() -> str:
    import os

    return (
        os.environ.get("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "").strip()
        or f"postgresql://dungeonmind:dungeonmind-dev@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}"
    )


def _probe_world(world_id: str, *, dsn: str, seams: AcceptanceSeams) -> Any:
    if seams.probe_world is not None:
        return seams.probe_world(world_id)
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )

    return DungeonMindWorldGraphInitializationAdapter(database_url=dsn).probe(world_id)


def _assert_pristine(world_id: str, *, dsn: str, seams: AcceptanceSeams) -> None:
    try:
        state = _probe_world(world_id, dsn=dsn, seams=seams)
    except AcceptanceStop:
        raise
    except Exception as exc:
        raise AcceptanceStop(
            "acceptance World probe failed; operator must create a migrated "
            f"pristine database {DATABASE_NAME!r} on {EXPECTED_HOST}:{EXPECTED_PORT}: {exc}",
            boundary="recap_genesis_probe",
        ) from exc
    status = getattr(state, "state", None) or (
        state.get("state") if isinstance(state, Mapping) else None
    )
    if status != "uninitialized":
        raise AcceptanceStop(
            f"World {world_id!r} is not pristine (state={status!r}); "
            "operator must recreate the acceptance database",
            boundary="recap_genesis_probe",
        )


def _run_genesis(
    *,
    repo_root: Path,
    dsn: str,
    seams: AcceptanceSeams,
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
        raise AcceptanceStop(
            "genesis receipt missing published_revision_id",
            boundary="production_genesis",
        )
    if parent is not None:
        raise AcceptanceStop(
            f"genesis D0 must have null parent, got {parent!r}",
            boundary="production_genesis",
        )
    pcs = tuple(getattr(receipt, "pc_object_ids", ()) or getattr(plan, "pc_object_ids", ()) or ())
    if len(pcs) != 6:
        raise AcceptanceStop(
            f"genesis must materialize six PC anchors, got {len(pcs)}",
            boundary="production_genesis",
        )
    return d0


def _extract_session(
    *,
    repo_root: Path,
    entry: ManifestEntry,
    output_dir: Path,
    seams: AcceptanceSeams,
) -> dict[str, Any]:
    if seams.extract_session is not None:
        return seams.extract_session(repo_root=repo_root, entry=entry, output_dir=output_dir)

    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
        load_registered_source_artifact_text,
        load_source_span_index,
    )
    from graph_memory.source_span import source_span_index_to_dict
    from src.graph_memory.extraction.graph_preview_runner import (
        ProductionExtractionRequest,
        run_production_extraction,
    )
    from src.graph_memory.extraction.recap_extraction_profile import (
        RECAP_PROFILE_ID,
        RECAP_PROFILE_VERSION,
    )
    from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource

    artifact = create_recap_source_artifact(
        repo_root,
        campaign_id=entry.campaign_id,
        session_id=entry.session_id,
        recap_path=repo_root / entry.original_path,
        expected_content_sha256=entry.original_sha256,
    )
    if artifact.source_artifact_id != entry.source_artifact_id:
        raise AcceptanceStop(
            "registered source_artifact_id disagrees with frozen manifest",
            boundary="exact_source_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
        )
    registered, text = load_registered_source_artifact_text(
        repo_root, artifact.source_artifact_id
    )
    index = load_source_span_index(repo_root, artifact.source_artifact_id)
    source = NormalizedExtractionSource(
        source_artifact_id=registered.source_artifact_id,
        source_domain=str(registered.source_domain),
        source_text=text,
        source_sha256=registered.content_sha256 or "",
        source_uri=registered.uri,
        campaign_id=registered.campaign_id,
        session_id=registered.session_id,
        document_class=registered.document_class,
        source_span_index=source_span_index_to_dict(index),
    )
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=repo_root,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            model_id=None,
            allow_llm=True,
            output_dir=output_dir / "extraction" / entry.session_id,
        )
    )
    status = result.run.status
    status_value = getattr(status, "value", status)
    if result.failure_kind or status_value != "reviewable":
        raise AcceptanceStop(
            f"production extraction failed: {result.failure_kind or status_value}",
            boundary="production_extraction",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            diagnostics=list(result.diagnostics or []),
            candidate_preserved="yes" if result.candidate_graph is not None else "not-produced",
        )
    if not isinstance(result.candidate_graph, dict):
        raise AcceptanceStop(
            "REVIEWABLE extraction produced no candidate_graph",
            boundary="production_extraction",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
        )
    return {
        "run_id": result.run.run_id,
        "status": str(status),
        "model_id": result.model_id,
        "candidate_graph": result.candidate_graph,
        "source_uri": source.source_uri,
        "source_revision_id": f"sha256:{entry.original_sha256}",
        "source_artifact_id": artifact.source_artifact_id,
    }


def _admit_and_confirm(
    *,
    repo_root: Path,
    dsn: str,
    entry: ManifestEntry,
    candidate_graph: dict[str, Any],
    source_uri: str,
    source_revision_id: str,
    source_artifact_id: str,
    candidate_path: Path,
    prior_head: str,
    seams: AcceptanceSeams,
) -> dict[str, Any]:
    from apps.live_control_server.services.candidate_graph_admission import (
        canonical_candidate_digest,
        confirm_candidate_graph_admission,
        prepare_candidate_graph_admission,
    )
    from apps.live_control_server.models.candidate_graph_admission import (
        CandidateAdmissionIntegrityError,
        CandidateAdmissionNotConfirmableError,
    )

    frozen = json.loads(json.dumps(candidate_graph))
    digest = canonical_candidate_digest(candidate_graph)
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(
        json.dumps(candidate_graph, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if seams.load_mutation_context is not None:
        context = seams.load_mutation_context(WORLD_ID, dsn=dsn, prior_head=prior_head)
    else:
        from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
            load_production_mutation_context,
        )

        context = load_production_mutation_context(WORLD_ID, database_url=dsn)
    context_rev = str(getattr(context, "revision_id", "") or "")
    if context_rev != prior_head:
        raise AcceptanceStop(
            f"mutation context parent {context_rev!r} != prior head {prior_head!r}",
            boundary="governed_write_seam",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        )

    prepare_kwargs = dict(
        candidate_graph=candidate_graph,
        source_uri=source_uri,
        source_revision_id=source_revision_id,
        prepared_by=OPERATOR,
        world_id=WORLD_ID,
        source_artifact_id=source_artifact_id,
        campaign_scope=entry.campaign_id,
        candidate_graph_path=str(candidate_path),
        repo_root=repo_root,
        mutation_context=context,
    )
    try:
        if seams.prepare_admission is not None:
            prepared = seams.prepare_admission(**prepare_kwargs)
        else:
            prepared = prepare_candidate_graph_admission(**prepare_kwargs)
    except CandidateAdmissionIntegrityError as exc:
        raise AcceptanceStop(
            f"candidate integrity failure at admission: {exc}",
            boundary="candidate_document_integrity",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            diagnostics=[str(item) for item in getattr(exc, "diagnostics", ())],
            candidate_preserved="yes",
        ) from exc

    if candidate_graph != frozen:
        raise AcceptanceStop(
            "runner or admission mutated candidate semantics",
            boundary="exact_candidate_forwarding",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="no",
        )

    package = prepared.review_package
    if seams.prepare_admission is None:
        from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
            bind_identity_ledger_to_package,
        )

        package = bind_identity_ledger_to_package(package, context)
        from dataclasses import replace

        prepared = replace(
            prepared,
            review_package=package,
            proposal_digest=str(package["proposal_digest"]),
        )

    binding = dict((package.get("effect") or {}).get("candidate_admission") or {})
    if binding.get("candidate_digest") != digest:
        raise AcceptanceStop(
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
        raise AcceptanceStop(
            "admission is nonconfirmable; stopping before governed confirm",
            boundary="candidate_graph_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            diagnostics=[f"{d.get('item_id')}:{d.get('reason')}" for d in dispositions],
            candidate_preserved="yes",
        )

    accepted = list((package.get("effect") or {}).get("accepted_proposals") or [])
    assertion_ids = [
        str(item.get("assertion_id") or "").strip()
        for item in accepted
        if isinstance(item, Mapping) and str(item.get("assertion_id") or "").strip()
    ]
    if not assertion_ids:
        raise AcceptanceStop(
            "confirmable package has no accepted assertion_ids",
            boundary="candidate_graph_admission",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        )

    # Stale-head check immediately before confirm.
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
        raise AcceptanceStop(
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
            # Deterministic tests inject both prepare and confirm seams; do not
            # require a fully sealed production proposal package for orchestration.
            payload = _governed_confirm()
        else:
            payload = confirm_candidate_graph_admission(
                review_package=package,
                candidate_graph=candidate_graph,
                governed_confirm=_governed_confirm,
            )
    except CandidateAdmissionNotConfirmableError as exc:
        raise AcceptanceStop(
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
            raise AcceptanceStop(
                f"stale parent during confirm: {exc}",
                boundary="governed_write_seam",
                campaign_id=entry.campaign_id,
                session_id=entry.session_id,
                last_good_head=prior_head,
                candidate_preserved="yes",
            ) from exc
        raise AcceptanceStop(
            f"governed write failed: {exc}",
            boundary="dungeonmind_write",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
            diagnostics=[str(code)],
        ) from exc

    if candidate_graph != frozen:
        raise AcceptanceStop(
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
        raise AcceptanceStop(
            "confirm returned no child revision",
            boundary="receipt_verification",
            campaign_id=entry.campaign_id,
            session_id=entry.session_id,
            last_good_head=prior_head,
            candidate_preserved="yes",
        )
    if str(parent or "") != prior_head:
        raise AcceptanceStop(
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
        raise AcceptanceStop(
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
            raise AcceptanceStop(
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
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _report_payload(state: AcceptanceState) -> dict[str, Any]:
    manifest = state.manifest.as_dict() if state.manifest else None
    return {
        "schema": "dmb_current_corpus_admission_acceptance_report_v1",
        "structural_acceptance": state.structural_acceptance,
        "mode": state.mode,
        "run_id": state.run_id,
        "git_head": state.git_head,
        "model_policy_digest": state.model_policy_digest,
        "resolved_model_id": state.resolved_model_id,
        "world_id": state.world_id,
        "database_name": state.database_name,
        "dsn_host_port": f"{EXPECTED_HOST}:{EXPECTED_PORT}",
        "manifest": manifest,
        "genesis_d0": state.genesis_d0,
        "last_good_head": state.last_good_head,
        "terminal_head": state.terminal_head,
        "model_calls": state.model_calls,
        "graph_writes": state.graph_writes,
        "session_ledger": state.session_ledger,
        "stop": state.stop,
        "claims_that_remain_false": [
            "SEMANTIC MODEL SELECTION = HOLD",
            "no model winner exists",
            "no semantic recall/precision/truthfulness score exists",
            "no unattended production batch ingestion exists",
        ],
        "generated_at": _now_iso(),
    }


def _new_run_id(prefix: str) -> str:
    import uuid

    return f"{prefix}-{_now_iso().replace(':', '')}-{uuid.uuid4().hex[:8]}"


def run_preflight(
    *,
    repo_root: Path | None = None,
    dsn: str | None = None,
    seams: AcceptanceSeams | None = None,
    require_clean_worktree: bool = False,
) -> AcceptanceState:
    """Zero model calls; zero graph mutation."""
    from src.bootstrap_env import load_dungeonmindbuddy_dotenv

    load_dungeonmindbuddy_dotenv()
    root = (repo_root or REPO_ROOT).resolve()
    seams = seams or AcceptanceSeams()
    run_id = _new_run_id("preflight")
    out = root / OUTPUT_REL / run_id
    out.mkdir(parents=True, exist_ok=True)

    head = git_head(root)
    if require_clean_worktree and not git_worktree_clean(root):
        raise AcceptanceStop(
            "worktree is dirty; expected clean checkout for acceptance",
            boundary="acceptance_preflight",
        )

    dsn_value = dsn or _default_dsn()
    assert_runtime_dsn(dsn_value)
    policy_digest = model_policy_digest(root)
    model_id = resolved_production_model_id()
    manifest = freeze_current_corpus_manifest(root)
    _assert_pristine(WORLD_ID, dsn=dsn_value, seams=seams)

    state = AcceptanceState(
        run_id=run_id,
        mode="preflight",
        git_head=head,
        model_policy_digest=policy_digest,
        resolved_model_id=model_id,
        dsn=dsn_value,
        manifest=manifest,
        model_calls=0,
        graph_writes=0,
        structural_acceptance="HOLD",
        output_dir=out,
    )
    _write_json(out / "manifest.json", manifest.as_dict())
    _write_json(out / "preflight_report.json", _report_payload(state))
    return state


def run_execute(
    *,
    repo_root: Path | None = None,
    dsn: str | None = None,
    seams: AcceptanceSeams | None = None,
    require_clean_worktree: bool = False,
) -> AcceptanceState:
    """Full fresh acceptance from pristine authority; stop on first failure."""
    from src.bootstrap_env import load_dungeonmindbuddy_dotenv

    load_dungeonmindbuddy_dotenv()
    root = (repo_root or REPO_ROOT).resolve()
    seams = seams or AcceptanceSeams()
    run_id = _new_run_id("execute")
    out = root / OUTPUT_REL / run_id
    out.mkdir(parents=True, exist_ok=True)

    head = git_head(root)
    if require_clean_worktree and not git_worktree_clean(root):
        raise AcceptanceStop(
            "worktree is dirty; expected clean checkout for acceptance",
            boundary="acceptance_preflight",
        )
    dsn_value = dsn or _default_dsn()
    assert_runtime_dsn(dsn_value)
    policy_digest = model_policy_digest(root)
    model_id = resolved_production_model_id()
    manifest = freeze_current_corpus_manifest(root)
    _write_json(out / "manifest.json", manifest.as_dict())
    _assert_pristine(WORLD_ID, dsn=dsn_value, seams=seams)

    state = AcceptanceState(
        run_id=run_id,
        mode="execute",
        git_head=head,
        model_policy_digest=policy_digest,
        resolved_model_id=model_id,
        dsn=dsn_value,
        manifest=manifest,
        output_dir=out,
    )

    try:
        d0 = _run_genesis(repo_root=root, dsn=dsn_value, seams=seams)
        state.genesis_d0 = d0
        state.last_good_head = d0
        state.graph_writes += 1
        prior_head = d0

        for entry in manifest.entries:
            verify_entry_source_bytes(root, entry)
            extract = _extract_session(
                repo_root=root,
                entry=entry,
                output_dir=out,
                seams=seams,
            )
            state.model_calls += 1
            candidate = extract["candidate_graph"]
            from apps.live_control_server.services.candidate_graph_admission import (
                canonical_candidate_digest,
            )

            candidate_digest = canonical_candidate_digest(candidate)
            candidate_path = (
                out / "candidates" / f"{entry.campaign_id}-{entry.session_id}.json"
            )
            admit = _admit_and_confirm(
                repo_root=root,
                dsn=dsn_value,
                entry=entry,
                candidate_graph=candidate,
                source_uri=extract["source_uri"],
                source_revision_id=extract["source_revision_id"],
                source_artifact_id=extract["source_artifact_id"],
                candidate_path=candidate_path,
                prior_head=prior_head,
                seams=seams,
            )
            state.graph_writes += 1
            prior_head = admit["child_revision_id"]
            state.last_good_head = prior_head
            state.session_ledger.append(
                {
                    "ordinal": entry.ordinal,
                    "campaign_id": entry.campaign_id,
                    "session_id": entry.session_id,
                    "normalized_path": entry.normalized_path,
                    "normalized_sha256": entry.normalized_sha256,
                    "original_path": entry.original_path,
                    "original_sha256": entry.original_sha256,
                    "source_artifact_id": entry.source_artifact_id,
                    "source_revision_id": extract["source_revision_id"],
                    "extraction_run_id": extract["run_id"],
                    "extraction_status": extract["status"],
                    "resolved_model_id": extract.get("model_id") or model_id,
                    "candidate_locator": str(candidate_path.relative_to(root)),
                    "candidate_digest": candidate_digest,
                    "candidate_counts": {
                        key: len(candidate.get(key) or [])
                        for key in ("nodes", "edges", "beats", "proposed_writes")
                    },
                    "candidate_integrity_outcome": "ok",
                    "admission_confirmable": True,
                    "admission_dispositions": admit["dispositions"],
                    "accepted_proposal_count": admit["accepted_proposal_count"],
                    "sealed_parent_revision": admit["parent_revision_id"],
                    "proposal_id": admit["proposal_id"],
                    "proposal_digest": admit["proposal_digest"],
                    "receipt_child_revision": admit["child_revision_id"],
                    "verified_current_head": admit["child_revision_id"],
                }
            )
            _write_json(out / "session_ledger.json", {"sessions": state.session_ledger})

        state.terminal_head = prior_head
        state.structural_acceptance = "PASS"
    except AcceptanceStop as stop:
        state.structural_acceptance = "HOLD"
        remaining = []
        seen_fail = False
        for entry in manifest.entries:
            key = f"{entry.campaign_id}/{entry.session_id}"
            if (
                stop.campaign_id == entry.campaign_id
                and stop.session_id == entry.session_id
            ):
                seen_fail = True
                remaining.append(key)
                continue
            if seen_fail:
                remaining.append(key)
        state.stop = {
            "message": str(stop),
            "boundary": stop.boundary,
            "campaign_id": stop.campaign_id,
            "session_id": stop.session_id,
            "last_verified_good_head": stop.last_good_head or state.last_good_head,
            "candidate_preserved": stop.candidate_preserved,
            "diagnostics": list(stop.diagnostics),
            "model_calls_spent": state.model_calls,
            "sessions_not_attempted": remaining,
        }
    finally:
        _write_json(out / "acceptance_report.json", _report_payload(state))

    return state


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Current-corpus admission structural acceptance harness"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--preflight",
        action="store_true",
        help="Zero model calls; zero graph/source mutation",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Full fresh acceptance from pristine authority",
    )
    parser.add_argument(
        "--dsn",
        default=None,
        help="Optional override; must still be loopback:54329/dmb_current_corpus_acceptance_v1",
    )
    parser.add_argument(
        "--require-clean-worktree",
        action="store_true",
        help="Refuse dirty checkouts",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.preflight:
            state = run_preflight(
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
                        "resolved_model_id": state.resolved_model_id,
                        "model_policy_digest": state.model_policy_digest,
                        "world_id": state.world_id,
                        "database_name": state.database_name,
                        "model_calls": state.model_calls,
                        "graph_writes": state.graph_writes,
                        "output_dir": str(state.output_dir),
                    },
                    indent=2,
                )
            )
            return 0

        state = run_execute(
            dsn=args.dsn,
            require_clean_worktree=args.require_clean_worktree,
        )
        print(
            json.dumps(
                {
                    "mode": "execute",
                    "structural_acceptance": state.structural_acceptance,
                    "git_head": state.git_head,
                    "manifest_digest": state.manifest.digest if state.manifest else None,
                    "genesis_d0": state.genesis_d0,
                    "terminal_head": state.terminal_head,
                    "last_good_head": state.last_good_head,
                    "model_calls": state.model_calls,
                    "stop": state.stop,
                    "output_dir": str(state.output_dir),
                },
                indent=2,
            )
        )
        return 0 if state.structural_acceptance == "PASS" else 2
    except AcceptanceStop as stop:
        print(
            json.dumps(
                {
                    "structural_acceptance": "HOLD",
                    "boundary": stop.boundary,
                    "message": str(stop),
                    "campaign_id": stop.campaign_id,
                    "session_id": stop.session_id,
                    "diagnostics": list(stop.diagnostics),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
