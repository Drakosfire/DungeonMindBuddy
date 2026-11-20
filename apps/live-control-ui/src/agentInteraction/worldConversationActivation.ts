import { useEffect, useState } from "react";

const MAX_RECOVERY_KEYS = 256;

function isRecoveryKey(key: string, worldId: string): boolean {
  const world = encodeURIComponent(worldId);
  return key.startsWith(`dmb:world-plan-pending-ask:v1:${world}:`)
    || key.startsWith(`dmb:world-agent-new-conversation:v1:${world}:`)
    || key === `dmb:world-play-pending-turn:v1:${world}`
    || key.startsWith(`dmb:world-command-resolution:v1:${world}:`);
}

/** Presence only. The loaded controller owns validation; never inspect or modify envelopes here. */
export function hasWorldConversationRecovery(worldId: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    const storage = window.localStorage;
    // If absence cannot be established cheaply, load the recovery owner.
    if (storage.length > MAX_RECOVERY_KEYS) return true;
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (key !== null && isRecoveryKey(key, worldId)) return true;
    }
    return false;
  } catch {
    return true;
  }
}

/** Mounted under the World key; activation never reverses during that owner's lifetime. */
export function useWorldConversationActivation(worldId: string, surfaceActive: boolean): boolean {
  const [activated, setActivated] = useState(() => surfaceActive || hasWorldConversationRecovery(worldId));
  useEffect(() => {
    const check = () => {
      if (surfaceActive || hasWorldConversationRecovery(worldId)) setActivated(true);
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key !== null && !isRecoveryKey(event.key, worldId)) return;
      try {
        if (event.storageArea !== null && event.storageArea !== window.localStorage) return;
      } catch {
        setActivated(true);
        return;
      }
      check();
    };
    window.addEventListener("storage", onStorage);
    // Recheck after installing the listener, closing the render→effect gap.
    check();
    return () => window.removeEventListener("storage", onStorage);
  }, [surfaceActive, worldId]);
  return surfaceActive || activated;
}
