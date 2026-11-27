# Negative-retrieval H4 observations

The frozen H4 set was authored independently of the implementation lane before
its first replay. Its author had seen the implementation and earlier fixtures;
this is independent authorship, not a blinded study. It contains one creative
negative, one 46-exchange context-reuse negative, and one saved-current-page
source-required control. The source-required control uses an App page, not a
native Core source. The fixture and private rubric remain local so this record
is not a model input or a reusable held-out set after exposure.

Configuration: exact serving source
`95ee0e6102f77cec1806ccf83b6144e5f7305578`, independently pinned Core
and model dependencies, the one retained disposable App clone and existing
read-only Core snapshot. The frozen fixture file SHA-256 is
`f1040fd19c9074bdeb2bdcbdcca03361f5e612aa6c3519b74f7be7b02ada0a45`;
the private rubric file SHA-256 is
`e01bbe1a6ee1f0873a76ad611cce0de17a20b55da382df2d7a779c585b67cf63`.
The PDF-loader probe came from merged evaluator revision
`e15a43d3ae50e0d0ee876e2bb5e6726829ef2772`. Each case ran serially in a
fresh synthetic World on the same clone. Wires were audited before dispatch;
private rubrics and host identifiers were not sent to the model.

| Case | Captured case | Semantic review | Observed catalog calls | Observed selected-page materializations | Local request time |
| --- | --- | --- | ---: | ---: | ---: |
| Creative negative | 329; repeat 341 | Both passed | 0 | 0 | 3.627 s repeat |
| 46-exchange context negative | 332; repeat 344 | Both passed | 0 | 0 | 4.087 s repeat |
| Saved-current-page control | 338 | Passed; exact returned page identity and body supported citation | 0 | 1 | 5.313 s |

The covered native Graph and PDF probes recorded no entries for these cases;
the direct-current metadata owner recorded one lookup for case 338. These are
observations, not proof that uninstrumented owners did no work or a count of
all distinct sources. The selected-page materialization column does not include
the Build route's primary-work validation read: that route-bound reader was not
instrumented in these captures, so its count for these turns is unknown. A later
provider-free check of the same serving-source resolver observed one returned
primary-page read on the synthetic App fixture (case 355); this is not a replay
of H4. Each bound offline report remains **unproven** because capture-environment
and complete-journal verification are not established.
Cases 329 and 332 had manual audit pauses; their repeat timings use only
byte-identical, previously independently audited requests and are local single
observations, not production latency guarantees. Repeat outputs were separately
reviewed, but repeats are no longer fresh held-out evidence.

Case 335 is a retained incomplete attempt: the writer request was not sent
before the prompt-audit handoff timed out. An independent offline audit later
confirmed its bytes were safe; the fresh case 338 retry used only exact audited
request bytes. Do not treat the interruption as a product failure or erase it.

The original Shepherd trace remains a useful failure observation, not a
controlled baseline: its roughly four-minute execution and related-read
observations overlap and do not establish distinct acquisition counts. The
separate development replay and its limitations are documented in the
[negative-retrieval README](../../evals/negative_retrieval/README.md).

The synthetic fixture, private rubric, request and response artifacts, bound
semantic reviews, preflight manifests and offline reports are retained under
`/home/drakosfire/Projects/.codex/buddy-check.current-page-owner.ssCukO` in
`heldout-h4` and the named `owner/case-*` directories. This host-local evidence
is not a portable fixture dependency. No new database was created; the owner
retains the clone for ongoing work, with its last worker closed.

The native-Core source-required control remains missing: the shared read-only
Core has no documented synthetic source and valid binding available in the
inspected evidence. An absent-key source-view probe does not satisfy that
control. No existing source data was searched to manufacture one. The source
release used here is live via [deployment run 45934071368](https://github.com/Drakosfire/DungeonMindBuddy/actions/runs/45934071368);
a separate signed-in current-page partial-answer smoke completed in 12.1 s.
Neither these observations nor that smoke complete the wider over-retrieval goal.
