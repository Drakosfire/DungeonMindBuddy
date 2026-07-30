import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

interface AskPluginSlotValue {
  hostElement: HTMLElement | null;
  setHostElement: (element: HTMLElement | null) => void;
  askPluginPresent: boolean;
  setAskPluginPresent: (present: boolean) => void;
}

const AskPluginSlotContext = createContext<AskPluginSlotValue | null>(null);

export function AskPluginSlotProvider({ children }: { children: ReactNode }) {
  const [hostElement, setHostElementState] = useState<HTMLElement | null>(null);
  const [askPluginPresent, setAskPluginPresent] = useState(false);

  const setHostElement = useCallback((element: HTMLElement | null) => {
    setHostElementState(element);
  }, []);

  const value = useMemo(
    () => ({
      hostElement,
      setHostElement,
      askPluginPresent,
      setAskPluginPresent,
    }),
    [askPluginPresent, hostElement, setHostElement],
  );

  return (
    <AskPluginSlotContext.Provider value={value}>{children}</AskPluginSlotContext.Provider>
  );
}

export function useAskPluginSlot(): AskPluginSlotValue {
  const value = useContext(AskPluginSlotContext);
  if (!value) {
    throw new Error("useAskPluginSlot requires AskPluginSlotProvider");
  }
  return value;
}

/** Optional for tests that render Ask without the app chrome host. */
export function useAskPluginSlotOptional(): AskPluginSlotValue | null {
  return useContext(AskPluginSlotContext);
}

export function useRegisterAskPluginPresence(present: boolean): void {
  const slot = useAskPluginSlotOptional();
  useEffect(() => {
    if (!slot || !present) return;
    slot.setAskPluginPresent(true);
    return () => slot.setAskPluginPresent(false);
  }, [present, slot]);
}
