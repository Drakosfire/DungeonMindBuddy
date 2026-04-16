"""User-message fragments appended by planner live-eval harness (not model instructions)."""

from __future__ import annotations

# Appended after ``--- Planning goal ---`` when a fixture uses ``planning_goal`` (autonomous mode).
AUTONOMOUS_PLANNING_USER_SUFFIX = """## How to respond (autonomous plan)

You are given a **goal**, not a recipe. From the corpus tree, **choose** which markdown files to open with `read_corpus_file`. Then deliver a **structured plan** for the GM using several top-level `##` Markdown sections (for example: situation summary, suggested beats, sensory/atmosphere, PC hooks, open questions, sources).

In your JSON `message`, include **inline** corpus-relative `.md` paths (`Elderwyld/...` or
`Longmont Campaign/...`) matching files you opened with `read_corpus_file`—at least once when
you use the corpus—woven into normal prose; avoid a closing section that is only a file list.
Do not call `generate_statblock` unless the goal clearly
requires a creature stat block."""
