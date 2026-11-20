# PERF: Reuse validated native writer prefixes during retained citation checks

ACTIVE serial successor to merged #4186. Base 66556c8c7358ab6d1b917017bec74cf947281733.
User authority is the hosted first-dispatch goal. No provider use in qualification.
Worktree, fixture outputs, and scratch stay on Projects. Verify isolated APP state.

The Build dialogue driver pays the completed Turn codec's full citation validation
cost while loading recent dialogue. Its observed current stage cost is 974 ms.
The earlier isolated profile put most time in retained citation reconstruction,
including repeated validation and serialization of the writer prefix.

Write scope: native_execution.py, native_completion.py, native_writer.py, their
existing tests and this handoff. Derive a writer prefix only inside the retained
completion join from a fully validated parent. Rerun the prefix lifecycle,
context and citation predicates, and extract the same evidence frame without
reparsing its unchanged typed components. Keep the public writer's full validator.
No cache, schema change, persistence change or reduced citation checks.

Verify ordinary Build, writer and native execution contracts with existing
disposable clones. Test exact citation reopening and refusal of a changed retained
witness. Require independent exact-head review and compare the CPU and hosted
driver timings before attributing a speedup.
