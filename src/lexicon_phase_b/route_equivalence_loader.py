from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from .schemas import RouteEquivalenceRecord

# Schema versions this loader can deserialize. Keep in sync with
# RouteEquivalenceRecord.schema_version. Add new versions explicitly when
# the writer schema bumps.
SUPPORTED_ROUTE_EQUIVALENCE_SCHEMA_VERSIONS: frozenset[str] = frozenset({"0.2.0"})


def load_route_equivalence_manifest(path: Path) -> list[RouteEquivalenceRecord]:
    """Load a single committed `route_equivalence_*_v1.jsonl` artifact.

    - Skips blank lines.
    - Validates each row's `schema_version` is in
      ``SUPPORTED_ROUTE_EQUIVALENCE_SCHEMA_VERSIONS``; raises ``ValueError``
      with the offending value, line number (1-based), and path otherwise.
    - Returns records in the file's natural order. The writer emits
      ``sorted(records, key=lambda r: r.record_id)``, so consumers can rely
      on canonical order without a re-sort.
    - Raises ``FileNotFoundError`` if ``path`` is not a file.
    """
    resolved = Path(path)
    if not resolved.is_file():
        raise FileNotFoundError(f"route equivalence manifest not found: {resolved}")
    records: list[RouteEquivalenceRecord] = []
    for line_number, line in enumerate(resolved.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        schema_version = str(payload.get("schema_version") or "")
        if schema_version not in SUPPORTED_ROUTE_EQUIVALENCE_SCHEMA_VERSIONS:
            raise ValueError(
                f"unsupported route equivalence schema_version {schema_version!r} "
                f"at line {line_number} in {resolved}"
            )
        records.append(RouteEquivalenceRecord.model_validate(payload))
    return records


def load_route_equivalence_manifests(
    paths: Sequence[Path],
) -> list[RouteEquivalenceRecord]:
    """Load and concatenate multiple manifests deterministically.

    - Calls ``load_route_equivalence_manifest`` for each path in order.
    - Dedupes by ``record_id`` (first occurrence wins).
    - Returns the deduped list **sorted by ``record_id``** so callers
      get the same ordering whether they passed [c1, c2] or [c2, c1].
    - Empty ``paths`` returns ``[]``.
    """
    if not paths:
        return []
    by_record_id: dict[str, RouteEquivalenceRecord] = {}
    for path in paths:
        for record in load_route_equivalence_manifest(path):
            by_record_id.setdefault(record.record_id, record)
    return sorted(by_record_id.values(), key=lambda r: r.record_id)
