"""CUTOVER D.2C2: native first-world initialization behind DungeonMind authority."""



from __future__ import annotations



import ast

import hashlib

import json

import threading

from concurrent.futures import ThreadPoolExecutor

from dataclasses import dataclass, replace

from datetime import UTC, datetime, timedelta

from pathlib import Path



import pytest

from fastapi.testclient import TestClient



import apps.live_control_server.config as live_config

import apps.live_control_server.services.extract_promote as promote_svc

import apps.live_control_server.services.promotable_ingest_run as promotable_mod

from apps.live_control_server.main import create_app

from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (

    exported_contribution_evidence_ref_id,

    raw_buddy_evidence_ref_id,

)

from apps.live_control_server.models.extract_promote import FirstWorldGraphConfirmRequest

from apps.live_control_server.ports.world_graph_initialization import (

    WorldGraphInitializationError,

    WorldGraphInitializationRequest,

)

from apps.live_control_server.ports.world_graph_initialization_access import (

    get_world_graph_initialization_authority,

)

from apps.live_control_server.services.first_world_graph import first_world_initialization_id

from apps.live_control_server.services.first_world_graph_publication import (

    _initialization_request,

)

from apps.live_control_server.services.graph_ingest_run_registry import (

    GRAPH_INGEST_RUNS_ENV,

)

from tests._cutover_d3a_blocker_safe_fixtures import (

    TRUNCATE_SQL,

    ensure_migrated as _ensure_migrated,

    require_test_dsn as _test_dsn,

)

from tests._cutover_d3a_blocker_safe_fixtures import (

    FIRST_WORLD_CONFIRM_URL,

    FIRST_WORLD_PREPARE_URL,

    GLASS_ORCHARD_WORLD_ID,

    first_world_confirm_body as _first_world_confirm_body,

    first_world_decisions as _first_world_decisions,

    first_world_prepare_body as _first_world_prepare_body,

    _mutate_extraction_candidate,

    write_glass_orchard_bld08_run as _write_glass_orchard_bld08_run,

)



REPO_ROOT = Path(__file__).resolve().parents[1]

DUNGEONMIND_PIN = "5ca5d688612349034f8ca490d465af166d883e6e"

REJECTED_NODE_ID = "obj_rejected_extra"





def _forbidden_imports(path: Path, names: tuple[str, ...]) -> list[str]:

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    found: list[str] = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                if alias.name in names or any(

                    alias.name.startswith(f"{item}.") for item in names

                ):

                    found.append(alias.name)

        elif isinstance(node, ast.ImportFrom) and node.module:

            if node.module in names or any(

                node.module.startswith(f"{item}.") for item in names

            ):

                found.append(node.module)

    return found





def test_dungeonmind_pin_is_exact_pr47_merge() -> None:

    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    lock = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")

    assert DUNGEONMIND_PIN in pyproject

    assert DUNGEONMIND_PIN in lock

    assert "bf40e933bdedf3cf08bb23a07a135958bdb7cc6b" not in pyproject

    assert "bf40e933bdedf3cf08bb23a07a135958bdb7cc6b" not in lock





def _other_shaped_command(command):

    from dungeonmind.contracts.evidence import SourceDomain



    assertions = [

        item.model_copy(

            update={

                "evidence_refs": [

                    ref.model_copy(update={"source_domain": SourceDomain.OTHER})

                    for ref in item.evidence_refs

                ]

            }

        )

        for item in command.reviewed_contribution.assertions

    ]

    return command.model_copy(

        update={

            "reviewed_contribution": command.reviewed_contribution.model_copy(

                update={"assertions": assertions}

            )

        }

    )





def _worldbuilding_artifact(*, source_domain=None, source_domain_key="worldbuilding"):

    from dungeonmind.contracts.evidence import (

        SourceArtifactV2,

        SourceAuthority,

        SourceDomain,

        SourceStatus,

    )

    from dungeonmind.contracts.vocabulary import Visibility



    now = datetime(2026, 8, 27, tzinfo=UTC)

    return SourceArtifactV2(

        source_artifact_id="src:notes",

        source_domain_key=source_domain_key,

        source_domain=source_domain or SourceDomain.WORLDBUILDING,

        world_id="world:w",

        campaign_id="camp",

        session_id=None,

        uri="object://src",

        current_revision_id="rev:notes",

        authority=SourceAuthority.PRIMARY,

        visibility=Visibility.GM,

        artifact_kind="notes",

        document_class="worldbuilding",

        review_state=None,

        source_visibility_state=None,

        workspace_document_ref=None,

        status=SourceStatus.ACTIVE,

        created_at=now,

        updated_at=now,

    )





def _mapped_other_contribution():

    from dungeonmind.contracts.contribution import (

        AcceptanceState,

        ContributionEpistemicKind,

        ContributionSourceKind,

        ContributionStatus,

        GraphContributionAssertionV2,

        GraphContributionV2,

    )

    from dungeonmind.contracts.evidence import EvidenceRef, EvidenceRole, SourceDomain

    from dungeonmind.contracts.vocabulary import Visibility





    draft = EvidenceRef(

        evidence_ref_id="ev:raw",

        source_artifact_id="src:notes",

        source_revision_id="rev:notes",

        source_domain=SourceDomain.OTHER,

        evidence_role=EvidenceRole.SUPPORT,

        can_open_source=False,

        can_highlight_span=False,

        locator=None,

        uri=None,

    )

    exported_id = exported_contribution_evidence_ref_id("ev:raw", draft)

    ref = draft.model_copy(update={"evidence_ref_id": exported_id})

    assertion = GraphContributionAssertionV2(

        assertion_id="asrt:1",

        assertion_kind="node",

        subject_object_id="obj:1",

        label="X",

        evidence_refs=[ref],

        source_artifact_id="src:notes",

        source_revision_id="rev:notes",

        campaign_scope="camp",

        visibility=Visibility.GM,

        epistemic_kind=ContributionEpistemicKind.ASSERTED,

        acceptance_state=AcceptanceState.ACCEPTED,

    )

    contribution = GraphContributionV2(

        contribution_id="contrib:1",

        world_id="world:w",

        source_kind=ContributionSourceKind.EXTRACTION,

        source_artifact_id="src:notes",

        source_revision_id="rev:notes",

        produced_at=datetime(2026, 8, 27, tzinfo=UTC),

        campaign_scope="camp",

        status=ContributionStatus.ACTIVE,

        assertions=[assertion],

    )

    return contribution, exported_id





