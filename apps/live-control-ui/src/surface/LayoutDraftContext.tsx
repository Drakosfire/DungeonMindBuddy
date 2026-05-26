import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { putSurfaceLayout } from "../api/liveApi";
import type { SurfaceLayout, SurfaceModuleDefinition } from "../api/types";
import { cloneLayout } from "./layoutUtils";

interface LayoutDraftContextValue {
  draft: SurfaceLayout;
  catalogById: Map<string, SurfaceModuleDefinition>;
  saving: boolean;
  error: string | null;
  setDraft: (layout: SurfaceLayout) => void;
  persist: (layout?: SurfaceLayout) => Promise<void>;
}

const LayoutDraftContext = createContext<LayoutDraftContextValue | null>(null);

interface LayoutDraftProviderProps {
  layout: SurfaceLayout;
  catalog: SurfaceModuleDefinition[];
  onLayoutSaved: (layout: SurfaceLayout) => void | Promise<void>;
  children: ReactNode;
}

export function LayoutDraftProvider({
  layout,
  catalog,
  onLayoutSaved,
  children,
}: LayoutDraftProviderProps) {
  const [draft, setDraft] = useState(() => cloneLayout(layout));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(cloneLayout(layout));
  }, [layout]);

  const catalogById = useMemo(
    () => new Map(catalog.map((row) => [row.module_id, row])),
    [catalog],
  );

  const persist = useCallback(
    async (nextLayout?: SurfaceLayout) => {
      const payload = nextLayout ?? draft;
      setSaving(true);
      setError(null);
      try {
        const saved = await putSurfaceLayout(payload);
        setDraft(cloneLayout(saved.layout));
        await onLayoutSaved(saved.layout);
      } catch (saveError) {
        setError(saveError instanceof Error ? saveError.message : "Layout save failed");
      } finally {
        setSaving(false);
      }
    },
    [draft, onLayoutSaved],
  );

  const value = useMemo(
    () => ({
      draft,
      catalogById,
      saving,
      error,
      setDraft,
      persist,
    }),
    [draft, catalogById, saving, error, persist],
  );

  return (
    <LayoutDraftContext.Provider value={value}>{children}</LayoutDraftContext.Provider>
  );
}

export function useLayoutDraft(): LayoutDraftContextValue {
  const context = useContext(LayoutDraftContext);
  if (!context) {
    throw new Error("useLayoutDraft must be used within LayoutDraftProvider");
  }
  return context;
}
