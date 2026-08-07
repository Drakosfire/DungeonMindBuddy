import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { clearProjectionRequestCache } from "./planSurface/reference/projectionRequestCache";
import { installSurfaceLatencyDogfoodHooks } from "./worldGraph/surfaceLatencyMarks";
import "./styles.css";

// No-op unless VITE_DMB_BENCH_SURFACE / sessionStorage / window flag enables bench mode.
installSurfaceLatencyDogfoodHooks({
  clearProjectionCache: clearProjectionRequestCache,
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