def test_align_preserves_historical_evidence_id_and_copies_artifact_domain() -> None:

    from dungeonmind.contracts.evidence import SourceDomain



    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        _align_first_world_command_evidence_domains,

    )



    contribution, exported_id = _mapped_other_contribution()

    aligned = _align_first_world_command_evidence_domains(

        contribution, [_worldbuilding_artifact()]

    )

    ref = aligned.assertions[0].evidence_refs[0]

    assert ref.evidence_ref_id == exported_id

    assert ref.source_domain is SourceDomain.WORLDBUILDING





def test_align_fails_closed_on_missing_source_artifact() -> None:

    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        _align_first_world_command_evidence_domains,

    )



    contribution, _exported_id = _mapped_other_contribution()

    with pytest.raises(WorldGraphInitializationError) as exc:

        _align_first_world_command_evidence_domains(contribution, [])

    assert exc.value.code == "inexpressible"

    assert exc.value.details["reason"] == "missing_source_artifact"





def test_align_fails_closed_on_non_worldbuilding_artifact() -> None:

    from dungeonmind.contracts.evidence import SourceDomain



    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        _align_first_world_command_evidence_domains,

    )



    contribution, _exported_id = _mapped_other_contribution()

    with pytest.raises(WorldGraphInitializationError) as exc:

        _align_first_world_command_evidence_domains(

            contribution,

            [

                _worldbuilding_artifact(

                    source_domain=SourceDomain.RULEBOOK,

                    source_domain_key="rulebook",

                )

            ],

        )

    assert exc.value.code == "inexpressible"

    assert exc.value.details["reason"] == "non_worldbuilding_source_artifact"





def test_align_fails_closed_on_ambiguous_source_artifact() -> None:

    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        _align_first_world_command_evidence_domains,

    )



    contribution, _exported_id = _mapped_other_contribution()

    first = _worldbuilding_artifact()

    second = first.model_copy(update={"uri": "object://other"})

    with pytest.raises(WorldGraphInitializationError) as exc:

        _align_first_world_command_evidence_domains(contribution, [first, second])

    assert exc.value.code == "inexpressible"

    assert exc.value.details["reason"] == "ambiguous_source_artifact"





def test_projection_constructor_consumes_reviewed_world_initializations() -> None:

    source = (

        REPO_ROOT

        / "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py"

    ).read_text(encoding="utf-8")

    assert "reviewed_world_initializations=bundle.reviewed_world_initializations" in source

    assert "WorldGraphProjectionService(" in source





def test_initialization_id_is_deterministic() -> None:

    first = first_world_initialization_id("the-glass-orchard", "plan-a")

    second = first_world_initialization_id("the-glass-orchard", "plan-a")

    other = first_world_initialization_id("the-glass-orchard", "plan-b")

    assert first == second

    assert first.startswith("dmb:first-world:")

    assert first != other

    payload = json.dumps(

        {"world_id": "the-glass-orchard", "plan_id": "plan-a"},

        sort_keys=True,

        separators=(",", ":"),

    )

    assert first == "dmb:first-world:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()





def test_factory_is_dungeonmind_only_and_rejects_alternate_root(

    tmp_path: Path, monkeypatch: pytest.MonkeyPatch

) -> None:

    from apps.live_control_server import config

    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        DungeonMindWorldGraphInitializationAdapter,

    )



    prod = tmp_path / "prod"

    other = tmp_path / "other"

    prod.mkdir()

    other.mkdir()

    monkeypatch.setenv(

        config.WORLD_GRAPH_AUTHORITY_ENV, config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND

    )

    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(prod))

    native = get_world_graph_initialization_authority(world_root=prod)

    assert isinstance(native, DungeonMindWorldGraphInitializationAdapter)

    with pytest.raises(config.WorldGraphAuthorityConfigurationError, match="alternate"):

        get_world_graph_initialization_authority(world_root=other)





def test_product_services_do_not_import_postgres_infrastructure() -> None:

    forbidden = (

        "dungeonmind.infrastructure.postgres",

        "dungeonmind.infrastructure.postgres.reviewed_world_initialization",

    )

    for rel in (

        "apps/live_control_server/services/first_world_graph_publication.py",

        "apps/live_control_server/services/extract_promote.py",

        "apps/live_control_server/services/first_world_graph.py",

        "apps/live_control_server/ports/world_graph_initialization.py",

        "apps/live_control_server/ports/world_graph_initialization_access.py",

    ):

        found = _forbidden_imports(REPO_ROOT / rel, forbidden)

        assert found == [], f"{rel} imports {found}"





def test_mounted_first_world_path_has_no_kernel_initialization_authority() -> None:

    forbidden = (

        "graph_memory.kernel.reviewed_world_initialization",

        "graph_memory.kernel.world_initialization",

        "graph_memory.world_supergraph.storage",

        "graph_memory.world_supergraph.paths",

    )

    for rel in (

        "apps/live_control_server/services/first_world_graph_publication.py",

        "apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py",

        "apps/live_control_server/services/extract_promote.py",

    ):

        found = _forbidden_imports(REPO_ROOT / rel, forbidden)

        assert found == [], f"{rel} still imports {found}"





