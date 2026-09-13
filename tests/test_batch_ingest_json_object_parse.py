from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_BATCH_INGEST_PATH = ROOT / "tools" / "batch_ingest_corpus.py"
_spec = importlib.util.spec_from_file_location("batch_ingest_corpus", _BATCH_INGEST_PATH)
assert _spec is not None and _spec.loader is not None
_batch_ingest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_batch_ingest)
json_object_parse_row_counts = _batch_ingest.json_object_parse_row_counts


def test_json_object_parse_row_counts_zero_retries_are_zero() -> None:
    attempts, retries, retried = json_object_parse_row_counts(
        {"json_object_attempts": 12, "json_object_retries": 0}
    )
    assert (attempts, retries, retried) == (12, 0, 0)


def test_json_object_parse_row_counts_does_not_treat_zero_as_attempts_minus_one() -> None:
    rows = [
        {"json_object_attempts": 12, "json_object_retries": 0},
        {"json_object_attempts": 13, "json_object_retries": 1},
        {"json_object_attempts": 12, "json_object_retries": 0},
    ]
    http_attempts = retries = retried_calls = 0
    for row in rows:
        a, r, c = json_object_parse_row_counts(row)
        http_attempts += a
        retries += r
        retried_calls += c
    assert http_attempts == 37
    assert retries == 1
    assert retried_calls == 1
    # Old bug: `retries or (attempts-1)` would count 11+12+11 = 34.
    assert retries != sum(max(0, int(row["json_object_attempts"]) - 1) for row in rows)


def test_json_object_parse_row_counts_skips_responses_rows() -> None:
    assert json_object_parse_row_counts({"input_tokens": 9}) == (0, 0, 0)
