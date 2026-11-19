# CLEANUP: retire historical correction checkout copies

Status: ACTIVE bounded assignment under the user's cleanup goal. This lease
ends when the assigned PR merges or closes; it grants no successor work.
Base: `241da54e96965a43909e20c0018b8523a81a80d2`. Serial, one PR, no unmerged parent.

Outcome: remove only 11 unused duplicate correction payload files (591,922
bytes), preserving exact Git recovery and their historical semantic contracts.
Fresh remote retrieval reproduced every byte at `30008dc473bd80144a46c035d09b56ad1deb2928` before deletion.
Independent caller review covered current source, 99 open PRs and 200 registered
worktrees; no maintained executable package reader or conflicting write lease.

Writes: the 11 tracked JSON files under `graph_data/approved_graph_corrections/`;
`graph_data/README.md`; new `graph_data/historical-corrections.sha256`; this brief;
historical handoffs containing that directory name (recovery/pinned-source note
only). No historical payload bytes, current runtime, fixtures or active branch
contents are changed. Original private World/source trees remain read-only.

Verify fresh remote byte recovery, documented restore and failure cleanup,
historical package replay/tests with explicitly recorded environment/input
limits, current runtime file-reader/provenance boundaries, net checkout bytes,
local links, exact-source hosted verifier and independent cumulative review.
Git recovery alone does not qualify semantics or authorize publication. #3588
owns the disposition and evidence. No deployment/provider/production write.
