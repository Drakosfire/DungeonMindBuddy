# ONBOARD: show Gazetteer evidence review

Status: ACTIVE under the owner's Sizzek ingestion goal. Serial product slice on
`codex/onboard-gazetteer-review`, based on current main after #4548. Production
Winter Gazetteer run `b6e91d8e-21e9-59fb-b16c-f559dd373c8b` completed and was
recovered, but its invalid evidence caused Build to call the frozen-span
correction endpoint, which only supports the focused-lore profile. The resulting
error hid the entire review.

Outcome: show the exact Gazetteer review and its invalid-evidence warnings while
making clear that inline quote correction is unavailable for that profile. Keep
publication blocked when evidence is invalid. Preserve focused-lore correction,
Recap, World and exact-source checks, and manual authoring. Write lease: this
handoff, BuildRunReview and its focused tests. No backend, World or live runtime
writes are leased. Verify at the component boundary, then exact-SHA frontend
hosted and discovered diagnostics and Bugbot review. The owner authorizes merge
and a subsequent separate serving-line integration and deployment.
