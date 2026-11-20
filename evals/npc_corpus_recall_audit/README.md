# NPC corpus recall lab

This offline audit examines the checked-in NPC hubs and recap mentions for
Campaign1 Sessions1–3 and Campaign2 Session20. It is experimental checkout
tooling, not a hosted Buddy API or production readiness check. Its owning tests
are `tests/test_npc_corpus_recall_audit.py`.

The generator is `npc_corpus_recall_audit.py`. Its default invocation writes a
dated report and replaces `artifacts/last_npc_corpus_recall_audit.json`.
Supplying `--output` changes the dated output destination but **still replaces
the last-report mirror** unless `--no-update-latest` is also supplied. The retained
last report is a historical result, not automatically refreshed current truth.

For a new offline report without changing checkout artifacts, use the checked
Projects launcher and both output options from the repository root:

```bash
scripts/run_local_lab.sh npc-recall-audit bash -c \
  'uv run --locked python evals/npc_corpus_recall_audit/npc_corpus_recall_audit.py --output "$TMPDIR/npc-recall-audit.json" --no-update-latest'
```

Use a task slug you own. The JSON command receipt reports `mirror: null` when
the automatic mirror write is disabled. Without an explicit `--output`, the
runner still creates a dated checkout report even with `--no-update-latest`.

## Historical snapshots

The following reports remain recoverable from exact Git history instead of
occupying the working checkout. They record thirteen targets, failed readiness
checks, and differing historical schemas/results. Their retirement does not
assert that current inputs regenerate those results.

- [npc_corpus_recall_audit--20260508T001859Z.json](https://github.com/Drakosfire/DungeonMindBuddy/blob/5fd10acc0d67127ea89bfb67de67fc1cb22e64bd/evals/npc_corpus_recall_audit/artifacts/runs/2026-05-07/npc_corpus_recall_audit--20260508T001859Z.json): 16355 bytes; SHA256 `1cf858b6ab934974a35db2b2ed1a2100156a87511e205009d7bdba481133f959`.
- [npc_corpus_recall_audit--20260508T002251Z.json](https://github.com/Drakosfire/DungeonMindBuddy/blob/5fd10acc0d67127ea89bfb67de67fc1cb22e64bd/evals/npc_corpus_recall_audit/artifacts/runs/2026-05-07/npc_corpus_recall_audit--20260508T002251Z.json): 19754 bytes; SHA256 `7534675aa4669791e656829afe5533276b9268178ce7a798b410c67c26211f6d`.
- [npc_corpus_recall_audit--20260508T021307Z.json](https://github.com/Drakosfire/DungeonMindBuddy/blob/5fd10acc0d67127ea89bfb67de67fc1cb22e64bd/evals/npc_corpus_recall_audit/artifacts/runs/2026-05-07/npc_corpus_recall_audit--20260508T021307Z.json): 22021 bytes; SHA256 `a5008fb30991f53401bd7d4c260b15d712649a4036d9649d06e3d352c44293f9`.
