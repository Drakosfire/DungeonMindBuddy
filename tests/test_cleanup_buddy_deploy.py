from datetime import datetime, timezone
import json
import os
from types import SimpleNamespace

from scripts import cleanup_buddy_deploy as cleanup


def test_retention_preserves_rollback_staging_mounts_and_compose(tmp_path, monkeypatch):
    revisions = ["a" * 40, "b" * 40, "c" * 40, "d" * 40]
    tags = [f"dungeonmindbuddy:{revision}" for revision in revisions]
    image_ids = ["sha256:" + revision[0] * 64 for revision in revisions]
    images = {
        tag: {
            "Id": image_id, "Created": f"2025-01-0{index + 1}T00:00:00Z",
            "Config": {"Labels": {"org.opencontainers.image.revision": revision}},
        }
        for index, (tag, image_id, revision) in enumerate(zip(tags, image_ids, revisions))
    }
    release = tmp_path / "buddy-1-releases" / revisions[0]
    removable = release / "src"
    mounted = release / "apps"
    removable.mkdir(parents=True)
    mounted.mkdir()
    (release / "rollout.sh").touch()
    overlay = release / f"compose.release.{revisions[0]}.yaml"
    overlay.touch()
    timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp()
    os.utime(overlay, (timestamp, timestamp))
    container = {
        "Image": image_ids[2],
        "State": {"Running": True, "Health": {"Status": "healthy"}},
        "Config": {"Labels": {
            "com.docker.compose.project": "buddy", "com.docker.compose.service": "buddy",
            "com.docker.compose.project.config_files": str(overlay),
        }},
        "Mounts": [{"Source": str(mounted)}],
    }
    mutations = []

    def docker(*args):
        if args[:2] == ("image", "inspect"):
            return json.dumps([images[args[-1]]])
        if args[:2] == ("image", "ls"):
            return "\n".join(tags)
        if args[:2] == ("ps", "-aq"):
            return "serving"
        if args[:2] == ("container", "inspect"):
            return json.dumps([container])
        if args[:2] in {("image", "rm"), ("buildx", "prune")}:
            mutations.append(args)
            return ""
        raise AssertionError(args)

    monkeypatch.setattr(cleanup, "docker", docker)
    cleanup.cleanup(SimpleNamespace(project="buddy", serving_tag=tags[2], serving_image=image_ids[2],
        rollback_tag=tags[1], rollback_image=image_ids[1], release_root=tmp_path, apply=True))
    assert mutations[0] == ("image", "rm", "--no-prune", tags[0])
    assert len(mutations) == 2 and mutations[1][:2] == ("buildx", "prune")
    assert mounted.is_dir() and overlay.is_file() and not removable.exists()
