"""Guard: session-memory normalization canonical package is ``src.session_memory``."""

from __future__ import annotations

import ast
import inspect

import pytest

from src.session_memory import breadcrumb_normalize as canonical_mod
from src.session_memory.breadcrumb_normalize import (
    normalize_breadcrumb_artifact,
    write_records_jsonl,
)


def test_normalize_api_same_object_via_eval_shim() -> None:
    from evals.sentence_routing_retrieval_falsification import (
        breadcrumb_normalize as shim_mod,
    )

    assert shim_mod.normalize_breadcrumb_artifact is normalize_breadcrumb_artifact
    assert shim_mod.write_records_jsonl is write_records_jsonl


def test_materialize_script_imports_from_src_not_eval_shim() -> None:
    from pathlib import Path

    import scripts.materialize_session_memory as msm

    src = inspect.getsourcefile(msm)
    assert src is not None
    tree = ast.parse(Path(src).read_text(encoding="utf-8"))
    eval_imports = [
        n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and "evals" in n.module
    ]
    assert not eval_imports, "materialize_session_memory must not import eval package"


def test_canonical_module_file_under_src() -> None:
    src_file = inspect.getsourcefile(canonical_mod)
    assert src_file is not None
    assert "/src/session_memory/breadcrumb_normalize.py" in src_file.replace("\\", "/")
