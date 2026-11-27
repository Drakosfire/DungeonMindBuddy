# RETRIEVAL: retained evidence presentation reader

Status: MERGED as `22f871c8e73752756593858311cb1580471b5f38` in #4959;
reader deployment and verification remain prerequisites for the producer.
This slice does not emit the new presentation. Base serving revision
`c3f58d55b7df156ab101ed2b607a8309b502c74b`, branch
`codex/retrieval-retained-dedup-reader`. The user authorized the retrieval goal,
reviewed merges and deployment.

The deployed long-chat creative check included 81 retained native excerpts and
508,412 excerpt characters. Visible labels, ranges and text indicate repeated
material, but labels do not prove source identity. The full conversation must
remain intact, and prior evidence must remain available for factual questions.

This reader accepts a new, non-emitted retained presentation only after proving
that every removed writer row duplicates an already admitted row under the
same immutable World, Graph revision, source/revision, access span, scope,
extent, text and planning metadata. Original records remain in the retained
closure. A selected row resolves to its own real authorized read; unoffered
handles cannot cite omitted rows. All existing presentation versions reconstruct
their original bytes and citations. Pending saved-page citations, exact full
dialogue, current request and correction order are preserved.

Write lease: this handoff; retained-conversation presentation and native writer
reconstruction; the retained presentation codec and pending saved-page reader;
focused retained-presentation tests and their CI classification. No database or
provider mutation is needed. The current serving branch has other pre-existing
unclassified tests; this slice classifies its new test only.
Validate exact duplicate collapse and non-equivalence for changed World, source,
revision, access span, scope, extent, text or planning ranges; existing v4 and
historical replay; full dialogue and saved-page citations; unoffered selector
rejection and exact citation readback. Independently review the exact head.

Only after the reader is reviewed, deployed and verified may a successor emit
the new policy. Its rollback must be the deployed reader, and it must be tested
on the actual long-chat and required-source controls before and after release.
The separately observed selected-source Graph-query and App-catalog acquisition
is not solved by this slice.
