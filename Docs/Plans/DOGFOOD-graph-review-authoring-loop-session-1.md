# Dogfood checklist — Graph Review human-authored gold loop, longmont-c1/session-1

- **campaign:** longmont-c1
- **session:** session-1
- **surface:** Graph Review Workbench
- **goal:** stage, prepare, commit, reload, verify, inspect
- **mode:** Human-authored Author Draft only; no LLM assist and no identity merge.

Use this checklist to dogfood the complete editorial loop:

```text
Read projected prose → switch to Author Draft → stage node / edge / link intent → accept locally → prepare write preview → commit prepared preview → reload gold projection → verify committed changes → inspect committed object in gold lane
```

| Step | Action | Expected result | Actual result | Notes |
| --- | --- | --- | --- | --- |
| 1 | Open the Graph Review Workbench for `longmont-c1 / session-1`. | Review mode is the default; the gold and live lanes remain read-only. |  |  |
| 2 | Switch to Author Draft. | The workflow reads as: 1. Local staged proposals; 2. Prepare preview; 3. Commit prepared preview; 4. Verify committed changes. |  |  |
| 3 | Select prose in a projection lane and stage a node from the selected span. | A local staged node proposal appears; copy says draft-only and no gold fixture, graph state, or corpus file changed. |  |  |
| 4 | Click a graph pill/object and stage a node assertion. | A local node assertion proposal appears without writing files. |  |  |
| 5 | Select/use two graph objects and stage a relationship. | A local relationship proposal appears with source and target clear enough to review. |  |  |
| 6 | Use the resolver from a selected object and stage a resolver link intent. | A link-intent proposal appears as a proposal only; no identity link was written. |  |  |
| 7 | Accept one or more staged local proposals. | Accepted proposal counts update and rejected proposals are not included in the prepared write preview. |  |  |
| 8 | Click **Prepare write preview**. | Preview prepares read-only; status says “Preview prepared. No files were changed.” |  |  |
| 9 | Inspect prepare diagnostics and operation cards. | Blocking diagnostics prevent commit controls; ready previews show proposed operations and gold-shaped payload details remain collapsed by default. |  |  |
| 10 | Confirm the commit checkbox. | The commit button becomes available only after explicit confirmation. |  |  |
| 11 | Click **Commit prepared preview** once. | The gold fixture is written, a backup/event path is shown, and the button is disabled during loading and after success to prevent duplicate submission. |  |  |
| 12 | Click **Reload gold projection**. | Gold projection reloads and verification begins for committed operations. |  |  |
| 13 | Review verification statuses for add-node, add-edge, and event-only operations. | Projection-visible objects show `found_in_gold_projection`; fixture-only/event-only/missing statuses are named honestly; event-only link intent says “No identity link was written.” |  |  |
| 14 | Click **Show authored:node:…** for a projection-visible committed node. | The gold lane selects that node and the normal lane-aware selected-object card opens for the gold object. |  |  |
| 15 | Confirm stale/non-projection operations do not have **Show** actions. | Fixture-only, event-only, missing, not-expected, and stale projection results do not render a Show button. |  |  |
| 16 | Change a proposal after a prepared or committed preview. | Prepared preview, commit controls, commit response, and verification response clear until a fresh preview is prepared. |  |  |
| 17 | Try a blocked prepare. | Commit controls stay hidden and the panel continues to say no files were changed. |  |  |
| 18 | Reset the local draft. | Local proposals, selected text, relationship source, prepared response, commit response, verification response, and commit confirmation clear. |  |  |
| 19 | Scan visible copy for forbidden language. | No “LLM confirmed,” “identity resolved,” “canon merged,” “auto-promoted,” “save all,” or “apply changes” language appears. |  |  |
