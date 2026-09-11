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

export interface PeekClaimDescriptor {
  kind: PeekClaimKind;
  label: string;
  onDismiss: () => void;
}

const PEEK_PRIORITY: Record<PeekClaimKind, number> = {
  "world-object": 1,
  tools: 2,
  projection: 3,
};

interface PeekRegionContextValue {
  target: HTMLElement | null;
  winner: PeekClaimDescriptor | null;
  register: (descriptor: PeekClaimDescriptor) => () => void;
  setTarget: (target: HTMLElement | null) => void;
}

const PeekRegionContext = createContext<PeekRegionContextValue | null>(null);

export function PeekRegionProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<HTMLElement | null>(null);
  const [claims, setClaims] = useState<ReadonlyMap<PeekClaimKind, PeekClaimDescriptor>>(
    () => new Map(),
  );

  const register = useCallback((descriptor: PeekClaimDescriptor) => {
    setClaims((current) => {
      const next = new Map(current);
      next.set(descriptor.kind, descriptor);
      return next;
    });
    return () => {
      setClaims((current) => {
        if (current.get(descriptor.kind) !== descriptor) return current;
        const next = new Map(current);
        next.delete(descriptor.kind);
        return next;
      });
    };
  }, []);

  const winner = useMemo(() => {
    let selected: PeekClaimDescriptor | null = null;
    for (const descriptor of claims.values()) {
      if (
        selected === null
        || PEEK_PRIORITY[descriptor.kind] > PEEK_PRIORITY[selected.kind]
      ) {
        selected = descriptor;
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

export function usePeekRegionState() {
  const value = useContext(PeekRegionContext);
  if (!value) throw new Error("Peek region must be used inside PeekRegionProvider");
  return value;
}

export function PeekRegionSlot() {
  const { setTarget, winner } = usePeekRegionState();
  const targetRef = useCallback((node: HTMLElement | null) => setTarget(node), [setTarget]);

  return (
    <aside
      ref={targetRef}
      className="app-peek-region"
      data-testid="app-peek-region"
      data-active-peek={winner?.kind ?? undefined}
      aria-label="Secondary context"
      hidden={winner === null}
    >
      {winner ? (
        <header className="app-peek-region__nav">
          <button type="button" onClick={winner.onDismiss}>
            ← Back
          </button>
          <span>{winner.label}</span>
        </header>
      ) : null}
    </aside>
  );
}

export function PeekClaim({
  kind,
  active,
  label,
  onDismiss,
  children,
}: {
  kind: PeekClaimKind;
  active: boolean;
  label: string;
  onDismiss: () => void;
  children: ReactNode;
}) {
  const region = useContext(PeekRegionContext);
  const register = region?.register;

  useEffect(() => {
    if (!active || !register) return;
    const descriptor = { kind, label, onDismiss };
    return register(descriptor);
  }, [active, kind, label, onDismiss, register]);

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
      hidden={region.winner?.kind !== kind}
      aria-hidden={region.winner?.kind !== kind}
    >
      {children}
    </div>,
    region.target,
  );
}
