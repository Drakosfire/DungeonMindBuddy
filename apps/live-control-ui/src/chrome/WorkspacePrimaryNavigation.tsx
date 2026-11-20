import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { CompactAppNavigation } from "./CompactAppNavigation";
import type { AppRouteKey } from "./appChromeConfig";

type PrimaryActionsRef = (element: HTMLDivElement | null) => void;
type Attach = (header: HTMLElement, primaryActionsRef?: PrimaryActionsRef) => () => void;

const WorkspaceNavigationContext = createContext<Attach | null>(null);

export function useWorkspacePrimaryNavigation() {
  return useContext(WorkspaceNavigationContext);
}

export function WorkspacePrimaryNavigation({ route, children }: { route: AppRouteKey; children: ReactNode }) {
  const [portalHost] = useState(() => {
    const element = document.createElement("div");
    element.style.display = "contents";
    return element;
  });
  const fallbackHeader = useRef<HTMLElement | null>(null);
  const [primaryActionsRef, setPrimaryActionsRef] = useState<PrimaryActionsRef | undefined>();
  const attach = useCallback<Attach>((header, actionsRef) => {
    header.prepend(portalHost);
    setPrimaryActionsRef(() => actionsRef);
    return () => {
      if (portalHost.parentNode !== header) return;
      fallbackHeader.current?.append(portalHost);
      setPrimaryActionsRef(undefined);
    };
  }, [portalHost]);
  const setFallbackHeader = useCallback((header: HTMLElement | null) => {
    fallbackHeader.current = header;
    if (header && !portalHost.parentNode) header.append(portalHost);
  }, [portalHost]);

  return (
    <WorkspaceNavigationContext.Provider value={attach}>
      <header ref={setFallbackHeader} className="app-chrome-header workspace-navigation-fallback" />
      {createPortal(<CompactAppNavigation activeRoute={route} primaryActionsRef={primaryActionsRef} />, portalHost)}
      {children}
    </WorkspaceNavigationContext.Provider>
  );
}
