import type { GlobalProvider } from "@ladle/react";

import "../src/ui/tokens.css";

export const Provider: GlobalProvider = ({ children }) => (
  <div
    style={{
      minHeight: "100vh",
      padding: "var(--ui-space-6)",
      background: "var(--ui-background-app)",
      color: "var(--ui-text-primary)",
      fontFamily: "var(--ui-font-body)",
    }}
  >
    {children}
  </div>
);
