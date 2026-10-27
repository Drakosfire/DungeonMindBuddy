# INGEST — adopt reviewed OpenAI native schema projection

Status: ACTIVE serial dependency adoption. PRIME owns branch
`codex/adopt-openai-schema-projection` in the existing Buddy checkout, base
`b368c903d30c87865d25ce9d2bd5af66a5f4b927`.

ADVERSARY's original ordinary c1-s01/Luna cell failed with HTTP400 because OpenAI
rejects nested `uniqueItems` in the native schema. Preserve that failure and
all comparison controls. GE#30 owns the fix, merge
`5c3c67cd5a088242f6a28421be0951e834cef2f8`, reviewed head
`55807f82aa2fc6b4c769a7ef2c2c744f2c7218ba`, independent APPROVE,
405 provider-free tests plus Python3.11/3.13 test/build/wheel CI passed.

Invariant: only OpenAI wire schema projection changes. Original consumer schemas,
local GE uniqueness validation/repair, source authority, model targets, prompts,
pass sequence, semantic acceptance and benchmark gold stay unchanged. The actual
captured schema offline replay differs only by the rejected uniqueness keyword.
No fallback or new retries. Do not mask any subsequent provider/validation failure.

Exclusive writes: pyproject.toml, uv.lock (GE revision only), this handoff and
HANDOFF-INGEST-explicit-ge-targets.md (settle delivered predecessor). No concurrent
lockfile writer; previous explicit-target lease settled. No runtime source edits,
new dependencies, migrations, test fixture/schema or benchmark environment writes.

Verify lock metadata and unrelated package identity, existing bounded/advisory/
registered-source/worker/Plan writer consumer tests against exact GE source,
cumulative diff and independent Bugbot. Push/open the owning PR, hosted gates,
PRIME merge and protected immutable API delivery. Primary APP/native data and
corpus/drafts remain protected. No live calls here. Hand exact merged owner pins
to ADVERSARY for its independent comparison readiness and rerun; local tests do
not establish model quality or completed adventure acceptance. Lease ends on merge.
