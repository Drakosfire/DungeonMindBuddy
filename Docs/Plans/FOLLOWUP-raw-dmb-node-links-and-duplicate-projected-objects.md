# Follow-up investigation: raw dmb-node links and duplicate projected objects

## Trigger

Manual review of PR #272 surfaced raw projected markdown-style links such as `[Edge](dmb-node:organization_edge)` and duplicate projected labels such as multiple entries for “the wall.” This appears to be a projection/rendering/data-quality issue, not only a selected-object interaction issue.

## Questions to answer

- Why are edge-like objects rendering as node links?
- Should edges be rendered differently from nodes in projected prose?
- Are duplicate labels coming from extraction, projection, fixture data, or rendering?
- Can duplicate same-label objects be disambiguated in the UI without implying identity merge?

## Non-goals

- Do not implement identity merge.
- Do not imply duplicate labels are automatically the same object.
- Do not change prepare/commit/verify write semantics as part of the investigation.

## Expected output

Produce a short diagnosis with concrete examples, source layer attribution, and a scoped fix recommendation for a later PR.
