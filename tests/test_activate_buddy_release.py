"""Test the production entry point against a disposable Compose command double."""

from pathlib import Path
import os
import subprocess

import pytest


CANDIDATE = "a" * 40
ROLLBACK = "b" * 40
CANDIDATE_ID = "sha256:" + "a" * 64
ROLLBACK_ID = "sha256:" + "b" * 64
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cutover(tmp_path):
    releases = tmp_path / "releases"
    releases.mkdir()
    (tmp_path / "compose.conf").write_text(
        "compose=(docker compose)\nupstream=http://127.0.0.1:8080\n"
        "persistent_root=/srv/buddy\n"
    )
    (releases / f"{CANDIDATE}.conf").write_text(
        f"candidate_tag=dungeonmindbuddy:{CANDIDATE}\ncandidate_id={CANDIDATE_ID}\n"
        f"rollback_tag=dungeonmindbuddy:{ROLLBACK}\nrollback_id={ROLLBACK_ID}\n"
        f"rollback_revision={ROLLBACK}\n"
    )
    script = tmp_path / "activate"
    script.write_text(
        (ROOT / "scripts/activate_buddy_release.sh").read_text()
        .replace("/etc/buddy-deploy", str(tmp_path))
        .replace("/run/lock/buddy-production-deploy.lock", str(tmp_path / "lock"))
    )
    state = tmp_path / "serving"
    state.write_text(ROLLBACK_ID)
    log = tmp_path / "activations"
    log.touch()
    stub = tmp_path / "docker"
    stub.write_text(
        """#!/usr/bin/env bash
set -eu
case "$1:$2" in
  image:inspect)
    revision=${@: -1}
    revision=${revision#dungeonmindbuddy:}
    digest=$ROLLBACK_ID
    if [[ "$revision" == "$CANDIDATE" ]]; then digest=$CANDIDATE_ID; fi
    if [[ "$revision" == "$CANDIDATE" && "$MODE" == wrong-image ]]; then digest=$ROLLBACK_ID; fi
    printf '%s %s\\n' "$digest" "$revision"
    ;;
  compose:ps) printf '%s\\n' buddy-container ;;
  compose:port) printf '%s\\n' 127.0.0.1:8080 ;;
  compose:-f)
    [[ "$*" == 'compose -f - up -d --no-deps --no-build --pull never --wait --wait-timeout 330 buddy' ]]
    override=$(cat)
    tag=${override##*dungeonmindbuddy:}
    printf '%s\\n' "$tag" >> "$LOG"
    if [[ "$tag" == "$CANDIDATE" ]]; then
      printf %s "$CANDIDATE_ID" > "$STATE"
      [[ "$MODE" != unhealthy ]]
    elif [[ "$tag" == "$ROLLBACK" ]]; then
      printf %s "$ROLLBACK_ID" > "$STATE"
    else
      exit 2
    fi
    ;;
  inspect:--format) printf '%s healthy /srv/buddy\\n' "$(cat "$STATE")" ;;
  *) exit 2 ;;
esac
"""
    )
    stub.chmod(0o755)
    for command, content in {
        "curl": "exit 0\n",
        "stat": "printf '0 600\\n'\n",
    }.items():
        stub = tmp_path / command
        stub.write_text("#!/usr/bin/env bash\n" + content)
        stub.chmod(0o755)

    def run(revision=CANDIDATE, mode="healthy"):
        env = dict(
            os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}",
            MODE=mode, STATE=str(state), LOG=str(log), CANDIDATE=CANDIDATE,
            ROLLBACK=ROLLBACK, CANDIDATE_ID=CANDIDATE_ID, ROLLBACK_ID=ROLLBACK_ID,
        )
        result = subprocess.run(
            ["bash", str(script), revision], env=env,
            text=True, capture_output=True, timeout=10, check=False,
        )
        return result, log.read_text().splitlines(), state.read_text()

    return run


def test_cutover_and_idempotent_repeat(cutover):
    for _ in range(2):
        result, activated, serving = cutover()
        assert result.returncode == 0, result.stderr
        assert f"BUDDY_LIVE {CANDIDATE} {CANDIDATE_ID}" in result.stdout
        assert activated == [CANDIDATE]
        assert serving == CANDIDATE_ID


def test_candidate_failure_rolls_back_and_fails_workflow(cutover):
    result, activated, serving = cutover(mode="unhealthy")
    assert result.returncode != 0
    assert f"BUDDY_ROLLED_BACK {ROLLBACK} {ROLLBACK_ID}" in result.stderr
    assert activated == [CANDIDATE, ROLLBACK]
    assert serving == ROLLBACK_ID


@pytest.mark.parametrize("revision,mode", [
    ("../../compose", "healthy"), ("c" * 40, "healthy"), (CANDIDATE, "wrong-image"),
])
def test_unapproved_or_mismatched_release_leaves_buddy_running(cutover, revision, mode):
    result, activated, serving = cutover(revision, mode)
    assert result.returncode != 0
    assert not activated
    assert serving == ROLLBACK_ID
