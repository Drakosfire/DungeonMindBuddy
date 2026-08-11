import {
  createContext,
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { SurfaceContextContribution } from "./surfaceContextTypes";

export type SurfaceContextContributions = Record<string, SurfaceContextContribution>;

export interface SurfaceContextStore {
  contributions: SurfaceContextContributions;
  registerContribution: (contribution: SurfaceContextContribution) => () => void;
  updateContribution: (
    id: string,
    patch: Partial<Omit<SurfaceContextContribution, "id">>,
  ) => void;
  unregisterContribution: (id: string) => void;
}

export const SurfaceContextStoreContext = createContext<SurfaceContextStore | null>(null);

interface SurfaceContextProviderProps {
  children: ReactNode;
}

export function SurfaceContextProvider({ children }: SurfaceContextProviderProps) {
  const [contributions, setContributions] = useState<SurfaceContextContributions>({});

  const registerContribution = useCallback((contribution: SurfaceContextContribution) => {
    setContributions((current) => ({
      ...current,
      [contribution.id]: contribution,
    }));
    return () => {
      setContributions((current) => {
        if (!(contribution.id in current)) {
          return current;
        }
        const { [contribution.id]: _removed, ...rest } = current;
        return rest;
      });
    };
  }, []);

  const updateContribution = useCallback(
    (id: string, patch: Partial<Omit<SurfaceContextContribution, "id">>) => {
      setContributions((current) => {
        const existing = current[id];
        if (!existing) {
          return current;
        }

        const nextOrder = patch.order ?? existing.order;
        const nextContent = patch.content ?? existing.content;
        const nextSurfaceIdentity = patch.surfaceIdentity ?? existing.surfaceIdentity;

        if (
          nextOrder === existing.order &&
          nextContent === existing.content &&
          nextSurfaceIdentity.surfaceId === existing.surfaceIdentity.surfaceId &&
          nextSurfaceIdentity.instanceKey === existing.surfaceIdentity.instanceKey
        ) {
          return current;
        }

        return {
          ...current,
          [id]: {
            ...existing,
            order: nextOrder,
            content: nextContent,
            surfaceIdentity: nextSurfaceIdentity,
          },
        };
      });
    },
    [],
  );

  const unregisterContribution = useCallback((id: string) => {
    setContributions((current) => {
      if (!(id in current)) {
        return current;
      }
      const { [id]: _removed, ...rest } = current;
      return rest;
    });
  }, []);

  const value = useMemo<SurfaceContextStore>(
    () => ({
      contributions,
      registerContribution,
      updateContribution,
      unregisterContribution,
    }),
    [contributions, registerContribution, updateContribution, unregisterContribution],
  );

  return (
    <SurfaceContextStoreContext.Provider value={value}>
      {children}
    </SurfaceContextStoreContext.Provider>
  );
}
