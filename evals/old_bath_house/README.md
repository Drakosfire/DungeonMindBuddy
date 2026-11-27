# Old Bath House performance checks

The pinned-assets runner starts the exact Buddy image from the fixture
on loopback, using a disposable App database, a restricted read-only
Core login, and a disposable local statblock service. It launches a
fresh Chromium context. Stage owned copies of managed World, artifacts
and sessions before the run. Each replay needs its own clean Plan scene
and a fresh App database if it will repeat encounter attachment.
The launcher copies the three fixture directories into the new run
directory before mounting them. It rejects symlinks and special files.
The Linux runner uses `setfacl` to grant the unprivileged image user
access to the run copy.

The launcher serves the image's shipped static UI while Buddy runs in
local operator mode. The image's usual frontend route serves those
files only in production mode. API requests still use the image's
Buddy application. Keep the per-run manifest checksum and a stable
`sourceFixtureDigest` for the logical fixture. The latter excludes
disposable database identities and runtime ports.

Prepare the manifest with `python -m evals.old_bath_house.make_fixture`.
It reads the scoped App rows, saved statblock and media export,
Meatling revision lineage and acceptance artifacts, and World binding
metadata in the export directory. Provision new database identities
before generating the manifest. Use `restore_app`, `stage_artifacts`
and `seed_statblocks` for the App rows, artifact tree and disposable
Firestore namespace respectively. The exact exported content stays in
the benchmark evidence directory. The repository carries its source
pins and the fixture tools.

Run from the repository root with the locked Python environment. Supply
the two database DSNs, statblock base URL and internal key, and the
`DMB_BENCHMARK_NODE`, `DMB_BENCHMARK_PLAYWRIGHT` and
`DMB_BENCHMARK_CHROMIUM` paths through the process environment.

```sh
python -m evals.old_bath_house.run \
  --fixture /path/to/fixture.json --fixture-sha256 FIXTURE_SHA256 \
  --output /path/to/new/run-directory
```

The run directory contains browser timings and correctness results in
`run.json` and the pinned server's logs in `buddy.log`. The browser
timers measure the user-visible product boundaries. The Plan confirmation
timer starts at the confirmation click. Preview time is retained alongside
the run. Runtime and fixture preparation fall outside the timing boundary.

Pass arrays of run records to the comparator.

```sh
python -m evals.old_bath_house.compare baseline.json candidate.json
```

Only runs with all required correctness checks and phase measurements enter
timing distributions. Rejections remain visible. Warm and cold conditions
and mismatched fixture digests are reported separately. A percentile is
omitted when the sample count is too small to distinguish it from the maximum.

## Live providers

The live replay uses the same exact Buddy image and signed-in browser, plus
pinned Old Bath House and Corrupted Edge source revisions, the original
Meat Mind statblock, and a read-only copy of the relevant Graph. Supply
OpenAI, Jev and fal credentials through the local operator environment.
Pass `--live-grounding`, `--live-grounding-sha256` and `--live-core-head`
to `make_fixture`. Restore the scoped source-page rows into the disposable
App database and seed the exact original Meat Mind revision in the
disposable statblock service.

```sh
python -m evals.old_bath_house.live_sources \
  --grounding /path/to/live-source-rows.json --sha256 GROUNDING_SHA256 \
  --isolation /path/to/isolation.json
```
Set `DUNGEONBUDDY_JEV_TOKENIZER_FILE` to the exact tokenizer asset required by the
runtime. Portrait generation ends when the browser decodes the private
preview. The replay then binds the existing reviewed portrait to the new
statblock and records both asset IDs. No CDN upload is needed.

The browser checks the visible and terminal replies, confirms a distinct
statblock variant, and follows that variant and the saved portrait through
Plan and Play. A successful live run must also match the server's provider
trace to the browser turns. It applies the same exact-revision and explicit
combat-start checks as the pinned-assets replay. Keep incomplete attempts
as diagnostics. They do not enter the live baseline.

To qualify only the mounted statblock save, set
`live.variantConfirmationOnly` to true in the pinned live fixture. The same
ordinary conversation runs first. The browser then opens the approval on the
final turn, checks that it resolves to the preceding producing turn and the
current unsaved review revision, confirms it, and reads the exact saved locator
back from the owner. This track ends before portrait generation or encounter
setup. A failed review lookup or a changed revision stops before confirmation.

Pass `--verify-linked-variant` to the live runner to verify saved variant
continuation. After confirmation, the browser opens the original Build page
in a fresh tab, inserts the link once, reopens the committed page, then loads
and independently reopens the exact mechanics revision in Combat. The result
records the locator and encounter. This track ends before portrait generation.
