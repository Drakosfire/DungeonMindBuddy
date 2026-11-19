# Open the exact saved conversation variant

ACTIVE under the ordinary Meat Mind workflow goal. Serial successor to #3828.
Base 2fe2bf4d7a0bdf50578ea208d7ff8dbfdecfa9f0, branch codex/aw-saved-variant-readback,
isolated checkout aw-conversation-drafts. Open statblock PRs #3716, #3808, #3729,
and hosted integration #3824 were checked. Use existing World draft authorization
and exact mechanics verification.

Own the conversation variant receipt reader and the matching application-state
service, scoped HTTP endpoint, API transport and review link, plus their tests.
Verify scoped access, absent and pending receipts, exact saved revision and
digest, and that reopen performs no mutation. Keep primary data unchanged and
run owning tests in the disposable AW database. Edge linking and Combat
admission follow this slice serially.
