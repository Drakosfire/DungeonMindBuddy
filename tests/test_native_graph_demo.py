from __future__ import annotations

import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any

from apps.live_control_server.native_graph_demo import DemoError, NativeGraphDemoService
from dungeonmind.infrastructure.memory.vnext_sources import (
    InMemoryNativeSourceEvidenceRepository,
)


class NativeGraphDemoServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.temp.name)
        self.repository = InMemoryNativeSourceEvidenceRepository()
        self.service = NativeGraphDemoService(
            self.repository, self.state_dir, storage_label="test-memory"
        )

    def tearDown(self) -> None:
        self.service._store.close()
        self.temp.cleanup()

    def _operation_id(self) -> str:
        return str(uuid.uuid4())

    def _create_request(
        self, graph: dict[str, Any], *, name: str = "Ivo", kind: str = "person"
    ) -> dict[str, str]:
        return {
            "operation_id": self._operation_id(),
            "expected_revision_id": graph["revision_id"],
            "kind": "create_object",
            "name": name,
            "object_kind": kind,
        }

    def test_seed_is_admitted_and_published_by_native_authorities(self) -> None:
        graph = self.service.graph()

        self.assertEqual(graph["storage"], "test-memory")
        self.assertEqual(
            {(node["name"], node["kind"]) for node in graph["nodes"]},
            {
                ("Mara", "person"),
                ("Tomas", "person"),
                ("Lantern Inn", "location"),
            },
        )
        self.assertEqual(len(graph["edges"]), 4)
        self.assertEqual(
            {
                (edge["predicate"], edge["source_id"], edge["target_id"])
                for edge in graph["edges"]
            },
            {
                ("knows", self._id(graph, "Mara"), self._id(graph, "Tomas")),
                ("knows", self._id(graph, "Tomas"), self._id(graph, "Mara")),
                ("visits", self._id(graph, "Mara"), self._id(graph, "Lantern Inn")),
                ("visits", self._id(graph, "Tomas"), self._id(graph, "Lantern Inn")),
            },
        )
        self.assertEqual(graph["capabilities"]["object_kinds"], ["person", "location"])
        self.assertFalse(graph["capabilities"]["rename"])
        self.assertFalse(graph["capabilities"]["delete"])
        self.assertEqual(len(graph["limitations"]), 1)

        source = self.repository.get_native_source_admission_receipt(
            graph["world_id"], "native-graph-demo:seed-source:v1"
        )
        publication = self.repository.get_prospective_publication(
            graph["world_id"], "prepared:native-graph-demo-seed-v1"
        )
        self.assertIsNotNone(source)
        self.assertIsNotNone(publication)
        self.assertEqual(
            source.published_revision_id,
            publication.publication_receipt.expected_parent_revision_id,
        )

        head = self.repository.get_head(graph["world_id"])
        stored = self.repository.get_revision(graph["world_id"], head.head_revision_id)
        self.assertEqual(stored.revision.revision_id, graph["revision_id"])
        self.assertEqual(stored.graph_payload_sha256, graph["graph_sha256"])
        self.assertTrue(all(node["id"].startswith("ent:") for node in graph["nodes"]))
        self.assertTrue(all(edge["id"].startswith("asrt:") for edge in graph["edges"]))

    def test_create_prepare_confirm_and_replay_use_exact_native_readback(self) -> None:
        before = self.service.graph()
        request = self._create_request(before)

        prepared = self.service.prepare(request)
        self.assertEqual(prepared["status"], "prepared")
        self.assertNotEqual(prepared["parent_revision_id"], before["revision_id"])
        operation_source = self.repository.get_native_source_admission_receipt(
            before["world_id"],
            "native-graph-demo:operation-source:"
            + request["operation_id"].replace("-", ""),
        )
        self.assertIsNotNone(operation_source)
        exact_source = self.repository.open_native_source_view(
            before["world_id"]
        ).get_native_text_source(
            source_artifact_id=operation_source.source_artifact_id,
            source_revision_id=operation_source.source_revision_id,
            span_id=operation_source.bindings[0].span_id,
        )
        self.assertEqual(
            exact_source.body_bytes, b"Authored demo entry: Ivo is a person.\n"
        )

        committed = self.service.confirm(request["operation_id"])
        self.assertEqual(committed["status"], "committed")
        after = committed["graph"]
        self.assertEqual(len(after["nodes"]), 4)
        self.assertEqual(len(after["edges"]), len(before["edges"]))
        created = next(node for node in after["nodes"] if node["name"] == "Ivo")
        self.assertEqual(created["kind"], "person")
        receipt = self.repository.get_prospective_publication(
            before["world_id"], "prepared:" + request["operation_id"].replace("-", "")
        )
        self.assertIsNotNone(receipt)
        self.assertEqual(
            receipt.publication_receipt.published_revision_id, after["revision_id"]
        )

        replay = self.service.confirm(request["operation_id"])
        self.assertEqual(replay["graph"]["revision_id"], after["revision_id"])
        self.assertEqual(len(replay["graph"]["nodes"]), 4)
        prepared_replay = self.service.prepare(request)
        self.assertEqual(prepared_replay["status"], "committed")
        self.assertEqual(prepared_replay["graph"]["revision_id"], after["revision_id"])

    def test_connect_uses_safe_custom_predicate_and_duplicate_intent_is_refused(
        self,
    ) -> None:
        graph = self.service.graph()
        request = {
            "operation_id": self._operation_id(),
            "expected_revision_id": graph["revision_id"],
            "kind": "connect",
            "source_id": self._id(graph, "Mara"),
            "target_id": self._id(graph, "Tomas"),
            "predicate": "helps.out",
        }
        prepared = self.service.prepare(request)
        self.assertEqual(prepared["status"], "prepared")
        result = self.service.confirm(request["operation_id"])
        self.assertEqual(len(result["graph"]["edges"]), 5)
        new_edge = next(
            edge
            for edge in result["graph"]["edges"]
            if edge["predicate"] == "helps.out"
        )
        self.assertTrue(new_edge["id"].startswith("asrt:"))

        duplicate_graph = result["graph"]
        duplicate = self.service.prepare(
            {
                **request,
                "operation_id": self._operation_id(),
                "expected_revision_id": duplicate_graph["revision_id"],
            }
        )
        self.assertEqual(duplicate["status"], "already_exists")
        self.assertEqual(
            duplicate["graph"]["revision_id"], duplicate_graph["revision_id"]
        )

    def test_stale_parent_unknown_fields_and_world_injection_are_rejected(self) -> None:
        graph = self.service.graph()
        request = self._create_request(graph)
        with self.assertRaises(DemoError) as stale:
            self.service.prepare({**request, "expected_revision_id": "rev:stale"})
        self.assertEqual(stale.exception.code, "stale_revision")
        self.assertIsNone(
            self.repository.get_native_source_admission_receipt(
                graph["world_id"],
                "native-graph-demo:operation-source:"
                + request["operation_id"].replace("-", ""),
            )
        )
        with self.assertRaises(DemoError) as extra:
            self.service.prepare({**request, "world_id": "space:another"})
        self.assertEqual(extra.exception.code, "invalid_request")
        with self.assertRaises(DemoError) as event:
            self.service.prepare(
                {**request, "object_kind": "event", "name": "Lantern Festival"}
            )
        self.assertEqual(event.exception.code, "unsupported_kind")
        self.assertIsNone(
            self.repository.get_native_source_admission_receipt(
                graph["world_id"],
                "native-graph-demo:operation-source:"
                + request["operation_id"].replace("-", ""),
            )
        )

    def test_name_and_relationship_label_byte_caps_precede_native_writes(self) -> None:
        graph = self.service.graph()
        before_head = self.repository.get_head(graph["world_id"])
        too_long_name = self._create_request(graph, name="n" * 129)
        with self.assertRaises(DemoError) as name_limit:
            self.service.prepare(too_long_name)
        self.assertEqual(name_limit.exception.code, "limit_exceeded")
        self.assertEqual(self.repository.get_head(graph["world_id"]), before_head)

        too_long_label = {
            "operation_id": self._operation_id(),
            "expected_revision_id": graph["revision_id"],
            "kind": "connect",
            "source_id": self._id(graph, "Mara"),
            "target_id": self._id(graph, "Tomas"),
            "predicate": "a" * 129,
        }
        with self.assertRaises(DemoError) as label_limit:
            self.service.prepare(too_long_label)
        self.assertEqual(label_limit.exception.code, "limit_exceeded")
        self.assertEqual(self.repository.get_head(graph["world_id"]), before_head)

    def test_reused_operation_id_is_bound_to_exact_canonical_input(self) -> None:
        graph = self.service.graph()
        request = self._create_request(graph)
        first = self.service.prepare(request)
        replay = self.service.prepare(request)
        self.assertEqual(replay["status"], "prepared")
        self.assertEqual(replay["parent_revision_id"], first["parent_revision_id"])
        with self.assertRaises(DemoError) as conflict:
            self.service.prepare({**request, "name": "Different"})
        self.assertEqual(conflict.exception.code, "operation_id_conflict")

    def test_same_name_does_not_define_identity_or_break_seed_restart_check(
        self,
    ) -> None:
        graph = self.service.graph()
        request = self._create_request(graph, name="Mara")
        self.service.prepare(request)
        committed = self.service.confirm(request["operation_id"])
        self.assertEqual(committed["status"], "committed")
        maras = [node for node in committed["graph"]["nodes"] if node["name"] == "Mara"]
        self.assertEqual(len(maras), 2)
        self.assertEqual(len({node["id"] for node in maras}), 2)
        self.service._store.close()

        restarted = NativeGraphDemoService(
            self.repository, self.state_dir, storage_label="test-memory"
        )
        self.assertEqual(
            len(
                [node for node in restarted.graph()["nodes"] if node["name"] == "Mara"]
            ),
            2,
        )
        restarted._store.close()

    def test_lost_response_recovers_native_receipt_before_replay(self) -> None:
        graph = self.service.graph()
        request = self._create_request(graph, name="Rin")
        self.service.prepare(request)
        record = self.service._store.get_operation(request["operation_id"])
        prepared = self.service._record_prepared(record)

        # Simulate native publication succeeding while the local response/journal
        # update is lost. Operation status must recover this receipt and exact child.
        self.service._runtime(
            prepared_id=prepared.prepared_change_id
        ).commit_prepared_change(prepared, confirmed_by="native-graph-demo-user")
        recovered = self.service.operation(request["operation_id"])
        self.assertEqual(recovered["status"], "committed")
        self.assertEqual(len(recovered["graph"]["nodes"]), 4)
        self.assertEqual(
            self.service.operation(request["operation_id"])["status"], "committed"
        )

    def test_unknown_commit_without_receipt_stays_unknown_and_is_not_redispatched(
        self,
    ) -> None:
        graph = self.service.graph()
        request = self._create_request(graph, name="Tavi")
        self.service.prepare(request)
        self.service._store.mark_operation_unknown(
            request["operation_id"], updated_at="test"
        )
        publication_id = "prepared:" + request["operation_id"].replace("-", "")

        operation = self.service.operation(request["operation_id"])
        self.assertEqual(operation["status"], "unknown")
        prepared_again = self.service.prepare(request)
        self.assertEqual(prepared_again["status"], "unknown")
        confirmed_again = self.service.confirm(request["operation_id"])
        self.assertEqual(confirmed_again["status"], "unknown")
        self.assertIsNone(
            self.repository.get_publication_receipt(graph["world_id"], publication_id)
        )
        self.assertIsNone(
            self.repository.get_prospective_publication(
                graph["world_id"], publication_id
            )
        )

    def test_prepared_journal_tamper_is_detected_before_native_commit(self) -> None:
        graph = self.service.graph()
        request = self._create_request(graph, name="Uma")
        self.service.prepare(request)
        connection = sqlite3.connect(self.state_dir / "native_graph_demo.sqlite3")
        try:
            row = connection.execute(
                "SELECT prepared_json FROM demo_operations WHERE operation_id = ?",
                (request["operation_id"],),
            ).fetchone()
            prepared_json = row[0]
            connection.execute(
                "UPDATE demo_operations SET prepared_json = ? WHERE operation_id = ?",
                (
                    prepared_json.replace('"new-object-name"', '"changed-name"'),
                    request["operation_id"],
                ),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(DemoError) as tampered:
            self.service.confirm(request["operation_id"])
        self.assertEqual(tampered.exception.code, "journal_integrity_failure")
        self.assertIsNone(
            self.repository.get_publication_receipt(
                graph["world_id"],
                "prepared:" + request["operation_id"].replace("-", ""),
            )
        )

    def test_stale_preparation_after_other_source_admission_requires_new_review(
        self,
    ) -> None:
        first_graph = self.service.graph()
        first = self._create_request(first_graph, name="Milo")
        self.service.prepare(first)
        second_parent = self.service.graph()
        second = self._create_request(second_parent, name="Nia")
        self.service.prepare(second)

        stale = self.service.confirm(first["operation_id"])
        self.assertEqual(stale["status"], "rejected")
        self.assertEqual(stale["code"], "stale_revision")
        self.assertIn("current graph", stale["error"])
        recovered = self.service.operation(first["operation_id"])
        self.assertEqual(recovered["status"], "rejected")
        self.assertEqual(recovered["code"], "stale_revision")
        replayed = self.service.prepare(first)
        self.assertEqual(replayed["status"], "rejected")
        self.assertIsNone(
            self.repository.get_publication_receipt(
                first_graph["world_id"],
                "prepared:" + first["operation_id"].replace("-", ""),
            )
        )

    def test_operation_lookup_distinguishes_not_found_from_recorded_unknown(
        self,
    ) -> None:
        missing_id = self._operation_id()
        self.assertEqual(
            self.service.operation(missing_id),
            {"operation_id": missing_id, "status": "not_found"},
        )
        graph = self.service.graph()
        request = self._create_request(graph, name="Jules")
        self.service.prepare(request)
        self.service._store.mark_operation_unknown(
            request["operation_id"], updated_at="test"
        )
        self.assertEqual(
            self.service.operation(request["operation_id"])["status"], "unknown"
        )

    def test_operation_reservation_recovers_admitted_source_without_duplicate_write(
        self,
    ) -> None:
        graph = self.service.graph()
        request = self._create_request(graph, name="Kei")
        normalized, request_json = self.service._validate_prepare_request(request)
        with self.service._store.atomic():
            self.service._store.reserve_operation(
                operation_id=request["operation_id"],
                request_json=request_json,
                parent_revision_id=graph["revision_id"],
                updated_at="test",
            )
            with self.service._store.checkpoint():
                pass

        receipt = self.service._admit_operation_source(
            normalized, expected_parent_revision_id=graph["revision_id"]
        )
        head_after_admission = self.repository.get_head(graph["world_id"])
        self.assertEqual(
            head_after_admission.head_revision_id, receipt.published_revision_id
        )
        recovered = self.service.operation(request["operation_id"])
        self.assertEqual(recovered["status"], "prepared")
        self.assertEqual(self.service._store.operation_count(), 2)
        self.assertIsNone(self.service._store.get_reservation(request["operation_id"]))
        self.assertEqual(
            self.repository.get_head(graph["world_id"]).head_revision_id,
            head_after_admission.head_revision_id,
        )

    def test_operation_quota_is_enforced_before_native_source_or_head_change(
        self,
    ) -> None:
        graph = self.service.graph()
        before_head = self.repository.get_head(graph["world_id"])
        request = self._create_request(graph, name="Lio")
        self.service._store.max_operations = self.service._store.operation_count()

        with self.assertRaises(DemoError) as full:
            self.service.prepare(request)
        self.assertEqual(full.exception.code, "operation_limit_reached")
        self.assertEqual(self.repository.get_head(graph["world_id"]), before_head)
        self.assertIsNone(
            self.repository.get_native_source_admission_receipt(
                graph["world_id"],
                "native-graph-demo:operation-source:"
                + request["operation_id"].replace("-", ""),
            )
        )
        self.assertIsNone(self.service._store.get_reservation(request["operation_id"]))

    @staticmethod
    def _id(graph: dict[str, Any], name: str) -> str:
        return next(node["id"] for node in graph["nodes"] if node["name"] == name)


if __name__ == "__main__":
    unittest.main()
