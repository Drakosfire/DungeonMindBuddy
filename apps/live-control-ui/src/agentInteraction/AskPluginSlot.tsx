import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

interface AskPluginSlotValue {
  layoutOwner: "chrome" | "plan-workspace";
  setLayoutOwner: (owner: "chrome" | "plan-workspace") => void;
  launcherHost: HTMLElement | null;
  setLauncherHost: (element: HTMLElement | null) => void;
  menuHost: HTMLElement | null;
  setMenuHost: (element: HTMLElement | null) => void;
  hostElement: HTMLElement | null;
  setHostElement: (element: HTMLElement | null) => void;
  clearHostElement: (expected: HTMLElement) => void;
  askPluginPresent: boolean;
  setAskPluginPresent: (present: boolean) => void;
}

const AskPluginSlotContext = createContext<AskPluginSlotValue | null>(null);

export function AskPluginSlotProvider({ children }: { children: ReactNode }) {
  const [menuHost, setMenuHost] = useState<HTMLElement | null>(null);
  const [hostElement, setHostElementState] = useState<HTMLElement | null>(null);
  const [askPluginPresent, setAskPluginPresent] = useState(false);
  const [layoutOwner, setLayoutOwner] = useState<"chrome" | "plan-workspace">("chrome");
  const [launcherHost, setLauncherHost] = useState<HTMLElement | null>(null);

  const setHostElement = useCallback((element: HTMLElement | null) => {
    setHostElementState(element);
  }, []);

  const clearHostElement = useCallback((expected: HTMLElement) => {
    setHostElementState(current => current === expected ? null : current);
  }, []);

  const value = useMemo(
    () => ({
      layoutOwner, setLayoutOwner, launcherHost, setLauncherHost,
      menuHost, setMenuHost, hostElement,
      setHostElement, clearHostElement,
      askPluginPresent,
      setAskPluginPresent,
    }),
    [askPluginPresent, menuHost, hostElement, setHostElement, clearHostElement, layoutOwner, launcherHost],
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

/** A departing host can release only the element it previously registered. */
export function useOwnedAskHostRef() {
  const {setHostElement, clearHostElement} = useAskPluginSlot();
  const owned = useRef<HTMLElement | null>(null);
  return useCallback((element: HTMLElement | null) => {
    if (element) {
      owned.current = element;
      setHostElement(element);
    } else if (owned.current) {
      clearHostElement(owned.current);
      owned.current = null;
    }
  }, [setHostElement, clearHostElement]);
}
