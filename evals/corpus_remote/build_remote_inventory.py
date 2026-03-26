from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import paramiko


TEXT_EXTENSIONS = {".docx", ".md", ".txt", ".pdf"}
OUT_DIR = Path(__file__).resolve().parents[2] / "out" / "evals" / "corpus_remote"


@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    modified_time: str


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _slugify(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return cleaned or "document"


def _extract_campaign_group(path: str) -> str:
    lowered = path.lower()
    match = re.search(r"campaign[\s_]*([0-9]+)", lowered)
    if not match:
        return "world_baseline"
    return f"campaign_{match.group(1)}"


def _infer_source_class(path: str) -> str:
    lowered = path.lower()
    if "session" in lowered and "recap" in lowered:
        return "observed_session_recap"
    if "dossier" in lowered or "ledger" in lowered:
        return "ledger_or_dossier"
    if "prep" in lowered:
        return "planning_document"
    if "world" in lowered or "module" in lowered:
        return "seed_reference"
    return "other"


def _infer_canon_layer(path: str) -> tuple[str, str | None]:
    parts = [part.lower() for part in Path(path).parts]
    for part in parts:
        match = re.search(r"campaign[\s_]*([0-9]+)", part)
        if match:
            return "campaign", f"campaign_{match.group(1)}"
    if any("session" in part for part in parts):
        campaign_group = _extract_campaign_group(path)
        if campaign_group == "world_baseline":
            return "campaign", "campaign_unknown"
        return "campaign", campaign_group
    return "world", None


def _manifest_record(record: FileRecord) -> dict[str, Any]:
    source_class = _infer_source_class(record.path)
    canon_layer, campaign_id = _infer_canon_layer(record.path)
    campaign_group = _extract_campaign_group(record.path)
    return {
        "document_id": _slugify(Path(record.path).stem),
        "remote_path": record.path,
        "source_class": source_class,
        "canon_layer": canon_layer,
        "campaign_id": campaign_id,
        "campaign_group": campaign_group,
    }


def _collect_local_inventory(local_root: Path) -> list[FileRecord]:
    if not local_root.exists():
        raise ValueError(f"Local root does not exist: {local_root}")
    records: list[FileRecord] = []
    for path in sorted(local_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        stat = path.stat()
        records.append(
            FileRecord(
                path=str(path),
                size=int(stat.st_size),
                modified_time=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            )
        )
    return records


def _collect_remote_inventory(
    ssh_host: str,
    remote_root: str,
    ssh_username: str | None = None,
    ssh_password: str | None = None,
) -> list[FileRecord]:
    if ssh_password:
        return _collect_remote_inventory_paramiko(
            ssh_host=ssh_host,
            remote_root=remote_root,
            ssh_username=ssh_username,
            ssh_password=ssh_password,
        )
    return _collect_remote_inventory_ssh(ssh_host=ssh_host, remote_root=remote_root)


def _collect_remote_inventory_ssh(ssh_host: str, remote_root: str) -> list[FileRecord]:
    script = (
        "import json, pathlib, datetime; "
        f"root=pathlib.Path({remote_root!r}); "
        "allowed={'.docx','.md','.txt','.pdf'}; "
        "records=["
        "{"
        "'path':str(p),"
        "'size':int((st:=p.stat()).st_size),"
        "'modified_time':datetime.datetime.fromtimestamp(st.st_mtime, datetime.UTC).isoformat()"
        "}"
        " for p in sorted(root.rglob('*'))"
        " if p.is_file() and p.suffix.lower() in allowed"
        "]; "
        "print(json.dumps(records));"
    )
    command = [
        "ssh",
        ssh_host,
        "python3",
        "-c",
        script,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout)
    return [
        FileRecord(
            path=str(entry["path"]),
            size=int(entry["size"]),
            modified_time=str(entry["modified_time"]),
        )
        for entry in payload
    ]


def _collect_remote_inventory_paramiko(
    ssh_host: str,
    remote_root: str,
    ssh_username: str | None,
    ssh_password: str,
) -> list[FileRecord]:
    host = ssh_host
    username = ssh_username
    if "@" in ssh_host and not ssh_username:
        username, host = ssh_host.split("@", 1)
    if not username:
        raise ValueError("ssh_username is required when using password auth.")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        username=username,
        password=ssh_password,
        look_for_keys=False,
        allow_agent=False,
        timeout=20,
    )
    try:
        script = (
            "import json, pathlib, datetime; "
            f"root=pathlib.Path({remote_root!r}); "
            "allowed={'.docx','.md','.txt','.pdf'}; "
            "records=["
            "{"
            "'path':str(p),"
            "'size':int((st:=p.stat()).st_size),"
            "'modified_time':datetime.datetime.fromtimestamp(st.st_mtime, datetime.UTC).isoformat()"
            "}"
            " for p in sorted(root.rglob('*'))"
            " if p.is_file() and p.suffix.lower() in allowed"
            "]; "
            "print(json.dumps(records));"
        )
        command = (
            "python3 -c "
            + json.dumps(script)
        )
        _, stdout, stderr = client.exec_command(command, timeout=90)
        stdout_payload = stdout.read().decode("utf-8")
        stderr_payload = stderr.read().decode("utf-8")
        if stderr_payload.strip():
            raise RuntimeError(f"Remote command failed: {stderr_payload.strip()}")
        payload = json.loads(stdout_payload)
    finally:
        client.close()

    return [
        FileRecord(
            path=str(entry["path"]),
            size=int(entry["size"]),
            modified_time=str(entry["modified_time"]),
        )
        for entry in payload
    ]


def _inventory_payload(source_host: str, records: list[FileRecord]) -> dict[str, Any]:
    listing = [
        {"path": record.path, "size": record.size, "modified_time": record.modified_time}
        for record in records
    ]
    listing_hash = _canonical_hash(listing)
    snapshot_id = f"snapshot_{listing_hash[:16]}"
    extension_counter = Counter(Path(record.path).suffix.lower() for record in records)
    return {
        "snapshot_id": snapshot_id,
        "source_host": source_host,
        "captured_at": datetime.now(tz=UTC).isoformat(),
        "totals": {
            "total_documents": len(records),
            "total_bytes": sum(record.size for record in records),
            "by_extension": dict(sorted(extension_counter.items())),
        },
        "documents": listing,
    }


def _manifest_payload(
    source_host: str,
    snapshot_id: str,
    records: list[FileRecord],
    sample_size: int,
) -> dict[str, Any]:
    sampled = sorted(records, key=lambda entry: entry.path)[:sample_size]
    return {
        "snapshot_id": snapshot_id,
        "source_host": source_host,
        "captured_at": datetime.now(tz=UTC).isoformat(),
        "documents": [_manifest_record(record) for record in sampled],
    }


def _reproducibility_payload(
    inventory: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    inventory_hash = _canonical_hash(inventory["documents"])
    manifest_hash = _canonical_hash(manifest["documents"])
    return {
        "snapshot_id": inventory["snapshot_id"],
        "inventory_hash": inventory_hash,
        "manifest_hash": manifest_hash,
        "document_counts_match": len(inventory["documents"]) >= len(manifest["documents"]),
        "captured_at": datetime.now(tz=UTC).isoformat(),
    }


def _validate_manifest(manifest: dict[str, Any]) -> None:
    required_fields = {
        "document_id",
        "remote_path",
        "source_class",
        "canon_layer",
        "campaign_id",
        "campaign_group",
    }
    for document in manifest["documents"]:
        missing = sorted(required_fields.difference(document.keys()))
        if missing:
            raise ValueError(f"Manifest document missing fields: {missing}")
        if document["canon_layer"] == "campaign" and not document["campaign_id"]:
            raise ValueError(
                "Manifest document has canon_layer=campaign but no campaign_id: "
                f"{document['remote_path']}"
            )


def generate_remote_artifacts(
    source_host: str,
    records: list[FileRecord],
    sample_size: int,
    out_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    inventory = _inventory_payload(source_host=source_host, records=records)
    manifest = _manifest_payload(
        source_host=source_host,
        snapshot_id=inventory["snapshot_id"],
        records=records,
        sample_size=sample_size,
    )
    _validate_manifest(manifest)
    reproducibility = _reproducibility_payload(inventory=inventory, manifest=manifest)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "remote_inventory.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out_dir / "normalization_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out_dir / "reproducibility_report.json").write_text(
        json.dumps(reproducibility, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return inventory, manifest, reproducibility


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build remote corpus inventory artifacts")
    parser.add_argument("--source-host", default="gpu_desktop")
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--local-root", default=None)
    parser.add_argument("--ssh-host", default=None)
    parser.add_argument("--remote-root", default=None)
    parser.add_argument("--ssh-username", default=None)
    parser.add_argument("--ssh-password", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)

    if args.local_root:
        records = _collect_local_inventory(Path(args.local_root))
    else:
        if not args.ssh_host or not args.remote_root:
            raise ValueError(
                "Use either --local-root, or provide both --ssh-host and --remote-root."
            )
        records = _collect_remote_inventory(
            ssh_host=str(args.ssh_host),
            remote_root=str(args.remote_root),
            ssh_username=str(args.ssh_username) if args.ssh_username else None,
            ssh_password=str(args.ssh_password) if args.ssh_password else None,
        )

    generate_remote_artifacts(
        source_host=str(args.source_host),
        records=records,
        sample_size=int(args.sample_size),
        out_dir=out_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

