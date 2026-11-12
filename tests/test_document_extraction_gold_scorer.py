from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCORER = ROOT / "evals" / "document_extraction_gold" / "score_ocr2_artifacts.py"
GOLD = ROOT / "evals" / "document_extraction_gold" / "adventure_pdf_source_gold_v1.json"
SCORER_SPEC = importlib.util.spec_from_file_location("document_extraction_gold_scorer", SCORER)
assert SCORER_SPEC and SCORER_SPEC.loader
SCORER_MODULE = importlib.util.module_from_spec(SCORER_SPEC)
SCORER_SPEC.loader.exec_module(SCORER_MODULE)


class RegionArtifactScorerTests(unittest.TestCase):
    def test_standalone_dash_is_not_collapsed_to_an_empty_value(self) -> None:
        self.assertEqual(SCORER_MODULE.normalize("—"), "dash")

    def test_selected_region_scores_exact_source_and_prose(self) -> None:
        gold = json.loads(GOLD.read_text(encoding="utf-8"))
        case = next(item for item in gold["cases"] if item["block_type"] == "prose_region")
        source = next(item for item in gold["sources"] if item["source_id"] == case["source_id"])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            gold_path = root / "gold.json"
            gold_path.write_text(json.dumps({"dataset_id": gold["dataset_id"], "sources": [source], "cases": [case]}))
            result_dir = root / case["case_id"]
            result_dir.mkdir()
            (root / "run.json").write_text(json.dumps({
                "model_id": "deepseek-ai/DeepSeek-OCR-2",
                "model_snapshot": "fixture-snapshot",
                "input_pdf_sha256": {case["source_id"]: source["pdf_sha256"]},
            }))
            (result_dir / "result.json").write_text(json.dumps({
                "case_id": case["case_id"],
                "source_id": case["source_id"],
                "source_pdf_sha256": source["pdf_sha256"],
                "page_index": case["physical_page"] - 1,
                "region": case["source_region"],
                "elapsed_seconds": 0.25,
                "text": f"<|ref|>text<|/ref|>\n{case['expected_text']}",
            }))
            completed = subprocess.run(
                [sys.executable, str(SCORER), "--gold", str(gold_path), "--artifact-root", f"{case['source_id']}={root}"],
                check=False, capture_output=True, text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        scored = next(item for item in report["cases"] if item["case_id"] == case["case_id"])
        self.assertEqual(scored["classification"]["status"], "matched")
        self.assertTrue(scored["transcription"]["normalized_exact_match"])
        self.assertEqual(scored["source_location"], {
            "source_hash_match": True,
            "run_manifest_hash_match": True,
            "page_match": True,
            "region_match": True,
        })
        self.assertEqual(scored["model_snapshot"], "fixture-snapshot")

    def test_wrong_region_is_a_failing_source_location(self) -> None:
        gold = json.loads(GOLD.read_text(encoding="utf-8"))
        case = next(item for item in gold["cases"] if item["block_type"] == "prose_region")
        source = next(item for item in gold["sources"] if item["source_id"] == case["source_id"])
        wrong_region = {**case["source_region"], "x": case["source_region"]["x"] + 0.01}

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            gold_path = root / "gold.json"
            gold_path.write_text(json.dumps({"dataset_id": gold["dataset_id"], "sources": [source], "cases": [case]}))
            result_dir = root / case["case_id"]
            result_dir.mkdir()
            (root / "run.json").write_text(json.dumps({
                "input_pdf_sha256": {case["source_id"]: source["pdf_sha256"]},
            }))
            (result_dir / "result.json").write_text(json.dumps({
                "case_id": case["case_id"],
                "source_id": case["source_id"],
                "source_pdf_sha256": source["pdf_sha256"],
                "page_index": case["physical_page"] - 1,
                "region": wrong_region,
                "text": f"<|ref|>text<|/ref|>\n{case['expected_text']}",
            }))
            completed = subprocess.run(
                [sys.executable, str(SCORER), "--gold", str(gold_path), "--artifact-root", f"{case['source_id']}={root}"],
                check=False, capture_output=True, text=True,
            )

        self.assertEqual(completed.returncode, 1)
        scored = json.loads(completed.stdout)["cases"][0]
        self.assertFalse(scored["source_location"]["region_match"])

    def test_invalid_present_run_manifest_is_rejected(self) -> None:
        gold = json.loads(GOLD.read_text(encoding="utf-8"))
        case = next(item for item in gold["cases"] if item["block_type"] == "prose_region")
        source = next(item for item in gold["sources"] if item["source_id"] == case["source_id"])

        for manifest_text in (
            json.dumps({"input_pdf_sha256": {case["source_id"]: "0" * 64}}),
            json.dumps({"input_pdf_sha256": {}}),
            "{ invalid json",
        ):
            with self.subTest(manifest_text=manifest_text), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                gold_path = root / "gold.json"
                gold_path.write_text(json.dumps({"dataset_id": gold["dataset_id"], "sources": [source], "cases": [case]}))
                result_dir = root / case["case_id"]
                result_dir.mkdir()
                (root / "run.json").write_text(manifest_text)
                (result_dir / "result.json").write_text(json.dumps({
                    "case_id": case["case_id"],
                    "source_id": case["source_id"],
                    "source_pdf_sha256": source["pdf_sha256"],
                    "page_index": case["physical_page"] - 1,
                    "region": case["source_region"],
                    "text": f"<|ref|>text<|/ref|>\n{case['expected_text']}",
                }))
                completed = subprocess.run(
                    [sys.executable, str(SCORER), "--gold", str(gold_path), "--artifact-root", f"{case['source_id']}={root}"],
                    check=False, capture_output=True, text=True,
                )

                self.assertEqual(completed.returncode, 1)
                scored = json.loads(completed.stdout)["cases"][0]
                self.assertFalse(scored["source_location"]["run_manifest_hash_match"])

    def test_existing_page_artifact_shape_remains_supported(self) -> None:
        gold = json.loads(GOLD.read_text(encoding="utf-8"))
        case = next(item for item in gold["cases"] if item["block_type"] == "prose_region")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_pdf = root / "source.pdf"
            source_pdf.write_bytes(b"pinned source fixture")
            source = {"source_id": case["source_id"], "pdf_sha256": hashlib.sha256(source_pdf.read_bytes()).hexdigest()}
            case = {**case, "expected_text": "A short source paragraph."}
            gold_path = root / "gold.json"
            gold_path.write_text(json.dumps({"dataset_id": gold["dataset_id"], "sources": [source], "cases": [case]}))
            page_dir = root / "page-artifacts"
            page_dir.mkdir()
            (page_dir / "stageA.page.json").write_text(json.dumps({
                "page_index": case["physical_page"] - 1,
                "source_pdf": str(source_pdf),
                "raw_markdown": case["expected_text"],
            }))
            completed = subprocess.run(
                [sys.executable, str(SCORER), "--gold", str(gold_path), "--artifact-root", f"{case['source_id']}={root}"],
                check=False, capture_output=True, text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        scored = json.loads(completed.stdout)["cases"][0]
        self.assertEqual(scored["artifact_status"], "present")
        self.assertTrue(scored["source_location"]["source_hash_match"])
        self.assertTrue(scored["transcription"]["normalized_exact_match"])


if __name__ == "__main__":
    unittest.main()
