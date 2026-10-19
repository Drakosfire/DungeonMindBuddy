import { useEffect, useState } from "react";

const EVENT = "dmb:workspace-inventory-changed";
export function announceWorkspaceInventoryChange(worldId: string): void {
  window.dispatchEvent(new CustomEvent(EVENT, {detail:{worldId}}));
}
/** Invalidate inventories only: restoring an item never reloads an editor or selects it. */
export function useWorkspaceInventoryVersion(worldId: string | null): number {
  const [state, setState] = useState({worldId, version:0});
  useEffect(() => {
    const changed = (event: Event) => {
      if ((event as CustomEvent<{worldId:string}>).detail?.worldId !== worldId) return;
      setState(current => ({worldId,version:current.worldId === worldId ? current.version+1 : 1}));
    };
    window.addEventListener(EVENT,changed);
    return () => window.removeEventListener(EVENT,changed);
  },[worldId]);
  return state.worldId === worldId ? state.version : 0;
}