def test_genesis_semantic_profile_is_builtin_worldbuilding_descriptor() -> None:

    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        _genesis_semantic_profile,

    )

    from dungeonmind.application.semantic_profiles import descriptor_sha256

    from dungeonmind_dnd.application.world_object_vocabulary import (

        load_builtin_v3_descriptor,

    )



    descriptor = load_builtin_v3_descriptor()

    profile = _genesis_semantic_profile()

    assert profile.profile_id == descriptor.profile_id

    assert profile.profile_revision == descriptor.profile_revision

    assert profile.descriptor_sha256 == descriptor_sha256(descriptor)





@dataclass

class _FakeReceipt:

    initialization_id: str = "init-1"

    published_revision_id: str = "rev:d0"

    initialized_at: datetime = datetime(2026, 1, 1, tzinfo=UTC)





class _FakeReviewedInit:

    def __init__(self, result=None, error: BaseException | None = None) -> None:

        self._result = result

        self._error = error



    def get_for_world(self, world_id: str):

        if self._error is not None:

            raise self._error

        return self._result





class _FakeGraph:

    def __init__(self, head=None, error: BaseException | None = None) -> None:

        self._head = head

        self._error = error



    def get_head(self, world_id: str):

        if self._error is not None:

            raise self._error

        return self._head





class _FakeBundle:

    def __init__(

        self,

        *,

        receipt=None,

        receipt_error: BaseException | None = None,

        head=None,

        head_error: BaseException | None = None,

    ) -> None:

        self.reviewed_world_initializations = _FakeReviewedInit(receipt, receipt_error)

        self.world_graph = _FakeGraph(head, head_error)





def _dummy_initialization_request() -> WorldGraphInitializationRequest:

    return WorldGraphInitializationRequest(

        world_id="the-glass-orchard",

        campaign_id="the-glass-orchard",

        initialization_id="dmb:first-world:test",

        source_plan_schema="dmb_first_world_plan_v1",

        source_plan_id="plan",

        source_plan_sha256="0" * 64,

        actor="live_control:graph_review_confirm",

        source_artifact=object(),

        source_revision_token="rev:src",

        source_uri="object://src",

        reviewed_contribution=object(),

    )





def test_probe_maps_verified_receipt_integrity_not_unavailable(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    from dungeonmind.domain.errors import PersistenceIntegrityError



    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        DungeonMindWorldGraphInitializationAdapter,

    )



    adapter = DungeonMindWorldGraphInitializationAdapter(database_url="postgresql://unused")

    bundle = _FakeBundle(

        receipt_error=PersistenceIntegrityError(

            "reviewed-world initialization receipt references a missing revision"

        )

    )

    monkeypatch.setattr(adapter, "_bundle", lambda: bundle)

    with pytest.raises(WorldGraphInitializationError) as exc_info:

        adapter.probe("the-glass-orchard")

    assert type(exc_info.value) is WorldGraphInitializationError

    assert exc_info.value.code == "integrity_failure"





def test_initialize_maps_verified_receipt_integrity_without_leaking(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    from dungeonmind.domain.errors import PersistenceIntegrityError



    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        DungeonMindWorldGraphInitializationAdapter,

    )



    adapter = DungeonMindWorldGraphInitializationAdapter(database_url="postgresql://unused")

    bundle = _FakeBundle(

        receipt_error=PersistenceIntegrityError(

            "reviewed-world initialization receipt references a missing revision"

        )

    )

    monkeypatch.setattr(adapter, "_bundle", lambda: bundle)

    with pytest.raises(WorldGraphInitializationError) as exc_info:

        adapter.initialize(_dummy_initialization_request())

    assert type(exc_info.value) is WorldGraphInitializationError

    assert exc_info.value.code == "integrity_failure"





def test_probe_maps_unavailable_receipt_read_to_authority_unavailable(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    from dungeonmind.domain.errors import PersistenceUnavailableError



    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        DungeonMindWorldGraphInitializationAdapter,

    )



    adapter = DungeonMindWorldGraphInitializationAdapter(database_url="postgresql://unused")

    bundle = _FakeBundle(

        receipt_error=PersistenceUnavailableError("initialization repository unavailable")

    )

    monkeypatch.setattr(adapter, "_bundle", lambda: bundle)

    with pytest.raises(WorldGraphInitializationError) as exc_info:

        adapter.probe("the-glass-orchard")

    assert exc_info.value.code == "authority_unavailable"





def test_probe_and_initialize_treat_receipt_without_head_as_integrity(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        DungeonMindWorldGraphInitializationAdapter,

    )



    adapter = DungeonMindWorldGraphInitializationAdapter(database_url="postgresql://unused")

    bundle = _FakeBundle(receipt=_FakeReceipt(), head=None)

    monkeypatch.setattr(adapter, "_bundle", lambda: bundle)

    with pytest.raises(WorldGraphInitializationError) as probe_exc:

        adapter.probe("the-glass-orchard")

    assert probe_exc.value.code == "integrity_failure"

    assert probe_exc.value.details.get("reason") == "reviewed_init_receipt_without_head"

    with pytest.raises(WorldGraphInitializationError) as init_exc:

        adapter.initialize(_dummy_initialization_request())

    assert init_exc.value.code == "integrity_failure"

    assert init_exc.value.details.get("reason") == "reviewed_init_receipt_without_head"





def _add_rejected_node(payload: dict) -> None:

    nodes = list(payload.get("nodes") or [])

    template = dict(nodes[0])

    template["node_id"] = REJECTED_NODE_ID

    template["label"] = "Rejected extra"

    payload["nodes"] = [*nodes, template]





@pytest.fixture

