"""Owner readbacks for the provider-free mounted Play Choice capture."""

import json
from uuid import UUID

from .artifacts import immutable_save
from .workflow import response_envelope


def validate_play_choice(spec):
    if not isinstance(spec, dict) or set(spec) != {"run_id", "revision", "scene_id", "choice_id", "option_id"}:
        raise ValueError("Play Choice requires one exact Run revision, scene, Choice and option")
    if str(UUID(spec["run_id"])) != spec["run_id"] or type(spec["revision"]) is not int or spec["revision"] < 1:
        raise ValueError("Invalid Play Run pin")
    for kind in ("scene", "choice", "option"):
        value = spec[kind + "_id"]
        if not isinstance(value, str) or not value.startswith(kind + ":") or len(value) == len(kind) + 1:
            raise ValueError("Invalid Play " + kind + " pin")


def read_choice_state(client, folder, name, world, spec, template):
    from application_state.content.service import current_committed_revision

    run_path = "/api/live/world-play-runs/v2/" + spec["run_id"]
    run = response_envelope(client.get(run_path, params={"world_id": world}).raise_for_status())
    plan = current_committed_revision(template["primary_work"]["object_id"])
    pin = {"object": plan.work_object.model_dump(mode="json"),
           "revision_id": str(plan.work_revision.work_revision_id),
           "sha256": plan.work_revision.content_sha256}
    immutable_save(folder, name, {"run": run, "plan": pin})
    return run["body"], pin


def record_choice_result(folder, output, before, after, spec, driver_failed, turn_posts):
    timing = output / "browser-timing.json"
    observed = json.loads(timing.read_bytes()).get("play_choice") if timing.is_file() else None
    original, plan_before = before
    reopened, plan_after = after
    expected = {**original["progress"], "selections": {
        **original["progress"]["selections"], spec["choice_id"]: spec["option_id"]}}
    checks = {
        "single_mounted_choice": bool(observed and observed["progress_puts"] == 1
                                      and observed["reopened_selected"] and observed["response_status"] == 200),
        "exact_run_effect": reopened["run_revision"] == original["run_revision"] + 1
            and reopened["progress"] == expected
            and all(reopened[key] == original[key] for key in (
                "run_id", "world_id", "playable_artifact_id", "playable_revision",
                "playable_work_revision_id", "playable_content_sha256", "lifecycle_status")),
        "plan_unchanged": plan_before == plan_after,
        "no_assistant_send": bool(observed and observed["turn_posts"] == turn_posts == 0),
    }
    immutable_save(folder, "fixture-result", {
        "status": "observed" if all(checks.values()) and not driver_failed else "incomplete",
        "checks": checks, "browser": observed,
    })
