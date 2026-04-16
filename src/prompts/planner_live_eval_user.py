"""User-message fragments appended by planner live-eval harness (not model instructions)."""

from __future__ import annotations

# Appended after ``--- Planning goal ---`` when a fixture uses ``planning_goal`` (autonomous mode).
AUTONOMOUS_PLANNING_USER_SUFFIX = """## How to respond (autonomous plan)

You are given a **goal**, not a recipe. From the corpus tree, **choose** which markdown files to open with `read_corpus_file`. Then deliver a **structured plan** for the GM using several top-level `##` Markdown sections (for example: situation summary, suggested beats, sensory/atmosphere, PC hooks, open questions, sources).

Do **not** close with a path bibliography or bullet-list corpus-relative `.md` paths; evaluation
records reads via the tool trace. Ground claims in prose without raw file paths unless the GM
explicitly asked which files you opened. Do not call `generate_statblock` unless the goal clearly
requires a creature stat block."""