def native_first_world_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):

    dsn = _test_dsn()

    _ensure_migrated(dsn)

    from dungeonmind.infrastructure.postgres import PostgresDatabase



    database = PostgresDatabase(dsn)

    with database.connect() as conn:

        conn.execute(TRUNCATE_SQL)

        conn.commit()



    from apps.live_control_server import config as wg_config



    repo = tmp_path / "repo"

    world_root = tmp_path / "world"

    repo.mkdir()

    world_root.mkdir()

    monkeypatch.setenv(

        wg_config.WORLD_GRAPH_AUTHORITY_ENV,

        wg_config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND,

    )

    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", dsn)

    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(world_root))

    monkeypatch.setenv(

        "DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT",

        str(tmp_path / "_designated_live_not_used"),

    )

    monkeypatch.delenv("DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT", raising=False)

    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")

    monkeypatch.setattr(live_config, "repo_root", lambda: repo)

    monkeypatch.setattr(promote_svc, "repo_root", lambda: repo)

    monkeypatch.setattr(promotable_mod, "repo_root", lambda: repo)

    client = TestClient(create_app())

    return client, world_root, repo, dsn





def _prepare_native_plan(client, repo: Path, *, with_rejected: bool = False) -> tuple[str, dict]:

    run_id, _source = _write_glass_orchard_bld08_run(repo)

    decisions = _first_world_decisions()

    if with_rejected:

        _mutate_extraction_candidate(repo, run_id, _add_rejected_node)

        decisions = [*decisions, {"assertionId": REJECTED_NODE_ID, "decision": "reject"}]

    prepare = client.post(

        FIRST_WORLD_PREPARE_URL,

        json=_first_world_prepare_body(run_id, decisions),

    )

    assert prepare.status_code == 200, prepare.text

    return run_id, prepare.json()





def _sealed_native_request(repo: Path, plan: dict) -> WorldGraphInitializationRequest:

    from apps.live_control_server.services.extract_promote import (

        _load_typed_worldbuilding_preview_for_run,

    )

    from apps.live_control_server.services.first_world_graph import (

        materialize_first_world_plan,

    )

    from apps.live_control_server.services.promotable_ingest_run import (

        resolve_promotable_ingest_run,

    )

    from graph_memory.worldbuilding_write_plan import WorldbuildingDispositionInput



    resolved = resolve_promotable_ingest_run(plan["runId"], root=repo)

    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(resolved)

    rematerialized = materialize_first_world_plan(

        preview=typed_preview,

        world_id=plan["worldId"],

        run_id=plan["runId"],

        source_artifact_id=plan["sourceArtifactId"],

        source_revision_id=plan["sourceRevisionId"],

        source_uri=resolved.sealed_source_uri,

        extraction_profile=expected_profile,

        campaign_scope=plan["campaignScope"],

        workspace_document_id=plan["workspaceDocumentId"],

        workspace_document_revision=plan["workspaceDocumentRevision"],

        dispositions=[

            WorldbuildingDispositionInput(

                assertion_id=str(item["assertion_id"]),

                decision=str(item["decision"]),

                target_node_id=item.get("target_node_id"),

            )

            for item in plan["reviewedEffect"]["decision_snapshot"]

        ],

    )

    return _initialization_request(

        plan=FirstWorldGraphConfirmRequest.model_validate(

            _first_world_confirm_body(plan)

        ).plan,

        rematerialized=rematerialized,

        resolved=resolved,

    )





def _bundle(dsn: str):

    from dungeonmind.infrastructure.postgres import (

        PostgresDatabase,

        PostgresRepositoryBundle,

    )



    return PostgresRepositoryBundle(PostgresDatabase(dsn))





def _project_native(dsn: str, *, world_id: str, campaign_id: str):

    from dungeonmind.application.world_graph_projection import WorldGraphProjectionService

    from dungeonmind.contracts.projection import Admissibility

    from dungeonmind.contracts.projection_v2 import ScopeModeV2, WorldGraphProjectionRequestV2



    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (

        _build_graph_reader,

    )



    bundle = _bundle(dsn)

    result = WorldGraphProjectionService(

        world_graph=bundle.world_graph,

        sources=bundle.sources,

        graph_reader=_build_graph_reader(),

        reviewed_world_initializations=bundle.reviewed_world_initializations,

    ).project(

        WorldGraphProjectionRequestV2(

            world_id=world_id,

            campaign_id=campaign_id,

            admissibility=Admissibility.GM,

            scope_mode=ScopeModeV2.CAMPAIGN,

        )

    )

    return result, bundle





def _counts(dsn: str, world_id: str) -> dict[str, int]:

    import psycopg



    with psycopg.connect(dsn) as conn:

        def count(sql_text: str, params: tuple = (world_id,)) -> int:

            row = conn.execute(sql_text, params).fetchone()

            return int(row[0])



        return {

            "heads": count(

                "SELECT count(*) FROM dungeonmind.world_graph_heads WHERE world_id = %s"

            ),

            "revisions": count(

                "SELECT count(*) FROM dungeonmind.graph_revisions WHERE world_id = %s"

            ),

            "receipts": count(

                "SELECT count(*) FROM dungeonmind.reviewed_world_initializations "

                "WHERE world_id = %s"

            ),

            "contributions": count(

                "SELECT count(*) FROM dungeonmind.graph_contributions WHERE world_id = %s"

            ),

            "artifacts": count(

                "SELECT count(*) FROM dungeonmind.source_artifacts WHERE world_id = %s"

            ),

            "revisions_src": count(

                "SELECT count(*) FROM dungeonmind.source_revisions r "

                "JOIN dungeonmind.source_artifacts a "

                "ON a.source_artifact_id = r.source_artifact_id "

                "WHERE a.world_id = %s"

            ),

            "adoptions": count(

                "SELECT count(*) FROM dungeonmind.existing_world_adoptions "

                "WHERE world_id = %s"

            ),

        }





def _artifact_ids(dsn: str, world_id: str) -> list[tuple[str]]:

    import psycopg



    with psycopg.connect(dsn) as conn:

        return conn.execute(

            "SELECT source_artifact_id FROM dungeonmind.source_artifacts WHERE world_id = %s",

            (world_id,),

        ).fetchall()





