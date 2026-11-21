"""Exercise release rehearsal acceptance/refusal through the actual CLI."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / "scripts" / "plan_buddy_preview_release.py"
COMMIT = "a" * 40
CANDIDATE = "sha256:" + "b" * 64
PRIOR = "sha256:" + "c" * 64
NEWER = "sha256:" + "d" * 64


class PlanReleaseTest(unittest.TestCase):
    def setUp(self):
        self.request = {
            "environment": "local-preview",
            "source_commit": COMMIT,
            "candidate_image_id": CANDIDATE,
            "expected_current_image_id": PRIOR,
        }
        self.witness = {
            "source_commit": COMMIT,
            "image_id": CANDIDATE,
            "network_mode": "none",
            "live_status": 200,
            "spa_status": 200,
        }

    def invoke(self, observed=PRIOR, *, raw_request=None, flags=()):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "request.json"
            request.write_text(raw_request if raw_request is not None else json.dumps(self.request))
            witness = Path(directory) / "witness.json"
            witness.write_text(json.dumps(self.witness))
            return subprocess.run(
                [sys.executable, str(CLI), str(request), str(witness),
                 "--observed-current-image-id", observed, *flags],
                capture_output=True, text=True, check=False,
            )

    def test_plan_is_unchanged_on_duplicate(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, self.invoke().stdout)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["prior_image_for_rehearsal"], PRIOR)
        self.assertFalse(plan["mutation_performed"])
        self.assertFalse(plan["production_authorized"])

    def test_initial_preview_without_prior(self):
        self.request["expected_current_image_id"] = None
        result = self.invoke("none")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(json.loads(result.stdout)["prior_image_for_rehearsal"])

    def test_stale_plan_after_newer_release(self):
        result = self.invoke(NEWER)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Stale request", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_already_current_is_a_noop(self):
        self.request["expected_current_image_id"] = CANDIDATE
        result = self.invoke(CANDIDATE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["disposition"], "already_current")

    def test_stale_preview_witness(self):
        for key, val in (("image_id", NEWER), ("source_commit", "e" * 40)):
            with self.subTest(key=key):
                previous = self.witness[key]
                self.witness[key] = val
                result = self.invoke()
                self.assertEqual(result.returncode, 2)
                self.assertIn("exact source and image", result.stderr)
                self.witness[key] = previous

    def test_preview_failure_or_connected_network(self):
        for key, val in (("live_status", 503), ("spa_status", 404), ("network_mode", "host")):
            with self.subTest(key=key):
                previous = self.witness[key]
                self.witness[key] = val
                self.assertEqual(self.invoke().returncode, 2)
                self.witness[key] = previous

    def test_no_production_or_apply(self):
        self.request["environment"] = "production"
        self.assertEqual(self.invoke().returncode, 2)
        self.request["environment"] = "local-preview"
        self.assertEqual(self.invoke(flags=("--apply",)).returncode, 2)

    def test_unknown_and_duplicate_fields_are_rejected(self):
        self.request["shell_command"] = "irrelevant"
        self.assertEqual(self.invoke().returncode, 2)
        result = self.invoke(raw_request='{"environment":"production","environment":"local-preview"}')
        self.assertEqual(result.returncode, 2)
        self.assertIn("Duplicate field", result.stderr)
