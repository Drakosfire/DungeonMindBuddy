# Reply retrieval replay

ACTIVE under the user’s reply-trace redesign goal. Serial successor to merged #4625 at `c76aff0a2648483dc99114f9b367a3bfee32589d`. Work in the graph-timeline-layouts checkout on `codex/reply-trace-replay`.

Own BuddyRetrievalReplay, its presentation styles and tests, the replay disclosure integration and this handoff. Keep recorded arrows, label the current step and its endpoints, make the step list available alongside playback, and inspect a node without changing the selected step. Keep excluded nodes distinguishable after the exclusion step. Report missing candidate reasons explicitly and retain reasons the capture does establish. Treat reconstructed discovery frames and playback timing as presentation. Preserve World, attempt, revision and visibility checks.

Verify historical traces, excluded candidates, step jumps, keyboard focus and nested dialogs. Run the exact-commit hosted verifier and compare the full diagnostic against the verified baseline where applicable. Dogfood the integrated exact code on 5202 using the Elderwyld Mossglade turn, including exact citation access without playback, narrow-panel usability and a representative long replay. Coordinate with the existing 5202 runtime owner before changing its checkout or API target.
