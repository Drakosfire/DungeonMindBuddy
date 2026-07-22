import { useState } from "react";

import { AppChrome, type AppChromeTools } from "../chrome/AppChrome";
import { BuildIngestToolbar } from "./BuildIngestToolbar";
import { BuildSurfaceShell } from "./BuildSurfaceShell";

export function BuildSurfacePage() {
  const [editorTools, setEditorTools] = useState<AppChromeTools | null>(null);

  return (
    <AppChrome activeRoute="build" editorTools={editorTools} editToolboxLayout="dock">
      <BuildIngestToolbar />
      <BuildSurfaceShell onEditorToolsChange={setEditorTools} />
    </AppChrome>
  );
}
