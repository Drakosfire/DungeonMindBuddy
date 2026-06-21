import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export interface EditCapabilityValue {
  isLocked: boolean;
  toggleLock: () => void;
  canEdit: boolean;
}

const EditCapabilityContext = createContext<EditCapabilityValue | null>(null);

export function EditCapabilityProvider({ children }: { children: ReactNode }) {
  const [isLocked, setIsLocked] = useState(true);

  const toggleLock = useCallback(() => {
    setIsLocked((current) => !current);
  }, []);

  const value = useMemo<EditCapabilityValue>(
    () => ({
      isLocked,
      toggleLock,
      canEdit: !isLocked,
    }),
    [isLocked, toggleLock],
  );

  return <EditCapabilityContext.Provider value={value}>{children}</EditCapabilityContext.Provider>;
}

export function useEditCapability(): EditCapabilityValue {
  const context = useContext(EditCapabilityContext);
  if (!context) {
    throw new Error("useEditCapability must be used within EditCapabilityProvider");
  }
  return context;
}
