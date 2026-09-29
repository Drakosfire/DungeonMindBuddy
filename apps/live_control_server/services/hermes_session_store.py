"""Durable server-authoritative Hermes session pointer bindings per agent thread.

Concurrency contract
--------------------
``HermesSessionPointerStore`` is safe for concurrent access from multiple
store instances **within a single Python process** via a path-scoped shared
``RLock``. Unique temporary filenames avoid same-process temp-file collisions.

It is **not** safe across multiple OS processes writing the same
``hermes_thread_pointers.json``. Each process has its own lock map; two
processes can still load–modify–replace and lose updates. The live-control
server is expected to own the store as a single-process writer. Cross-process
safety would require an OS file lock, transactional DB, or CAS revision.
"""

from __future__ import annotations

import threading
import uuid
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from src.live_play.live_store import load_json, write_json

POINTER_BINDING_SCHEMA = "dmb_hermes_session_pointer_binding_v1"
POINTER_STORE_SCHEMA = "dmb_hermes_session_pointer_store_v1"
STRUCTURED_POINTER_BINDING_SCHEMA = "dmb_hermes_structured_session_pointer_binding_v1"
BindingStatus = Literal["active", "expired", "invalid"]
PointerStatus = Literal["absent", "accepted", "rejected", "recovered"]

# Same-process only: path → shared RLock. Not shared across OS processes.
_STORE_LOCKS: dict[str, threading.RLock] = {}
_STORE_LOCKS_GUARD = threading.Lock()


def _lock_for_base(base: Path) -> threading.RLock:
    key = str(base.resolve())
    with _STORE_LOCKS_GUARD:
        lock = _STORE_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _STORE_LOCKS[key] = lock
        return lock


@dataclass(frozen=True, slots=True)
class HermesSessionPointerBinding:
    schema: str
    pointer_id: str
    agent_thread_id: str
    campaign_id: str
    hermes_session_id: str
    status: BindingStatus
    created_at: str
    updated_at: str
    last_worker_pid: int | None = None


@dataclass(frozen=True, slots=True)
class HermesPointerResolution:
    continuity_session_id: str | None
    pointer_status: PointerStatus
    pointer_in_request: bool
    recovery_message: str | None = None


@dataclass(frozen=True, slots=True)
class HermesStructuredSessionPointerBinding:
    schema: str
    pointer_id: str
    agent_thread_id: str
    owner_kind: str | None
    owner_id: str | None
    work_kind: str | None
    work_id: str | None
    hermes_session_id: str
    status: BindingStatus
    created_at: str
    updated_at: str
    last_worker_pid: int | None = None


@dataclass(frozen=True, slots=True)
class HermesStructuredPointerResolution:
    continuity_session_id: str | None
    pointer_status: PointerStatus
    pointer_in_request: bool
    pointer_id: str | None = None
    recovery_message: str | None = None


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _store_path(base: Path) -> Path:
    return base / "hermes_thread_pointers.json"


def _binding_key(campaign_id: str, agent_thread_id: str) -> str:
    return f"{campaign_id}::{agent_thread_id}"