def _revision_ids(dsn: str, world_id: str) -> list[tuple[str]]:

    import psycopg



    with psycopg.connect(dsn) as conn:

        return conn.execute(

            "SELECT r.source_revision_id FROM dungeonmind.source_revisions r "

            "JOIN dungeonmind.source_artifacts a "

            "ON a.source_artifact_id = r.source_artifact_id "

            "WHERE a.world_id = %s",

            (world_id,),

        ).fetchall()





@pytest.mark.integration

def test_native_review_prepare_confirm_with_buddy_graph_absent(

    native_first_world_client,

) -> None:

    client, world_root, repo, dsn = native_first_world_client

    glass_dir = world_root / "graph_memory" / "worlds" / GLASS_ORCHARD_WORLD_ID

    run_id, plan = _prepare_native_plan(client, repo, with_rejected=True)

    assert not glass_dir.exists()

    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["receipts"] == 0



    review = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")

    assert review.status_code == 200, review.text

    body = review.json()

    assert body["worldState"] == "uninitialized"

    assert body["firstWorldPublishEligible"] is True



    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert confirm.status_code == 200, confirm.text

    receipt = confirm.json()

    assert receipt["outcome"] == "initialized"

    assert receipt["baselineRevisionId"] is None

    assert receipt["committedRevisionId"]

    assert not glass_dir.exists()



    after = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")

    assert after.status_code == 200, after.text

    assert after.json()["worldState"] == "initialized"

    assert after.json()["firstWorldPublishEligible"] is False

    assert not glass_dir.exists()





@pytest.mark.integration

def test_native_empty_to_d0_topology_and_source_closure(

    native_first_world_client,

) -> None:

    from dungeonmind.contracts.identity import IdentityOutcome



    client, world_root, repo, dsn = native_first_world_client

    _run_id, plan = _prepare_native_plan(client, repo, with_rejected=True)

    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert confirm.status_code == 200, confirm.text

    published = confirm.json()["committedRevisionId"]

    counts = _counts(dsn, GLASS_ORCHARD_WORLD_ID)

    assert counts["heads"] == 1

    assert counts["revisions"] == 1

    assert counts["receipts"] == 1

    assert counts["contributions"] == 1

    assert counts["artifacts"] == 1

    assert counts["revisions_src"] == 1

    assert counts["adoptions"] == 0

    assert not (world_root / "graph_memory" / "worlds" / GLASS_ORCHARD_WORLD_ID).exists()



    bundle = _bundle(dsn)

    head = bundle.world_graph.get_head(GLASS_ORCHARD_WORLD_ID)

    assert head is not None

    assert head.head_revision_id == published

    stored = bundle.world_graph.get_revision(GLASS_ORCHARD_WORLD_ID, published)

    assert stored is not None

    assert stored.revision.parent_revision_id is None

    payload = stored.graph_payload

    object_ids = {item["object_id"] for item in payload.get("objects") or []}

    assert "obj_session22_vial" in object_ids

    assert "mystery_puddles" in object_ids

    assert REJECTED_NODE_ID not in object_ids



    init = bundle.reviewed_world_initializations.get_for_world(GLASS_ORCHARD_WORLD_ID)

    assert init is not None

    contribution = bundle.contributions.get(

        GLASS_ORCHARD_WORLD_ID, init.reviewed_contribution_id

    )

    assert contribution is not None

    vial = next(

        item

        for item in contribution.assertions

        if item.assertion_kind == "node"

        and item.subject_object_id == "obj_session22_vial"

        and item.acceptance_state.value == "accepted"

    )

    edge = next(item for item in contribution.assertions if item.assertion_kind == "edge")

    rejected = next(

        item

        for item in contribution.assertions

        if item.subject_object_id == REJECTED_NODE_ID

    )

    assert vial.identity_resolution_outcome is IdentityOutcome.CREATED_NEW

    assert edge.identity_resolution_outcome is None

    assert rejected.acceptance_state.value == "rejected"

    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        _genesis_semantic_profile,

    )



    profile = _genesis_semantic_profile()

    assert profile.profile_id == "dungeonmind.dnd5e"

    artifact_ids = {row[0] for row in _artifact_ids(dsn, GLASS_ORCHARD_WORLD_ID)}

    revision_ids = {row[0] for row in _revision_ids(dsn, GLASS_ORCHARD_WORLD_ID)}

    assert artifact_ids

    assert revision_ids

    for assertion in contribution.assertions:

        assert assertion.source_artifact_id in artifact_ids

        assert assertion.source_revision_id in revision_ids

        for ref in assertion.evidence_refs:

            assert ref.source_artifact_id in artifact_ids

            assert ref.source_revision_id in revision_ids

            assert ref.source_domain.value == "worldbuilding"



    from dungeonmind.contracts.evidence import SourceDomain





    stored_artifact = bundle.sources.get_artifact(next(iter(artifact_ids)))

    assert stored_artifact is not None

    assert stored_artifact.source_domain is SourceDomain.WORLDBUILDING

    assert stored_artifact.source_domain_key == "worldbuilding"

    for record in payload.get("evidence_refs") or []:

        assert record["source_domain"] == "worldbuilding"

        assert record["source_domain_key"] == "worldbuilding"

    for ref in contribution.assertions[0].evidence_refs:

        raw_id = raw_buddy_evidence_ref_id(ref.evidence_ref_id)

        historical = ref.model_copy(update={"source_domain": SourceDomain.OTHER})

        assert ref.evidence_ref_id == exported_contribution_evidence_ref_id(

            raw_id, historical

        )

        assert ref.source_domain is SourceDomain.WORLDBUILDING



    projected, _ = _project_native(

        dsn,

        world_id=GLASS_ORCHARD_WORLD_ID,

        campaign_id=plan.get("campaignScope") or plan["worldId"],

    )

    admitted = set(projected.graph.objects)

    assert "obj_session22_vial" in admitted

    assert "mystery_puddles" in admitted





