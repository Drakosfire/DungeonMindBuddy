"""Durable server-authoritative Hermes session pointer bindings per agent thread."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from src.live_play.live_store import load_json, write_json

POINTER_BINDING_SCHEMA = "dmb_hermes_session_pointer_binding_v1"
POINTER_STORE_SCHEMA = "dmb_hermes_session_pointer_store_v1"
BindingStatus = Literal["active", "expired", "invalid"]
PointerStatus = Literal["absent", "accepted", "rejected", "recovered"]


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


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _store_path(base: Path) -> Path:
    return base / "hermes_thread_pointers.json"


def _binding_key(campaign_id: str, agent_thread_id: str) -> str:
    return f"{campaign_id}::{agent_thread_id}"


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
    """File-backed pointer store scoped to one live session directory."""

    def __init__(self, base: Path) -> None:
        self._base = base.resolve()
        self._lock = threading.RLock()

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
        return {"schema": POINTER_STORE_SCHEMA, "bindings": bindings}

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


class HermesSessionPointerError(ValueError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "HermesPointerResolution",
    "HermesSessionPointerBinding",
    "HermesSessionPointerError",
    "HermesSessionPointerStore",
    "PointerStatus",
]
