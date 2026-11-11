from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path

from apps.live_control_server.native_graph_demo import DemoError, NativeGraphDemoService
from apps.live_control_server.native_graph_demo.storage import NativeGraphDemoStore
from dungeonmind.infrastructure.memory.vnext_sources import (
    InMemoryNativeSourceEvidenceRepository,
)


class NativeGraphDemoStorageTests(unittest.TestCase):
    def test_same_service_retries_initialization_after_source_response_loss(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repository = InMemoryNativeSourceEvidenceRepository()
            service = NativeGraphDemoService(
                repository, temp, storage_label="test-memory"
            )
            original_admit = service._admit_seed_source

            def lose_response(expected_parent_revision_id: str):
                original_admit(expected_parent_revision_id)
                raise RuntimeError("simulated lost source-admission response")

            service._admit_seed_source = lose_response
            with self.assertRaises(DemoError):
                service.graph()
            service._admit_seed_source = original_admit

            recovered = service.graph()
            self.assertEqual(len(recovered["nodes"]), 3)
            self.assertEqual(len(recovered["edges"]), 4)
            self.assertTrue(service._initialized)
            service.close()

    def test_reconstructed_service_recovers_seed_receipt_after_local_write_loss(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repository = InMemoryNativeSourceEvidenceRepository()
            first = NativeGraphDemoService(
                repository, temp, storage_label="test-memory"
            )
            original_confirm = first._confirm_record

            def lose_local_result(operation_id: str, *args: object, **kwargs: object):
                result = original_confirm(operation_id, *args, **kwargs)
                if operation_id == "seed:native-graph-demo-v1":
                    raise RuntimeError("simulated lost local journal response")
                return result

            first._confirm_record = lose_local_result
            with self.assertRaises(DemoError):
                first.graph()
            first.close()

            restarted = NativeGraphDemoService(
                repository, temp, storage_label="test-memory"
            )
            recovered = restarted.graph()
            self.assertEqual(len(recovered["nodes"]), 3)
            self.assertEqual(len(recovered["edges"]), 4)
            self.assertTrue(restarted._initialized)
            restarted.close()

    def test_service_restart_recovers_prepared_command_and_same_native_world(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            repository = InMemoryNativeSourceEvidenceRepository()
            first_service = NativeGraphDemoService(
                repository, path, storage_label="test-memory"
            )
            first_graph = first_service.graph()
            operation_id = str(uuid.uuid4())
            request = {
                "operation_id": operation_id,
                "expected_revision_id": first_graph["revision_id"],
                "kind": "create_object",
                "name": "Sol",
                "object_kind": "person",
            }
            prepared = first_service.prepare(request)
            self.assertEqual(prepared["status"], "prepared")
            first_service.close()

            restarted = NativeGraphDemoService(
                repository, path, storage_label="test-memory"
            )
            operation = restarted.operation(operation_id)
            self.assertEqual(operation["status"], "prepared")
            committed = restarted.confirm(operation_id)
            self.assertEqual(committed["status"], "committed")
            self.assertEqual(committed["graph"]["world_id"], first_graph["world_id"])
            self.assertIn("Sol", {node["name"] for node in committed["graph"]["nodes"]})
            restarted.close()

            final_service = NativeGraphDemoService(
                repository, path, storage_label="test-memory"
            )
            self.assertEqual(
                final_service.operation(operation_id)["status"], "committed"
            )
            self.assertEqual(final_service.graph()["world_id"], first_graph["world_id"])
            final_service.close()

    def test_local_journal_keeps_command_metadata_not_graph_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            repository = InMemoryNativeSourceEvidenceRepository()
            service = NativeGraphDemoService(
                repository, path, storage_label="test-memory"
            )
            graph = service.graph()
            operation_id = str(uuid.uuid4())
            service.prepare(
                {
                    "operation_id": operation_id,
                    "expected_revision_id": graph["revision_id"],
                    "kind": "create_object",
                    "name": "Eli",
                    "object_kind": "person",
                }
            )
            service.close()

            connection = sqlite3.connect(path / "native_graph_demo.sqlite3")
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                self.assertEqual(
                    tables,
                    {
                        "demo_metadata",
                        "demo_operations",
                        "demo_operation_reservations",
                    },
                )
                row = connection.execute(
                    "SELECT request_json, prepared_json FROM demo_operations WHERE operation_id = ?",
                    (operation_id,),
                ).fetchone()
                self.assertIsNotNone(row)
                request_data, prepared_data = json.loads(row[0]), json.loads(row[1])
                self.assertEqual(request_data["name"], "Eli")
                self.assertEqual(prepared_data["schema"], "dmb_wk_prepared_standing_v1")
                self.assertEqual(prepared_data["value"]["type"], "PreparedWorldChange")
                self.assertNotIn("nodes", prepared_data)
                self.assertNotIn("edges", prepared_data)
            finally:
                connection.close()

    def test_new_repository_cannot_rebind_saved_journal_to_another_world(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            first = NativeGraphDemoService(
                InMemoryNativeSourceEvidenceRepository(),
                path,
                storage_label="test-memory",
            )
            original_world = first.graph()["world_id"]
            first.close()

            second = NativeGraphDemoService(
                InMemoryNativeSourceEvidenceRepository(),
                path,
                storage_label="test-memory",
            )
            with self.assertRaises(DemoError) as mismatch:
                second.graph()
            self.assertEqual(mismatch.exception.code, "space_binding_mismatch")
            self.assertNotEqual(original_world, second._space_id)
            second.close()

    def test_operation_payload_digest_fails_closed_after_edit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = NativeGraphDemoStore(temp)
            store.insert_prepared_operation(
                operation_id="op:test",
                request_json='{"kind":"connect"}',
                parent_revision_id="rev:test",
                prepared_json='{"$type":"PreparedWorldChange"}',
                updated_at="2026-11-10T00:00:00+00:00",
            )
            store.close()
            connection = sqlite3.connect(Path(temp) / "native_graph_demo.sqlite3")
            try:
                connection.execute(
                    "UPDATE demo_operations SET prepared_json = ? WHERE operation_id = ?",
                    ('{"$type":"PreparedWorldChange","tampered":true}', "op:test"),
                )
                connection.commit()
            finally:
                connection.close()
            reopened = NativeGraphDemoStore(temp)
            with self.assertRaises(ValueError):
                reopened.get_operation("op:test")
            reopened.close()


if __name__ == "__main__":
    unittest.main()
