"""Owner readbacks for the provider-free mounted Play Choice capture."""

import json
import re
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
        if not isinstance(value, str) or not re.fullmatch(kind + r":[A-Za-z0-9][A-Za-z0-9._:-]*", value):
            raise ValueError("Invalid Play " + kind + " pin")


def read_choice_state(client, folder, name, world, spec, template):
    from application_state.content.service import current_committed_revision, exact_committed_revision

    run_path = "/api/live/world-play-runs/v2/" + spec["run_id"]
    run = response_envelope(client.get(run_path, params={"world_id": world}).raise_for_status())
    plan_id = template["primary_work"]["object_id"]
    exact = exact_committed_revision(plan_id, run["body"]["playable_revision"], kind="plan",
                                     expected_world_id=world,
                                     expected_sha256=run["body"]["playable_content_sha256"])
    if str(exact.work_revision.work_revision_id) != run["body"]["playable_work_revision_id"]:
        raise ValueError("Run does not bind the exact sealed Plan revision")
    plan = current_committed_revision(plan_id, kind="plan")
    pin = {"object": plan.work_object.model_dump(mode="json"),
           "revision_id": str(plan.work_revision.work_revision_id),
           "sha256": plan.work_revision.content_sha256,
           "sealed_revision_id": str(exact.work_revision.work_revision_id),
           "sealed_sha256": exact.work_revision.content_sha256}
    active_path = "/api/live/world-play-runs/v2/active"
    active = response_envelope(client.get(active_path, params={"world_id": world}).raise_for_status())
    immutable_save(folder, name, {"run": run, "plan": pin, "active": active})
    return run["body"], pin, active["body"]


def record_choice_result(folder, output, before, after, spec, driver_failed, turn_posts, rejected_writes):
    timing = output / "browser-timing.json"
    observed = json.loads(timing.read_bytes()).get("play_choice") if timing.is_file() else None
    original, plan_before, active_before = before
    reopened, plan_after, active_after = after
    expected = {**original["progress"], "selections": {
        **original["progress"]["selections"], spec["choice_id"]: spec["option_id"]}}
    checks = {
        "single_mounted_choice": bool(observed and observed["progress_puts"] == 1
                                      and observed.get("reopened_selected") and observed.get("response_status") == 200),
        "exact_run_effect": reopened["run_revision"] == original["run_revision"] + 1
            and reopened["progress"] == expected
            and all(reopened[key] == original[key] for key in (
                "run_id", "world_id", "playable_artifact_id", "playable_revision",
                "playable_work_revision_id", "playable_content_sha256", "lifecycle_status")),
        "plan_unchanged": plan_before == plan_after,
        "active_run_unchanged": active_before == active_after,
        "no_unrelated_writes_attempted": not rejected_writes,
        "no_assistant_send": bool(observed and observed["turn_posts"] == turn_posts == 0),
    }
    immutable_save(folder, "fixture-result", {
        "status": "observed" if all(checks.values()) and not driver_failed else "incomplete",
        "checks": checks, "browser": observed, "rejected_writes": rejected_writes,
    })



def read_play_turn_state(client, folder, name, world, template):
    from application_state.content.service import current_committed_revision, exact_committed_revision

    work = template["primary_work"]
    path = "/api/live/world-play-runs/v2/" + work["object_id"]
    state = {}
    for key, suffix in (("run", ""), ("content", "/content"), ("proposals", "/content/proposals")):
        state[key] = response_envelope(client.get(path + suffix, params={"world_id": world}).raise_for_status())["body"]
    run = state["run"]
    plan = current_committed_revision(run["playable_artifact_id"], kind="plan")
    sealed = exact_committed_revision(run["playable_artifact_id"], run["playable_revision"], kind="plan",
                                      expected_world_id=world, expected_sha256=run["playable_content_sha256"])
    if str(sealed.work_revision.work_revision_id) != run["playable_work_revision_id"]:
        raise ValueError("Play turn Run lacks its exact sealed Plan")
    state["plan"] = {"object": plan.work_object.model_dump(mode="json"),
                     "revision_id": str(plan.work_revision.work_revision_id),
                     "sha256": plan.work_revision.content_sha256}
    state["active"] = response_envelope(client.get("/api/live/world-play-runs/v2/active",
                                                   params={"world_id": world}).raise_for_status())["body"]
    immutable_save(folder, name, state)
    return state


def validate_play_turn_state(state, template):
    work, target = template["primary_work"], template["play_target"]
    run, content, active = state["run"], state["content"], state["active"]
    world_id = template["owner_scope"]["world_id"]
    if (run["run_id"] != work["object_id"] or run["world_id"] != world_id
            or content["run_id"] != run["run_id"] or content["world_id"] != world_id
            or active["run_id"] != run["run_id"] or active["world_id"] != world_id
            or run["lifecycle_status"] != "active" or run["run_revision"] != work["expected_revision"]
            or content["observed_run_revision"] != run["run_revision"]
            or any(work["play_content_basis"][key] != content[key]
                   for key in ("edition_revision", "edition_revision_id", "content_sha256"))
            or run["progress"]["current_scene_id"] != target["scene_id"]
            or run["progress"]["current_beat_id"] != target["beat_id"]):
        raise ValueError("Play turn input differs from the active Run, edition or scene")
