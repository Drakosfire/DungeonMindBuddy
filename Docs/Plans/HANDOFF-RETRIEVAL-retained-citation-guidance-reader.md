# RETRIEVAL: read explicit retained-citation routing

Status: MERGED as `4816694498f3f9f34799758abd42c18175540712` in #4962;
deployment and verification are the producer's prerequisites. Base serving revision
`66f685b983e1b8d9b76e42cf14c3be69111bb11b`; branch
`codex/retrieval-retained-citation-guidance-reader`. The user authorized the
over-retrieval goal, reviewed merges and Actions deployment.

A signed-in turn asked to cite an already-read saved page and explicitly
prohibited new searches and reads. The stored work decision chose
`source_lookup`; the turn then recorded one App catalog discovery and two
related-page reads. Current source-need wording says that a citation can call
for lookup while separately saying explicit reuse is anchored. The captured
controller request included both instructions and the prior dialogue.

This slice only makes stored-question readers accept a new exact routing
question that removes the ambiguity: citing previously supplied evidence under
an explicit no-new-source request is anchored; a genuinely fresh lookup remains
source lookup. Preserve every previous exact question and vote validation, ties,
history and current-page distinction. Do not emit the new question yet, change
the routing decision or authorize a source read. A later producer must refuse
to invent missing evidence and must not quietly search if retained evidence is
insufficient.

Write lease: this handoff, the source-need question reader and focused tests.
Verify new and historical exact questions, option sets, altered requests, tied
and invented votes, plus unchanged producer output. Independently review the
exact head. Deploy and verify the reader before a serial producer; the producer
must prove ordinary no-search and fresh-source behavior with the dedicated
negative benchmark and signed-in app, and retain partial-capture limitations.
