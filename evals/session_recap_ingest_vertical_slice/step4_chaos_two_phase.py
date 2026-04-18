"""C3 chaos scenario: stale ``confirm_token`` when content mutates between phases.

Covered in production by ``tests/test_corpus_writer.py`` (token invalidates on content change).
This module is a documentation anchor for the benchmark gate list.
"""

from __future__ import annotations

DOCUMENTATION = "See tests/test_corpus_writer.py::test_token_invalidates_when_content_changes_between_phases"
