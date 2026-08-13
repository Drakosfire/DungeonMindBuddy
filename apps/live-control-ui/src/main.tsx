import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { getAdmittedCampaignWorlds } from "./api/liveApi";
import { setAdmittedCampaignWorldOverlay } from "./worldGraph/admittedCampaignWorldOverlay";
import "./styles.css";

async function bootstrap(): Promise<void> {
  try {
    const admitted = await getAdmittedCampaignWorlds();
    setAdmittedCampaignWorldOverlay(admitted.mappings ?? []);
  } catch (err) {
    console.warn("[admitted-campaign-worlds] overlay unavailable; using defaults only", err);
  }

  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

void bootstrap();
