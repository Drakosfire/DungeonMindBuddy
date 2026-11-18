import json
from unittest.mock import Mock

import pytest

from scripts import retire_buddy_release as retirement


def container(identifier, image, status, project="pilot"):
    return {
        "Id": identifier,
        "Image": image,
        "State": {"Status": status, "Running": status == "running", "Health": {"Status": "healthy"}},
        "Config": {"Labels": {"com.docker.compose.project": project, "com.docker.compose.service": "buddy"}},
    }


@pytest.mark.parametrize("case", ["plan", "apply", "absent", "foreign", "running", "rollback"])
def test_retirement_is_scoped_to_the_approved_release(monkeypatch, case):
    tag = "dungeonmindbuddy:" + "a" * 40
    candidate = "rollback" if case == "rollback" else "retired"
    records = [
        container("live", "serving", "running"),
        container("old", candidate, "running" if case == "running" else "exited",
                  "other" if case == "foreign" else "pilot"),
    ]
    responses = {
        ("ps", "-aq", "--no-trunc"): "live\nold",
        ("container", "inspect", "live", "old"): json.dumps(records),
        ("image", "inspect", "rollback"): "{}",
        ("image", "ls", "--format", "{{.Repository}}:{{.Tag}}", "dungeonmindbuddy"): "" if case == "absent" else tag,
        ("image", "inspect", "--format", "{{.Id}}", tag): candidate,
        ("system", "df"): "inventory",
        ("container", "rm", "old"): "old",
        ("image", "rm", "--no-prune", tag): "retired",
    }
    docker = Mock(side_effect=lambda *args: responses[args])
    monkeypatch.setattr(retirement, "docker", docker)
    monkeypatch.setattr(retirement.subprocess, "run", Mock())
    if case in {"foreign", "running", "rollback"}:
        with pytest.raises(ValueError):
            retirement.retire("pilot", tag, "serving", "rollback", apply=True)
    else:
        retirement.retire("pilot", tag, "serving", "rollback", apply=case != "plan")
    removals = [call.args for call in docker.call_args_list if call.args[1] == "rm"]
    assert removals == ([("container", "rm", "old"), ("image", "rm", "--no-prune", tag)] if case == "apply" else [])
