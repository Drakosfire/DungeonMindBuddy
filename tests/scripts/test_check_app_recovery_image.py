"""Safety checks for building from the reviewed runtime image."""
import json
import subprocess
import sys
from unittest.mock import patch

import pytest

from scripts import check_app_recovery_image as builder

SHA = "a" * 40
IMAGE_ID = "sha256:" + "b" * 64


def invoke(label, tags=""):
    def fake_run(*args):
        if args[0] == "git":
            return SHA + "\n"
        if args[2] == "inspect":
            return json.dumps([{"Id": IMAGE_ID, "Config": {"Labels": {"org.opencontainers.image.revision": label}}}])
        return tags
    with patch.object(sys, "argv", ["builder", SHA, SHA, "runtime"]), patch.object(builder, "run", fake_run), patch.object(subprocess, "run") as execution:
        with pytest.raises(SystemExit):
            builder.main()
        assert not execution.called


def test_rejects_runtime_with_wrong_revision_before_build():
    invoke("c" * 40)


def test_rejects_existing_output_tag_before_build():
    invoke(SHA, f"buddy-app-recovery:{SHA}-{SHA}\n")