def _structured_binding_key(
    *,
    owner_kind: str | None,
    owner_id: str | None,
    work_kind: str | None,
    work_id: str | None,
    agent_thread_id: str,
) -> str:
    identity = [owner_kind, owner_id, work_kind, work_id, agent_thread_id]
    encoded = json.dumps(identity, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _new_pointer_id() -> str:
    return f"hptr-{uuid.uuid4().hex[:24]}"


def _parse_binding(raw: dict[str, Any]) -> HermesSessionPointerBinding | None:
    pointer_id = str(raw.get("pointer_id") or "").strip()
    agent_thread_id = str(raw.get("agent_thread_id") or "").strip()
    campaign_id = str(raw.get("campaign_id") or "").strip()
    hermes_session_id = str(raw.get("hermes_session_id") or "").strip()
    if not pointer_id or not agent_thread_id or not campaign_id or not hermes_session_id:
        return None
    status_raw = str(raw.get("status") or "active")
    status: BindingStatus = status_raw if status_raw in {"active", "expired", "invalid"} else "invalid"
    last_worker_pid = raw.get("last_worker_pid")
    return HermesSessionPointerBinding(
        schema=POINTER_BINDING_SCHEMA,
        pointer_id=pointer_id,
        agent_thread_id=agent_thread_id,
        campaign_id=campaign_id,
        hermes_session_id=hermes_session_id,
        status=status,
        created_at=str(raw.get("created_at") or _utc_now_z()),
        updated_at=str(raw.get("updated_at") or _utc_now_z()),
        last_worker_pid=int(last_worker_pid) if isinstance(last_worker_pid, int) else None,
    )


class HermesSessionPointerStore:
    """File-backed pointer store scoped to one live session directory.

    Single-process ownership: concurrent same-process instances share a
    path-scoped lock. Multiple server processes must not write the same file.
    """

    def __init__(self, base: Path) -> None:
        self._base = base.resolve()
        self._lock = _lock_for_base(self._base)

    def _load_store(self) -> dict[str, Any]:
        path = _store_path(self._base)
        if not path.is_file():
            return {"schema": POINTER_STORE_SCHEMA, "bindings": {}}
        payload = load_json(path)
        if not isinstance(payload, dict):
            return {"schema": POINTER_STORE_SCHEMA, "bindings": {}}
        bindings = payload.get("bindings")
        if not isinstance(bindings, dict):
            bindings = {}
        result: dict[str, Any] = {"schema": POINTER_STORE_SCHEMA, "bindings": bindings}
        structured = payload.get("structured_bindings")
        if isinstance(structured, dict):
            result["structured_bindings"] = structured
        return result

    def _save_store(self, payload: dict[str, Any]) -> None:
        path = _store_path(self._base)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, payload)

    def get_by_pointer(self, pointer_id: str) -> HermesSessionPointerBinding | None:
        normalized = str(pointer_id or "").strip()
        if not normalized:
            return None
        with self._lock:
            store = self._load_store()
            bindings = store.get("bindings")
            if not isinstance(bindings, dict):
                return None
            for raw in bindings.values():
                if not isinstance(raw, dict):
                    continue
                binding = _parse_binding(raw)
                if binding is not None and binding.pointer_id == normalized:
                    return binding
        return None

    def get_for_thread(
        self,
        *,
        campaign_id: str,
        agent_thread_id: str,
    ) -> HermesSessionPointerBinding | None:
        key = _binding_key(campaign_id, agent_thread_id)
        with self._lock:
            store = self._load_store()
            bindings = store.get("bindings")
            if not isinstance(bindings, dict):
                return None
            raw = bindings.get(key)
            if not isinstance(raw, dict):
                return None
            return _parse_binding(raw)

    def resolve_for_request(
        self,
        *,
        campaign_id: str,
        agent_thread_id: str | None,
        pointer_id: str | None,
    ) -> HermesPointerResolution:
        normalized_pointer = str(pointer_id or "").strip()
        if not normalized_pointer:
            return HermesPointerResolution(
                continuity_session_id=None,
                pointer_status="absent",
                pointer_in_request=False,
            )
        if not agent_thread_id:
            raise HermesSessionPointerError(
                "Hermes session pointer requires agent_thread_id.",
                code="hermes_session_pointer_rejected",
            )
        binding = self.get_by_pointer(normalized_pointer)
        if binding is None:
            return HermesPointerResolution(
                continuity_session_id=None,
                pointer_status="recovered",
                pointer_in_request=True,
                recovery_message="Unknown Hermes session pointer; started a fresh session.",
            )
        if (
            binding.campaign_id != campaign_id
            or binding.agent_thread_id != agent_thread_id
        ):
            raise HermesSessionPointerError(
                "Hermes session pointer is not bound to this thread.",
                code="hermes_session_pointer_rejected",
            )
        if binding.status != "active":
            return HermesPointerResolution(
                continuity_session_id=None,
                pointer_status="recovered",
                pointer_in_request=True,
                recovery_message=(
                    f"Hermes session pointer is {binding.status}; started a fresh session."
                ),
            )
        return HermesPointerResolution(
            continuity_session_id=binding.hermes_session_id,
            pointer_status="accepted",
            pointer_in_request=True,
        )

    def upsert_after_turn(
        self,
        *,
        campaign_id: str,
        agent_thread_id: str,
        hermes_session_id: str,
        worker_pid: int | None = None,
        existing_pointer_id: str | None = None,
    ) -> HermesSessionPointerBinding:
        normalized_session = str(hermes_session_id or "").strip()
        if not normalized_session:
            raise ValueError("hermes_session_id is required to persist a pointer binding")
        key = _binding_key(campaign_id, agent_thread_id)
        now = _utc_now_z()
        with self._lock:
            store = self._load_store()
            bindings = store.setdefault("bindings", {})
            if not isinstance(bindings, dict):
                bindings = {}
                store["bindings"] = bindings
            raw = bindings.get(key)
            pointer_id = str(existing_pointer_id or "").strip()
            created_at = now
            if isinstance(raw, dict):
                existing = _parse_binding(raw)
                if existing is not None:
                    created_at = existing.created_at
                    if not pointer_id:
                        pointer_id = existing.pointer_id
            if not pointer_id:
                pointer_id = _new_pointer_id()
            binding = HermesSessionPointerBinding(
                schema=POINTER_BINDING_SCHEMA,
                pointer_id=pointer_id,
                agent_thread_id=agent_thread_id,
                campaign_id=campaign_id,
                hermes_session_id=normalized_session,
                status="active",
                created_at=created_at,
                updated_at=now,
                last_worker_pid=worker_pid,
            )
            bindings[key] = {
                "schema": binding.schema,
                "pointer_id": binding.pointer_id,
                "agent_thread_id": binding.agent_thread_id,
                "campaign_id": binding.campaign_id,
                "hermes_session_id": binding.hermes_session_id,
                "status": binding.status,
                "created_at": binding.created_at,
                "updated_at": binding.updated_at,
                "last_worker_pid": binding.last_worker_pid,
            }
            self._save_store(store)
            return binding

    def clear_for_thread(
        self,
        *,
        campaign_id: str,
        agent_thread_id: str,
    ) -> None:
        key = _binding_key(campaign_id, agent_thread_id)
        with self._lock:
            store = self._load_store()
            bindings = store.get("bindings")
            if not isinstance(bindings, dict):
                return
            if key in bindings:
                del bindings[key]
                self._save_store(store)

    def worker_pid_changed(
        self,
        binding: HermesSessionPointerBinding | None,
        worker_pid: int | None,
    ) -> bool:
        if binding is None or worker_pid is None:
            return False
        previous = binding.last_worker_pid
        return previous is not None and previous != worker_pid

    def resolve_structured_for_request(
        self,
        *,
        owner_kind: str | None,
        owner_id: str | None,
        work_kind: str | None,
        work_id: str | None,
        agent_thread_id: str,
        pointer_id: str | None,
    ) -> HermesStructuredPointerResolution:
        """Resolve only the exact structured owner/work/thread key.

        A supplied pointer bound to another key is recovered as a fresh
        provider session; it is never used to cross the current authority.
        Legacy campaign bindings are intentionally not inspected here.
        """
        key = _structured_binding_key(
            owner_kind=owner_kind,
            owner_id=owner_id,
            work_kind=work_kind,
            work_id=work_id,
            agent_thread_id=agent_thread_id,
        )
        normalized_pointer = str(pointer_id or "").strip() or None
        with self._lock:
            store = self._load_store()
            bindings = store.get("structured_bindings")
            if not isinstance(bindings, dict):
                return HermesStructuredPointerResolution(
                    continuity_session_id=None,
                    pointer_status="recovered" if normalized_pointer else "absent",
                    pointer_in_request=normalized_pointer is not None,
                    recovery_message=(
                        "Unknown structured Hermes pointer; started a fresh session."
                        if normalized_pointer
                        else None
                    ),
                )
            raw = bindings.get(key)
            binding = _parse_structured_binding(raw) if isinstance(raw, dict) else None
            if binding is None or binding.status != "active":
                return HermesStructuredPointerResolution(
                    continuity_session_id=None,
                    pointer_status="recovered" if normalized_pointer else "absent",
                    pointer_in_request=normalized_pointer is not None,
                    recovery_message=(
                        "Structured Hermes session is unavailable; started a fresh session."
                        if normalized_pointer
                        else None
                    ),
                )
            if normalized_pointer is not None and normalized_pointer != binding.pointer_id:
                return HermesStructuredPointerResolution(
                    continuity_session_id=None,
                    pointer_status="recovered",
                    pointer_in_request=True,
                    recovery_message="Hermes pointer did not match this context; started a fresh session.",
                )
            return HermesStructuredPointerResolution(
                continuity_session_id=binding.hermes_session_id,
                pointer_status="accepted" if normalized_pointer else "absent",
                pointer_in_request=normalized_pointer is not None,
                pointer_id=binding.pointer_id,
            )

    def upsert_structured_after_turn(
        self,
        *,
        owner_kind: str | None,
        owner_id: str | None,
        work_kind: str | None,
        work_id: str | None,
        agent_thread_id: str,
        hermes_session_id: str,
        worker_pid: int | None = None,
        existing_pointer_id: str | None = None,
    ) -> HermesStructuredSessionPointerBinding:
        normalized_session = str(hermes_session_id or "").strip()
        if not normalized_session:
            raise ValueError("hermes_session_id is required to persist a structured pointer binding")
        key = _structured_binding_key(
            owner_kind=owner_kind,
            owner_id=owner_id,
            work_kind=work_kind,
            work_id=work_id,
            agent_thread_id=agent_thread_id,
        )
        now = _utc_now_z()
        with self._lock:
            store = self._load_store()
            bindings = store.setdefault("structured_bindings", {})
            if not isinstance(bindings, dict):
                bindings = {}
                store["structured_bindings"] = bindings
            raw = bindings.get(key)
            previous = _parse_structured_binding(raw) if isinstance(raw, dict) else None
            pointer_id = str(existing_pointer_id or "").strip()
            if previous is not None and previous.status == "active":
                if pointer_id and pointer_id != previous.pointer_id:
                    raise HermesSessionPointerError(
                        "structured Hermes pointer is not bound to this context",
                        code="hermes_session_pointer_rejected",
                    )
                pointer_id = pointer_id or previous.pointer_id
            if not pointer_id:
                pointer_id = _new_pointer_id()
            binding = HermesStructuredSessionPointerBinding(
                schema=STRUCTURED_POINTER_BINDING_SCHEMA,
                pointer_id=pointer_id,
                agent_thread_id=agent_thread_id,
                owner_kind=owner_kind,
                owner_id=owner_id,
                work_kind=work_kind,
                work_id=work_id,
                hermes_session_id=normalized_session,
                status="active",
                created_at=previous.created_at if previous is not None else now,
                updated_at=now,
                last_worker_pid=worker_pid,
            )
            bindings[key] = {
                "schema": binding.schema,
                "pointer_id": binding.pointer_id,
                "agent_thread_id": binding.agent_thread_id,
                "owner_kind": binding.owner_kind,
                "owner_id": binding.owner_id,
                "work_kind": binding.work_kind,
                "work_id": binding.work_id,
                "hermes_session_id": binding.hermes_session_id,
                "status": binding.status,
                "created_at": binding.created_at,
                "updated_at": binding.updated_at,
                "last_worker_pid": binding.last_worker_pid,
            }
            self._save_store(store)
            return binding


