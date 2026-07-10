import { useMemo, useState, type CSSProperties } from "react";

import type { AppChromeTools } from "../chrome/AppChrome";
import type { PlanViewProjection } from "../api/types";
import { PlanAgentInteractionBar } from "./components/PlanAgentInteractionBar";
import { PlanNavBar } from "./components/PlanNavBar";
import { PlanSurfaceCanvas } from "./components/PlanSurfaceCanvas";
import { PlanDogfoodPanel } from "./dogfood/PlanDogfoodPanel";
import { dogfoodModeFromLocation } from "./dogfood/planDogfoodState";
import { createPlanSurfaceConfig } from "./config/planSurfaceConfig";
import { EditCapabilityProvider } from "./edit/editCapability";
import { AdaptiveProjectionContainer } from "./projection/AdaptiveProjectionContainer";
import { ProjectionProvider } from "./projection/projectionContext";
import type { PlanSurfaceConfig } from "./types";
import "./planSurface.css";

interface PlanSurfaceShellProps {
  planView: PlanViewProjection;
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
}

function themeStyle(config: PlanSurfaceConfig): CSSProperties {
  return (config.theme.tokens ?? {}) as CSSProperties;
}

export function PlanSurfaceShell({ planView, onEditorToolsChange }: PlanSurfaceShellProps) {
  const config = useMemo(() => createPlanSurfaceConfig(planView), [planView]);
  const [saveStatusLabel, setSaveStatusLabel] = useState("Local draft · not yet saved to Markdown");
  const dogfoodMode = dogfoodModeFromLocation();

  return (
    <EditCapabilityProvider>
      <ProjectionProvider config={config}>
        <div
          className="plan-surface-root"
          data-surface={config.id}
          data-md-theme={config.theme.themeId}
          style={themeStyle(config)}
        >
          <PlanNavBar config={config} saveStatusLabel={saveStatusLabel} />
          {dogfoodMode ? (
            <PlanDogfoodPanel
              sessionDescriptor={config.sessionDescriptor}
              saveStatusLabel={saveStatusLabel}
            />
          ) : null}
          <div className="plan-surface-layout">
            <div className="plan-surface-main">
              <PlanSurfaceCanvas
                sessionDescriptor={config.sessionDescriptor}
                theme={config.theme}
                onEditorToolsChange={onEditorToolsChange}
                onSaveStatusChange={setSaveStatusLabel}
              />
            </div>
            <AdaptiveProjectionContainer config={config} />
          </div>
          <PlanAgentInteractionBar planView={planView} sessionDescriptor={config.sessionDescriptor} />
        </div>
      </ProjectionProvider>
    </EditCapabilityProvider>
  );
}
