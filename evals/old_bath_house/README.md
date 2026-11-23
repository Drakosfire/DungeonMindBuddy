# Old Bath House performance checks

The pinned-assets runner starts the exact Buddy image from the fixture
on loopback, using a disposable App database, a restricted read-only
Core login, and a disposable local statblock service. It launches a
fresh Chromium context. Stage owned copies of managed World, artifacts
and sessions before the run. Each replay needs its own clean Plan scene
and a fresh App database if it will repeat encounter attachment.

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
