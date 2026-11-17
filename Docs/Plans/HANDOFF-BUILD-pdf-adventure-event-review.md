# BUILD: Publish a reviewed PDF passage as a prep Event

ACTIVE serial implementation on `codex/pdf-adventure-event-review`, based on
`0bdc7c91151a60ae01cc5b1e9c9b013c3ecea281`. The active adventure benchmark goal
authorizes implementation. The acceptance contract is pinned in [#3737 at
e692fa5](https://github.com/Drakosfire/DungeonMindBuddy/blob/e692fa5ee/evals/adventure-to-follow-up-benchmark.md#first-hill-climb-slice-save-one-reviewed-pdf-passage-as-prep).
Dependencies are the existing PDF and WorldKeeper contracts on the base.

One retained, source-bound PDF region enters an editable review in Build.
Prepare may register its exact evidence. Only explicit confirmation publishes
the Event with provisional Plan claims. Bind reviewed content, citation, GM,
World binding and parent Graph revision. A stale or changed review fails closed.
Retry uses the same operation and recovers its exact receipt. Graph readback
must reopen the cited PDF region.

Write scope covers the dedicated PDF Event route, service and review UI,
their focused tests, their entries in the test classification inventory, and registration hooks in the local application and PDF
preview. Reuse the PDF evidence registration helper with the existing creature
consumer. Open #3196 owns PDF upload validation and #3664 owns Build shell
navigation. Keep their files outside this slice. Use disposable databases and
provider-free owner and browser checks for confirmation and retries.

The benchmark PR owns Gold and fixture evidence. This product slice contains
generic behavior and synthetic tests.
