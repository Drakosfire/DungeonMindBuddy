"""Classify a few exact App SQL call sites; never infer complete coverage."""

from .sql_window import validate_sql_window

_KNOWN_RUNTIME = {
    "normalizer": "marshal-code-v1", "implementation": "cpython",
    "version": [3, 13, 12], "cache_tag": "cpython-313", "optimize": 0,
}
_PAGES = {
    "29179cbe37f50b19157e6f0f157ed0cb860a42d6a7c62d3ccccfa15d42244273",
    "39c0f3585645a70f81f0f995c036f90b9c2ffbb5ed3272b41f72d11d35b811d7",
}
_REPOSITORIES = {
    "59803ac57cbb152e87e27665a8a626a9a1c47fcf56194f92e5efa40eabdc619d",
    "4a10c408016820ef35c1f119a2ffdd2d700f85c4336ed450cc8442039fd47819",
}
_PAGE_INVENTORY = "96e294fcca6a28d86a82ab36468e4c101183f31092ec1f49cb6875a8e089a50b"
_REVISION = "bbaebdc2798fa84dc5a247ba31ba0a51c5c20b32e734c87a65c3a8e450081e54"
_REVISION_BY_N = "7e19c7fbd63ed5955c6222a93262d08b9fce1e94e8ffff5488514088c46a1d15"
_WORKING_COPY = {
    ("59803ac57cbb152e87e27665a8a626a9a1c47fcf56194f92e5efa40eabdc619d",
     "e37ec5aefa173accec3fdf72c2d22067676b6a214dc2e248a2db80d4bff60ac3", 321),
    ("4a10c408016820ef35c1f119a2ffdd2d700f85c4336ed450cc8442039fd47819",
     "3709f20f417440079f1db36cf739beea5e08f0f94b40d238d86251a51282b81f", 334),
}


def classify_sql_window(value, case_id):
    """Return observed lower bounds; unknowns never become zero-read proof."""
    if value is None:
        return None
    value = validate_sql_window(value, case_id)
    if (value["schema"] != "dmb_negative_retrieval_sql_window_v2"
            or value["runtime"] != _KNOWN_RUNTIME
            or value["status"] not in {"observed", "uncertain"}):
        return None
    counts = {"page_inventory_attempts": 0, "saved_revision_body_attempts": 0,
              "working_copy_body_attempts": 0}
    for row in value["calls"]:
        if row["scope"] != "app" or row["api"] != "execute":
            continue
        source, code, line = row["source_sha256"], row["code_sha256"], row["line"]
        if source in _PAGES and code == _PAGE_INVENTORY and line == 512:
            counts["page_inventory_attempts"] += row["count"]
        elif source in _REPOSITORIES and ((code == _REVISION and line == 192)
                                          or (code == _REVISION_BY_N and line == 209)):
            counts["saved_revision_body_attempts"] += row["count"]
        elif (source, code, line) in _WORKING_COPY:
            counts["working_copy_body_attempts"] += row["count"]
    return {"schema": "dmb_negative_retrieval_sql_source_classification_v1",
            "coverage": "partial", "window_status": value["status"], "observed_attempts": counts,
            "unclassified_started": value["started"] - sum(counts.values()),
            "dropped_starts": value["dropped_starts"], "resumed_unknown": value["resumed_unknown"]}
