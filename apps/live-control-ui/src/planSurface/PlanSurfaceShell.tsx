import { useMemo, useState, type CSSProperties } from "react";

import type { AppChromeTools } from "../chrome/AppChrome";
import type { PlanViewProjection } from "../api/types";
import { PlanAgentInteractionBar } from "./components/PlanAgentInteractionBar";
import { PlanEditBar } from "./components/PlanEditBar";
import { PlanNavBar } from "./components/PlanNavBar";
import { PlanSurfaceCanvas } from "./components/PlanSurfaceCanvas";
import { createPlanSurfaceConfig } from "./config/planSurfaceConfig";
import { EditCapabilityProvider } from "./edit/editCapability";
import { AdaptiveProjectionContainer } from "./projection/AdaptiveProjectionContainer";
import { ProjectionProvider } from "./projection/projectionContext";
import type { PlanSurfaceConfig } from "./types";
import "./planSurface.css";

interface PlanSurfaceShellProps {
  planView: PlanViewProjection;
}

function themeStyle(config: PlanSurfaceConfig): CSSProperties {
  return (config.theme.tokens ?? {}) as CSSProperties;
}

export function PlanSurfaceShell({ planView }: PlanSurfaceShellProps) {
  const config = useMemo(() => createPlanSurfaceConfig(planView), [planView]);
  const [editorTools, setEditorTools] = useState<AppChromeTools | null>(null);

  return (
    <EditCapabilityProvider>
      <ProjectionProvider config={config}>
        <div
          className="plan-surface-root"
          data-surface={config.id}
          data-md-theme={config.theme.themeId}
          style={themeStyle(config)}
        >
          <PlanNavBar config={config} />
          <div className="plan-surface-layout">
            <div className="plan-surface-main">
              <PlanSurfaceCanvas
                canvas={config.canvas}
                sessionDescriptor={config.sessionDescriptor}
                theme={config.theme}
                onEditorToolsChange={setEditorTools}
              />
            </div>
            <AdaptiveProjectionContainer config={config} />
            <PlanEditBar editorTools={editorTools} />
          </div>
          <PlanAgentInteractionBar planView={planView} />
        </div>
      </ProjectionProvider>
    </EditCapabilityProvider>
  );
}
