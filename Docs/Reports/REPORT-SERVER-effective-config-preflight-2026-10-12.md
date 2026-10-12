# SERVER — explicit effective configuration preflight

PRIME authorized this final preparation check after accepting PR #1096 at merge
`3e831bc367882ff41e8859c3367c6390c2581662`, exact head
`d77f73487d975678f5e9751b4e078fe81d71aef2`, review `6129657061`.
It grants no runtime activation, listener, provider or database connection.

The initial accepted candidate is preserved clean detached at
`fad78a85d710f560bc297f867b6e3c1fa4f0940e` in
`/tmp/buddy-runtime-candidate-20261012`, with its accepted separate locked
environment, Core `13143455`, and built UI. Later main changes only documented
preparation evidence. No private configuration file was copied into the candidate.

## Explicit constructor and observed result

The accepted initial [constructor/probe](evidence/server-effective-config-preflight-2026-10-12/effective_config.py)
is the baseline for the controlled Core115 successor. It constructed the initial checkpoint environment in memory. It retains only
basic OS settings, excludes ambient credentials/DSNs/model overrides/venv and
Python-path selectors, checks the exact code pin and absence of incidental dotenv
files, and loads these existing owner-private files without interpolation:

1. Buddy settings and dedicated model key from
   `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/.env`.
2. APP override from
   `/home/drakosfire/.local/state/dungeonmindbuddy/runtime-config/dogfood-current-main.env`.
3. Retained Native override from
   `/home/drakosfire/.local/state/dungeonmind/recovery/native-live-20261011/dogfood-runtime.env`.
4. The existing strict six-field operator profile validator loads
   `/home/drakosfire/.local/state/dungeonmindbuddy/runtime-config/dogfood-local-operator.env`.

This ordering replaces Buddy's older Native database setting with the exact
retained authority. `DUNGEONBUDDY_OPENAI` is the dedicated source for
`OPENAI_API_KEY`; an incidental shell key is never selected. Fixed artifact,
managed, session/profile roots and existing launcher ports/settings complete
the environment. File ownership/mode checks and the existing operator validator
fail closed. The constructor neither prints nor persists configuration values.

One isolated candidate process passed the actual configuration/auth/policy checks:

- Actual Native authority mode: `dungeonmind`; Native identity: 127.0.0.1:54330 / `dungeonmind_cutover_live_restore_20261011`.
- APP identity: 127.0.0.1:54331 / `dungeonbuddy_application_state`; its actual
  DSN loader validated separation from Native authority without connecting.
- Artifact and managed roots resolve to the primary Buddy data repository.
- Session root remains exactly
  `/tmp/buddy-automatic-chat-reconciliation/evals/c2_live_prep/live/session_22`;
  profile root remains its `hermes_agent_profiles` child.
- Actual local-operator mode, token-presence boolean and loopback GM bearer
  validation passed in memory. No HTTP request or auth-store write occurred.
- Dedicated Buddy model-key presence and selection booleans passed. Actual
  credential-required policy resolved `openai-api` / `gpt-6-luna` without a
  provider call. This proves configuration presence, not remote key validity.
- Private configuration byte hashes before/after matched. No listener,
  database connection, provider request or operator-state mutation occurred.

[Receipt](evidence/server-effective-config-preflight-2026-10-12/effective-config.json)
SHA-256: `188c2f45897669b022b411be285508ff456a0910543a7d649a3e198911344f4c`.
It contains only paths, authority/model identities, booleans and whole-file
integrity hashes. No credentials, key values or source/provider bodies occur.
Constructor SHA-256:
`b78ba91857a8a4a59a287e3b75811c8299c7e89f66bca13145cf1d0786603f2b`.

The current Core115 successor and controlled constructor delta are recorded in `REPORT-SERVER-isolated-runtime-prep-2026-10-12.md`; the following recipes now target that successor.

## Current Core115 conditional launcher recipe

These commands are **not executed**. They require PRIME's fresh quiet authority,
current owned-group/port proof, draft/working-state and open-turn/action checks,
private-file hash verification, and the accepted preservation snapshot. Coordinate
the existing #1014 rollout lane. After that separate authority, create the
candidate-owned log directory and stop only the freshly verified owning group.
Verify all three listeners close before invoking the existing launcher.

The actual candidate recipe now explicitly constructs its private environment:

```bash
cd /tmp/buddy-runtime-candidate-core115-20261012
nohup setsid .venv/bin/python - > .run/launcher.log 2>&1 <<'PY' &
import hashlib, os, sys
from pathlib import Path
loader = Path('/tmp/buddy-core115-candidate-prep-20261012/effective_config.py')
assert hashlib.sha256(loader.read_bytes()).hexdigest() == '69f323d1a3192e41b94271abd1e6a38dcf9a18e80f789f5cb8254fbb3b271efb'
sys.path.insert(0, str(loader.parent))
from effective_config import build_environment, CANDIDATE
env = build_environment(CANDIDATE)
os.chdir(CANDIDATE)
os.execve(str(CANDIDATE / 'run'), ['./run'], env)
PY
```

The constructor pins Node 22.23.0, managed World `elderwyld`, ports
5202/8000/7860, unchanged private operator profile and data roots,
`RUN_NO_RELOAD=1`, and `UV_NO_SYNC=1`. It selects the prepared candidate's local
environment for Buddy and leaves the Web API's owning environment selection
unchanged. Explicit old session/profile roots preserve continuity without file
copying or two simultaneous pointer writers. No global `UV_PROJECT_ENVIRONMENT`
or `PYTHONPATH` is inherited into `./run`.

Before any product/provider activity, rollback under unchanged-state proof uses
the original checkout and `.venv` link:

```bash
cd /tmp/buddy-automatic-chat-reconciliation
nohup setsid .venv/bin/python - > .run/launcher.log 2>&1 <<'PY' &
import hashlib, os, sys
from pathlib import Path
loader = Path('/tmp/buddy-core115-candidate-prep-20261012/effective_config.py')
assert hashlib.sha256(loader.read_bytes()).hexdigest() == '69f323d1a3192e41b94271abd1e6a38dcf9a18e80f789f5cb8254fbb3b271efb'
sys.path.insert(0, str(loader.parent))
from effective_config import build_environment, ROLLBACK
env = build_environment(ROLLBACK)
os.chdir(ROLLBACK)
os.execve(str(ROLLBACK / 'run'), ['./run'], env)
PY
```

The constructor enforces rollback head
`98f0c225066fff9ec836b05ac7d78e0de983e8ff` and the same preserved roots/config.
Stop only the verified candidate group and prove empty ports before rollback.
Never reset/clean the old checkout, restore DB data or erase continuity state.
Changed product/provider lifecycle state requires a new PRIME decision rather
than automatic rollback to the old event contract.

Effective-configuration preparation passes. SERVER is idle pending fresh quiet
state/activation authority and the separately funded full World/readiness-story
phase. The running stack remains untouched; no operator dogfood invitation follows.
