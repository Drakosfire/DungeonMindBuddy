import { useReducer, useRef } from "react";

/** A Surface owns presentation; the existing Studio owns generation and assets. */
export function useSurfaceImageStudio(identity: string, ready: boolean) {
  const [, refresh] = useReducer((value: number) => value + 1, 0);
  const live = useRef({ identity, ready, session: null as { prompt: string } | null });
  if (live.current.identity !== identity) live.current = { identity, ready, session: null };
  live.current.ready = ready;
  const owner = live.current;
  const session = owner.session;
  return {
    session,
    open(prompt = "") {
      // The owner object changes even on A→B→A navigation. Old callbacks cannot
      // replace a new Studio, and two clicks in one render cannot erase a draft.
      if (live.current !== owner || !owner.ready || owner.session) return false;
      owner.session = { prompt };
      refresh();
      return true;
    },
    close() {
      if (live.current !== owner || owner.session !== session) return;
      owner.session = null;
      refresh();
    },
  };
}
