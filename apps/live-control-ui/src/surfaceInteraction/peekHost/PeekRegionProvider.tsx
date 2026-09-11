import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

export type PeekClaimKind = "world-object" | "tools" | "projection";

const PEEK_PRIORITY: Record<PeekClaimKind, number> = {
  "world-object": 1,
  tools: 2,
  projection: 3,
};

interface PeekRegionContextValue {
  target: HTMLElement | null;
  winner: PeekClaimKind | null;
  register: (kind: PeekClaimKind) => () => void;
  setTarget: (target: HTMLElement | null) => void;
}

const PeekRegionContext = createContext<PeekRegionContextValue | null>(null);

export function PeekRegionProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<HTMLElement | null>(null);
  const [claims, setClaims] = useState<ReadonlySet<PeekClaimKind>>(() => new Set());

  const register = useCallback((kind: PeekClaimKind) => {
    setClaims((current) => {
      if (current.has(kind)) return current;
      const next = new Set(current);
      next.add(kind);
      return next;
    });
    return () => {
      setClaims((current) => {
        if (!current.has(kind)) return current;
        const next = new Set(current);
        next.delete(kind);
        return next;
      });
    };
  }, []);

  const winner = useMemo(() => {
    let selected: PeekClaimKind | null = null;
    for (const kind of claims) {
      if (selected === null || PEEK_PRIORITY[kind] > PEEK_PRIORITY[selected]) {
        selected = kind;
      }
    }
    return selected;
  }, [claims]);

  const value = useMemo(
    () => ({ target, winner, register, setTarget }),
    [register, target, winner],
  );

  return <PeekRegionContext.Provider value={value}>{children}</PeekRegionContext.Provider>;
}

function usePeekRegion() {
  const value = useContext(PeekRegionContext);
  if (!value) throw new Error("Peek region must be used inside PeekRegionProvider");
  return value;
}

export function PeekRegionSlot() {
  const { setTarget, winner } = usePeekRegion();
  const targetRef = useCallback((node: HTMLElement | null) => setTarget(node), [setTarget]);

  return (
    <aside
      ref={targetRef}
      className="app-peek-region"
      data-testid="app-peek-region"
      data-active-peek={winner ?? undefined}
      aria-label="Secondary context"
      hidden={winner === null}
    />
  );
}

export function PeekClaim({
  kind,
  active,
  children,
}: {
  kind: PeekClaimKind;
  active: boolean;
  children: ReactNode;
}) {
  const region = useContext(PeekRegionContext);
  const register = region?.register;

  useEffect(() => {
    if (!active || !register) return;
    return register(kind);
  }, [active, kind, register]);

  if (!active) return null;
  // Component-level tests and isolated stories may render an owner without the
  // app shell. The real App always provides a region; inline fallback preserves
  // the owner's content without inventing a second target.
  if (!region) return <>{children}</>;
  if (!region.target) return null;

  return createPortal(
    <div
      className="app-peek-claim"
      data-peek-claim={kind}
      hidden={region.winner !== kind}
      aria-hidden={region.winner !== kind}
    >
      {children}
    </div>,
    region.target,
  );
}
