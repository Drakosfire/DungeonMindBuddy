"""Smoke test for corpus index builder."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_corpus_index import build_index, render_markdown

ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "corpus" / "eldyrwild-markdown"


def test_build_corpus_index_shape():
    if not CORPUS_ROOT.is_dir():
        return
    index = build_index()
    assert index["schema"] == "dmb_corpus_index_v1"
    assert index["corpus_roots"]["primary_markdown"]["markdown_file_count"] > 0
    c1 = index["session_recaps"]["campaign_1"]
    c2 = index["session_recaps"]["campaign_2"]
    assert c1["counts"]["canonical"] >= 10
    assert c2["counts"]["_normalized"] >= 20
    md = render_markdown(index)
    assert "Campaign 1 — Session Recaps" in md
    assert "Elderwyld" in md
    json.dumps(index)  # serializable