def _corrected_and_historical_commands(repo: Path, plan: dict, *, initialized_at: datetime):

    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        _build_command,

    )



    request = _sealed_native_request(repo, plan)

    corrected = _build_command(request, requested_initialized_at=initialized_at)

    return request, corrected, _other_shaped_command(corrected)





def _command_evidence_refs(command):

    return [

        ref

        for assertion in command.reviewed_contribution.assertions

        for ref in assertion.evidence_refs

    ]





def _assert_corrected_preserves_historical_identity(corrected, historical) -> None:

    from dungeonmind.application.reviewed_world_initialization import (

        reviewed_world_initialization_command_sha256,

        reviewed_world_initialization_replay_identity,

    )

    from dungeonmind.contracts.evidence import SourceDomain



    corrected_refs = _command_evidence_refs(corrected)

    historical_refs = _command_evidence_refs(historical)

    assert corrected_refs

    assert [ref.evidence_ref_id for ref in corrected_refs] == [

        ref.evidence_ref_id for ref in historical_refs

    ]

    assert all(ref.source_domain is SourceDomain.WORLDBUILDING for ref in corrected_refs)

    assert all(ref.source_domain is SourceDomain.OTHER for ref in historical_refs)

    assert all(

        artifact.source_domain is SourceDomain.WORLDBUILDING

        and artifact.source_domain_key == "worldbuilding"

        for artifact in corrected.source_artifacts

    )

    current = reviewed_world_initialization_command_sha256(corrected)

    historical_hash = reviewed_world_initialization_command_sha256(historical)

    assert current != historical_hash

    identity = reviewed_world_initialization_replay_identity(corrected)

    assert identity.current_command_sha256 == current

    assert identity.historical_other_normalized_sha256 == historical_hash





@pytest.mark.integration

def test_corrected_command_preserves_historical_evidence_identity(

    native_first_world_client,

) -> None:

    client, _world, repo, _dsn = native_first_world_client

    _run_id, plan = _prepare_native_plan(client, repo, with_rejected=True)

    _request, corrected, historical = _corrected_and_historical_commands(

        repo,

        plan,

        initialized_at=datetime(2026, 8, 27, 15, 0, tzinfo=UTC),

    )

    _assert_corrected_preserves_historical_identity(corrected, historical)





@pytest.mark.integration

def test_historical_other_receipt_replays_as_already_initialized(

    native_first_world_client,

) -> None:

    from dungeonmind.application.reviewed_world_initialization import (

        initialize_reviewed_world,

        reviewed_world_initialization_command_sha256,

        reviewed_world_initialization_replay_identity,

    )

    from dungeonmind.contracts.evidence import SourceDomain



    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        DungeonMindWorldGraphInitializationAdapter,

    )

    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (

        _build_graph_reader,

    )



    client, _world, repo, dsn = native_first_world_client

    _run_id, plan = _prepare_native_plan(client, repo, with_rejected=True)

    frozen = datetime(2026, 8, 27, 15, 0, tzinfo=UTC)

    request, corrected, historical = _corrected_and_historical_commands(

        repo, plan, initialized_at=frozen

    )

    _assert_corrected_preserves_historical_identity(corrected, historical)



    bundle = _bundle(dsn)

    seeded = initialize_reviewed_world(

        historical,

        initialization_repository=bundle.reviewed_world_initializations,

        graph_reader=_build_graph_reader(),

    )

    stored = bundle.world_graph.get_revision(

        GLASS_ORCHARD_WORLD_ID, seeded.published_revision_id

    )

    assert stored is not None

    assert stored.revision.parent_revision_id is None

    historical_payload = stored.graph_payload

    object_ids = {item["object_id"] for item in historical_payload.get("objects") or []}

    assert "obj_session22_vial" in object_ids

    assert "mystery_puddles" in object_ids

    assert REJECTED_NODE_ID not in object_ids

    for record in historical_payload.get("evidence_refs") or []:

        assert record["source_domain"] == "other"

        assert record["source_domain_key"] == "other"

    historical_hash = reviewed_world_initialization_command_sha256(historical)

    assert seeded.command_sha256 == historical_hash

    counts = _counts(dsn, GLASS_ORCHARD_WORLD_ID)

    assert counts["revisions"] == 1

    assert counts["receipts"] == 1

    assert counts["adoptions"] == 0



    replayed = DungeonMindWorldGraphInitializationAdapter(database_url=dsn).initialize(

        request

    )

    assert replayed.outcome == "already_initialized"

    assert replayed.published_revision_id == seeded.published_revision_id

    assert replayed.command_sha256 == historical_hash

    after = bundle.reviewed_world_initializations.get_for_world(GLASS_ORCHARD_WORLD_ID)

    assert after is not None

    assert after.command_sha256 == historical_hash

    identity = reviewed_world_initialization_replay_identity(corrected)

    assert identity.historical_other_normalized_sha256 == after.command_sha256

    unchanged = bundle.world_graph.get_revision(

        GLASS_ORCHARD_WORLD_ID, seeded.published_revision_id

    )

    assert unchanged is not None

    assert unchanged.graph_payload == historical_payload

    after_counts = _counts(dsn, GLASS_ORCHARD_WORLD_ID)

    assert after_counts["revisions"] == 1

    assert after_counts["receipts"] == 1

    assert after_counts["adoptions"] == 0



    projected, _ = _project_native(

        dsn,

        world_id=GLASS_ORCHARD_WORLD_ID,

        campaign_id=plan.get("campaignScope") or plan["worldId"],

    )

    admitted = set(projected.graph.objects)

    assert "obj_session22_vial" in admitted

    assert "mystery_puddles" in admitted

    for record in unchanged.graph_payload.get("evidence_refs") or []:

        assert record["source_domain"] == SourceDomain.OTHER.value

        assert record["source_domain_key"] == "other"





