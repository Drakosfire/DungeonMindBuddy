#!/usr/bin/env python3
"""Run only a task-owned native DungeonMind demo, never the normal Buddy server.

No DSN option or ambient database fallback exists. PostgreSQL is private to the
specified data directory and accepts Unix-socket peer authentication only.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import fcntl
import grp
import hashlib
import pwd
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
from urllib.parse import quote

CORE_PIN = "430c1a6db631d097dfa0a273f8933067f708bc56"
WK_PIN = "ef9c50f2d6aa89a35e9408f83fc4d0ba47825ca2"
DATABASE = "dmb_native_graph_demo"
ROOT = Path(__file__).resolve().parents[1]
PGVECTOR_IMAGE_ID = (
    "sha256:9b05db12a35460fff0587e009f9326e414a53e9484555547f96d214a2ba98ef7"
)
PGVECTOR_REPO_DIGEST = "pgvector/pgvector@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b"
PGVECTOR_IMAGE_TAG = "pgvector/pgvector:0.8.6-pg16"
PGVECTOR_IMAGE_PGDATA = "/var/lib/postgresql/data"
PGVECTOR_BIN_DIR = "/usr/lib/postgresql/16/bin"
DOCKER_ENDPOINT = "unix:///var/run/docker.sock"
DOCKER_OWNER_LABEL = "io.dungeonmind.native-demo.owner"
DOCKER_STATE_LABEL = "io.dungeonmind.native-demo.state-sha256"
DOCKER_VERSION_LABEL = "io.dungeonmind.native-demo.runtime-version"


class LaunchBlocked(RuntimeError):
    pass


def verify_runtime_environment() -> None:
    # libpq reads PGHOSTADDR/PGSERVICE/etc in this process even when child
    # processes get a clean environment. Refuse them before any connection.
    if any(key.startswith("PG") for key in os.environ):
        raise LaunchBlocked(
            "The native demo refuses ambient PG* connection settings. Launch it from a clean environment; no connection was attempted."
        )


def postgres_tools(directory: Path | None = None):
    result = {}
    for name in ("initdb", "pg_ctl"):
        value = str(directory / name) if directory else shutil.which(name)
        if not value or not Path(value).is_file() or not os.access(value, os.X_OK):
            raise LaunchBlocked(
                "Dedicated PostgreSQL server tools are unavailable. Provide an authorized PostgreSQL installation with pgvector; no Docker, remote database or production fallback will be used."
            )
        result[name] = value
    return result


def docker_environment(home: Path | None = None):
    """Keep Docker CLI configuration local and omit all caller context overrides."""
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(home or Path.home()),
        "LANG": "C.UTF-8",
    }


def docker_run(args, *, home: Path | None = None, **kwargs):
    """Run the Docker CLI against the local Unix socket with a clean environment."""
    executable = shutil.which("docker", path="/usr/local/bin:/usr/bin:/bin")
    if not executable:
        raise LaunchBlocked(
            "The local Docker CLI is unavailable; no runtime was started."
        )
    return subprocess.run(
        [executable, "--host", DOCKER_ENDPOINT, *args],
        env=docker_environment(home),
        **kwargs,
    )


def verify_docker_image():
    """Verify the exact already-local pgvector image; never resolve or pull a tag."""
    try:
        result = docker_run(
            ["image", "inspect", PGVECTOR_IMAGE_ID],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise LaunchBlocked(
            "The local Docker image could not be inspected; no image pull or container creation was attempted."
        ) from exc
    if result.returncode != 0:
        raise LaunchBlocked(
            "The pinned pgvector image is not available locally; no image pull was attempted."
        )
    try:
        images = json.loads(result.stdout)
        if not isinstance(images, list) or len(images) != 1:
            raise ValueError("expected one image")
        image = images[0]
        config = image["Config"]
        image_env = config["Env"]
        volumes = config["Volumes"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LaunchBlocked(
            "The pinned pgvector image metadata is incomplete."
        ) from exc
    expected_env = [
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/lib/postgresql/16/bin",
        "GOSU_VERSION=1.19",
        "LANG=en_US.utf8",
        "PG_MAJOR=16",
        "PG_VERSION=16.15-1.pgdg12+2",
        f"PGDATA={PGVECTOR_IMAGE_PGDATA}",
    ]
    if (
        image.get("Id") != PGVECTOR_IMAGE_ID
        or PGVECTOR_REPO_DIGEST not in image.get("RepoDigests", [])
        or PGVECTOR_IMAGE_TAG not in image.get("RepoTags", [])
        or config.get("Entrypoint") != ["docker-entrypoint.sh"]
        or config.get("Cmd") != ["postgres"]
        or config.get("User", "") != ""
        or image_env != expected_env
        or volumes != {PGVECTOR_IMAGE_PGDATA: {}}
        or image.get("Os") != "linux"
        or image.get("Architecture") != "amd64"
    ):
        raise LaunchBlocked(
            "The local pgvector image does not match the pinned immutable runtime contract."
        )
    return {"id": PGVECTOR_IMAGE_ID, "env": image_env}


def _private_directory(path: Path, label: str, *, create: bool):
    if path.is_symlink():
        raise LaunchBlocked(f"The {label} directory must not be a symlink.")
    if not path.exists():
        if not create:
            raise LaunchBlocked(f"The {label} directory is missing.")
        path.mkdir(mode=0o700)
    info = path.stat()
    if (
        not path.is_dir()
        or info.st_uid != os.getuid()
        or info.st_gid != os.getgid()
        or info.st_mode & 0o077
    ):
        raise LaunchBlocked(
            f"The {label} directory must be privately owned by this user and group."
        )
    return path.resolve(strict=True)


def _private_file(path: Path, content: bytes | None = None, *, create: bool):
    if path.is_symlink():
        raise LaunchBlocked("Container identity files must not be symlinks.")
    if not path.exists():
        if not create or content is None:
            raise LaunchBlocked("A private container identity file is missing.")
        fd = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    info = path.stat()
    if (
        not path.is_file()
        or info.st_uid != os.getuid()
        or info.st_gid != os.getgid()
        or info.st_mode & 0o077
        or content is not None
        and path.read_bytes() != content
    ):
        raise LaunchBlocked("A private container identity file does not match.")
    return path.resolve(strict=True)


def _write_private_json(path: Path, value: dict):
    if path.is_symlink():
        raise LaunchBlocked("The container ownership record must not be a symlink.")
    temporary = path.with_name(path.name + ".new")
    if temporary.exists() or temporary.is_symlink():
        raise LaunchBlocked(
            "An incomplete container ownership write must be inspected."
        )
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    fd = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        if temporary.exists() and not temporary.is_symlink():
            temporary.unlink()
        raise


def _container_name(state: Path):
    digest = hashlib.sha256(str(state.resolve(strict=True)).encode()).hexdigest()[:20]
    return f"native-graph-demo-{os.getuid()}-{digest}"


def _safe_account_name(value: str):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,30}\$?", value):
        raise LaunchBlocked(
            "The host account name cannot be mapped safely in the container."
        )
    return value


def _container_identity_files(state: Path):
    uid, gid = os.getuid(), os.getgid()
    if uid == 0 or gid == 0:
        raise LaunchBlocked(
            "The isolated container runtime requires a non-root host user."
        )
    user = _safe_account_name(pwd.getpwuid(uid).pw_name)
    group = _safe_account_name(grp.getgrgid(gid).gr_name)
    passwd_path = state / "container.passwd"
    group_path = state / "container.group"
    passwd_bytes = f"{user}:x:{uid}:{gid}:native demo:/:/bin/false\n".encode()
    group_bytes = f"{group}:x:{gid}:{user}\n".encode()
    return (
        _private_file(passwd_path, passwd_bytes, create=True),
        _private_file(group_path, group_bytes, create=True),
    )


def _load_json_file(path: Path):
    if path.is_symlink() or not path.is_file():
        raise LaunchBlocked("The container ownership record is missing or linked.")
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_gid != os.getgid() or info.st_mode & 0o077:
        raise LaunchBlocked("The container ownership record is not private.")
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise LaunchBlocked("The container ownership record is unreadable.") from exc
    if not isinstance(value, dict):
        raise LaunchBlocked("The container ownership record has an invalid shape.")
    return value


def _expected_container_record(state: Path, image: dict):
    state = state.resolve(strict=True)
    name = _container_name(state)
    state_hash = hashlib.sha256(str(state).encode()).hexdigest()
    return {
        "version": 1,
        "uid": os.getuid(),
        "gid": os.getgid(),
        "state_directory": str(state),
        "container_name": name,
        "container_id": None,
        "image_id": image["id"],
        "repo_digest": PGVECTOR_REPO_DIGEST,
        "image_environment": image["env"],
        "data_directory": str(state / "pgdata"),
        "data_target": PGVECTOR_IMAGE_PGDATA,
        "socket_directory": str(state / "s"),
        "passwd_file": str(state / "container.passwd"),
        "group_file": str(state / "container.group"),
        "state_hash": state_hash,
    }


class NativePostgresRunner:
    """Run the existing host-installed PostgreSQL tools without behavior changes."""

    def __init__(self, tools):
        self.tools = tools
        self.started_by_invocation = False

    def data_directory(self, state: Path):
        return state / "pgdata"

    def expected_data_directory(self, state: Path):
        return str(self.data_directory(state).resolve())

    @property
    def containerized(self):
        return False

    def log_file(self, state: Path):
        return state / "postgres.log"

    def prepare(self):
        return None

    def run(self, tool: str, args, **kwargs):
        return subprocess.run([self.tools[tool], *args], **kwargs)

    def close(self):
        return None


class DockerPostgresRunner:
    """Run pinned PostgreSQL tools in one inert, task-owned container."""

    def __init__(self, state: Path, image: dict):
        self.state = state.resolve(strict=True)
        self.image = image
        self.name = _container_name(self.state)
        self.container_id: str | None = None
        self.record_path = self.state / "container-owner.json"
        self.started_by_invocation = False
        self.image_env = image["env"]
        self.labels = {
            DOCKER_OWNER_LABEL: "v1",
            DOCKER_STATE_LABEL: hashlib.sha256(str(self.state).encode()).hexdigest(),
            DOCKER_VERSION_LABEL: "1",
        }
        self.identity_user = _safe_account_name(pwd.getpwuid(os.getuid()).pw_name)
        self.identity_group = _safe_account_name(grp.getgrgid(os.getgid()).gr_name)

    def data_directory(self, state: Path):
        return Path(PGVECTOR_IMAGE_PGDATA)

    def expected_data_directory(self, state: Path):
        return PGVECTOR_IMAGE_PGDATA

    @property
    def containerized(self):
        return True

    def log_file(self, state: Path):
        return Path(PGVECTOR_IMAGE_PGDATA) / "postgres.log"

    def _inspect(self, reference: str):
        try:
            result = docker_run(
                ["inspect", "--type", "container", reference],
                home=self.state,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise LaunchBlocked(
                "The exact task container inspection timed out or failed; preserve its state and do not retry startup blindly."
            ) from exc
        if result.returncode != 0:
            if (
                "No such object" in result.stderr
                or "No such container" in result.stderr
            ):
                return None
            raise LaunchBlocked(
                "The exact task container could not be inspected; preserve its state and do not retry startup blindly."
            )
        try:
            items = json.loads(result.stdout)
            if not isinstance(items, list) or len(items) != 1:
                raise ValueError("expected one container")
            return items[0]
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LaunchBlocked(
                "Docker returned invalid container inspection data."
            ) from exc

    def _validate_inspect(self, info: dict, *, expected_id: str | None = None):
        state = info.get("State", {})
        config = info.get("Config", {})
        host = info.get("HostConfig", {})
        name = info.get("Name")
        container_id = info.get("Id")
        expected_mounts = {
            (
                "bind",
                str(self.state / "pgdata"),
                PGVECTOR_IMAGE_PGDATA,
                True,
                "rprivate",
            ),
            (
                "bind",
                str(self.state / "s"),
                str(self.state / "s"),
                True,
                "rprivate",
            ),
            (
                "bind",
                str(self.state / "container.passwd"),
                "/etc/passwd",
                False,
                "rprivate",
            ),
            (
                "bind",
                str(self.state / "container.group"),
                "/etc/group",
                False,
                "rprivate",
            ),
        }
        try:
            actual_mounts = {
                (
                    mount["Type"],
                    str(Path(mount["Source"]).resolve(strict=True)),
                    mount["Destination"],
                    mount["RW"],
                    mount["Propagation"],
                )
                for mount in info["Mounts"]
            }
            host_mounts = {
                (
                    mount["Type"],
                    str(Path(mount["Source"]).resolve(strict=True)),
                    mount["Target"],
                    mount.get("ReadOnly", False),
                    (mount.get("BindOptions") or {}).get("Propagation"),
                )
                for mount in host["Mounts"]
            }
            unexpected_mount_modes = any(
                mount.get("Mode", "") != "" for mount in info["Mounts"]
            )
        except (KeyError, OSError, TypeError) as exc:
            raise LaunchBlocked(
                "The task container mount identity is incomplete."
            ) from exc
        port_bindings = host.get("PortBindings")
        security_options = set(host.get("SecurityOpt") or [])
        expected_host_mounts = {
            (
                "bind",
                str(self.state / "pgdata"),
                PGVECTOR_IMAGE_PGDATA,
                False,
                "rprivate",
            ),
            (
                "bind",
                str(self.state / "s"),
                str(self.state / "s"),
                False,
                "rprivate",
            ),
            (
                "bind",
                str(self.state / "container.passwd"),
                "/etc/passwd",
                True,
                "rprivate",
            ),
            (
                "bind",
                str(self.state / "container.group"),
                "/etc/group",
                True,
                "rprivate",
            ),
        }
        if (
            expected_id is not None
            and container_id != expected_id
            or name != f"/{self.name}"
            or config.get("Image") != self.image["id"]
            or config.get("User") != f"{os.getuid()}:{os.getgid()}"
            or config.get("Entrypoint") != ["/bin/sleep"]
            or config.get("Cmd") != ["infinity"]
            or config.get("Env") != self.image_env
            or config.get("Labels") != self.labels
            or len(info["Mounts"]) != len(expected_mounts)
            or actual_mounts != expected_mounts
            or len(host["Mounts"]) != len(expected_host_mounts)
            or host_mounts != expected_host_mounts
            or unexpected_mount_modes
            or host.get("NetworkMode") != "none"
            or port_bindings not in (None, {})
            or host.get("PublishAllPorts") is not False
            or host.get("Privileged") is not False
            or host.get("ReadonlyRootfs") is not True
            or (host.get("CapAdd") or [])
            or (host.get("CapDrop") or []) != ["ALL"]
            or security_options != {"no-new-privileges:true"}
            or host.get("PidMode") not in (None, "")
            or host.get("IpcMode") not in ("private", None, "")
            or host.get("UTSMode") not in (None, "")
            or host.get("UsernsMode") not in (None, "")
            or host.get("AutoRemove") is not False
            or (host.get("RestartPolicy") or {}).get("Name") != "no"
            or (host.get("RestartPolicy") or {}).get("MaximumRetryCount") != 0
            or (host.get("Devices") or [])
            or (host.get("DeviceRequests") or [])
            or (host.get("Tmpfs") or {})
            or (info.get("Image") != self.image["id"])
            or info.get("Path") != "/bin/sleep"
            or info.get("Args") != ["infinity"]
            or set((info.get("NetworkSettings", {}).get("Networks") or {}).keys())
            != {"none"}
            or config.get("OpenStdin") is not False
            or config.get("Tty") is not False
            or (host.get("Binds") or [])
            or (host.get("VolumesFrom") or [])
        ):
            raise LaunchBlocked(
                "A task container identity, command, environment, mount or isolation setting differs; it was not adopted or changed."
            )
        return container_id, state.get("Status")

    def _state_dirs(self, *, create: bool):
        data = _private_directory(
            self.state / "pgdata", "PostgreSQL data", create=create
        )
        socket = _private_directory(
            self.state / "s", "PostgreSQL socket", create=create
        )
        if len(os.fsencode(str(socket / ".s.PGSQL.5432"))) >= 104:
            raise LaunchBlocked("The task-owned PostgreSQL socket path is too long.")
        if any(char in str(data) for char in (",", "\n", "\r")) or any(
            char in str(socket) for char in (",", "\n", "\r")
        ):
            raise LaunchBlocked(
                "The task-owned container paths contain unsupported characters."
            )
        return data, socket

    def _create_record(self):
        data, socket = self._state_dirs(create=True)
        if any(data.iterdir()) or any(socket.iterdir()):
            raise LaunchBlocked(
                "A new container cannot adopt non-empty PostgreSQL or socket directories."
            )
        for identity_path in (
            self.state / "container.passwd",
            self.state / "container.group",
        ):
            if identity_path.exists() or identity_path.is_symlink():
                raise LaunchBlocked(
                    "Unowned container identity files exist; inspect task state before retrying."
                )
        passwd_path, group_path = _container_identity_files(self.state)
        expected = _expected_container_record(self.state, self.image)
        expected["passwd_file"] = str(passwd_path)
        expected["group_file"] = str(group_path)
        _write_private_json(self.record_path, expected)
        return expected

    def _load_record(self):
        incomplete = self.record_path.with_name(self.record_path.name + ".new")
        if incomplete.exists() or incomplete.is_symlink():
            raise LaunchBlocked(
                "An incomplete container ownership write must be inspected before reuse."
            )
        value = _load_json_file(self.record_path)
        expected = _expected_container_record(self.state, self.image)
        container_id = value.get("container_id")
        expected["container_id"] = container_id
        if value != expected:
            raise LaunchBlocked(
                "The private container ownership record differs from this task runtime."
            )
        if container_id is not None and not re.fullmatch(r"[0-9a-f]{64}", container_id):
            raise LaunchBlocked("The recorded container ID is not a full immutable ID.")
        user = _safe_account_name(pwd.getpwuid(os.getuid()).pw_name)
        group = _safe_account_name(grp.getgrgid(os.getgid()).gr_name)
        passwd_bytes = (
            f"{user}:x:{os.getuid()}:{os.getgid()}:native demo:/:/bin/false\n".encode()
        )
        group_bytes = f"{group}:x:{os.getgid()}:{user}\n".encode()
        _private_file(self.state / "container.passwd", passwd_bytes, create=False)
        _private_file(self.state / "container.group", group_bytes, create=False)
        self._state_dirs(create=False)
        return value

    def _store_container_id(self, record: dict, container_id: str):
        updated = dict(record)
        updated["container_id"] = container_id
        _write_private_json(self.record_path, updated)
        self.container_id = container_id
        return updated

    def _create_argv(self):
        state = self.state
        mounts = [
            f"type=bind,source={state / 'pgdata'},target={PGVECTOR_IMAGE_PGDATA},bind-propagation=rprivate",
            f"type=bind,source={state / 's'},target={state / 's'},bind-propagation=rprivate",
            f"type=bind,source={state / 'container.passwd'},target=/etc/passwd,readonly,bind-propagation=rprivate",
            f"type=bind,source={state / 'container.group'},target=/etc/group,readonly,bind-propagation=rprivate",
        ]
        args = [
            "container",
            "create",
            "--pull=never",
            "--name",
            self.name,
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--restart",
            "no",
            "--read-only",
        ]
        for key, value in sorted(self.labels.items()):
            args.extend(["--label", f"{key}={value}"])
        for mount in mounts:
            args.extend(["--mount", mount])
        args.extend(["--entrypoint", "/bin/sleep", self.image["id"], "infinity"])
        return args

    def _ensure_container(self):
        if self.record_path.exists() or self.record_path.is_symlink():
            record = self._load_record()
            recorded_id = record["container_id"]
            info = self._inspect(recorded_id) if recorded_id else None
            if recorded_id is None:
                name_info = self._inspect(self.name)
                if name_info is not None:
                    raise LaunchBlocked(
                        "A container exists but its full ID was not durably recorded; ownership is uncertain and no cleanup was attempted."
                    )
                data, socket = self._state_dirs(create=False)
                if any(data.iterdir()) or any(socket.iterdir()):
                    raise LaunchBlocked(
                        "A container ID is unrecorded and its data paths are not empty; preserve the state for review."
                    )
                self._create_container(record)
                return
            if info is None:
                raise LaunchBlocked(
                    "The recorded task container is absent; its persistent data was preserved and no replacement was created."
                )
            inspected_id, status = self._validate_inspect(info, expected_id=recorded_id)
            name_info = self._inspect(self.name)
            if name_info is None or name_info.get("Id") != inspected_id:
                raise LaunchBlocked(
                    "The task container name no longer resolves to its recorded ID."
                )
        else:
            data, socket = self._state_dirs(create=True)
            if any(data.iterdir()) or any(socket.iterdir()):
                raise LaunchBlocked(
                    "A new container cannot adopt existing PostgreSQL or socket state."
                )
            name_info = self._inspect(self.name)
            if name_info is not None:
                raise LaunchBlocked(
                    "A pre-existing container occupies the task-owned name; it was not adopted, stopped or changed."
                )
            record = self._create_record()
            self._create_container(record)
            return

        if status == "running":
            raise LaunchBlocked(
                "The recorded task container is already running; it was not adopted or stopped. Inspect its owner before retrying."
            )
        if status not in ("created", "exited"):
            raise LaunchBlocked(
                f"The recorded task container has uncertain state {status!r}; no start or cleanup was attempted."
            )
        self.container_id = inspected_id

    def _create_container(self, record: dict):
        try:
            result = docker_run(
                self._create_argv(),
                home=self.state,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            existing = self._inspect(self.name)
            if existing is not None:
                raise LaunchBlocked(
                    "Container creation had an uncertain outcome; the exact ID was not recorded, so no container was adopted or cleaned up."
                ) from exc
            raise LaunchBlocked(
                "Container creation timed out or failed; its outcome is unverified and no retry or cleanup was attempted."
            ) from exc
        if result.returncode != 0:
            existing = self._inspect(self.name)
            if existing is not None:
                raise LaunchBlocked(
                    "Container creation had an uncertain outcome; the exact ID was not recorded, so no container was adopted or cleaned up."
                )
            raise LaunchBlocked(
                "The isolated container could not be created; no image pull was attempted."
            )
        container_id = result.stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{64}", container_id):
            raise LaunchBlocked(
                "Docker returned no full container ID; the named container was left untouched for inspection."
            )
        self._store_container_id(record, container_id)
        info = self._inspect(container_id)
        if info is None:
            raise LaunchBlocked(
                "The created container could not be re-inspected; its outcome is uncertain and it was not cleaned up."
            )
        inspected_id, status = self._validate_inspect(info, expected_id=container_id)
        named = self._inspect(self.name)
        if status != "created" or named is None or named.get("Id") != inspected_id:
            raise LaunchBlocked(
                "The created container identity or state is uncertain; it was not started or cleaned up."
            )
        if inspected_id != container_id:
            raise LaunchBlocked(
                "Docker inspected a different container ID than it returned; no start or cleanup was attempted."
            )

    def prepare(self):
        self._ensure_container()
        if self.container_id is None:
            raise LaunchBlocked("The task container ID was not established.")
        try:
            result = docker_run(
                ["container", "start", self.container_id],
                home=self.state,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            info = self._inspect(self.container_id)
            if info is not None:
                self._validate_inspect(info, expected_id=self.container_id)
            raise LaunchBlocked(
                "Container start timed out or failed; its state was inspected once and preserved without cleanup."
            ) from exc
        if result.returncode != 0:
            info = self._inspect(self.container_id)
            if info is not None:
                self._validate_inspect(info, expected_id=self.container_id)
            if info is not None and info.get("State", {}).get("Status") == "running":
                raise LaunchBlocked(
                    "Container start returned an uncertain result and the container is running; it was preserved without cleanup."
                )
            raise LaunchBlocked(
                "The recorded task container did not start cleanly; no data or container was removed."
            )
        info = self._inspect(self.container_id)
        if info is None:
            raise LaunchBlocked(
                "The started task container could not be re-inspected; its state is uncertain and it was not stopped."
            )
        inspected_id, status = self._validate_inspect(
            info, expected_id=self.container_id
        )
        if status != "running":
            raise LaunchBlocked(
                "The task container start outcome is uncertain; it was not stopped or removed."
            )
        self.container_id = inspected_id
        self.started_by_invocation = True

    def run(self, tool: str, args, **kwargs):
        if self.container_id is None or not self.started_by_invocation:
            raise LaunchBlocked("The task container was not started by this launcher.")
        if tool not in ("initdb", "pg_ctl"):
            raise LaunchBlocked(
                "The container runner only exposes pinned PostgreSQL tools."
            )
        environment = [
            f"PATH={PGVECTOR_BIN_DIR}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            f"HOME={PGVECTOR_IMAGE_PGDATA}",
            "LANG=C.UTF-8",
            f"TMPDIR={PGVECTOR_IMAGE_PGDATA}",
        ]
        command = [
            "exec",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            self.container_id,
            "/usr/bin/env",
            "-i",
            *environment,
            f"{PGVECTOR_BIN_DIR}/{tool}",
            *args,
        ]
        kwargs.pop("env", None)
        return docker_run(command, home=self.state, **kwargs)

    def stop_container(self):
        if not self.started_by_invocation or self.container_id is None:
            return
        info = self._inspect(self.container_id)
        if info is None:
            raise LaunchBlocked(
                "The task container disappeared before cleanup; its durable state was not removed."
            )
        inspected_id, status = self._validate_inspect(
            info, expected_id=self.container_id
        )
        if status == "exited" or status == "created":
            self.started_by_invocation = False
            return
        if status != "running":
            raise LaunchBlocked(
                "The exact task container has uncertain state; it was not stopped or removed."
            )
        try:
            result = docker_run(
                ["container", "stop", "--time", "10", inspected_id],
                home=self.state,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            result = None
        if result is None or result.returncode != 0:
            final = self._inspect(inspected_id)
            if final is not None and final.get("State", {}).get("Status") in (
                "exited",
                "created",
            ):
                self.started_by_invocation = False
                return
            raise LaunchBlocked(
                "Stopping the exact task container had an uncertain outcome; data and the container were preserved."
            )
        final = self._inspect(inspected_id)
        if final is None:
            raise LaunchBlocked("The stopped task container could not be re-inspected.")
        self._validate_inspect(final, expected_id=inspected_id)
        if final.get("State", {}).get("Status") not in ("exited", "created"):
            raise LaunchBlocked(
                "The exact task container did not reach a stopped state; it was not removed."
            )
        self.started_by_invocation = False

    def close(self):
        return None


def verified_source(source: Path):
    source = source.resolve(strict=True)
    git_environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(Path.home()),
        "LANG": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True, env=git_environment
    ).strip()
    if sha != CORE_PIN:
        raise LaunchBlocked(
            "DungeonMind migrations must be the exact pinned source checkout."
        )
    entries = subprocess.check_output(
        ["git", "ls-tree", "-rz", CORE_PIN, "--", "migrations", "alembic.ini"],
        cwd=source,
        env=git_environment,
    )
    expected = {}
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        metadata, encoded_path = entry.split(b"\t", 1)
        mode, kind, digest = metadata.split()
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise LaunchBlocked("Migration inputs must be ordinary pinned files.")
        expected[encoded_path.decode()] = digest.decode()
    if (source / "migrations").is_symlink():
        raise LaunchBlocked("Migration inputs cannot contain symlinks.")
    actual = {"alembic.ini"}
    for path in (source / "migrations").rglob("*"):
        if path.is_symlink():
            raise LaunchBlocked("Migration inputs cannot contain symlinks.")
        if path.is_file():
            actual.add(path.relative_to(source).as_posix())
    if not expected or actual != set(expected):
        raise LaunchBlocked(
            "Migration file inventory differs from the pinned source (including ignored files)."
        )
    for relative, digest in expected.items():
        path = source / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size > 2 * 1024 * 1024
        ):
            raise LaunchBlocked("Migration input is missing, linked or oversized.")
        body = path.read_bytes()
        if (
            hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            != digest
        ):
            raise LaunchBlocked(
                "Migration input bytes differ from the exact source pin."
            )
    return source


def verified_dependencies():
    from importlib.metadata import distribution

    for name, pin in (("dungeonmind", CORE_PIN), ("worldkeeper", WK_PIN)):
        raw = distribution(name).read_text("direct_url.json")
        if raw is None or json.loads(raw).get("vcs_info", {}).get("commit_id") != pin:
            raise LaunchBlocked(
                f"Installed {name} must match Buddy's exact native source pin."
            )


def owned_state(path: Path):
    if path.is_symlink():
        raise LaunchBlocked("The demo state directory must not be a symlink.")
    path = path.absolute()
    if not path.exists():
        path.mkdir(mode=0o700, parents=False)
    stat = path.stat()
    if not path.is_dir() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise LaunchBlocked(
            "The demo state directory must be privately owned by this user."
        )
    path = path.resolve(strict=True)
    marker = path / "native-demo-owner.json"
    expected = {
        "version": 1,
        "uid": os.getuid(),
        "data_directory": str(path / "pgdata"),
        "database": DATABASE,
    }
    if not marker.exists():
        if any(path.iterdir()):
            raise LaunchBlocked(
                "Refusing an existing unowned directory; choose an empty demo directory."
            )
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(expected, stream)
            stream.flush()
            os.fsync(stream.fileno())
    elif marker.is_symlink() or json.loads(marker.read_text()) != expected:
        raise LaunchBlocked(
            "The native demo ownership marker does not match this directory."
        )
    for name in ("pgdata", "s", "commands"):
        candidate = path / name
        if candidate.is_symlink() or (candidate.exists() and not candidate.is_dir()):
            raise LaunchBlocked(
                "Demo runtime paths must be owned directories, not links or files."
            )
    if len(os.fsencode(str(path / "s" / ".s.PGSQL.5432"))) >= 104:
        raise LaunchBlocked(
            "The owned PostgreSQL socket path is too long; use a shorter task-owned directory."
        )
    return path


def clean_env(state: Path):
    # In particular, never inherit PG*, DATABASE_URL, dotenv, or provider settings.
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(Path.home()),
        "LANG": "C.UTF-8",
        "TMPDIR": str(state),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def isolated_database(state: Path, tools, source: Path, runner=None):
    verify_runtime_environment()
    import psycopg
    from psycopg import sql

    runner = runner or NativePostgresRunner(tools)
    socket = state / "s"
    host_data = state / "pgdata"
    data = runner.data_directory(state)
    environment = clean_env(state)
    start_requested = False
    prestart_status = None
    try:
        if runner.containerized:
            runner.prepare()
            prestart = runner.run(
                "pg_ctl",
                ["-D", str(data), "status"],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            prestart_status = prestart.returncode
            if prestart_status == 0:
                raise LaunchBlocked(
                    "The task container already has a running PostgreSQL process; it was preserved without adoption."
                )
            if prestart_status != 3:
                raise LaunchBlocked(
                    "The task container PostgreSQL stopped state is unverified; the container was preserved."
                )
        else:
            socket.mkdir(mode=0o700, exist_ok=True)
            runner.prepare()
        if runner.containerized:
            host_data = _private_directory(host_data, "PostgreSQL data", create=False)
        else:
            if not host_data.exists():
                host_data.mkdir(mode=0o700)
            if (
                host_data.is_symlink()
                or not host_data.is_dir()
                or host_data.stat().st_uid != os.getuid()
            ):
                raise LaunchBlocked(
                    "The task-owned PostgreSQL data directory is unavailable."
                )
        version_path = host_data / "PG_VERSION"
        if version_path.is_symlink():
            raise LaunchBlocked("The PostgreSQL version marker must not be a symlink.")
        initialized = version_path.is_file()
        if any(host_data.iterdir()) and not initialized:
            raise LaunchBlocked(
                "PostgreSQL data is partially initialized or unowned; preserve it for inspection."
            )
        if initialized and runner.containerized:
            if version_path.read_text().strip() != "16":
                raise LaunchBlocked(
                    "The retained container database is not PostgreSQL 16."
                )
        if not initialized:
            runner.run(
                "initdb",
                [
                    "-D",
                    str(data),
                    "--auth-local=peer",
                    "--auth-host=reject",
                    "--username",
                    pwd.getpwuid(os.getuid()).pw_name,
                    "--encoding=UTF8",
                ],
                env=environment,
                check=True,
            )
        # The launcher never adopts an already-running service, even one pointing at
        # a plausible socket. It owns this process from start until normal shutdown.
        status = runner.run(
            "pg_ctl",
            ["-D", str(data), "status"],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if status.returncode == 0:
            raise LaunchBlocked(
                "The demo PostgreSQL process is already running. Stop its owning launcher before starting another."
            )
        if status.returncode != 3:
            raise LaunchBlocked(
                "The owned PostgreSQL stopped state could not be verified; do not retry startup blindly."
            )
        if any(ch in str(socket) for ch in ("'", '"', "\n", "\r", "\\")):
            raise LaunchBlocked("Unsupported characters in the owned socket path.")
        start_requested = True
        runner.run(
            "pg_ctl",
            [
                "-D",
                str(data),
                "-l",
                str(runner.log_file(state)),
                "-o",
                f"-k '{socket}' -h '' -p 5432 -c unix_socket_permissions=0700",
                "-w",
                "start",
            ],
            env=environment,
            check=True,
        )

        def connection(db=DATABASE):
            return psycopg.connect(
                host=str(socket),
                port=5432,
                dbname=db,
                user=pwd.getpwuid(os.getuid()).pw_name,
                connect_timeout=5,
                autocommit=True,
            )

        with connection("postgres") as conn:
            expected_user = pwd.getpwuid(os.getuid()).pw_name
            actual_data = conn.execute("SHOW data_directory").fetchone()[0]
            if (
                actual_data != runner.expected_data_directory(state)
                or conn.execute("SHOW listen_addresses").fetchone()[0] != ""
            ):
                raise LaunchBlocked(
                    "PostgreSQL identity does not match the isolated demo runtime."
                )
            if conn.execute("SELECT current_user, session_user").fetchone() != (
                expected_user,
                expected_user,
            ):
                raise LaunchBlocked(
                    "PostgreSQL peer authentication did not resolve the current host user."
                )
            hba_rules = conn.execute(
                "SELECT type, auth_method, error FROM pg_hba_file_rules"
            ).fetchall()
            if not hba_rules:
                raise LaunchBlocked("PostgreSQL authentication rules are unavailable.")
            seen_local = False
            seen_host = False
            for rule_type, auth_method, error in hba_rules:
                if error is not None:
                    raise LaunchBlocked(
                        "PostgreSQL authentication rules contain a parse error."
                    )
                if rule_type == "local":
                    seen_local = True
                    if auth_method != "peer":
                        raise LaunchBlocked(
                            "PostgreSQL local authentication is not peer-only."
                        )
                elif rule_type.startswith("host"):
                    seen_host = True
                    if auth_method != "reject":
                        raise LaunchBlocked(
                            "PostgreSQL host authentication is not reject-only."
                        )
                else:
                    raise LaunchBlocked(
                        "PostgreSQL has an unsupported authentication rule type."
                    )
            if not seen_local or not seen_host:
                raise LaunchBlocked(
                    "PostgreSQL is missing the required peer or host-reject authentication rule."
                )
            if not conn.execute(
                "SELECT 1 FROM pg_available_extensions WHERE name='vector'"
            ).fetchone():
                raise LaunchBlocked(
                    "This PostgreSQL installation lacks pgvector, required by the existing DungeonMind migrations."
                )
            names = {
                row[0]
                for row in conn.execute(
                    "SELECT datname FROM pg_database WHERE NOT datistemplate"
                )
            }
            if names - {"postgres", DATABASE}:
                raise LaunchBlocked("Refusing a cluster containing non-demo databases.")
            if DATABASE not in names:
                conn.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(DATABASE),
                        sql.Identifier(pwd.getpwuid(os.getuid()).pw_name),
                    )
                )
        url = f"postgresql://{quote(pwd.getpwuid(os.getuid()).pw_name, safe='')}@/{DATABASE}?host={quote(str(socket), safe='')}&port=5432&options={quote('-c statement_timeout=15000 -c lock_timeout=5000', safe='')}"
        migration_env = {**environment, "DUNGEONMIND_DATABASE_URL": url}
        subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                str(source / "alembic.ini"),
                "upgrade",
                "head",
            ],
            cwd=source,
            env=migration_env,
            check=True,
        )
        yield url
    finally:
        if runner.containerized and runner.started_by_invocation:
            if prestart_status != 3:
                raise LaunchBlocked(
                    "The container was started, but PostgreSQL stopped state was not proven before setup; the container was preserved."
                )
            current = runner.run(
                "pg_ctl",
                ["-D", str(data), "status"],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if start_requested and current.returncode == 0:
                runner.run(
                    "pg_ctl",
                    ["-D", str(data), "-m", "fast", "-w", "stop"],
                    env=environment,
                    check=True,
                )
                current = runner.run(
                    "pg_ctl",
                    ["-D", str(data), "status"],
                    env=environment,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            if current.returncode != 3:
                raise LaunchBlocked(
                    "The PostgreSQL shutdown outcome is uncertain; the exact container and all data were preserved."
                )
            runner.stop_container()
        elif start_requested:
            # A failed/interrupted pg_ctl start can still have launched the
            # postmaster. The exclusive launcher lease and pre-start stopped
            # check bind this cleanup to the owned data directory.
            current = runner.run(
                "pg_ctl",
                ["-D", str(data), "status"],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if current.returncode == 0:
                runner.run(
                    "pg_ctl",
                    ["-D", str(data), "-m", "fast", "-w", "stop"],
                    env=environment,
                    check=True,
                )
            elif current.returncode != 3:
                raise LaunchBlocked(
                    "The owned PostgreSQL startup/cleanup outcome is uncertain; inspect this task's runtime before retrying."
                )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--dungeonmind-source", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--postgres-bin", type=Path)
    parser.add_argument(
        "--postgres-runtime",
        choices=("native", "container"),
        default="native",
        help="Use host PostgreSQL tools by default; container mode is an explicit pinned-image opt-in",
    )
    parser.add_argument("--port", type=int, default=4183)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only dependency/preflight check; do not create or start anything",
    )
    args = parser.parse_args(argv)
    previous_sigterm = None
    try:
        verify_runtime_environment()
        if args.postgres_runtime == "container":
            if args.postgres_bin is not None:
                raise LaunchBlocked(
                    "--postgres-bin cannot be combined with container mode."
                )
            image = verify_docker_image()
            tools = {
                "initdb": f"{PGVECTOR_BIN_DIR}/initdb",
                "pg_ctl": f"{PGVECTOR_BIN_DIR}/pg_ctl",
            }
        else:
            image = None
            tools = postgres_tools(args.postgres_bin)
        source = verified_source(args.dungeonmind_source)
        verified_dependencies()
        assets = args.assets.resolve(strict=True)
        if not (assets / "native-demo.html").is_file():
            raise LaunchBlocked(
                "Build the isolated native-demo Vite entry before launch."
            )
        if args.check:
            print(
                "Pinned runtime dependencies and assets are present. Database initialization and restart qualification have not run."
            )
            return 0
        # Check loopback availability before creating a database or graph.
        import socket

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", args.port))

        def stop(signum, frame):
            raise KeyboardInterrupt

        previous_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, stop)
        state = owned_state(args.state_dir)
        with (state / "launcher.lock").open("a") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise LaunchBlocked(
                    "Another launcher owns this demo directory."
                ) from exc
            from contextlib import contextmanager

            runner = (
                DockerPostgresRunner(state, image)
                if args.postgres_runtime == "container"
                else NativePostgresRunner(tools)
            )
            with contextmanager(isolated_database)(state, tools, source, runner) as url:
                sys.path[:0] = [str(ROOT), str(ROOT / "src")]
                from dungeonmind.infrastructure.postgres import (
                    PostgresDatabase,
                    PostgresNativeSourceEvidenceRepository,
                )
                from apps.live_control_server.native_graph_demo.service import (
                    NativeGraphDemoService,
                )
                from apps.live_control_server.native_graph_demo.server import (
                    DemoHTTPServer,
                )

                service = NativeGraphDemoService(
                    PostgresNativeSourceEvidenceRepository(PostgresDatabase(url)),
                    state / "commands",
                    storage_label="postgres",
                )
                with (
                    closing(service),
                    DemoHTTPServer(args.port, service, assets) as server,
                ):
                    print(
                        f"Native DungeonMind demo: {server.origin} (isolated durable database; local only)",
                        flush=True,
                    )
                    try:
                        server.serve_forever()
                    except KeyboardInterrupt:
                        pass
        return 0
    except KeyboardInterrupt:
        print("Native demo stopped; startup was interrupted.", file=sys.stderr)
        return 130
    except (LaunchBlocked, OSError, subprocess.CalledProcessError) as exc:
        print(f"Native demo launch blocked: {exc}", file=sys.stderr)
        return 2
    finally:
        if previous_sigterm is not None:
            signal.signal(signal.SIGTERM, previous_sigterm)


if __name__ == "__main__":
    raise SystemExit(main())
