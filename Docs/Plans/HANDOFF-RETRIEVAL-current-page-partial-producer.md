# RETRIEVAL: Answer from an incomplete current page

Status: ACTIVE. User authorization covers the over-retrieval lane and reviewed
deployment. Serial successor to reader PR #4922, merged as
`7969a5d8862dcbd440aa463f9da980c338f7805c` on
`codex/coverage-capability-serving-base`; branch
`codex/current-page-partial-producer`. Deploy the reader before the producer.

An exclusive saved-current-page question should return a cited answer for
what the page supports and identify missing details, without searching other
sources or editing a page. A signed-in test on The Memory Ferry instead stopped
after the coverage vote required further evidence. No missing read, access
failure, provider failure or unknown result may become a partial success.

Scope: enable admission of the reader's exact current-page partial terminal;
allow it past current-page source preparation without invoking the native
source owner; focused tests and this brief. Expected files:
`writer_evidence_selection.py`, `build_pending_source.py`,
`plan_jev_writer.py`, and `test_build_current_page_direct.py`. The ordinary
partial replay returned a cited supported fact but only a generic limitation;
the writer guidance therefore must identify an explicitly open requested detail
from the selected page without claiming absence in other sources. Open serving PR #4884 was checked at
`4eea4fe1c7ff`; these files do not overlap its changed-file list.

Verify fresh and persisted terminals, exact source and incomplete/foreign
failure cases, and no native-owner call. Reuse the already-owned one-clone App
fixture for an ordinary captured run, verify the installed reader can read its
result, then independently review the exact head. The later release uses the
current live parent and GitHub Actions, with a signed-in current-page smoke.
Partial acquisition probes remain unknown for unobserved owners.