@pytest.mark.integration

def test_native_exact_retry_reuses_receipt_timestamp(

    native_first_world_client,

) -> None:

    client, _world, repo, dsn = native_first_world_client

    _run_id, plan = _prepare_native_plan(client, repo)

    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert first.status_code == 200, first.text

    bundle = _bundle(dsn)

    original = bundle.reviewed_world_initializations.get_for_world(GLASS_ORCHARD_WORLD_ID)

    assert original is not None

    retry = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert retry.status_code == 200, retry.text

    assert retry.json()["outcome"] == "already_initialized"

    assert retry.json()["committedRevisionId"] == first.json()["committedRevisionId"]

    assert retry.json()["baselineRevisionId"] is None

    replayed = bundle.reviewed_world_initializations.get_for_world(GLASS_ORCHARD_WORLD_ID)

    assert replayed is not None

    assert replayed.command_sha256 == original.command_sha256

    assert replayed.initialized_at == original.initialized_at

    assert replayed.published_revision_id == original.published_revision_id

    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1

    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["receipts"] == 1





@pytest.mark.integration

def test_native_lost_response_restart_replays_same_d0(

    native_first_world_client, monkeypatch: pytest.MonkeyPatch

) -> None:

    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        DungeonMindWorldGraphInitializationAdapter,

    )



    client, _world, repo, dsn = native_first_world_client

    _run_id, plan = _prepare_native_plan(client, repo)

    real = DungeonMindWorldGraphInitializationAdapter.initialize

    lost = {"done": False}



    def _lose(self, request):

        receipt = real(self, request)

        if not lost["done"]:

            lost["done"] = True

            raise WorldGraphInitializationError(

                "simulated lost response after provider commit",

                code="initialization_failed",

            )

        return receipt



    monkeypatch.setattr(DungeonMindWorldGraphInitializationAdapter, "initialize", _lose)

    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert first.status_code == 500, first.text

    retry = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert retry.status_code == 200, retry.text

    assert retry.json()["outcome"] == "already_initialized"

    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1

    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["receipts"] == 1





@pytest.mark.integration

def test_native_synchronized_identical_confirms_recover_via_timestamp_conflict(

    native_first_world_client, monkeypatch: pytest.MonkeyPatch

) -> None:

    from dungeonmind.application import reviewed_world_initialization as rwi

    from dungeonmind.domain.errors import IdempotencyConflictError



    from apps.live_control_server.integrations.dungeonmind import (

        world_graph_initialization_adapter as init_mod,

    )

    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        DungeonMindWorldGraphInitializationAdapter,

    )



    client, _world, repo, dsn = native_first_world_client

    _run_id, plan = _prepare_native_plan(client, repo)

    request = _sealed_native_request(repo, plan)

    first_stamp = datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC)

    second_stamp = first_stamp + timedelta(seconds=7)

    barrier = threading.Barrier(2, timeout=20)

    receipt_reads: list[str | None] = []

    provider_calls: list[dict[str, object]] = []



    real_verified = init_mod._get_verified_reviewed_init_receipt



    def tracking_verified(repository, world_id):

        receipt = real_verified(repository, world_id)

        receipt_reads.append(None if receipt is None else str(receipt.initialization_id))

        return receipt



    monkeypatch.setattr(init_mod, "_get_verified_reviewed_init_receipt", tracking_verified)



    real_provider = rwi.initialize_reviewed_world



    def tracking_provider(command, **kwargs):

        record: dict[str, object] = {

            "requested_initialized_at": command.requested_initialized_at,

            "outcome": "ok",

        }

        try:

            result = real_provider(command, **kwargs)

        except IdempotencyConflictError:

            record["outcome"] = "conflict"

            provider_calls.append(record)

            raise

        provider_calls.append(record)

        return result



    monkeypatch.setattr(rwi, "initialize_reviewed_world", tracking_provider)



    adapters = [

        DungeonMindWorldGraphInitializationAdapter(

            database_url=dsn,

            now=lambda stamp=first_stamp: stamp,

            after_uninitialized_receipt=barrier.wait,

        ),

        DungeonMindWorldGraphInitializationAdapter(

            database_url=dsn,

            now=lambda stamp=second_stamp: stamp,

            after_uninitialized_receipt=barrier.wait,

        ),

    ]



    with ThreadPoolExecutor(max_workers=2) as pool:

        results = list(pool.map(lambda adapter: adapter.initialize(request), adapters))



    outcomes = sorted(item.outcome for item in results)

    assert outcomes == ["already_initialized", "initialized"]

    published = {item.published_revision_id for item in results}

    assert len(published) == 1

    assert {item.command_sha256 for item in results} == {

        results[0].command_sha256

    }

    first_attempt_stamps = {

        call["requested_initialized_at"]

        for call in provider_calls

        if call["requested_initialized_at"] in {first_stamp, second_stamp}

    }

    assert first_attempt_stamps == {first_stamp, second_stamp}

    conflicts = [call for call in provider_calls if call["outcome"] == "conflict"]

    successes = [call for call in provider_calls if call["outcome"] == "ok"]

    assert len(conflicts) == 1

    assert len(provider_calls) == 3

    assert len(successes) == 2

    winner_stamp = next(

        call["requested_initialized_at"]

        for call in provider_calls

        if call["outcome"] == "ok"

        and call["requested_initialized_at"] in {first_stamp, second_stamp}

    )

    replay_stamps = [

        call["requested_initialized_at"]

        for call in successes

        if call["requested_initialized_at"] == winner_stamp

    ]

    assert len(replay_stamps) == 2

    assert receipt_reads.count(None) == 2

    assert sum(1 for item in receipt_reads if item is not None) == 1

    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1

    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["receipts"] == 1





