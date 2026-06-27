"""Import shim for the src/graph_memory package layout."""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]
_src_graph_memory = Path(__file__).resolve().parent.parent / "src" / "graph_memory"
if _src_graph_memory.is_dir():
    __path__.append(str(_src_graph_memory))