class HermesSessionPointerError(ValueError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _parse_structured_binding(raw: dict[str, Any]) -> HermesStructuredSessionPointerBinding | None:
    pointer_id = str(raw.get("pointer_id") or "").strip()
    thread_id = str(raw.get("agent_thread_id") or "").strip()
    session_id = str(raw.get("hermes_session_id") or "").strip()
    if not pointer_id or not thread_id or not session_id:
        return None
    status_raw = str(raw.get("status") or "active")
    status: BindingStatus = status_raw if status_raw in {"active", "expired", "invalid"} else "invalid"
    last_worker_pid = raw.get("last_worker_pid")
    return HermesStructuredSessionPointerBinding(
        schema=STRUCTURED_POINTER_BINDING_SCHEMA,
        pointer_id=pointer_id,
        agent_thread_id=thread_id,
        owner_kind=_optional_identity(raw.get("owner_kind")),
        owner_id=_optional_identity(raw.get("owner_id")),
        work_kind=_optional_identity(raw.get("work_kind")),
        work_id=_optional_identity(raw.get("work_id")),
        hermes_session_id=session_id,
        status=status,
        created_at=str(raw.get("created_at") or _utc_now_z()),
        updated_at=str(raw.get("updated_at") or _utc_now_z()),
        last_worker_pid=int(last_worker_pid) if isinstance(last_worker_pid, int) else None,
    )


def _optional_identity(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


__all__ = [
    "HermesPointerResolution",
    "HermesSessionPointerBinding",
    "HermesSessionPointerError",
    "HermesSessionPointerStore",
    "HermesStructuredPointerResolution",
    "HermesStructuredSessionPointerBinding",
    "PointerStatus",
]