@pytest.mark.integration

def test_native_changed_command_conflicts(native_first_world_client) -> None:

    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        DungeonMindWorldGraphInitializationAdapter,

    )



    client, _world, repo, dsn = native_first_world_client

    _run_id, plan = _prepare_native_plan(client, repo)

    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert first.status_code == 200, first.text

    request = _sealed_native_request(repo, plan)

    changed = replace(request, actor="attacker:not-the-confirming-principal")

    adapter = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)

    with pytest.raises(WorldGraphInitializationError) as exc_info:

        adapter.initialize(changed)

    assert exc_info.value.code == "idempotency_conflict"

    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1





@pytest.mark.integration

def test_native_non_pristine_without_receipt_fails_closed(

    native_first_world_client,

) -> None:

    import psycopg



    client, _world, repo, dsn = native_first_world_client

    _run_id, plan = _prepare_native_plan(client, repo)

    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert first.status_code == 200, first.text

    with psycopg.connect(dsn) as conn:

        conn.execute(

            "DELETE FROM dungeonmind.reviewed_world_initializations WHERE world_id = %s",

            (GLASS_ORCHARD_WORLD_ID,),

        )

        conn.commit()

    second = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert second.status_code == 409, second.text

    assert second.json()["code"] in {

        "world_already_initialized",

        "first_world_initialization_failed",

        "first_world_idempotency_conflict",

    }

    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1





@pytest.mark.integration

def test_native_workspace_drift_fails_before_publication(

    native_first_world_client,

) -> None:

    from apps.live_control_server.services.source_artifact_registry import (

        get_source_artifact,

    )

    from apps.live_control_server.services.workspace_document_registry import (

        WorkspaceDocumentRegistryDocument,

        get_workspace_document,

        workspace_documents_path,

    )

    from src.live_play.live_store import load_json, write_json



    client, _world, repo, dsn = native_first_world_client

    _run_id, plan = _prepare_native_plan(client, repo)

    artifact = get_source_artifact(repo, plan["sourceArtifactId"])

    workspace_path = workspace_documents_path(repo)

    workspace_doc = WorkspaceDocumentRegistryDocument.model_validate(load_json(workspace_path))

    rewritten = []

    for row in workspace_doc.records:

        if row.document_id == artifact.workspace_document_id:

            rewritten.append(row.model_copy(update={"revision": int(row.revision) + 1}))

        else:

            rewritten.append(row)

    write_json(

        workspace_path,

        WorkspaceDocumentRegistryDocument(

            schema_version=workspace_doc.schema_version,

            records=rewritten,

        ).model_dump(mode="json"),

    )

    assert get_workspace_document(repo, artifact.workspace_document_id).revision != int(

        plan["workspaceDocumentRevision"]

    )

    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert confirm.status_code == 422, confirm.text

    assert confirm.json()["code"] == "workspace_lineage_mismatch"

    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["receipts"] == 0





@pytest.mark.integration

def test_native_receipt_without_head_is_integrity_not_unavailable(

    native_first_world_client,

) -> None:

    import psycopg



    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        DungeonMindWorldGraphInitializationAdapter,

    )



    client, _world, repo, dsn = native_first_world_client

    run_id, plan = _prepare_native_plan(client, repo)

    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert first.status_code == 200, first.text

    with psycopg.connect(dsn) as conn:

        conn.execute(

            "DELETE FROM dungeonmind.world_graph_heads WHERE world_id = %s",

            (GLASS_ORCHARD_WORLD_ID,),

        )

        conn.commit()

    adapter = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)

    with pytest.raises(WorldGraphInitializationError) as probe_exc:

        adapter.probe(GLASS_ORCHARD_WORLD_ID)

    assert type(probe_exc.value) is WorldGraphInitializationError

    assert probe_exc.value.code == "integrity_failure"

    assert probe_exc.value.details.get("reason") == "reviewed_init_receipt_without_head"

    with pytest.raises(WorldGraphInitializationError) as init_exc:

        adapter.initialize(_sealed_native_request(repo, plan))

    assert init_exc.value.code == "integrity_failure"

    review = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")

    assert review.status_code == 200, review.text

    assert review.json()["worldState"] != "initialized"

    assert review.json()["firstWorldPublishEligible"] is False

    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert confirm.status_code == 409, confirm.text

    assert confirm.status_code != 503

    assert confirm.json()["code"] == "first_world_initialization_failed"





@pytest.mark.integration

def test_native_corrupt_d0_receipt_is_integrity_not_unavailable(

    native_first_world_client,

) -> None:

    import psycopg



    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (

        DungeonMindWorldGraphInitializationAdapter,

    )



    client, _world, repo, dsn = native_first_world_client

    _run_id, plan = _prepare_native_plan(client, repo)

    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert first.status_code == 200, first.text

    with psycopg.connect(dsn) as conn:

        conn.execute(

            "UPDATE dungeonmind.graph_revisions "

            "SET parent_revision_id = revision_id "

            "WHERE world_id = %s",

            (GLASS_ORCHARD_WORLD_ID,),

        )

        conn.commit()

    adapter = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)

    with pytest.raises(WorldGraphInitializationError) as probe_exc:

        adapter.probe(GLASS_ORCHARD_WORLD_ID)

    assert type(probe_exc.value) is WorldGraphInitializationError

    assert probe_exc.value.code == "integrity_failure"

    with pytest.raises(WorldGraphInitializationError) as init_exc:

        adapter.initialize(_sealed_native_request(repo, plan))

    assert type(init_exc.value) is WorldGraphInitializationError

    assert init_exc.value.code == "integrity_failure"

    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))

    assert confirm.status_code == 409, confirm.text

    assert confirm.status_code != 503

    assert confirm.json()["code"] == "first_world_initialization_failed"
